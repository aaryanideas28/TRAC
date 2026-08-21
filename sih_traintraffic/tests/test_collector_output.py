from datetime import datetime, timedelta, timezone
from pathlib import Path

from railradar.collection import CollectionConfig, DiscoveredTrain
from railradar.collector import OBSERVATION_COLUMNS, ObservationWriter, RailRadarCollector
from railradar.config import Settings


def test_normalized_output_is_append_only_and_has_fixed_columns(tmp_path: Path):
    writer = ObservationWriter(tmp_path / "data" / "live_observations.csv")
    writer.write({"run_id": "run-1", "train_number": "12345", "data_source": "REAL"})
    writer.write({"run_id": "run-1", "train_number": "12346", "data_source": "REAL"})
    writer.close()

    lines = (tmp_path / "data" / "live_observations.csv").read_text().splitlines()
    assert lines[0].split(",") == OBSERVATION_COLUMNS
    assert len(lines) == 3


def test_row_preserves_missing_fields_and_marks_stale_data(tmp_path: Path):
    collector = RailRadarCollector(
        project_root=tmp_path,
        settings=Settings("test-key"),
        config=CollectionConfig(stale_threshold_seconds=60),
        corridor={"name": "central", "origin_code": "CSMT", "destination_code": "TNA"},
    )
    train = DiscoveredTrain(
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
    collected = datetime.now(timezone.utc)
    old = (collected - timedelta(minutes=5)).isoformat()
    raw_file = tmp_path / "data" / "raw" / "run" / "12345" / "obs.json"
    raw_file.parent.mkdir(parents=True)
    raw_file.write_text("{}")
    row = collector._row_from_payload(
        train,
        {
            "success": True,
            "data": {
                "trainNumber": "12345",
                "trainName": "Demo Local",
                "lastUpdatedAt": old,
                "status": "running",
                "currentLocation": {"stationCode": "CSMT", "sequence": 1},
                "nextHalt": {"stationCode": "BYR", "stationName": "Byculla"},
                "route": [{"sequence": 1, "stationCode": "CSMT", "stationName": "CSMT", "lat": 18.94, "lng": 72.84}],
            },
            "meta": {"source": "test"},
        },
        collected,
        raw_file,
    )

    assert row["data_source"] == "REAL"
    assert row["is_stale"] is True
    assert row["latitude"] == 18.94
    assert row["longitude"] == 72.84
    assert row["speed_kmh"] is None
    assert row["next_station_code"] == "BYR"
