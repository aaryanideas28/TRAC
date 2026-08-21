from railradar.collection import DiscoveredTrain
from railradar.moving import classify_active, mark_movement, select_spread_active_trains


def _row(**overrides):
    row = {
        "train_number": "12345", "status": "running", "current_location_status": "departed",
        "route_sequence": "2", "distance_from_origin_km": "4.0", "distance_from_last_station_km": "1.0",
        "movement_state": "MOVING", "current_station_code": "BY", "next_station_code": "DR",
        "collection_timestamp": "2026-08-21T00:00:00+00:00", "latitude": "18.95", "longitude": "72.84",
    }
    row.update(overrides)
    return row


def test_not_started_is_never_active():
    active, moved = classify_active(_row(status="not-started", current_location_status="at-station", route_sequence="1", distance_from_origin_km="0", distance_from_last_station_km="0"))
    assert (active, moved) == (False, False)


def test_running_departed_is_verified_active():
    assert classify_active(_row()) == (True, True)


def test_station_transition_and_distance_are_derived_from_sequential_rows():
    rows = mark_movement([
        _row(collection_timestamp="2026-08-21T00:00:00+00:00", current_station_code="BY", route_sequence="2", distance_from_origin_km="4.0"),
        _row(collection_timestamp="2026-08-21T00:01:00+00:00", current_station_code="DR", route_sequence="3", distance_from_origin_km="9.0"),
    ])
    assert rows[1]["station_transition"] is True
    assert rows[1]["route_position_change"] is True
    assert rows[1]["distance_travelled_km"] == 5.0
    assert rows[1]["movement_state"] == "MOVING"


def test_selection_uses_exactly_five_route_spread_active_trains():
    trains = [DiscoveredTrain(str(i), f"Train {i}", "EMU", "Suburban", {}, {}, {}, {}, 1.0, 1, 1) for i in range(10)]
    records = [(train, _row(train_number=train.number, distance_from_origin_km=str(int(train.number)), verification_movement_evidence=True)) for train in trains]
    selected = select_spread_active_trains(records, 5)
    assert len(selected) == 5
    assert [row[1]["distance_from_origin_km"] for row in selected] == ["0", "2", "4", "7", "9"]
