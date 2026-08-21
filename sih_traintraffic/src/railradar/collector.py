"""Standalone real-data collection orchestration for the Nexora prototype."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import RailRadarClient
from .collection import (
    BudgetExceededError,
    CollectionConfig,
    CollectionPlan,
    DiscoveredTrain,
    RequestLedger,
    SlidingWindowRateLimiter,
    discover_trains,
    plan_collection,
)
from .config import Settings
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    RailRadarError,
)
from .normalizer import normalize_live_status
from .storage import RawResponseStore


OBSERVATION_COLUMNS = [
    "run_id",
    "raw_file",
    "collection_timestamp",
    "api_timestamp",
    "train_number",
    "train_name",
    "train_type",
    "train_category",
    "journey_date",
    "current_station",
    "current_station_code",
    "previous_station",
    "previous_station_code",
    "next_station",
    "next_station_code",
    "latitude",
    "longitude",
    "speed_kmh",
    "bearing_degrees",
    "segment_progress",
    "delay_minutes",
    "scheduled_arrival",
    "scheduled_departure",
    "actual_arrival",
    "actual_departure",
    "platform",
    "status",
    "source",
    "data_source",
    "is_stale",
    "data_age_seconds",
    "route_distance_km",
    "route_sequence",
    "route_speed_to_next_kmh",
    "route_json",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _json_write(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class ObservationWriter:
    """Append one normalized live observation per CSV row."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=OBSERVATION_COLUMNS, extrasaction="ignore")
        if self.path.stat().st_size == 0:
            self._writer.writeheader()
            self._file.flush()

    def write(self, row: dict[str, Any]) -> None:
        self._writer.writerow({key: "" if value is None else value for key, value in row.items()})
        self._file.flush()

    def close(self) -> None:
        self._file.flush()
        self._file.close()


class RailRadarCollector:
    """Collect real observations with validation, safe rate limiting, and reports."""

    def __init__(
        self,
        *,
        project_root: str | Path,
        settings: Settings,
        config: CollectionConfig,
        corridor: dict[str, str],
    ) -> None:
        self.project_root = Path(project_root)
        self.settings = settings
        self.config = config
        self.corridor = corridor
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        self.run_start = _now()
        self.collection_start: datetime | None = None
        self.collection_end: datetime | None = None
        self.plan: CollectionPlan | None = None
        self.selected: list[DiscoveredTrain] = []
        self.failures: list[dict[str, Any]] = []
        self.observation_count = 0
        self.stale_count = 0
        self.duplicate_count = 0
        self._fingerprints: set[str] = set()
        self.validation_successes = 0
        self.validation_failures = 0
        known_prior = len(list((self.project_root / "data" / "raw").glob("*/*.json")))
        self.config = CollectionConfig(
            **{**config.__dict__, "known_prior_requests": known_prior}
        )
        self.limiter = SlidingWindowRateLimiter(
            max_requests=self.config.max_requests_per_window,
            window_seconds=self.config.window_seconds,
            minimum_spacing_seconds=self.config.minimum_spacing,
        )
        self.ledger = RequestLedger(self.config.safe_budget, self.limiter)
        self.client = RailRadarClient(settings, before_request=self.ledger.before_request)
        self.raw_store = RawResponseStore(self.project_root / "data" / "raw")
        self.csv_writer = ObservationWriter(self.project_root / "data" / "processed" / "live_observations.csv")

    def _call(self, category: str, operation, *args, **kwargs):
        with self.ledger.request_category(category):
            try:
                result = operation(*args, **kwargs)
                self.ledger.record_success()
                return result
            except Exception as error:
                self.ledger.record_failure(error)
                raise

    def _record_failure(self, phase: str, train_number: str | None, error: Exception) -> None:
        self.failures.append(
            {
                "phase": phase,
                "train_number": train_number,
                "error_type": type(error).__name__,
                "status_code": getattr(error, "status_code", None),
                "message": str(error),
                "timestamp": _iso(_now()),
            }
        )

    def _static_document(self, endpoint: str, response: dict[str, Any]) -> dict[str, Any]:
        return {
            "collection_timestamp": _iso(_now()),
            "endpoint": endpoint,
            "http_status": 200,
            "response": response,
        }

    def discover_and_select(self) -> None:
        try:
            station_payload = self._call("station_discovery", self.client.get_station_directory)
            _json_write(
                self.project_root / "data" / "static" / "stations" / f"{self.run_id}_directory.json",
                self._static_document("/v1/lookup/stations", station_payload),
            )
            between_payload = self._call(
                "train_discovery",
                self.client.get_trains_between,
                self.corridor["origin_code"],
                self.corridor["destination_code"],
            )
            _json_write(
                self.project_root / "data" / "static" / "trains" / f"{self.run_id}_between.json",
                self._static_document(
                    f"/v1/trains/between/{self.corridor['origin_code']}/{self.corridor['destination_code']}",
                    between_payload,
                ),
            )
        except (AuthenticationError, ConfigurationError, BudgetExceededError):
            raise
        except Exception as error:
            self._record_failure("discovery", None, error)
            raise

        candidates = discover_trains(between_payload, _now(), self.config.duration_seconds)
        if not candidates:
            raise RuntimeError("No usable trains were returned for the configured corridor")
        self.plan = plan_collection(self.config, len(candidates))
        self.selected = candidates[: self.plan.train_count]
        selected_document = {
            "run_id": self.run_id,
            "selection_timestamp": _iso(_now()),
            "corridor": self.corridor,
            "selected_trains": [train.__dict__ for train in self.selected],
            "plan": self.plan.__dict__,
        }
        _json_write(self.project_root / "data" / "selected_trains.json", selected_document)

    def collect_static_routes(self) -> None:
        for train in self.selected:
            try:
                payload = self._call(
                    "static_data",
                    self.client.get_train_route_geometry,
                    train.number,
                    format="geojson",
                    stops=True,
                )
                _json_write(
                    self.project_root / "data" / "static" / "routes" / f"{self.run_id}_{train.number}.json",
                    self._static_document(f"/v1/trains/{train.number}/route", payload),
                )
            except BudgetExceededError:
                raise
            except Exception as error:
                self._record_failure("static_data", train.number, error)

    def _row_from_payload(
        self,
        train: DiscoveredTrain,
        payload: dict[str, Any],
        collected_at: datetime,
        raw_file: Path,
    ) -> dict[str, Any]:
        status = normalize_live_status(payload)
        api_timestamp = status.timestamp
        api_dt = _parse_timestamp(api_timestamp)
        age = max(0.0, (collected_at - api_dt).total_seconds()) if api_dt else None
        stale = age is not None and age > self.config.stale_threshold_seconds
        current = status.current_station
        previous = status.previous_station
        next_station = status.next_station
        route_items = []
        current_stop = None
        for stop in status.route_stops:
            item = {
                "sequence": stop.sequence,
                "station_code": stop.station_code,
                "station_name": stop.station_name,
                "latitude": stop.latitude,
                "longitude": stop.longitude,
                "scheduled_arrival": stop.scheduled_arrival,
                "scheduled_departure": stop.scheduled_departure,
                "actual_arrival": stop.actual_arrival,
                "actual_departure": stop.actual_departure,
                "delay_arrival_minutes": stop.delay_arrival_minutes,
                "delay_departure_minutes": stop.delay_departure_minutes,
                "status": stop.status,
                "distance_km": stop.distance_km,
                "platform": stop.platform,
            }
            route_items.append(item)
            if current and stop.station_code == current.code:
                current_stop = stop
        latitude = status.latitude if status.latitude is not None else (current_stop.latitude if current_stop else None)
        longitude = status.longitude if status.longitude is not None else (current_stop.longitude if current_stop else None)
        current_name = current.name if current else None
        if current_name is None and current_stop:
            current_name = current_stop.station_name
        fingerprint = hashlib.sha256(
            json.dumps(
                [status.train_number or train.number, api_timestamp, current.code if current else None, status.status],
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        if fingerprint in self._fingerprints:
            self.duplicate_count += 1
        self._fingerprints.add(fingerprint)
        if stale:
            self.stale_count += 1
        self.observation_count += 1
        route_speed = None
        if current_stop:
            raw_current = next(
                (item for item in payload.get("data", {}).get("route", []) if item.get("stationCode") == current_stop.station_code),
                None,
            )
            if isinstance(raw_current, dict):
                route_speed = raw_current.get("speedToNextStationKmph")
        return {
            "run_id": self.run_id,
            "raw_file": str(raw_file.relative_to(self.project_root)),
            "collection_timestamp": _iso(collected_at),
            "api_timestamp": api_timestamp,
            "train_number": status.train_number or train.number,
            "train_name": status.train_name or train.name,
            "train_type": status.train_type or train.train_type,
            "train_category": status.train_category or train.category,
            "journey_date": status.journey_date,
            "current_station": current_name,
            "current_station_code": current.code if current else None,
            "previous_station": previous.name if previous else None,
            "previous_station_code": previous.code if previous else None,
            "next_station": next_station.name if next_station else None,
            "next_station_code": next_station.code if next_station else None,
            "latitude": latitude,
            "longitude": longitude,
            "speed_kmh": status.speed_kmh,
            "bearing_degrees": status.bearing_degrees,
            "segment_progress": status.segment_progress,
            "delay_minutes": status.delay_minutes,
            "scheduled_arrival": status.scheduled_arrival,
            "scheduled_departure": status.scheduled_departure,
            "actual_arrival": status.actual_arrival,
            "actual_departure": status.actual_departure,
            "platform": status.platform,
            "status": status.status,
            "source": status.source,
            "data_source": "REAL",
            "is_stale": stale,
            "data_age_seconds": age,
            "route_distance_km": train.distance_km,
            "route_sequence": current.sequence if current else None,
            "route_speed_to_next_kmh": route_speed,
            "route_json": json.dumps(route_items, ensure_ascii=False, separators=(",", ":")),
        }

    def collect_one(self, train: DiscoveredTrain, phase: str) -> bool:
        collected_at = _now()
        try:
            payload = self._call(
                "live_data",
                self.client.get_live_train_status,
                train.number,
                include_coordinates=True,
            )
            raw_file = self.raw_store.save_run(
                run_id=self.run_id,
                train_number=train.number,
                timestamp=collected_at,
                endpoint=f"/v1/trains/{train.number}/live",
                response=payload,
            )
            row = self._row_from_payload(train, payload, collected_at, raw_file)
            self.csv_writer.write(row)
            if phase == "validation":
                self.validation_successes += 1
            return True
        except (AuthenticationError, ConfigurationError, BudgetExceededError):
            raise
        except Exception as error:
            self._record_failure(phase, train.number, error)
            if phase == "validation":
                self.validation_failures += 1
            return False

    def _metadata(self, end_time: datetime | None = None) -> dict[str, Any]:
        finish = end_time or _now()
        collection_duration = (
            (self.collection_end or finish) - self.collection_start
        ).total_seconds() if self.collection_start else 0.0
        return {
            "run_id": self.run_id,
            "start_time": _iso(self.run_start),
            "end_time": _iso(finish),
            "requested_duration_seconds": self.config.duration_seconds,
            "actual_duration_seconds": collection_duration,
            "corridor": self.corridor,
            "selected_train_count": len(self.selected),
            "selected_train_numbers": [train.number for train in self.selected],
            "polling_interval_seconds": self.plan.polling_interval_seconds if self.plan else None,
            "expected_cycles": self.plan.expected_cycles if self.plan else None,
            "expected_live_requests": self.plan.expected_live_requests if self.plan else None,
            "expected_validation_requests": self.plan.expected_validation_requests if self.plan else None,
            "expected_static_requests": self.plan.expected_static_requests if self.plan else None,
            "expected_total_requests": self.plan.expected_total_requests if self.plan else None,
            "actual_requests": self.ledger.stats.actual_requests,
            "successful_requests": self.ledger.stats.successful_requests,
            "failed_requests": self.ledger.stats.failed_requests,
            "retry_count": self.ledger.stats.retry_count,
            "rate_limit_waits": self.ledger.stats.rate_limit_waits,
            "rate_limit_wait_seconds": self.ledger.stats.rate_limit_wait_seconds,
            "429_count": self.ledger.stats.too_many_requests,
            "stale_observations": self.stale_count,
            "duplicate_observations": self.duplicate_count,
            "total_observations": self.observation_count,
            "validation_successes": self.validation_successes,
            "validation_failures": self.validation_failures,
            "request_counts_by_category": self.ledger.stats.by_category,
            "quota_total": self.config.quota_total,
            "known_prior_requests": self.config.known_prior_requests,
            "safe_request_budget": self.config.safe_budget,
            "remaining_safe_budget": max(0, self.config.safe_budget - self.ledger.stats.actual_requests),
            "failures": self.failures,
        }

    def save_metadata(self) -> Path:
        path = self.project_root / "data" / "runs" / f"{self.run_id}.json"
        _json_write(path, self._metadata())
        return path

    def quality_report(self) -> Path:
        csv_path = self.project_root / "data" / "processed" / "live_observations.csv"
        rows: list[dict[str, str]] = []
        if csv_path.exists():
            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows = [row for row in csv.DictReader(handle) if row.get("run_id") == self.run_id]
        important = [
            "train_number", "api_timestamp", "current_station_code", "latitude", "longitude",
            "speed_kmh", "delay_minutes", "previous_station_code", "next_station_code",
            "segment_progress", "status",
        ]
        missing = {
            column: sum(1 for row in rows if row.get(column, "") in {"", "None", "null"})
            for column in important
        }
        timestamps = [row.get("api_timestamp") or row.get("collection_timestamp") for row in rows]
        timestamps = [value for value in timestamps if value]
        fingerprints = [
            (row.get("train_number"), row.get("api_timestamp"), row.get("current_station_code"), row.get("status"))
            for row in rows
        ]
        report = {
            "run_id": self.run_id,
            "total_observations": len(rows),
            "observations_per_train": {
                train: sum(1 for row in rows if row.get("train_number") == train)
                for train in sorted({row.get("train_number") for row in rows if row.get("train_number")})
            },
            "successful_requests": self.ledger.stats.successful_requests,
            "failed_requests": self.ledger.stats.failed_requests,
            "retry_count": self.ledger.stats.retry_count,
            "429_responses": self.ledger.stats.too_many_requests,
            "missing_values_per_important_field": missing,
            "stale_observations": sum(1 for row in rows if row.get("is_stale") == "True"),
            "duplicate_observations": len(fingerprints) - len(set(fingerprints)),
            "first_timestamp": min(timestamps) if timestamps else None,
            "last_timestamp": max(timestamps) if timestamps else None,
            "actual_duration_seconds": self._metadata().get("actual_duration_seconds"),
            "expected_requests": self.plan.expected_total_requests if self.plan else None,
            "actual_requests": self.ledger.stats.actual_requests,
            "safe_request_budget": self.config.safe_budget,
            "remaining_safe_budget": max(0, self.config.safe_budget - self.ledger.stats.actual_requests),
            "raw_data_directory": str(self.project_root / "data" / "raw"),
            "normalized_dataset": str(csv_path),
            "static_data_directory": str(self.project_root / "data" / "static"),
        }
        path = self.project_root / "data" / "reports" / f"{self.run_id}_quality_report.json"
        _json_write(path, report)
        return path

    def run(self) -> dict[str, Any]:
        try:
            self.discover_and_select()
            assert self.plan is not None
            print("Selected train set:")
            for train in self.selected:
                print(f"  {train.number} — {train.name} ({train.train_type or 'unknown type'})")
            self.collect_static_routes()
            print(
                f"Selected trains: {len(self.selected)}\n"
                f"Polling interval: {self.plan.polling_interval_seconds} seconds\n"
                f"Duration: {self.config.duration_seconds // 60} minutes\n"
                f"Expected live observations: {self.plan.expected_live_requests}\n"
                f"Expected API requests: {self.plan.expected_total_requests}\n"
                f"Safe request budget: {self.plan.safe_budget}"
            )
            print("Validation: collecting one real live observation per selected train")
            for train in self.selected:
                self.collect_one(train, "validation")
                self.save_metadata()
            if self.validation_successes == 0:
                raise RuntimeError("Validation produced no successful live observations; full collection not started")
            print(
                f"Validation successful: {self.validation_successes}/{len(self.selected)} observations; "
                "starting the real mini-collection automatically."
            )
            self.collection_start = _now()
            deadline = self.collection_start.timestamp() + self.config.duration_seconds
            next_cycle = self.collection_start.timestamp()
            cycle = 0
            while time.time() < deadline and cycle < self.plan.expected_cycles:
                cycle += 1
                cycle_started = time.time()
                for train in self.selected:
                    try:
                        self.collect_one(train, "live")
                    except BudgetExceededError:
                        raise
                self.collection_end = _now()
                self.save_metadata()
                next_cycle += self.plan.polling_interval_seconds
                sleep_for = next_cycle - time.time()
                if sleep_for > 0 and time.time() + sleep_for < deadline:
                    print(f"Completed cycle {cycle}; observations={self.observation_count}; next cycle in {sleep_for:.1f}s")
                    time.sleep(sleep_for)
                elif time.time() < deadline:
                    print(f"Completed cycle {cycle}; starting next cycle immediately after request pacing")
                if time.time() >= deadline or cycle >= self.plan.expected_cycles:
                    break
            self.collection_end = _now()
            self.save_metadata()
            report_path = self.quality_report()
            return {"metadata": self._metadata(), "report": str(report_path)}
        except KeyboardInterrupt:
            self.collection_end = _now()
            self.save_metadata()
            report_path = self.quality_report()
            print("Collection interrupted cleanly; partial data and report saved.")
            return {"metadata": self._metadata(), "report": str(report_path), "interrupted": True}
        except Exception:
            self.collection_end = _now()
            self.save_metadata()
            self.quality_report()
            raise
        finally:
            self.csv_writer.close()
