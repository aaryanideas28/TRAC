"""Unit tests for ML preprocessing pipeline and data integrity."""

from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
import pytest

from railradar.ml_preprocessing import (
    build_ml_ready_dataset,
    create_future_target,
    create_sequential_features,
    create_time_features,
    filter_stale_observations,
    generate_feature_spec,
    load_dataset,
    run_preprocessing_pipeline,
    sort_chronologically,
)

ORIGINAL_CSV = Path("data/processed/live_observations_moving_20260821T162310Z-moving-625795fa.csv")


@pytest.fixture
def raw_df() -> pd.DataFrame:
    return load_dataset(ORIGINAL_CSV)


def test_stale_filtering(raw_df: pd.DataFrame):
    fresh_df, stats = filter_stale_observations(raw_df)
    assert stats["original_rows"] == 101
    assert stats["stale_rows"] == 19
    assert stats["fresh_rows"] == 82
    assert len(fresh_df) == 82
    assert not fresh_df["is_stale"].astype(str).str.lower().isin(["true", "1"]).any()


def test_timestamp_sorting(raw_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(raw_df)
    sorted_df = sort_chronologically(fresh_df)

    for train_num, grp in sorted_df.groupby("train_number"):
        timestamps = grp["collection_dt"].tolist()
        assert timestamps == sorted(timestamps), f"Train {train_num} timestamps are not in chronological order"


def test_group_wise_previous_delay(raw_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(raw_df)
    sorted_df = sort_chronologically(fresh_df)
    seq_df = create_sequential_features(sorted_df)

    for train_num, grp in seq_df.groupby("train_number"):
        first_idx = grp.index[0]
        assert pd.isna(seq_df.loc[first_idx, "previous_delay"]), "First observation of a train must have NaN previous_delay"
        if len(grp) > 1:
            second_idx = grp.index[1]
            assert seq_df.loc[second_idx, "previous_delay"] == grp.loc[first_idx, "delay_minutes"]


def test_group_wise_future_delay(raw_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(raw_df)
    sorted_df = sort_chronologically(fresh_df)
    target_df = create_future_target(sorted_df)

    for train_num, grp in target_df.groupby("train_number"):
        last_idx = grp.index[-1]
        assert pd.isna(target_df.loc[last_idx, "future_delay"]), "Last observation of a train must have NaN future_delay"
        assert pd.isna(target_df.loc[last_idx, "target_delay_change"]), "Last observation of a train must have NaN target_delay_change"

        if len(grp) > 1:
            first_idx = grp.index[0]
            second_idx = grp.index[1]
            assert target_df.loc[first_idx, "future_delay"] == grp.loc[second_idx, "delay_minutes"]
            assert target_df.loc[first_idx, "target_delay_change"] == (grp.loc[second_idx, "delay_minutes"] - grp.loc[first_idx, "delay_minutes"])


def test_leakage_prevention(raw_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(raw_df)
    sorted_df = sort_chronologically(fresh_df)
    seq_df = create_sequential_features(sorted_df)
    time_df = create_time_features(seq_df)
    target_df = create_future_target(time_df)
    ml_df = build_ml_ready_dataset(target_df)

    spec = generate_feature_spec(ml_df)
    cols_spec = spec["columns"]

    assert cols_spec["target_delay_change"]["use_as_feature"] is False
    assert cols_spec["future_delay"]["use_as_feature"] is False
    assert "target_delay_change" not in [c for c, meta in cols_spec.items() if meta["use_as_feature"]]


def test_train_boundary_isolation(raw_df: pd.DataFrame):
    fresh_df, _ = filter_stale_observations(raw_df)
    sorted_df = sort_chronologically(fresh_df)
    seq_df = create_sequential_features(sorted_df)
    target_df = create_future_target(seq_df)

    # Check that shift doesn't cross train boundaries
    trains = target_df["train_number"].unique()
    assert len(trains) == 5

    for t in trains:
        t_rows = target_df[target_df["train_number"] == t]
        # Target for last row must be NaN
        assert pd.isna(t_rows.iloc[-1]["target_delay_change"])


def test_pipeline_execution(tmp_path: Path):
    out_csv = tmp_path / "ml_ready_dataset.csv"
    out_spec = tmp_path / "ml_feature_spec.json"
    out_report = tmp_path / "ml_preprocessing_report.json"

    ml_df, report = run_preprocessing_pipeline(
        input_csv=ORIGINAL_CSV,
        output_csv=out_csv,
        feature_spec_json=out_spec,
        report_json=out_report,
    )

    assert out_csv.exists()
    assert out_spec.exists()
    assert out_report.exists()

    assert len(ml_df) == 77
    assert report["final_ml_row_count"] == 77
    assert report["train_count"] == 5

    spec_data = json.loads(out_spec.read_text(encoding="utf-8"))
    assert "target_delay_change" in spec_data["columns"]
    assert spec_data["columns"]["target_delay_change"]["category"] == "TARGET"


def test_original_csv_integrity():
    original_data = ORIGINAL_CSV.read_bytes()
    assert len(original_data) > 0
    # Re-run pipeline and verify original CSV file size and checksum remain untouched
    fresh_df = load_dataset(ORIGINAL_CSV)
    assert len(fresh_df) == 101
    assert ORIGINAL_CSV.read_bytes() == original_data
