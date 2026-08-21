from railradar.normalizer import (
    normalize_live_status,
    normalize_station_directory,
    normalize_trains_between,
)


def test_station_directory_normalization():
    stations = normalize_station_directory({"success": True, "data": {"CSMT": "Chhatrapati Shivaji Maharaj Terminus"}})
    assert stations[0].code == "CSMT"
    assert stations[0].name.startswith("Chhatrapati")


def test_train_discovery_normalization():
    trains = normalize_trains_between(
        {"success": True, "data": {"trains": [{"train": {"number": "12345", "name": "Demo", "type": "Local"}}]}}
    )
    assert trains == (trains[0],)
    assert trains[0].number == "12345"


def test_live_status_supports_optional_fields_without_inventing_values():
    status = normalize_live_status(
        {
            "success": True,
            "data": {
                "trainNumber": "12345",
                "trainName": "Demo",
                "startDate": "2026-08-21",
                "delayMinutes": 4,
                "currentLocation": {
                    "stationCode": "CSMT",
                    "segmentProgress": 0.4,
                    "speedKmh": 32.5,
                },
                "nextHalt": {"stationCode": "BYR", "stationName": "Byculla"},
                "route": [
                    {
                        "sequence": 1,
                        "stationCode": "CSMT",
                        "stationName": "CSMT",
                        "scheduledDeparture": "2026-08-21T08:00:00+05:30",
                        "platform": "3",
                    }
                ],
            },
            "meta": {"timestamp": "2026-08-21T08:01:00+05:30", "source": "test"},
        }
    )

    assert status.train_number == "12345"
    assert status.current_station.code == "CSMT"
    assert status.next_station.name == "Byculla"
    assert status.speed_kmh == 32.5
    assert status.latitude is None
    assert status.platform == "3"
    assert status.source == "test"
