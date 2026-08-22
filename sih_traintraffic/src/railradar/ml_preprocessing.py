"""Pandas-based preprocessing pipeline for Nexora machine learning datasets."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Increase CSV field size limit for large raw response string fields
try:
    csv.field_size_limit(10**7)
except (OverflowError, ValueError):
    csv.field_size_limit(2147483647)


def load_dataset(csv_path: str | Path) -> pd.DataFrame:
    """Load observation dataset safely using Pandas."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    return pd.read_csv(path, engine="python")



def filter_stale_observations(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Remove stale observations based on the ``is_stale`` boolean flag.

    Preserves the source dataset unchanged in memory while returning
    only fresh observations for downstream ML pipeline steps.
    """
    if "is_stale" not in df.columns:
        raise KeyError("Required column 'is_stale' missing from dataset")

    is_stale_series = df["is_stale"].astype(str).str.lower().isin(["true", "1"])
    original_rows = len(df)
    stale_rows = int(is_stale_series.sum())
    fresh_rows = original_rows - stale_rows

    fresh_df = df[~is_stale_series].copy()
    stats = {
        "original_rows": original_rows,
        "stale_rows": stale_rows,
        "fresh_rows": fresh_rows,
    }
    return fresh_df, stats


def sort_chronologically(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure observations are sorted by ``run_id`` (if present), ``train_number``, and ``collection_timestamp``."""
    out_df = df.copy()
    out_df["collection_dt"] = pd.to_datetime(out_df["collection_timestamp"], errors="coerce", utc=True)
    out_df["train_number"] = out_df["train_number"].astype(str)
    sort_cols = ["run_id", "train_number", "collection_dt"] if "run_id" in out_df.columns else ["train_number", "collection_dt"]
    out_df = out_df.sort_values(sort_cols).reset_index(drop=True)
    return out_df


def create_sequential_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create per-train/run lag and movement features strictly within train and run boundaries.

    Ensures no information from one train or run bleeds into another train's features.
    """
    out_df = df.copy()
    group_keys = ["run_id", "train_number"] if "run_id" in out_df.columns else ["train_number"]
    grouped_train = out_df.groupby(group_keys, sort=False)

    out_df["previous_delay"] = grouped_train["delay_minutes"].shift(1)
    out_df["delay_change_prev"] = out_df["delay_minutes"] - out_df["previous_delay"]
    out_df["time_since_previous_observation_seconds"] = (
        grouped_train["collection_dt"].diff().dt.total_seconds()
    )

    prev_distance = grouped_train["distance_from_origin_km"].shift(1)
    out_df["distance_travelled_km"] = out_df["distance_from_origin_km"] - prev_distance

    prev_station = grouped_train["current_station_code"].shift(1)
    out_df["station_transition"] = (
        (out_df["current_station_code"] != prev_station) & prev_station.notnull()
    )

    prev_sequence = grouped_train["route_sequence"].shift(1)
    out_df["route_position_change"] = out_df["route_sequence"] - prev_sequence

    # Defensible derived speed calculation (DERIVED feature, not raw API field)
    valid_speed_mask = (
        (out_df["time_since_previous_observation_seconds"] > 0)
        & out_df["distance_travelled_km"].notnull()
        & (out_df["distance_travelled_km"] >= 0)
    )
    out_df["estimated_speed_kmh"] = np.where(
        valid_speed_mask,
        (out_df["distance_travelled_km"] / out_df["time_since_previous_observation_seconds"]) * 3600.0,
        np.nan,
    )
    return out_df


def create_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract temporal features from observation timestamps."""
    out_df = df.copy()
    dt = out_df["collection_dt"]
    out_df["hour"] = dt.dt.hour
    out_df["minute"] = dt.dt.minute
    out_df["time_of_day_minutes"] = out_df["hour"] * 60 + out_df["minute"]
    out_df["day_of_week"] = dt.dt.dayofweek
    return out_df


def create_future_target(df: pd.DataFrame) -> pd.DataFrame:
    """Create the future target variable strictly within each train and run group.

    The target ``target_delay_change`` is defined as:
    ``delay(t+1) - delay(t)``.
    """
    out_df = df.copy()
    group_keys = ["run_id", "train_number"] if "run_id" in out_df.columns else ["train_number"]
    out_df["future_delay"] = out_df.groupby(group_keys, sort=False)["delay_minutes"].shift(-1)
    out_df["target_delay_change"] = out_df["future_delay"] - out_df["delay_minutes"]
    return out_df



def build_ml_ready_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to rows with valid future targets and select clean tabular columns."""
    valid_mask = df["target_delay_change"].notnull()
    ml_df = df[valid_mask].copy().reset_index(drop=True)

    keep_columns = [
        "run_id",
        "collection_timestamp",
        "train_number",
        "train_name",
        "train_type",
        "train_category",
        "journey_date",
        "current_station_code",
        "next_station_code",
        "latitude",
        "longitude",
        "segment_progress",
        "delay_minutes",
        "scheduled_arrival",
        "scheduled_departure",
        "actual_arrival",
        "actual_departure",
        "platform",
        "current_location_status",
        "movement_state",
        "distance_from_origin_km",
        "distance_from_last_station_km",
        "route_sequence",
        "previous_delay",
        "delay_change_prev",
        "time_since_previous_observation_seconds",
        "distance_travelled_km",
        "station_transition",
        "route_position_change",
        "estimated_speed_kmh",
        "hour",
        "minute",
        "time_of_day_minutes",
        "day_of_week",
        "future_delay",
        "target_delay_change",
    ]
    present_columns = [col for col in keep_columns if col in ml_df.columns]
    return ml_df[present_columns]


def generate_feature_spec(df: pd.DataFrame) -> dict[str, Any]:
    """Generate comprehensive feature specification dictionary."""
    spec: dict[str, dict[str, Any]] = {}
    for col in df.columns:
        if col == "target_delay_change":
            spec[col] = {
                "type": "numeric",
                "category": "TARGET",
                "description": "Future delay change: delay(t+1) - delay(t)",
                "source": "future_delay - delay_minutes",
                "use_as_feature": False,
            }
        elif col in ("run_id", "collection_timestamp", "train_name", "journey_date", "future_delay"):
            spec[col] = {
                "type": "string" if "timestamp" not in col else "datetime",
                "category": "IDENTIFIER" if col != "future_delay" else "FUTURE_TARGET_COMPONENT",
                "description": f"Metadata or future component: {col}",
                "source": col,
                "use_as_feature": False,
            }
        elif col in (
            "previous_delay",
            "delay_change_prev",
            "time_since_previous_observation_seconds",
            "distance_travelled_km",
            "station_transition",
            "route_position_change",
            "estimated_speed_kmh",
            "hour",
            "minute",
            "time_of_day_minutes",
            "day_of_week",
        ):
            spec[col] = {
                "type": "boolean" if col == "station_transition" else "numeric",
                "category": "DERIVED",
                "description": f"Derived sequential/time feature: {col}",
                "source": "Group-wise shift / datetime extraction",
                "use_as_feature": True,
            }
        else:
            dtype_str = "numeric" if pd.api.types.is_numeric_dtype(df[col]) else "categorical"
            spec[col] = {
                "type": dtype_str,
                "category": "REAL",
                "description": f"Real RailRadar API feature: {col}",
                "source": f"raw_csv.{col}",
                "use_as_feature": True,
            }
    return {"total_columns": len(spec), "columns": spec}


def generate_preprocessing_report(
    raw_df: pd.DataFrame,
    fresh_df: pd.DataFrame,
    ml_df: pd.DataFrame,
    stale_stats: dict[str, int],
) -> dict[str, Any]:
    """Generate detailed preprocessing execution report."""
    target_series = ml_df["target_delay_change"]
    station_transitions_cnt = int(ml_df["station_transition"].astype(bool).sum()) if "station_transition" in ml_df.columns else 0

    missing_stats = {}
    for col in ml_df.columns:
        null_cnt = int(ml_df[col].isnull().sum())
        if null_cnt > 0:
            missing_stats[col] = {
                "missing_count": null_cnt,
                "missing_pct": round(null_cnt / len(ml_df) * 100, 2),
                "decision": "Kept as NaN or ignored for feature matrix; no artificial imputation performed",
            }

    report = {
        "original_rows": stale_stats["original_rows"],
        "stale_rows": stale_stats["stale_rows"],
        "fresh_rows": stale_stats["fresh_rows"],
        "rows_with_valid_sequential_pairs": len(ml_df),
        "final_ml_row_count": len(ml_df),
        "train_count": int(ml_df["train_number"].nunique()),
        "unique_stations_count": int(ml_df["current_station_code"].nunique()),
        "station_transitions_count": station_transitions_cnt,
        "missing_value_statistics": missing_stats,
        "final_feature_count": len([c for c in ml_df.columns if c not in ("target_delay_change", "future_delay", "run_id", "collection_timestamp")]),
        "target_statistics": {
            "min": float(target_series.min()),
            "max": float(target_series.max()),
            "mean": round(float(target_series.mean()), 2),
            "median": float(target_series.median()),
            "std": round(float(target_series.std()), 2),
        },
        "rows_dropped_reasons": {
            "stale_observations_dropped": stale_stats["stale_rows"],
            "terminal_train_observations_without_future_target_dropped": stale_stats["fresh_rows"] - len(ml_df),
        },
    }
    return report


def run_preprocessing_pipeline(
    input_csv: str | Path,
    output_csv: str | Path,
    feature_spec_json: str | Path,
    report_json: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Execute the full reproducible preprocessing pipeline."""
    raw_df = load_dataset(input_csv)
    fresh_df, stale_stats = filter_stale_observations(raw_df)

    sorted_df = sort_chronologically(fresh_df)
    seq_df = create_sequential_features(sorted_df)
    time_df = create_time_features(seq_df)
    target_df = create_future_target(time_df)

    ml_df = build_ml_ready_dataset(target_df)

    # Save output CSV
    out_csv_path = Path(output_csv)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    ml_df.to_csv(out_csv_path, index=False)

    # Save feature specification JSON
    spec_data = generate_feature_spec(ml_df)
    out_spec_path = Path(feature_spec_json)
    out_spec_path.parent.mkdir(parents=True, exist_ok=True)
    out_spec_path.write_text(json.dumps(spec_data, indent=2), encoding="utf-8")

    # Save preprocessing report JSON
    report_data = generate_preprocessing_report(raw_df, fresh_df, ml_df, stale_stats)
    out_report_path = Path(report_json)
    out_report_path.parent.mkdir(parents=True, exist_ok=True)
    out_report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    return ml_df, report_data
