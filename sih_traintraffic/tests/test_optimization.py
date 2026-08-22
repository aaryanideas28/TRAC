"""Unit tests for the MILP train traffic optimization and platform allocation module."""

from __future__ import annotations

import pandas as pd
import pytest

from railradar.optimization import (
    OptimizationResult,
    ScheduledTrainDispatch,
    StationTrafficOptimizer,
    TrainTrafficRequest,
    recommend_traffic_decisions,
)


def test_empty_train_optimization():
    optimizer = StationTrafficOptimizer(default_platforms=2, min_headway_min=2.0)
    res = optimizer.solve([])
    assert res.status == "optimal"
    assert res.train_count == 0
    assert len(res.schedule) == 0
    assert res.total_delay_penalty == 0.0


def test_single_train_optimization():
    optimizer = StationTrafficOptimizer(default_platforms=2, min_headway_min=2.0)
    train = TrainTrafficRequest(
        train_number="97401",
        train_name="CSMT-Thane Slow",
        arrival_time_min=5.0,
        dwell_time_min=2.0,
    )
    res = optimizer.solve([train])
    assert res.status == "optimal"
    assert res.train_count == 1
    assert len(res.schedule) == 1
    sched = res.schedule[0]
    assert sched.assigned_platform == 1
    assert sched.scheduled_arrival_min == 5.0
    assert sched.scheduled_departure_min == 7.0
    assert sched.station_hold_delay_min == 0.0


def test_platform_exclusivity_and_headway():
    """Verify that trains assigned to the same platform never overlap and maintain minimum headway."""
    optimizer = StationTrafficOptimizer(default_platforms=1, min_headway_min=2.0)
    trains = [
        TrainTrafficRequest(
            train_number="T1",
            train_name="Train 1",
            arrival_time_min=0.0,
            dwell_time_min=3.0,
            priority_weight=1.0,
        ),
        TrainTrafficRequest(
            train_number="T2",
            train_name="Train 2",
            arrival_time_min=1.0,  # Arrives while T1 is dwelling
            dwell_time_min=3.0,
            priority_weight=1.0,
        ),
    ]
    res = optimizer.solve(trains, platforms=1, min_headway_min=2.0)
    assert res.status == "optimal"
    assert len(res.schedule) == 2

    first = res.schedule[0]
    second = res.schedule[1]

    # Second train must start at or after first departure + headway (3.0 + 2.0 = 5.0)
    assert second.scheduled_arrival_min >= first.scheduled_departure_min + 2.0 - 1e-4
    assert second.station_hold_delay_min >= 4.0 - 1e-4


def test_priority_and_risk_ordering():
    """Verify that a high-priority, high-risk train is prioritized over a low-priority local train."""
    optimizer = StationTrafficOptimizer(default_platforms=1, min_headway_min=2.0)
    trains = [
        TrainTrafficRequest(
            train_number="SLOW_1",
            train_name="Slow Local",
            arrival_time_min=0.0,
            dwell_time_min=2.0,
            delay_risk_prob=0.1,
            priority_weight=1.0,
        ),
        TrainTrafficRequest(
            train_number="EXP_1",
            train_name="Superfast Mail",
            arrival_time_min=0.1,  # Almost identical arrival time
            dwell_time_min=2.0,
            delay_risk_prob=0.9,
            priority_weight=3.0,
        ),
    ]
    res = optimizer.solve(trains, platforms=1, min_headway_min=2.0)
    assert res.status == "optimal"
    assert len(res.schedule) == 2

    # The high-priority express train should be dispatched first with minimal hold
    first = res.schedule[0]
    second = res.schedule[1]
    assert first.train_number == "EXP_1"
    assert second.train_number == "SLOW_1"


def test_recommend_traffic_decisions_integration():
    """Verify integration of DataFrame input with ML model pipeline."""
    from railradar.ml_random_forest import build_classifier_pipeline, CATEGORICAL_FEATURES, NUMERICAL_FEATURES

    # Mock fitted pipeline
    pipeline = build_classifier_pipeline(
        categorical_cols=CATEGORICAL_FEATURES,
        numerical_cols=NUMERICAL_FEATURES,
        n_estimators=10,
        max_depth=2,
        random_state=42,
    )

    df_sample = pd.DataFrame([
        {
            "train_number": "97401",
            "train_name": "CSMT-Thane Slow",
            "train_type": "EMU",
            "train_category": "Local",
            "current_station_code": "CSMT",
            "next_station_code": "BY",
            "current_location_status": "at-station",
            "movement_state": "MOVING",
            "latitude": 18.94,
            "longitude": 72.83,
            "segment_progress": 0.5,
            "delay_minutes": 2.0,
            "distance_from_origin_km": 5.0,
            "distance_from_last_station_km": 1.0,
            "route_sequence": 3,
            "previous_delay": 2.0,
            "delay_change_prev": 0.0,
            "time_since_previous_observation_seconds": 60.0,
            "distance_travelled_km": 1.0,
            "station_transition": 0.0,
            "route_position_change": 0.0,
            "estimated_speed_kmh": 45.0,
            "hour": 18,
            "minute": 30,
            "time_of_day_minutes": 1110,
            "day_of_week": 4,
        },
        {
            "train_number": "12809",
            "train_name": "Howrah Mail",
            "train_type": "Superfast Express",
            "train_category": "Express",
            "current_station_code": "DR",
            "next_station_code": "TNA",
            "current_location_status": "departed",
            "movement_state": "MOVING",
            "latitude": 19.01,
            "longitude": 72.84,
            "segment_progress": 0.8,
            "delay_minutes": 15.0,
            "distance_from_origin_km": 15.0,
            "distance_from_last_station_km": 3.0,
            "route_sequence": 8,
            "previous_delay": 12.0,
            "delay_change_prev": 3.0,
            "time_since_previous_observation_seconds": 60.0,
            "distance_travelled_km": 2.0,
            "station_transition": 1.0,
            "route_position_change": 1.0,
            "estimated_speed_kmh": 60.0,
            "hour": 18,
            "minute": 31,
            "time_of_day_minutes": 1111,
            "day_of_week": 4,
        },
    ])

    # Fit pipeline on mock target
    X_train = df_sample.copy()
    y_train = pd.Series([0, 1])
    pipeline.fit(X_train, y_train)

    opt_res = recommend_traffic_decisions(df_sample, pipeline, platforms=2)
    assert opt_res.status == "optimal"
    assert opt_res.train_count == 2
    assert len(opt_res.schedule) == 2
