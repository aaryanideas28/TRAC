"""Normalize documented RailRadar envelopes into stable internal models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import (
    NormalizedLocation,
    NormalizedRouteGeometry,
    NormalizedStop,
    NormalizedTrainStatus,
    Station,
    StationReference,
    TrainSummary,
)


def _data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("data", payload)
    return value if isinstance(value, Mapping) else {}


def _str(value: Any) -> str | None:
    return None if value is None else str(value)


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _station_reference(value: Any) -> StationReference | None:
    if not isinstance(value, Mapping):
        return None
    if not any(
        value.get(key) is not None
        for key in ("stationCode", "code", "stationName", "name", "sequence", "distance", "distanceKm")
    ):
        return None
    return StationReference(
        code=_str(value.get("stationCode", value.get("code"))),
        name=_str(value.get("stationName", value.get("name"))),
        sequence=_int(value.get("sequence")),
        distance_km=_float(value.get("distance", value.get("distanceKm"))),
    )


def _stop(value: Any) -> NormalizedStop:
    value = value if isinstance(value, Mapping) else {}
    return NormalizedStop(
        sequence=_int(value.get("sequence")),
        station_code=_str(value.get("stationCode", value.get("code"))),
        station_name=_str(value.get("stationName", value.get("name"))),
        latitude=_float(value.get("lat", value.get("latitude"))),
        longitude=_float(value.get("lng", value.get("longitude"))),
        scheduled_arrival=_str(value.get("scheduledArrival")),
        scheduled_departure=_str(value.get("scheduledDeparture")),
        actual_arrival=_str(value.get("actualArrival")),
        actual_departure=_str(value.get("actualDeparture")),
        delay_arrival_minutes=_int(value.get("delayArrival")),
        delay_departure_minutes=_int(value.get("delayDeparture")),
        status=_str(value.get("status")),
        distance_km=_float(value.get("distance")),
        platform=_str(value.get("platform")),
    )


def normalize_station_directory(payload: Mapping[str, Any]) -> tuple[Station, ...]:
    """Normalize the documented flat ``{code: name}`` station map."""

    data = _data(payload)
    if not isinstance(data, Mapping):
        return ()
    return tuple(Station(code=str(code), name=str(name)) for code, name in data.items())


def normalize_trains_between(payload: Mapping[str, Any]) -> tuple[TrainSummary, ...]:
    data = _data(payload)
    trains = data.get("trains", [])
    if not isinstance(trains, list):
        return ()
    normalized: list[TrainSummary] = []
    for item in trains:
        if not isinstance(item, Mapping):
            continue
        train = item.get("train", item)
        if not isinstance(train, Mapping):
            continue
        number = _str(train.get("number", train.get("trainNumber")))
        name = _str(train.get("name", train.get("trainName")))
        if not number or not name:
            continue
        run_days = train.get("runDays", [])
        normalized.append(
            TrainSummary(
                number=number,
                name=name,
                train_type=_str(train.get("type", train.get("category"))),
                run_days=tuple(str(day) for day in run_days) if isinstance(run_days, list) else (),
            )
        )
    return tuple(normalized)


def normalize_live_status(payload: Mapping[str, Any]) -> NormalizedTrainStatus:
    data = _data(payload)
    train = data.get("train", {})
    train = train if isinstance(train, Mapping) else {}
    current = data.get("currentLocation", {})
    current = current if isinstance(current, Mapping) else {}

    route_values = data.get("route", [])
    route_stops = tuple(_stop(item) for item in route_values) if isinstance(route_values, list) else ()
    current_code = _str(current.get("stationCode"))
    current_stop = next(
        (item for item in route_stops if item.station_code == current_code), None
    )

    current_station = _station_reference(current)
    if current_station and current_stop and not current_station.name:
        current_station = StationReference(
            code=current_station.code,
            name=current_stop.station_name,
            sequence=current_station.sequence,
            distance_km=current_station.distance_km,
        )

    meta = payload.get("meta", {})
    meta = meta if isinstance(meta, Mapping) else {}
    location = (
        NormalizedLocation(
            station_code=current_code,
            status=_str(current.get("status")),
            sequence=_int(current.get("sequence")),
            is_actual_position=_bool(current.get("isActualPosition")),
            segment_progress=_float(current.get("segmentProgress")),
            speed_kmh=_float(current.get("speedKmh")),
            bearing_degrees=_float(current.get("bearingDegrees")),
            latitude=_float(current.get("lat", current.get("latitude"))),
            longitude=_float(current.get("lng", current.get("longitude"))),
        )
        if current
        else None
    )

    return NormalizedTrainStatus(
        train_number=_str(data.get("trainNumber", train.get("number"))),
        train_name=_str(data.get("trainName", train.get("name"))),
        train_type=_str(train.get("type")),
        train_category=_str(train.get("category")),
        journey_date=_str(data.get("startDate")),
        status=_str(data.get("status")),
        current_location=location,
        current_station=current_station,
        previous_station=_station_reference(data.get("previousHalt")),
        next_station=_station_reference(data.get("nextHalt")),
        latitude=_float(current.get("lat", current.get("latitude"))),
        longitude=_float(current.get("lng", current.get("longitude"))),
        speed_kmh=_float(current.get("speedKmh")),
        bearing_degrees=_float(current.get("bearingDegrees")),
        segment_progress=_float(current.get("segmentProgress")),
        delay_minutes=_int(data.get("delayMinutes")),
        scheduled_arrival=current_stop.scheduled_arrival if current_stop else None,
        scheduled_departure=current_stop.scheduled_departure if current_stop else None,
        actual_arrival=current_stop.actual_arrival if current_stop else None,
        actual_departure=current_stop.actual_departure if current_stop else None,
        platform=current_stop.platform if current_stop else None,
        timestamp=_str(data.get("lastUpdatedAt", meta.get("timestamp"))),
        source=_str(meta.get("source", "railradar")),
        route_stops=route_stops,
        raw_data=dict(data),
    )


def normalize_route_geometry(payload: Mapping[str, Any]) -> NormalizedRouteGeometry:
    data = _data(payload)
    stops = data.get("stops", [])
    meta = payload.get("meta", {})
    return NormalizedRouteGeometry(
        train_number=_str(data.get("trainNumber")),
        format=_str(data.get("format")),
        geometry=data.get("geojson", data.get("coordinates", data.get("polyline"))),
        stops=tuple(_stop(item) for item in stops) if isinstance(stops, list) else (),
        source=_str(meta.get("source", "railradar")) if isinstance(meta, Mapping) else "railradar",
    )
