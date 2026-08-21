"""Planning and accounting helpers for a bounded RailRadar collection run."""

from __future__ import annotations

import math
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterator

from .exceptions import RailRadarError


class BudgetExceededError(RailRadarError):
    """Raised before a request would exceed the run's safe request budget."""


@dataclass(frozen=True)
class CollectionConfig:
    duration_seconds: int = 20 * 60
    stale_threshold_seconds: int = 5 * 60
    max_requests_per_window: int = 10
    window_seconds: float = 60.0
    minimum_spacing_seconds: float | None = None
    quota_total: int = 1000
    safety_fraction: float = 0.85
    known_prior_requests: int = 0
    max_trains: int = 10
    candidate_intervals_seconds: tuple[int, ...] = (60, 90, 120, 150)
    candidate_train_counts: tuple[int, ...] = (5, 6, 7, 8, 9, 10)

    @property
    def safe_budget(self) -> int:
        return max(
            0,
            math.floor(self.quota_total * self.safety_fraction) - self.known_prior_requests,
        )

    @property
    def minimum_spacing(self) -> float:
        return self.minimum_spacing_seconds or (
            self.window_seconds / self.max_requests_per_window + 0.1
        )


@dataclass(frozen=True)
class CollectionPlan:
    train_count: int
    polling_interval_seconds: int
    expected_cycles: int
    expected_live_requests: int
    expected_validation_requests: int
    expected_static_requests: int
    expected_total_requests: int
    safe_budget: int


def plan_collection(config: CollectionConfig, available_trains: int) -> CollectionPlan:
    """Choose the highest-observation safe configuration automatically."""

    max_count = min(config.max_trains, available_trains)
    static_requests = 2 + max_count  # station directory, discovery, one route per train
    validation_requests = max_count
    candidates: list[CollectionPlan] = []
    for count in config.candidate_train_counts:
        if count > max_count:
            continue
        for interval in config.candidate_intervals_seconds:
            cycle_seconds = max(interval, math.ceil(count * config.minimum_spacing))
            cycles = max(1, math.ceil(config.duration_seconds / cycle_seconds))
            live = count * cycles
            total = live + count + 2 + count
            if total <= config.safe_budget:
                candidates.append(
                    CollectionPlan(
                        train_count=count,
                        polling_interval_seconds=interval,
                        expected_cycles=cycles,
                        expected_live_requests=live,
                        expected_validation_requests=validation_requests,
                        expected_static_requests=static_requests,
                        expected_total_requests=total,
                        safe_budget=config.safe_budget,
                    )
                )
    if not candidates:
        raise BudgetExceededError("No safe train-count and polling-interval combination exists")
    return max(
        candidates,
        key=lambda item: (
            item.expected_live_requests,
            item.train_count,
            -item.polling_interval_seconds,
        ),
    )


class SlidingWindowRateLimiter:
    """Serialize requests and enforce at most N requests in a rolling window."""

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: float = 60.0,
        minimum_spacing_seconds: float = 6.1,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.minimum_spacing_seconds = minimum_spacing_seconds
        self._sleeper = sleeper
        self._clock = clock
        self._request_times: deque[float] = deque()
        self.wait_count = 0
        self.wait_seconds = 0.0

    def wait_for_slot(self) -> None:
        while True:
            now = self._clock()
            if self._request_times and now - self._request_times[-1] < self.minimum_spacing_seconds - 1e-9:
                delay = self.minimum_spacing_seconds - (now - self._request_times[-1])
            else:
                while self._request_times and now - self._request_times[0] >= self.window_seconds:
                    self._request_times.popleft()
                if len(self._request_times) < self.max_requests:
                    self._request_times.append(now)
                    return
                delay = self.window_seconds - (now - self._request_times[0]) + 0.01
            self.wait_count += 1
            self.wait_seconds += max(delay, 0.0)
            self._sleeper(max(delay, 0.0))


@dataclass
class RequestStats:
    actual_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retry_count: int = 0
    rate_limit_waits: int = 0
    rate_limit_wait_seconds: float = 0.0
    too_many_requests: int = 0
    by_category: dict[str, int] = field(default_factory=dict)


class RequestLedger:
    """Budget-aware callback used by the existing RailRadar client."""

    def __init__(self, budget: int, limiter: SlidingWindowRateLimiter) -> None:
        self.budget = budget
        self.limiter = limiter
        self.stats = RequestStats()
        self.category = "other"

    @contextmanager
    def request_category(self, category: str) -> Iterator[None]:
        previous = self.category
        self.category = category
        try:
            yield
        finally:
            self.category = previous

    def before_request(self, attempt: int) -> None:
        if self.stats.actual_requests >= self.budget:
            raise BudgetExceededError("Safe request budget reached; stopping before another request")
        self.limiter.wait_for_slot()
        self.stats.actual_requests += 1
        self.stats.by_category[self.category] = self.stats.by_category.get(self.category, 0) + 1
        if attempt > 0:
            self.stats.retry_count += 1
        self.stats.rate_limit_waits = self.limiter.wait_count
        self.stats.rate_limit_wait_seconds = self.limiter.wait_seconds

    def record_success(self) -> None:
        self.stats.successful_requests += 1

    def record_failure(self, error: Exception) -> None:
        self.stats.failed_requests += 1
        if getattr(error, "status_code", None) == 429:
            self.stats.too_many_requests += 1


@dataclass(frozen=True)
class DiscoveredTrain:
    number: str
    name: str
    train_type: str | None
    category: str | None
    source: dict
    destination: dict
    from_schedule: dict
    to_schedule: dict
    distance_km: float | None
    duration_minutes: int | None
    total_halts_between: int | None
    selection_score: float = 0.0
    selection_reason: str = ""


def discover_trains(payload: dict, now: datetime, duration_seconds: int) -> list[DiscoveredTrain]:
    """Extract train candidates and score local services near the run window."""

    data = payload.get("data", {})
    result: list[DiscoveredTrain] = []
    current_minutes = now.astimezone().hour * 60 + now.astimezone().minute
    end_minutes = current_minutes + math.ceil(duration_seconds / 60)
    for item in data.get("trains", []) if isinstance(data, dict) else []:
        if not isinstance(item, dict):
            continue
        train = item.get("train") or {}
        if not train.get("number") or not train.get("name"):
            continue
        train_type = str(train.get("type")) if train.get("type") is not None else None
        name = str(train.get("name"))
        from_schedule = item.get("from") or {}
        departure = str(from_schedule.get("departure", ""))
        try:
            hours, minutes = (int(part) for part in departure.split(":", 1))
            departure_minutes = hours * 60 + minutes
        except (ValueError, TypeError):
            departure_minutes = None
        local = bool(
            (train_type and "emu" in train_type.lower())
            or "local" in name.lower()
            or "mumbai" in name.lower() and "express" not in name.lower()
        )
        score = 100.0 if local else 0.0
        if departure_minutes is not None:
            distance = min(abs(departure_minutes - current_minutes), abs(departure_minutes + 1440 - current_minutes))
            if current_minutes <= departure_minutes <= end_minutes:
                score += 80.0
            elif departure_minutes >= current_minutes:
                score += max(0.0, 40.0 - distance / 10.0)
            else:
                score += max(0.0, 20.0 - distance / 10.0)
        reason = "Mumbai suburban/local service"
        if departure_minutes is not None and current_minutes <= departure_minutes <= end_minutes:
            reason += "; scheduled during collection window"
        result.append(
            DiscoveredTrain(
                number=str(train["number"]),
                name=name,
                train_type=train_type,
                category=str(train.get("category")) if train.get("category") is not None else None,
                source=dict(train.get("source") or from_schedule),
                destination=dict(train.get("destination") or item.get("to") or {}),
                from_schedule=dict(from_schedule),
                to_schedule=dict(item.get("to") or {}),
                distance_km=float(item["distance"]) if item.get("distance") is not None else None,
                duration_minutes=int(item["duration"]) if item.get("duration") is not None else None,
                total_halts_between=int(item["totalHaltsBetween"]) if item.get("totalHaltsBetween") is not None else None,
                selection_score=score,
                selection_reason=reason,
            )
        )
    return sorted(result, key=lambda item: (-item.selection_score, item.number))
