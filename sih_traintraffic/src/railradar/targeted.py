"""Targeted moving-train collection and deterministic dataset augmentation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .client import RailRadarClient
from .collection import CollectionConfig, DiscoveredTrain, RequestLedger, SlidingWindowRateLimiter, discover_trains
from .config import Settings
from .exceptions import AuthenticationError, ConfigurationError, RailRadarError
from .storage import RawResponseStore


TARGET_COLUMNS = [
    "run_id", "raw_file", "dataset_source", "collection_timestamp", "api_timestamp",
    "train_number", "train_name", "train_type", "train_category", "journey_date",
    "current_station", "current_station_code", "previous_station", "previous_station_code",
    "next_station", "next_station_code", "latitude", "longitude", "speed_kmh",
    "bearing_degrees", "segment_progress", "delay_minutes", "scheduled_arrival",
    "scheduled_departure", "actual_arrival", "actual_departure", "platform", "status",
    "source", "data_source", "is_stale", "data_age_seconds", "route_distance_km",
    "distance_from_origin_km", "distance_from_last_station_km", "route_sequence",
    "route_speed_to_next_kmh", "route_json", "position_source", "speed_source",
    "previous_station_source", "segment_progress_source", "movement_state",
    "time_of_day_minutes", "time_since_previous_observation_seconds", "previous_delay",
    "delay_change", "delay_change_source", "estimated_speed_kmh", "estimated_speed_source",
    "distance_from_previous_station_km", "station_to_station_travel_time_seconds",
    "travel_time_source", "headway_seconds", "headway_source",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result


def _json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _float(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    try:
        return None if value in (None, "") else int(value)
    except (TypeError, ValueError):
        return None


def _is_true(value: Any) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _load_candidates(root: Path, duration_seconds: int) -> list[DiscoveredTrain]:
    files = sorted((root / "data" / "static" / "trains").glob("*_between.json"))
    if not files:
        raise RuntimeError("No existing static train-discovery snapshot was found")
    document = json.loads(files[-1].read_text(encoding="utf-8"))
    return discover_trains(document.get("response", document), _now(), duration_seconds)


class TargetedCSVWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.open("a", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.handle, fieldnames=TARGET_COLUMNS, extrasaction="ignore")
        if path.stat().st_size == 0:
            self.writer.writeheader()
            self.handle.flush()

    def write(self, row: dict[str, Any]) -> None:
        self.writer.writerow({key: "" if value is None else value for key, value in row.items()})
        self.handle.flush()

    def close(self) -> None:
        self.handle.flush()
        self.handle.close()


def _route_stop(data: dict[str, Any], code: str | None) -> dict[str, Any] | None:
    if not code:
        return None
    for stop in data.get("route", []) or []:
        if isinstance(stop, dict) and stop.get("stationCode") == code:
            return stop
    return None


def live_row(
    *,
    run_id: str,
    train: DiscoveredTrain,
    payload: dict[str, Any],
    collected_at: datetime,
    raw_file: Path,
    stale_threshold_seconds: int,
) -> dict[str, Any]:
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    data = data if isinstance(data, dict) else {}
    current = data.get("currentLocation") or {}
    current = current if isinstance(current, dict) else {}
    next_halt = data.get("nextHalt") or {}
    next_halt = next_halt if isinstance(next_halt, dict) else {}
    current_code = current.get("stationCode")
    current_stop = _route_stop(data, current_code)
    route_sequence = _int(current.get("sequence"))
    previous_stop = None
    if route_sequence is not None:
        for stop in data.get("route", []) or []:
            if isinstance(stop, dict) and _int(stop.get("sequence")) == route_sequence - 1:
                previous_stop = stop
                break
    previous_explicit = data.get("previousHalt") if isinstance(data.get("previousHalt"), dict) else None
    previous = previous_explicit or previous_stop
    previous_source = "API" if previous_explicit else ("DERIVED" if previous_stop else "MISSING")
    coordinates = current.get("coordinates") if isinstance(current.get("coordinates"), dict) else {}
    lat = _float(coordinates.get("lat", current.get("lat")))
    lng = _float(coordinates.get("lng", current.get("lng")))
    position_source = "API" if lat is not None and lng is not None and coordinates else "MISSING"
    if position_source == "MISSING" and current_stop:
        lat = _float(current_stop.get("lat"))
        lng = _float(current_stop.get("lng"))
        position_source = "DERIVED" if lat is not None and lng is not None else "MISSING"
    api_timestamp = data.get("lastUpdatedAt") or (payload.get("meta") or {}).get("timestamp")
    api_dt = _parse(api_timestamp)
    age = max(0.0, (collected_at - api_dt).total_seconds()) if api_dt else None
    stale = age is not None and age > stale_threshold_seconds
    segment = _float(current.get("segmentProgress"))
    segment_source = "API" if segment is not None else "MISSING"
    distance_origin = _float(current.get("distanceFromOriginKm"))
    route_distance = train.distance_km
    if segment is None and distance_origin is not None and route_distance and 0 <= distance_origin <= route_distance:
        segment = distance_origin / route_distance
        segment_source = "DERIVED"
    raw_current = current_stop or {}
    route_speed = _float(raw_current.get("speedToNextStationKmph"))
    status = str(data.get("status")) if data.get("status") is not None else None
    current_status = str(current.get("status")) if current.get("status") is not None else ""
    if status == "running" and (current_status in {"departed", "between-stations"} or _float(current.get("distanceFromLastStationKm")) not in (None, 0.0)):
        movement = "MOVING"
    elif status == "running":
        movement = "AT_STATION"
    elif status == "not-started":
        movement = "NOT_STARTED"
    else:
        movement = status.upper() if status else "UNKNOWN"
    route_items = data.get("route", []) if isinstance(data.get("route", []), list) else []
    return {
        "run_id": run_id,
        "raw_file": str(raw_file),
        "dataset_source": "TARGETED_RUN",
        "collection_timestamp": _iso(collected_at),
        "api_timestamp": api_timestamp,
        "train_number": data.get("trainNumber") or train.number,
        "train_name": data.get("trainName") or train.name,
        "train_type": (data.get("train") or {}).get("type") or train.train_type,
        "train_category": (data.get("train") or {}).get("category") or train.category,
        "journey_date": data.get("startDate"),
        "current_station": current.get("stationName"),
        "current_station_code": current_code,
        "previous_station": (previous or {}).get("stationName") or (previous or {}).get("name"),
        "previous_station_code": (previous or {}).get("stationCode") or (previous or {}).get("code"),
        "next_station": next_halt.get("stationName"),
        "next_station_code": next_halt.get("stationCode"),
        "latitude": lat,
        "longitude": lng,
        "speed_kmh": _float(current.get("speedKmh")),
        "bearing_degrees": _float(current.get("bearingDegrees")),
        "segment_progress": segment,
        "delay_minutes": _int(data.get("delayMinutes", current.get("delayMinutes"))),
        "scheduled_arrival": raw_current.get("scheduledArrival"),
        "scheduled_departure": raw_current.get("scheduledDeparture"),
        "actual_arrival": raw_current.get("actualArrival"),
        "actual_departure": raw_current.get("actualDeparture"),
        "platform": raw_current.get("platform"),
        "status": status,
        "source": (payload.get("meta") or {}).get("source") or data.get("_provider"),
        "data_source": "REAL",
        "is_stale": stale,
        "data_age_seconds": age,
        "route_distance_km": route_distance,
        "distance_from_origin_km": distance_origin,
        "distance_from_last_station_km": _float(current.get("distanceFromLastStationKm")),
        "route_sequence": route_sequence,
        "route_speed_to_next_kmh": route_speed,
        "route_json": json.dumps(route_items, ensure_ascii=False, separators=(",", ":")),
        "position_source": position_source,
        "speed_source": "API" if current.get("speedKmh") is not None else "MISSING",
        "previous_station_source": previous_source,
        "segment_progress_source": segment_source,
        "movement_state": movement,
        "is_stale": stale,
    }


def _enrich(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add deterministic temporal, delay, movement, and travel-time features."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("train_number"))].append(row)
    for group in grouped.values():
        group.sort(key=lambda row: row.get("collection_timestamp") or "")
        previous = None
        for row in group:
            collected = _parse(row.get("collection_timestamp"))
            api_time = _parse(row.get("api_timestamp"))
            if not row.get("data_source"):
                row["data_source"] = "REAL"
            row.setdefault("dataset_source", "ORIGINAL")
            row.setdefault("position_source", "DERIVED" if row.get("latitude") not in (None, "") and row.get("longitude") not in (None, "") else "MISSING")
            row.setdefault("speed_source", "API" if row.get("speed_kmh") not in (None, "") else "MISSING")
            row.setdefault("previous_station_source", "MISSING")
            row.setdefault("segment_progress_source", "API" if row.get("segment_progress") not in (None, "") else "MISSING")
            if row.get("dataset_source") == "ORIGINAL" and row.get("previous_station_code") and row.get("previous_station_source") == "MISSING":
                row["previous_station_source"] = "DERIVED"
            if not row.get("previous_station_code") and row.get("route_sequence") not in (None, ""):
                try:
                    sequence = int(float(row["route_sequence"]))
                    route = json.loads(row.get("route_json") or "[]")
                except (TypeError, ValueError, json.JSONDecodeError):
                    sequence, route = None, []
                if sequence and sequence > 1 and isinstance(route, list):
                    prior_stop = next(
                        (stop for stop in route if isinstance(stop, dict) and _int(stop.get("sequence")) == sequence - 1),
                        None,
                    )
                    if prior_stop:
                        row["previous_station"] = prior_stop.get("station_name") or prior_stop.get("stationName")
                        row["previous_station_code"] = prior_stop.get("station_code") or prior_stop.get("stationCode")
                        row["previous_station_source"] = "DERIVED"
            row["time_of_day_minutes"] = collected.hour * 60 + collected.minute if collected else None
            row["time_since_previous_observation_seconds"] = None
            row["previous_delay"] = None
            row["delay_change"] = None
            row["delay_change_source"] = "MISSING"
            row["estimated_speed_kmh"] = None
            row["estimated_speed_source"] = "MISSING"
            row["distance_from_previous_station_km"] = row.get("distance_from_last_station_km") or None
            row["station_to_station_travel_time_seconds"] = None
            row["travel_time_source"] = "MISSING"
            row["headway_seconds"] = None
            row["headway_source"] = "MISSING"
            if previous and collected:
                prev_time = _parse(previous.get("collection_timestamp"))
                dt = (collected - prev_time).total_seconds() if prev_time else None
                if dt is not None and dt > 0:
                    row["time_since_previous_observation_seconds"] = dt
                    if previous.get("delay_minutes") not in (None, "") and row.get("delay_minutes") not in (None, ""):
                        row["previous_delay"] = previous.get("delay_minutes")
                        row["delay_change"] = _float(row.get("delay_minutes")) - _float(previous.get("delay_minutes"))
                        row["delay_change_source"] = "DERIVED"
                    lat1, lon1 = _float(previous.get("latitude")), _float(previous.get("longitude"))
                    lat2, lon2 = _float(row.get("latitude")), _float(row.get("longitude"))
                    if previous.get("position_source") == "API" and row.get("position_source") == "API" and None not in (lat1, lon1, lat2, lon2):
                        distance = _haversine_km(lat1, lon1, lat2, lon2)
                        speed = distance / dt * 3600
                        if distance >= 0.05 and 0 < speed <= 150:
                            row["estimated_speed_kmh"] = round(speed, 3)
                            row["estimated_speed_source"] = "DERIVED"
                    if previous.get("current_station_code") and row.get("current_station_code") and previous.get("current_station_code") != row.get("current_station_code"):
                        row["station_to_station_travel_time_seconds"] = dt
                        row["travel_time_source"] = "DERIVED"
            if row.get("dataset_source") == "ORIGINAL":
                if row.get("status") != "running":
                    row["movement_state"] = "NOT_STARTED"
                elif row.get("current_station_code") not in (None, "CSMT"):
                    row["movement_state"] = "MOVING"
                elif previous and row.get("current_station_code") != previous.get("current_station_code"):
                    row["movement_state"] = "MOVING"
                else:
                    row["movement_state"] = "AT_STATION"
            else:
                row.setdefault("movement_state", "MOVING" if row.get("status") == "running" else "NOT_STARTED")
            row.setdefault("is_stale", False)
            previous = row
    return rows


def augment_dataset(root: Path, targeted_rows: list[dict[str, Any]], run_id: str) -> tuple[Path, dict[str, Any]]:
    old_path = root / "data" / "processed" / "live_observations.csv"
    with old_path.open(newline="", encoding="utf-8") as handle:
        old_rows = [dict(row) for row in csv.DictReader(handle)]
    for row in old_rows:
        row["dataset_source"] = "ORIGINAL"
        row["raw_file"] = row.get("raw_file", "")
    combined = _enrich(old_rows + targeted_rows)
    output = root / "data" / "processed" / "live_observations_augmented.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TARGET_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in combined:
            writer.writerow({key: "" if row.get(key) is None else row.get(key, "") for key in TARGET_COLUMNS})
    old_count = len(old_rows)
    new_count = len(targeted_rows)
    def _observation_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return tuple(row.get(key) for key in ("train_number", "collection_timestamp", "current_station_code", "status", "delay_minutes"))

    def _state_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return tuple(row.get(key) for key in ("train_number", "current_station_code", "next_station_code", "status", "delay_minutes", "route_sequence"))

    def _timestamp_range(rows: list[dict[str, Any]]) -> tuple[str | None, str | None]:
        timestamps = [row.get("collection_timestamp") for row in rows if row.get("collection_timestamp")]
        return (min(timestamps), max(timestamps)) if timestamps else (None, None)

    old_first, old_last = _timestamp_range(old_rows)
    combined_first, combined_last = _timestamp_range(combined)
    report = {
        "run_id": run_id,
        "old_real_observations": old_count,
        "new_real_observations": new_count,
        "combined_real_observations": len(combined),
        "old_unique_trains": len({row.get("train_number") for row in old_rows}),
        "combined_unique_trains": len({row.get("train_number") for row in combined}),
        "observations_per_train": {
            "old": dict(sorted(Counter(str(row.get("train_number")) for row in old_rows).items())),
            "new": dict(sorted(Counter(str(row.get("train_number")) for row in targeted_rows).items())),
            "combined": dict(sorted(Counter(str(row.get("train_number")) for row in combined).items())),
        },
        "old_unique_stations": len({row.get("current_station_code") for row in old_rows if row.get("current_station_code")}),
        "combined_unique_stations": len({row.get("current_station_code") for row in combined if row.get("current_station_code")}),
        "old_moving_observations": sum(row.get("status") == "running" and row.get("current_station_code") not in {"CSMT", ""} for row in old_rows),
        "combined_moving_observations": sum(row.get("movement_state") == "MOVING" for row in combined),
        "old_not_started_observations": sum(row.get("status") == "not-started" for row in old_rows),
        "combined_not_started_observations": sum(row.get("movement_state") == "NOT_STARTED" for row in combined),
        "duplicate_observations": {
            "old_exact_duplicate_rows": old_count - len({_observation_key(row) for row in old_rows}),
            "combined_exact_duplicate_rows": len(combined) - len({_observation_key(row) for row in combined}),
            "old_repeated_state_rows": old_count - len({_state_key(row) for row in old_rows}),
            "combined_repeated_state_rows": len(combined) - len({_state_key(row) for row in combined}),
        },
        "stale_observations": {
            "old": sum(_is_true(row.get("is_stale")) for row in old_rows),
            "combined": sum(_is_true(row.get("is_stale")) for row in combined),
        },
        "timestamp_range": {
            "old_first": old_first,
            "old_last": old_last,
            "combined_first": combined_first,
            "combined_last": combined_last,
        },
        "delay_distribution": dict(sorted(Counter(str(row.get("delay_minutes")) for row in combined if row.get("delay_minutes") not in (None, "")).items())),
        "derived_field_counts": {
            "estimated_speed_kmh": sum(row.get("estimated_speed_source") == "DERIVED" for row in combined),
            "previous_station": sum(row.get("previous_station_source") == "DERIVED" for row in combined),
            "segment_progress": sum(row.get("segment_progress_source") == "DERIVED" for row in combined),
            "delay_change": sum(row.get("delay_change_source") == "DERIVED" for row in combined),
            "station_to_station_travel_time": sum(row.get("travel_time_source") == "DERIVED" for row in combined),
        },
        "missing_values": {key: sum(row.get(key, "") in (None, "") for row in combined) for key in ("latitude", "longitude", "speed_kmh", "estimated_speed_kmh", "previous_station_code", "segment_progress", "delay_minutes")},
        "dataset_path": str(output),
        "old_dataset_path": str(old_path),
    }
    report_path = root / "data" / "reports" / f"{run_id}_targeted_quality_report.json"
    _json_write(report_path, report)
    return output, report


class TargetedCollector:
    def __init__(self, root: Path, settings: Settings, duration_minutes: int = 20) -> None:
        self.root = root
        self.settings = settings
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-targeted-" + uuid.uuid4().hex[:8]
        self.config = CollectionConfig(duration_seconds=duration_minutes * 60, quota_total=1000, safety_fraction=0.85)
        prior = 0
        for path in (root / "data" / "runs").glob("*.json"):
            try:
                prior += int(json.loads(path.read_text()).get("actual_requests", 0))
            except (ValueError, OSError):
                pass
        prior += len(list((root / "data" / "raw").glob("*/*.json")))
        self.config = CollectionConfig(**{**self.config.__dict__, "known_prior_requests": prior})
        self.limiter = SlidingWindowRateLimiter(minimum_spacing_seconds=self.config.minimum_spacing)
        self.ledger = RequestLedger(self.config.safe_budget, self.limiter)
        self.client = RailRadarClient(settings, before_request=self.ledger.before_request)
        self.raw = RawResponseStore(root / "data" / "raw")
        self.writer = TargetedCSVWriter(root / "data" / "processed" / "live_observations_targeted.csv")
        self.rows: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []
        self.stale = 0
        self.start = _now()
        self.collection_start: datetime | None = None
        self.collection_end: datetime | None = None

    def _call(self, operation, *args, **kwargs):
        with self.ledger.request_category("targeted_live"):
            try:
                result = operation(*args, **kwargs)
                self.ledger.record_success()
                return result
            except Exception as error:
                self.ledger.record_failure(error)
                raise

    def _save_probe(self, train: DiscoveredTrain, payload: dict[str, Any]) -> dict[str, Any]:
        collected = _now()
        raw_file = self.raw.save_run(run_id=self.run_id, train_number=train.number, timestamp=collected, endpoint=f"/v1/trains/{train.number}/live", response=payload)
        row = live_row(run_id=self.run_id, train=train, payload=payload, collected_at=collected, raw_file=raw_file.relative_to(self.root), stale_threshold_seconds=self.config.stale_threshold_seconds)
        self.rows.append(row)
        self.writer.write(row)
        return row

    def run(self) -> dict[str, Any]:
        candidates = _load_candidates(self.root, self.config.duration_seconds)
        probe_candidates = candidates[:20]
        print(f"Probing {len(probe_candidates)} locally discovered candidates for current movement")
        probe_rows = []
        for train in probe_candidates:
            try:
                payload = self._call(self.client.get_live_train_status, train.number, include_coordinates=True)
                probe_rows.append((train, self._save_probe(train, payload), payload))
            except (AuthenticationError, ConfigurationError):
                raise
            except Exception as error:
                self.failures.append({"phase": "probe", "train_number": train.number, "error_type": type(error).__name__, "message": str(error)})
        running = [item for item in probe_rows if item[1].get("status") == "running"]
        running.sort(key=lambda item: (item[1].get("movement_state") != "MOVING", -(item[1].get("distance_from_origin_km") or 0), item[0].number))
        selected = [item[0] for item in running[:5]]
        if not selected:
            self.writer.close()
            output, report = augment_dataset(self.root, self.rows, self.run_id)
            metadata_path = self._save_metadata(selected=[], expected_cycles=0, expected_live_requests=len(probe_candidates))
            report.update({
                "selected_train_numbers": [],
                "selected_train_names": [],
                "api_requests": self.ledger.stats.actual_requests,
                "successful_requests": self.ledger.stats.successful_requests,
                "failed_requests": self.ledger.stats.failed_requests,
                "retry_count": self.ledger.stats.retry_count,
                "429_responses": self.ledger.stats.too_many_requests,
                "stale_observations": sum(_is_true(row.get("is_stale")) for row in self.rows),
                "first_timestamp": min((row.get("api_timestamp") for row in self.rows if row.get("api_timestamp")), default=None),
                "last_timestamp": max((row.get("api_timestamp") for row in self.rows if row.get("api_timestamp")), default=None),
                "failures": self.failures,
                "run_metadata": str(metadata_path),
            })
            _json_write(self.root / "data" / "reports" / f"{self.run_id}_targeted_quality_report.json", report)
            return {"status": "no_running_trains", "report": report, "output": str(output), "metadata": str(metadata_path)}
        print("Selected currently running trains:")
        for train in selected:
            print(f"  {train.number} — {train.name}")
        interval = 60
        cycles = math.ceil(self.config.duration_seconds / interval)
        expected = len(probe_candidates) + len(selected) * cycles
        if expected > self.config.safe_budget:
            interval = 120
            cycles = math.ceil(self.config.duration_seconds / interval)
            expected = len(probe_candidates) + len(selected) * cycles
        self.interval = interval
        print(f"Targeted polling interval: {interval} seconds; duration: {self.config.duration_seconds // 60} minutes; expected requests: {expected}; safe budget: {self.config.safe_budget}")
        self.collection_start = _now()
        deadline = self.collection_start.timestamp() + self.config.duration_seconds
        for cycle in range(cycles):
            if time.time() >= deadline:
                break
            cycle_start = time.time()
            for train in selected:
                try:
                    payload = self._call(self.client.get_live_train_status, train.number, include_coordinates=True)
                    self._save_probe(train, payload)
                except Exception as error:
                    if isinstance(error, (AuthenticationError, ConfigurationError)):
                        raise
                    self.failures.append({"phase": "targeted_live", "train_number": train.number, "error_type": type(error).__name__, "message": str(error)})
            self._save_metadata(selected, cycles, expected)
            remaining = cycle_start + interval - time.time()
            if cycle + 1 < cycles and remaining > 0:
                time.sleep(remaining)
            print(f"Targeted cycle {cycle + 1}/{cycles}; observations={len(self.rows)}")
        self.collection_end = _now()
        self.writer.close()
        output, report = augment_dataset(self.root, self.rows, self.run_id)
        metadata_path = self._save_metadata(selected, cycles, expected)
        report.update({
            "selected_train_numbers": [train.number for train in selected],
            "selected_train_names": [train.name for train in selected],
            "api_requests": self.ledger.stats.actual_requests,
            "successful_requests": self.ledger.stats.successful_requests,
            "failed_requests": self.ledger.stats.failed_requests,
            "retry_count": self.ledger.stats.retry_count,
            "429_responses": self.ledger.stats.too_many_requests,
            "stale_observations": sum(_is_true(row.get("is_stale")) for row in self.rows),
            "first_timestamp": min((row.get("api_timestamp") for row in self.rows if row.get("api_timestamp")), default=None),
            "last_timestamp": max((row.get("api_timestamp") for row in self.rows if row.get("api_timestamp")), default=None),
            "failures": self.failures,
            "run_metadata": str(metadata_path),
        })
        _json_write(self.root / "data" / "reports" / f"{self.run_id}_targeted_quality_report.json", report)
        return {"status": "complete", "output": str(output), "report": report, "metadata": str(metadata_path)}

    def _save_metadata(self, selected: list[DiscoveredTrain], expected_cycles: int, expected_live_requests: int) -> Path:
        end = self.collection_end or _now()
        document = {
            "run_id": self.run_id,
            "start_time": _iso(self.start),
            "end_time": _iso(end),
            "requested_duration_seconds": self.config.duration_seconds,
            "actual_duration_seconds": (end - self.collection_start).total_seconds() if self.collection_start else 0,
            "selected_train_count": len(selected),
            "selected_train_numbers": [train.number for train in selected],
            "polling_interval_seconds": getattr(self, "interval", 60),
            "expected_cycles": expected_cycles,
            "expected_live_requests": expected_live_requests,
            "actual_requests": self.ledger.stats.actual_requests,
            "successful_requests": self.ledger.stats.successful_requests,
            "failed_requests": self.ledger.stats.failed_requests,
            "retry_count": self.ledger.stats.retry_count,
            "rate_limit_waits": self.ledger.stats.rate_limit_waits,
            "429_count": self.ledger.stats.too_many_requests,
            "total_observations": len(self.rows),
            "quota_total": self.config.quota_total,
            "known_prior_requests": self.config.known_prior_requests,
            "safe_request_budget": self.config.safe_budget,
            "remaining_safe_budget": max(0, self.config.safe_budget - self.ledger.stats.actual_requests),
            "failures": self.failures,
        }
        path = self.root / "data" / "runs" / f"{self.run_id}.json"
        _json_write(path, document)
        return path
