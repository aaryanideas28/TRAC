"""Verified-active Central Line collection for movement-focused data."""

from __future__ import annotations

import csv
import json
import math
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .client import RailRadarClient
from .collection import CollectionConfig, DiscoveredTrain, RequestLedger, SlidingWindowRateLimiter, discover_trains
from .config import Settings
from .exceptions import AuthenticationError, ConfigurationError
from .storage import RawResponseStore
from .targeted import TARGET_COLUMNS, _enrich, _float, _haversine_km, _int, _iso, _is_true, _json_write, _now, live_row


MOVING_COLUMNS = TARGET_COLUMNS + [
    "current_location_status", "is_live", "is_halt", "is_actual_position",
    "station_transition", "station_transition_source", "distance_travelled_km",
    "distance_travelled_source", "route_position_change", "route_position_change_source",
]

INACTIVE_STATUSES = {"not-started", "cancelled", "completed", "inactive", "unknown", ""}
CENTRAL_DESTINATION_WORDS = {
    "THANE", "KALYAN", "TITWALA", "BADLAPUR", "AMBERNATH", "KHOPOLI", "KARJAT",
    "DOMBIVLI", "MULUND", "GHATKOPAR", "VIKHROLI", "KURLA", "SION", "BYCULLA",
}


def _safe_request_count(root: Path) -> int:
    metadata_requests = 0
    for path in (root / "data" / "runs").glob("*.json"):
        try:
            metadata_requests += int(json.loads(path.read_text(encoding="utf-8")).get("actual_requests", 0))
        except (OSError, ValueError, TypeError):
            pass
    raw_requests = len(list((root / "data" / "raw").rglob("*.json")))
    return max(metadata_requests, raw_requests)


def _local_candidates(payload: dict[str, Any]) -> list[DiscoveredTrain]:
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return []
    result: list[DiscoveredTrain] = []
    for number, name in data.items():
        if not isinstance(name, str) or not str(number).isdigit():
            continue
        upper = name.upper()
        if "CSMT" not in upper and not any(word in upper for word in CENTRAL_DESTINATION_WORDS):
            continue
        result.append(DiscoveredTrain(
            number=str(number), name=name, train_type="EMU", category="Suburban",
            source={"code": "CSMT", "name": "Chhatrapati Shivaji Maharaj Terminus"},
            destination={"name": name}, from_schedule={}, to_schedule={}, distance_km=None,
            duration_minutes=None, total_halts_between=None, selection_score=50.0,
            selection_reason="Mumbai suburban catalogue candidate; live verification required",
        ))
    return result


def _merge_candidates(*groups: list[DiscoveredTrain]) -> list[DiscoveredTrain]:
    merged: dict[str, DiscoveredTrain] = {}
    for group in groups:
        for train in group:
            current = merged.get(train.number)
            if current is None or train.distance_km is not None or train.selection_score > current.selection_score:
                merged[train.number] = train
    return sorted(merged.values(), key=lambda train: (-train.selection_score, train.number))


def classify_active(row: dict[str, Any]) -> tuple[bool, bool]:
    """Return (eligible active, direct movement evidence) from a live row."""
    status = str(row.get("status") or "").strip().lower()
    if status in INACTIVE_STATUSES:
        return False, False
    current_status = str(row.get("current_location_status") or "").strip().lower()
    sequence = _int(row.get("route_sequence"))
    distance = _float(row.get("distance_from_origin_km"))
    speed = _float(row.get("speed_kmh"))
    moved = (
        row.get("movement_state") == "MOVING"
        or current_status in {"departed", "between-stations"}
        or (speed is not None and speed > 0)
        or (_float(row.get("distance_from_last_station_km")) not in (None, 0.0))
        or (sequence is not None and sequence > 1)
        or (distance is not None and distance > 0)
    )
    return status == "running" and moved, moved


def _add_live_metadata(row: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    data = data if isinstance(data, dict) else {}
    current = data.get("currentLocation", {})
    current = current if isinstance(current, dict) else {}
    row["current_location_status"] = current.get("status")
    row["is_live"] = data.get("isLive")
    row["is_halt"] = current.get("isHalt")
    row["is_actual_position"] = current.get("isActualPosition")
    return row


class MovingCSVWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.handle, fieldnames=MOVING_COLUMNS, extrasaction="ignore")
        self.writer.writeheader()
        self.handle.flush()

    def write(self, row: dict[str, Any]) -> None:
        self.writer.writerow({key: "" if row.get(key) is None else row.get(key, "") for key in MOVING_COLUMNS})
        self.handle.flush()

    def close(self) -> None:
        self.handle.flush()
        self.handle.close()


def mark_movement(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark movement only from state changes between real observations."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("train_number"))].append(row)
    for group in grouped.values():
        group.sort(key=lambda row: row.get("collection_timestamp") or "")
        previous = None
        for row in group:
            row["station_transition"] = False
            row["station_transition_source"] = "MISSING"
            row["distance_travelled_km"] = None
            row["distance_travelled_source"] = "MISSING"
            row["route_position_change"] = False
            row["route_position_change_source"] = "MISSING"
            if previous is not None:
                station_changed = row.get("current_station_code") not in (None, "") and row.get("current_station_code") != previous.get("current_station_code")
                row["station_transition"] = station_changed
                row["station_transition_source"] = "DERIVED"
                d1, d2 = _float(previous.get("distance_from_origin_km")), _float(row.get("distance_from_origin_km"))
                if d1 is not None and d2 is not None:
                    row["distance_travelled_km"] = round(max(0.0, d2 - d1), 3)
                    row["distance_travelled_source"] = "DERIVED"
                s1, s2 = _int(previous.get("route_sequence")), _int(row.get("route_sequence"))
                if s1 is not None and s2 is not None:
                    row["route_position_change"] = s1 != s2
                    row["route_position_change_source"] = "DERIVED"
                lat1, lon1 = _float(previous.get("latitude")), _float(previous.get("longitude"))
                lat2, lon2 = _float(row.get("latitude")), _float(row.get("longitude"))
                if not station_changed and None not in (lat1, lon1, lat2, lon2) and _haversine_km(lat1, lon1, lat2, lon2) >= 0.05:
                    row["movement_state"] = "MOVING"
                elif station_changed or row["route_position_change"] or (row["distance_travelled_km"] or 0) > 0:
                    row["movement_state"] = "MOVING"
                else:
                    row["movement_state"] = "STATIONARY"
            elif row.get("movement_state") not in {"MOVING", "STATIONARY", "UNKNOWN"}:
                row["movement_state"] = "UNKNOWN"
            previous = row
    return rows


def _report_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = ("train_number", "collection_timestamp", "current_station_code", "status", "delay_minutes")
    return {
        "total_observations": len(rows),
        "observations_per_train": dict(sorted(Counter(str(row.get("train_number")) for row in rows).items())),
        "moving_observations": sum(row.get("movement_state") == "MOVING" for row in rows),
        "stationary_observations": sum(row.get("movement_state") == "STATIONARY" for row in rows),
        "unknown_movement_observations": sum(row.get("movement_state") == "UNKNOWN" for row in rows),
        "unique_stations": sorted({row.get("current_station_code") for row in rows if row.get("current_station_code")}),
        "station_transitions": sum(_is_true(row.get("station_transition")) for row in rows),
        "route_position_changes": sum(_is_true(row.get("route_position_change")) for row in rows),
        "delay_distribution": dict(sorted(Counter(str(row.get("delay_minutes")) for row in rows if row.get("delay_minutes") not in (None, "")).items())),
        "missing_values": {key: sum(row.get(key) in (None, "") for row in rows) for key in ("latitude", "longitude", "speed_kmh", "distance_from_origin_km", "distance_from_last_station_km", "delay_minutes", "route_sequence")},
        "duplicate_observations": len(rows) - len({tuple(row.get(key) for key in keys) for row in rows}),
        "stale_observations": sum(_is_true(row.get("is_stale")) for row in rows),
        "first_timestamp": min((row.get("collection_timestamp") for row in rows if row.get("collection_timestamp")), default=None),
        "last_timestamp": max((row.get("collection_timestamp") for row in rows if row.get("collection_timestamp")), default=None),
    }


def select_spread_active_trains(
    records: list[tuple[DiscoveredTrain, dict[str, Any]]],
    count: int = 5,
) -> list[tuple[DiscoveredTrain, dict[str, Any]]]:
    """Choose a fixed number of active trains spread across route progress."""
    if len(records) <= count:
        return records[:]
    preferred = [item for item in records if item[1].get("verification_movement_evidence")]
    pool = preferred if len(preferred) >= count else records
    ordered = sorted(
        pool,
        key=lambda item: (
            _float(item[1].get("distance_from_origin_km")) is None,
            _float(item[1].get("distance_from_origin_km")) or 0,
            item[0].number,
        ),
    )
    indices = [round(index * (len(ordered) - 1) / (count - 1)) for index in range(count)]
    return [ordered[index] for index in indices]


class MovingCollector:
    def __init__(self, root: Path, settings: Settings, duration_minutes: int = 20) -> None:
        self.root = root
        self.settings = settings
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-moving-" + uuid.uuid4().hex[:8]
        prior = _safe_request_count(root)
        self.config = CollectionConfig(duration_seconds=duration_minutes * 60, quota_total=1000, safety_fraction=0.85, known_prior_requests=prior, max_trains=10)
        self.limiter = SlidingWindowRateLimiter(minimum_spacing_seconds=self.config.minimum_spacing)
        self.ledger = RequestLedger(self.config.safe_budget, self.limiter)
        self.client = RailRadarClient(settings, before_request=self.ledger.before_request)
        self.raw = RawResponseStore(root / "data" / "raw")
        default_output = root / "data" / "processed" / "live_observations_moving.csv"
        self.output = default_output if not default_output.exists() else root / "data" / "processed" / f"live_observations_moving_{self.run_id}.csv"
        self.writer = MovingCSVWriter(self.output)
        self.rows: list[dict[str, Any]] = []
        self.probe_rows: list[dict[str, Any]] = []
        self.candidate_trains: list[DiscoveredTrain] = []
        self.verified_active_trains: list[DiscoveredTrain] = []
        self.active_trains: list[DiscoveredTrain] = []
        self.failures: list[dict[str, Any]] = []
        self.start = _now()
        self.collection_start: datetime | None = None
        self.collection_end: datetime | None = None

    def _call(self, category: str, operation: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> dict[str, Any]:
        with self.ledger.request_category(category):
            try:
                result = operation(*args, **kwargs)
                self.ledger.record_success()
                return result
            except Exception as error:
                self.ledger.record_failure(error)
                raise

    def _save_raw(self, label: str, endpoint: str, payload: dict[str, Any], collected_at: datetime) -> Path:
        return self.raw.save_run(run_id=self.run_id, train_number=label, timestamp=collected_at, endpoint=endpoint, response=payload)

    def _make_row(self, train: DiscoveredTrain, payload: dict[str, Any], *, write: bool) -> dict[str, Any]:
        collected = _now()
        raw_file = self._save_raw(train.number, f"/v1/trains/{train.number}/live", payload, collected)
        row = live_row(run_id=self.run_id, train=train, payload=payload, collected_at=collected, raw_file=raw_file.relative_to(self.root), stale_threshold_seconds=self.config.stale_threshold_seconds)
        _add_live_metadata(row, payload)
        if write:
            self.rows.append(row)
            self.writer.write(row)
        return row

    def _discover(self) -> list[DiscoveredTrain]:
        static_files = sorted((self.root / "data" / "static" / "trains").glob("*_between.json"))
        static_candidates: list[DiscoveredTrain] = []
        if static_files:
            document = json.loads(static_files[-1].read_text(encoding="utf-8"))
            static_candidates = discover_trains(document.get("response", document), _now(), self.config.duration_seconds)
        groups = [static_candidates]
        try:
            local = self._call("discovery", self.client.get_local_trains, "Mumbai")
            self._save_raw("discovery_local_mumbai", "/v1/lookup/trains/local?city=Mumbai", local, _now())
            groups.append(_local_candidates(local))
        except (AuthenticationError, ConfigurationError):
            raise
        except Exception as error:
            self.failures.append({"phase": "local_discovery", "error_type": type(error).__name__, "message": str(error)})
        try:
            between = self._call("discovery", self.client.get_trains_between, "CSMT", "TNA", live=True)
            self._save_raw("discovery_between_csmt_tna", "/v1/trains/between/CSMT/TNA?live=true", between, _now())
            groups.append(discover_trains(between.get("response", between), _now(), self.config.duration_seconds))
        except (AuthenticationError, ConfigurationError):
            raise
        except Exception as error:
            self.failures.append({"phase": "between_discovery", "error_type": type(error).__name__, "message": str(error)})
        return _merge_candidates(*groups)

    def _save_metadata(self, interval: int, cycles: int, expected: int) -> Path:
        end = self.collection_end or _now()
        document = {
            "run_id": self.run_id, "start_time": _iso(self.start), "end_time": _iso(end),
            "requested_duration_seconds": self.config.duration_seconds,
            "actual_duration_seconds": (end - self.collection_start).total_seconds() if self.collection_start else 0,
            "candidate_pool_size": len(self.candidate_trains), "candidate_trains_checked": len(self.probe_rows),
            "active_trains_found": len(self.verified_active_trains), "selected_active_train_count": len(self.active_trains),
            "selected_train_numbers": [train.number for train in self.active_trains],
            "polling_interval_seconds": interval, "expected_cycles": cycles, "expected_requests": expected,
            "actual_requests": self.ledger.stats.actual_requests, "successful_requests": self.ledger.stats.successful_requests,
            "failed_requests": self.ledger.stats.failed_requests, "retry_count": self.ledger.stats.retry_count,
            "rate_limit_waits": self.ledger.stats.rate_limit_waits, "429_count": self.ledger.stats.too_many_requests,
            "total_observations": len(self.rows), "quota_total": self.config.quota_total,
            "known_prior_requests": self.config.known_prior_requests, "safe_request_budget": self.config.safe_budget,
            "remaining_safe_budget": max(0, self.config.safe_budget - self.ledger.stats.actual_requests), "failures": self.failures,
        }
        path = self.root / "data" / "runs" / f"{self.run_id}.json"
        _json_write(path, document)
        return path

    def run(self) -> dict[str, Any]:
        self.candidate_trains = self._discover()
        probe_limit = min(50, len(self.candidate_trains))
        print(f"Live-checking {probe_limit} candidates; safe budget: {self.config.safe_budget}")
        probe_records: list[tuple[DiscoveredTrain, dict[str, Any]]] = []
        for train in self.candidate_trains[:probe_limit]:
            try:
                payload = self._call("active_verification", self.client.get_live_train_status, train.number, include_coordinates=True, authoritative=True)
                row = self._make_row(train, payload, write=False)
                active, moved = classify_active(row)
                row["verification_active"] = active
                row["verification_movement_evidence"] = moved
                probe_records.append((train, row))
                self.probe_rows.append(row)
            except (AuthenticationError, ConfigurationError):
                raise
            except Exception as error:
                self.failures.append({"phase": "active_verification", "train_number": train.number, "error_type": type(error).__name__, "message": str(error)})
        active_records = [(train, row) for train, row in probe_records if row.get("verification_active")]
        active_records.sort(key=lambda item: (not item[1].get("verification_movement_evidence"), -(_float(item[1].get("distance_from_origin_km")) or 0), item[0].number))
        selected_records = select_spread_active_trains(active_records, 5)
        self.verified_active_trains = [train for train, _ in active_records]
        self.active_trains = [train for train, _ in selected_records]
        if len(self.active_trains) < 5:
            self.writer.close()
            report = _report_for_rows([])
            report.update({
                "run_id": self.run_id, "candidate_pool_size": len(self.candidate_trains),
                "candidate_trains_checked": len(probe_records), "active_trains_found": len(self.verified_active_trains),
                "selected_active_train_count": len(self.active_trains),
                "selected_train_numbers": [], "verification_statuses": dict(Counter(str(row.get("status")) for row in self.probe_rows)),
                "api_requests": self.ledger.stats.actual_requests, "successful_requests": self.ledger.stats.successful_requests,
                "failed_requests": self.ledger.stats.failed_requests, "retry_count": self.ledger.stats.retry_count,
                "429_responses": self.ledger.stats.too_many_requests, "failures": self.failures,
                "remaining_safe_budget": max(0, self.config.safe_budget - self.ledger.stats.actual_requests), "output_path": str(self.output),
            })
            metadata = self._save_metadata(0, 0, self.ledger.stats.actual_requests)
            report["run_metadata"] = str(metadata)
            report_path = self.root / "data" / "reports" / f"{self.run_id}_moving_quality_report.json"
            _json_write(report_path, report)
            return {"status": "insufficient_active_trains", "output": str(self.output), "report": report, "metadata": str(metadata)}
        for train, row in selected_records:
            self.rows.append(row)
            self.writer.write(row)
        interval = 60
        cycles = math.ceil(self.config.duration_seconds / interval)
        expected = len(self.active_trains) * cycles + self.ledger.stats.actual_requests
        if expected > self.config.safe_budget:
            interval = 120
            cycles = math.ceil(self.config.duration_seconds / interval)
            expected = len(self.active_trains) * cycles + self.ledger.stats.actual_requests
        if expected > self.config.safe_budget:
            self.writer.close()
            raise RuntimeError("Safe request budget cannot support the verified active-train collection")
        self.collection_start = _now()
        deadline = self.collection_start.timestamp() + self.config.duration_seconds
        print(f"Tracking {len(self.active_trains)} verified active trains for {self.config.duration_seconds // 60} minutes at {interval}s")
        for cycle in range(cycles):
            if time.time() >= deadline:
                break
            cycle_start = time.time()
            for train in self.active_trains:
                try:
                    payload = self._call("moving_collection", self.client.get_live_train_status, train.number, include_coordinates=True, authoritative=True)
                    self._make_row(train, payload, write=True)
                except Exception as error:
                    if isinstance(error, (AuthenticationError, ConfigurationError)):
                        raise
                    self.failures.append({"phase": "moving_collection", "train_number": train.number, "error_type": type(error).__name__, "message": str(error)})
            self._save_metadata(interval, cycles, expected)
            remaining = cycle_start + interval - time.time()
            if cycle + 1 < cycles and remaining > 0:
                time.sleep(remaining)
            print(f"Moving cycle {cycle + 1}/{cycles}; observations={len(self.rows)}")
        self.collection_end = _now()
        self.writer.close()
        marked = mark_movement(self.rows)
        enriched = _enrich(marked)
        with self.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MOVING_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for row in enriched:
                writer.writerow({key: "" if row.get(key) is None else row.get(key, "") for key in MOVING_COLUMNS})
        report = _report_for_rows(enriched)
        report.update({
            "run_id": self.run_id, "candidate_pool_size": len(self.candidate_trains),
            "candidate_trains_checked": len(probe_records), "active_trains_found": len(self.verified_active_trains),
            "selected_active_train_count": len(self.active_trains),
            "selected_train_numbers": [train.number for train in self.active_trains],
            "initial_current_stations": {row.get("train_number"): row.get("current_station_code") for _, row in selected_records},
            "api_requests": self.ledger.stats.actual_requests, "successful_requests": self.ledger.stats.successful_requests,
            "failed_requests": self.ledger.stats.failed_requests, "retry_count": self.ledger.stats.retry_count,
            "429_responses": self.ledger.stats.too_many_requests, "rate_limit_waits": self.ledger.stats.rate_limit_waits,
            "failures": self.failures, "output_path": str(self.output),
            "previous_dataset": str(self.root / "data" / "processed" / "live_observations_augmented.csv"),
        })
        metadata = self._save_metadata(interval, cycles, expected)
        report["run_metadata"] = str(metadata)
        report_path = self.root / "data" / "reports" / f"{self.run_id}_moving_quality_report.json"
        _json_write(report_path, report)
        return {"status": "complete", "output": str(self.output), "report": report, "metadata": str(metadata)}
