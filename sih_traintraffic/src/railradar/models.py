"""Internal models that keep application code independent of raw RailRadar JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Corridor:
    """A configurable origin-to-destination prototype corridor."""

    name: str
    origin_code: str
    destination_code: str


@dataclass(frozen=True)
class Station:
    code: str
    name: str


@dataclass(frozen=True)
class TrainSummary:
    number: str
    name: str
    train_type: str | None = None
    run_days: tuple[str, ...] = ()


@dataclass(frozen=True)
class StationReference:
    code: str | None = None
    name: str | None = None
    sequence: int | None = None
    distance_km: float | None = None


@dataclass(frozen=True)
class NormalizedLocation:
    station_code: str | None = None
    status: str | None = None
    sequence: int | None = None
    is_actual_position: bool | None = None
    segment_progress: float | None = None
    speed_kmh: float | None = None
    bearing_degrees: float | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class NormalizedStop:
    sequence: int | None = None
    station_code: str | None = None
    station_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    scheduled_arrival: str | None = None
    scheduled_departure: str | None = None
    actual_arrival: str | None = None
    actual_departure: str | None = None
    delay_arrival_minutes: int | None = None
    delay_departure_minutes: int | None = None
    status: str | None = None
    distance_km: float | None = None
    platform: str | None = None


@dataclass(frozen=True)
class NormalizedTrainStatus:
    train_number: str | None = None
    train_name: str | None = None
    train_type: str | None = None
    train_category: str | None = None
    journey_date: str | None = None
    status: str | None = None
    current_location: NormalizedLocation | None = None
    current_station: StationReference | None = None
    previous_station: StationReference | None = None
    next_station: StationReference | None = None
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float | None = None
    bearing_degrees: float | None = None
    segment_progress: float | None = None
    delay_minutes: int | None = None
    scheduled_arrival: str | None = None
    scheduled_departure: str | None = None
    actual_arrival: str | None = None
    actual_departure: str | None = None
    platform: str | None = None
    timestamp: str | None = None
    source: str | None = None
    route_stops: tuple[NormalizedStop, ...] = ()
    raw_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class NormalizedRouteGeometry:
    train_number: str | None = None
    format: str | None = None
    geometry: Any = None
    stops: tuple[NormalizedStop, ...] = ()
    source: str | None = None
