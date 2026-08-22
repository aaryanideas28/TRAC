"""Comprehensive unit tests for Master Dataset ML preprocessing, leakage auditing, and integrity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from railradar.ml_preprocessing import (
    CATEGORICAL_FEATURES,
    DERIVED_FEATURES,
    NUMERICAL_FEATURES,
    TEMPORAL_FEATURES,
    build_ml_ready_dataset,
    create_future_target,
    create_sequential_features,
    create_time_features,
    filter_stale_observations,
    generate_feature_spec,
    generate_preprocessing_report,
    generate_split_specification,
    load_dataset,
    perform_leakage_audit,
    run_preprocessing_pipeline,
    sort_chronologically,
)

MASTER_CSV = Path("data/processed/live_observations_master.csv")
ML_DATASET_CSV = Path("data/processed/ml_ready_dataset.csv")


@pytest.fixture
def master_df() -> pd.DataFrame:
    return load_dataset(MASTER_CSV)


# 1. Master CSV loads successfully
def test_1_master_csv_loads(master_df: pd.DataFrame):
    assert len(master_df) == 798
    assert len(master_df.columns) == 65
    assert master_df["train_number"].nunique() == 32
    assert master_df["run_id"].nunique() == 4


# 2. Original master CSV is not modified
def test_2_original_master_csv_not_modified():
    initial_bytes = MASTER_CSV.read_bytes()
    initial_len = len(initial_bytes)
    # Run operations
    df = load_dataset(MASTER_CSV)
    fresh_df, stats = filter_stale_observations(df)
    assert len(df) == 798
    assert len(fresh_df) == 505
    # Verify byte-for-byte identity
    assert len(MASTER_CSV.read_bytes()) == initial_len
    assert MASTER_CSV.read_bytes() == initial_bytes


# 3. No duplicate observation keys
def test_3_no_duplicate_observation_keys(master_df: pd.DataFrame):
    dupes = master_df.duplicated(subset=["run_id", "train_number", "collection_timestamp"]).sum()
    assert dupes == 0, f"Found {dupes} duplicate observation keys in master CSV"


# 4. No stale rows in final ML dataset
def test_4_no_stale_rows_in_final_ml_dataset():
    ml_df = load_dataset(ML_DATASET_CSV)
    assert len(ml_df) == 470
    assert "is_stale" not in ml_df.columns or not ml_df["is_stale"].astype(str).str.lower().isin(["true", "1"]).any()


# 5. Every target row has a valid t+1 observation
def test_5_every_target_row_has_valid_future_observation():
    ml_df = load_dataset(ML_DATASET_CSV)
    assert not ml_df["future_delay"].isnull().any()
    assert not ml_df["target_delay_change"].isnull().any()


# 6. target_delay_change is mathematically correct
def test_6_target_delay_change_math_correctness():
    ml_df = load_dataset(ML_DATASET_CSV)
    expected_change = ml_df["future_delay"] - ml_df["delay_minutes"]
    assert np.allclose(ml_df["target_delay_change"].values, expected_change.values)


# 7. future_delay equals delay(t+1) within the same sequence
def test_7_future_delay_equals_delay_t_plus_1(master_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(master_df)
    sorted_df = sort_chronologically(fresh_df)
    target_df = create_future_target(sorted_df)

    for (r, t), grp in target_df.groupby(["run_id", "train_number"]):
        if len(grp) > 1:
            for i in range(len(grp) - 1):
                cur_row = grp.iloc[i]
                next_row = grp.iloc[i + 1]
                assert cur_row["future_delay"] == next_row["delay_minutes"]


# 8. previous_delay equals delay(t-1) within the same run_id + train_number
def test_8_previous_delay_equals_delay_t_minus_1(master_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(master_df)
    sorted_df = sort_chronologically(fresh_df)
    seq_df = create_sequential_features(sorted_df)

    for (r, t), grp in seq_df.groupby(["run_id", "train_number"]):
        # First observation in each sequence MUST have NaN previous_delay
        first_row = grp.iloc[0]
        assert pd.isna(first_row["previous_delay"])
        if len(grp) > 1:
            for i in range(1, len(grp)):
                prev_row = grp.iloc[i - 1]
                cur_row = grp.iloc[i]
                assert cur_row["previous_delay"] == prev_row["delay_minutes"]


# 9. No cross-run lag leakage
def test_9_no_cross_run_lag_leakage(master_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(master_df)
    sorted_df = sort_chronologically(fresh_df)
    seq_df = create_sequential_features(sorted_df)

    # Verify that sequence starts across distinct run_ids never borrow from previous runs
    for (r, t), grp in seq_df.groupby(["run_id", "train_number"]):
        first_row = grp.iloc[0]
        assert pd.isna(first_row["previous_delay"]), f"Cross-run lag leakage in ({r}, {t})"
        assert pd.isna(first_row["delay_change_prev"]), f"Cross-run lag leakage in ({r}, {t})"
        assert pd.isna(first_row["time_since_previous_observation_seconds"]), f"Cross-run lag leakage in ({r}, {t})"
        assert pd.isna(first_row["distance_travelled_km"]), f"Cross-run lag leakage in ({r}, {t})"


# 10. No cross-train lag leakage
def test_10_no_cross_train_lag_leakage(master_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(master_df)
    sorted_df = sort_chronologically(fresh_df)
    seq_df = create_sequential_features(sorted_df)

    # Verify trains in same run do not borrow from each other
    for (r, t), grp in seq_df.groupby(["run_id", "train_number"]):
        first_row = grp.iloc[0]
        assert pd.isna(first_row["previous_delay"])
        assert bool(first_row["station_transition"]) is False



# 11. Chronological ordering is preserved
def test_11_chronological_ordering_preserved(master_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(master_df)
    sorted_df = sort_chronologically(fresh_df)

    for (r, t), grp in sorted_df.groupby(["run_id", "train_number"]):
        timestamps = pd.to_datetime(grp["collection_timestamp"]).tolist()
        assert timestamps == sorted(timestamps)


# 12. No target column appears in X
def test_12_no_target_column_in_feature_matrix():
    ml_df = load_dataset(ML_DATASET_CSV)
    spec = generate_feature_spec(ml_df)
    feature_list = spec["ordered_feature_list"]

    assert "target_delay_change" not in feature_list
    assert "future_delay" not in feature_list


# 13. No future information appears in X
def test_13_no_future_information_in_feature_matrix():
    ml_df = load_dataset(ML_DATASET_CSV)
    spec = generate_feature_spec(ml_df)
    feature_list = spec["ordered_feature_list"]

    for feat in feature_list:
        assert "future" not in feat.lower()
        assert "next_delay" not in feat.lower()
        assert "t_plus" not in feat.lower()


# 14. Estimated speed uses only historical observations
def test_14_estimated_speed_uses_only_historical_observations(master_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(master_df)
    sorted_df = sort_chronologically(fresh_df)
    seq_df = create_sequential_features(sorted_df)

    for (r, t), grp in seq_df.groupby(["run_id", "train_number"]):
        # First observation must have NaN speed
        assert pd.isna(grp.iloc[0]["estimated_speed_kmh"])
        if len(grp) > 1:
            for i in range(1, len(grp)):
                dt = grp.iloc[i]["time_since_previous_observation_seconds"]
                dx = grp.iloc[i]["distance_travelled_km"]
                speed = grp.iloc[i]["estimated_speed_kmh"]
                if pd.notnull(dt) and pd.notnull(dx) and dt > 0 and dx >= 0:
                    expected_spd = (dx / dt) * 3600.0
                    assert abs(speed - expected_spd) < 1e-4


# 15. Terminal sequence rows are excluded
def test_15_terminal_sequence_rows_excluded(master_df: pd.DataFrame):
    fresh_df, stats = filter_stale_observations(master_df)
    ml_df = load_dataset(ML_DATASET_CSV)

    num_seqs = fresh_df.groupby(["run_id", "train_number"]).ngroups
    assert num_seqs == 35
    # Exactly 1 terminal row per sequence must be dropped
    assert len(ml_df) == len(fresh_df) - num_seqs
    assert len(ml_df) == 470


# 16. Final dataset contains no duplicate keys
def test_16_final_dataset_no_duplicate_keys():
    ml_df = load_dataset(ML_DATASET_CSV)
    dupes = ml_df.duplicated(subset=["run_id", "train_number", "collection_timestamp"]).sum()
    assert dupes == 0


# 17. Feature specification matches actual dataset columns
def test_17_feature_specification_matches_dataset():
    ml_df = load_dataset(ML_DATASET_CSV)
    spec = generate_feature_spec(ml_df)
    spec_cols = set(spec["features"].keys())
    actual_cols = set(ml_df.columns)
    assert spec_cols == actual_cols
    assert spec["total_model_features"] == 25


# 18. Report statistics match generated dataset
def test_18_report_statistics_match_generated_dataset():
    report_file = Path("data/reports/ml_preprocessing_report.json")
    assert report_file.exists()
    rep = json.loads(report_file.read_text(encoding="utf-8"))

    ml_df = load_dataset(ML_DATASET_CSV)
    assert rep["final_ml_row_count"] == len(ml_df)
    assert rep["train_count"] == ml_df["train_number"].nunique()
    assert rep["station_count"] == ml_df["current_station_code"].nunique()
    assert rep["target_statistics"]["min"] == float(ml_df["target_delay_change"].min())
    assert rep["target_statistics"]["max"] == float(ml_df["target_delay_change"].max())
    assert rep["leakage_audit_status"] == "PASSED"
