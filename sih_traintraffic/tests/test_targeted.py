from datetime import datetime, timezone
from pathlib import Path

from railradar.collection import DiscoveredTrain
from railradar.targeted import _enrich, live_row


def _train():
    return DiscoveredTrain(
        number="12345",
        name="Demo Local",
        train_type="EMU",
        category=None,
        source={"code": "CSMT"},
        destination={"code": "TNA"},
        from_schedule={},
        to_schedule={},
        distance_km=33.3,
        duration_minutes=54,
        total_halts_between=17,
    )


def _payload(timestamp, station, sequence, distance, lat, lng, delay=0):
    return {
        "success": True,
        "data": {
            "trainNumber": "12345",
            "trainName": "Demo Local",
            "startDate": "2026-08-21",
            "lastUpdatedAt": timestamp,
            "status": "running",
            "delayMinutes": delay,
            "currentLocation": {
                "stationCode": station,
                "stationName": station,
                "sequence": sequence,
                "status": "departed",
                "coordinates": {"lat": lat, "lng": lng},
                "distanceFromOriginKm": distance,
                "distanceFromLastStationKm": 1.2,
            },
            "nextHalt": {"stationCode": "BYR", "stationName": "Byculla", "sequence": sequence + 1},
            "route": [
                {"sequence": 1, "stationCode": "CSMT", "stationName": "CSMT", "lat": 18.94, "lng": 72.83, "scheduledDeparture": timestamp},
                {"sequence": 2, "stationCode": "BYR", "stationName": "Byculla", "lat": 18.95, "lng": 72.84},
            ],
        },
        "meta": {"timestamp": timestamp, "source": "test"},
    }


def test_live_row_preserves_api_coordinates_and_derives_route_context(tmp_path: Path):
    timestamp = "2026-08-21T20:30:00+05:30"
    raw = tmp_path / "raw.json"
    raw.write_text("{}")
    row = live_row(
        run_id="run",
        train=_train(),
        payload=_payload(timestamp, "BYR", 2, 4.0, 18.95, 72.84),
        collected_at=datetime(2026, 8, 21, 15, 0, tzinfo=timezone.utc),
        raw_file=raw,
        stale_threshold_seconds=600,
    )

    assert row["data_source"] == "REAL"
    assert row["position_source"] == "API"
    assert row["latitude"] == 18.95
    assert row["previous_station_code"] == "CSMT"
    assert row["previous_station_source"] == "DERIVED"
    assert row["segment_progress_source"] == "DERIVED"
    assert row["movement_state"] == "MOVING"


def test_enrich_derives_speed_and_delay_change_without_fabrication():
    rows = [
        {
            "dataset_source": "TARGETED_RUN", "train_number": "1", "collection_timestamp": "2026-08-21T00:00:00+00:00",
            "api_timestamp": "2026-08-21T00:00:00+00:00", "latitude": 18.940, "longitude": 72.830,
            "delay_minutes": "0", "current_station_code": "CSMT", "status": "running", "data_source": "REAL",
            "segment_progress": "0.1", "position_source": "API", "speed_source": "MISSING", "previous_station_source": "MISSING", "segment_progress_source": "API", "is_stale": False,
        },
        {
            "dataset_source": "TARGETED_RUN", "train_number": "1", "collection_timestamp": "2026-08-21T00:01:00+00:00",
            "api_timestamp": "2026-08-21T00:01:00+00:00", "latitude": 18.950, "longitude": 72.840,
            "delay_minutes": "2", "current_station_code": "BYR", "status": "running", "data_source": "REAL",
            "segment_progress": "0.2", "position_source": "API", "speed_source": "MISSING", "previous_station_source": "MISSING", "segment_progress_source": "API", "is_stale": False,
        },
    ]

    enriched = _enrich(rows)

    assert enriched[1]["estimated_speed_source"] == "DERIVED"
    assert enriched[1]["estimated_speed_kmh"] is not None
    assert enriched[1]["delay_change"] == 2.0
    assert enriched[1]["delay_change_source"] == "DERIVED"
    assert enriched[1]["station_to_station_travel_time_seconds"] == 60.0
