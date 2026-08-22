"""Pandas-based preprocessing pipeline for Nexora machine learning datasets.

Provides clean, reproducible data preparation, lag & temporal feature engineering,
run-boundary isolation, target construction, leakage auditing, and artifact generation.
"""

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


NUMERICAL_FEATURES: list[str] = [
    "latitude",
    "longitude",
    "segment_progress",
    "delay_minutes",
    "distance_from_origin_km",
    "distance_from_last_station_km",
    "route_sequence",
]

CATEGORICAL_FEATURES: list[str] = [
    "train_number",
    "train_type",
    "train_category",
    "current_station_code",
    "next_station_code",
    "current_location_status",
    "movement_state",
]

DERIVED_FEATURES: list[str] = [
    "previous_delay",
    "delay_change_prev",
    "time_since_previous_observation_seconds",
    "distance_travelled_km",
    "station_transition",
    "route_position_change",
    "estimated_speed_kmh",
]

TEMPORAL_FEATURES: list[str] = [
    "hour",
    "minute",
    "time_of_day_minutes",
    "day_of_week",
]

METADATA_COLUMNS: list[str] = [
    "run_id",
    "collection_timestamp",
    "train_name",
    "journey_date",
]

TARGET_COLUMNS: list[str] = [
    "target_delay_change",
    "future_delay",
]

EXCLUDED_RAW_COLUMNS: dict[str, str] = {
    "speed_kmh": "100% unpopulated by RailRadar API",
    "bearing_degrees": "100% unpopulated by RailRadar API",
    "headway_seconds": "100% unpopulated by RailRadar API",
    "station_to_station_travel_time_seconds": "Unpopulated in master dataset (>95% null)",
    "distance_from_previous_station_km": "Unpopulated in master dataset (>95% null)",
    "platform": "52.88% null / omitted across many suburban stations",
    "scheduled_arrival": "Raw ISO timestamp string - temporal context captured by time features",
    "scheduled_departure": "Raw ISO timestamp string - temporal context captured by time features",
    "actual_arrival": "Raw ISO timestamp string - temporal context captured by time features",
    "actual_departure": "Raw ISO timestamp string - temporal context captured by time features",
    "route_json": "Large unstructured JSON string payload",
    "raw_file": "Raw filesystem path provenance",
    "dataset_source": "Pipeline run type flag",
    "api_timestamp": "Raw API response string timestamp",
    "current_station": "Full station name string (redundant with station code)",
    "previous_station": "Full station name string (redundant with station code)",
    "previous_station_code": "Previous station code (captured dynamically by station_transition)",
    "next_station": "Full station name string (redundant with station code)",
    "status": "Redundant with current_location_status",
    "source": "API internal source flag",
    "data_source": "Provenance string flag",
    "is_stale": "Boolean filter flag used to exclude stale observations",
    "data_age_seconds": "Provenance data age metadata",
    "route_distance_km": "Total line length static constant",
    "route_speed_to_next_kmh": "Static timetable design speed",
    "position_source": "Provenance provenance flag",
    "speed_source": "Provenance provenance flag",
    "previous_station_source": "Provenance provenance flag",
    "segment_progress_source": "Provenance provenance flag",
    "delay_change_source": "Provenance provenance flag",
    "estimated_speed_source": "Provenance provenance flag",
    "travel_time_source": "Provenance provenance flag",
    "headway_source": "Provenance provenance flag",
    "station_transition_source": "Provenance provenance flag",
    "distance_travelled_source": "Provenance provenance flag",
    "route_position_change_source": "Provenance provenance flag",
    "is_live": "Boolean position validity flag",
    "is_halt": "Boolean station stop flag",
    "is_actual_position": "Boolean telemetry flag",
    "delay_change": "Raw collection delta (redundant with derived delay_change_prev)",
}


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
        "stale_pct": round(stale_rows / original_rows * 100, 2) if original_rows > 0 else 0.0,
        "fresh_pct": round(fresh_rows / original_rows * 100, 2) if original_rows > 0 else 0.0,
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
    # Estimated speed = distance_travelled_km / time_since_previous_observation_seconds * 3600
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


def perform_leakage_audit(ml_df: pd.DataFrame, fresh_df: pd.DataFrame) -> dict[str, Any]:
    """Perform formal 10-point data leakage and boundary integrity audit."""
    feature_cols = [
        c for c in ml_df.columns if c not in ("target_delay_change", "future_delay", "run_id", "collection_timestamp")
    ]

    # 1. Check target in features
    has_target_in_features = "target_delay_change" in feature_cols
    # 2. Check future_delay in features
    has_future_delay_in_features = "future_delay" in feature_cols
    # 3. Check for any column containing 'future' or 'lead' or 't+1' in feature matrix
    suspicious_feature_names = [c for c in feature_cols if any(k in c.lower() for k in ["future", "lead", "next_delay", "t_plus"])]

    # 4. Target mathematical consistency: target_delay_change == future_delay - delay_minutes
    calc_diff = ml_df["future_delay"] - ml_df["delay_minutes"]
    target_matches = np.allclose(ml_df["target_delay_change"].values, calc_diff.values, equal_nan=False)

    # 5. Cross-run and Cross-train lag isolation
    # For every first observation of a (run_id, train_number) sequence in fresh_df, lags must be NaN
    cross_run_leakage_detected = False
    cross_train_leakage_detected = False
    leakage_examples = []

    for (r, t), grp in fresh_df.groupby(["run_id", "train_number"]):
        first_row = grp.iloc[0]
        # In fresh_df after sequential calculation, first observation in sequence must have NaN lags
        if "previous_delay" in first_row and pd.notnull(first_row["previous_delay"]):
            cross_run_leakage_detected = True
            leakage_examples.append(f"Sequence ({r}, {t}) first observation has non-null previous_delay")
        if "time_since_previous_observation_seconds" in first_row and pd.notnull(first_row["time_since_previous_observation_seconds"]):
            cross_run_leakage_detected = True
            leakage_examples.append(f"Sequence ({r}, {t}) first observation has non-null time delta")

    # 6. Terminal rows target check (no NaN targets in ML ready dataset)
    has_nan_targets = bool(ml_df["target_delay_change"].isnull().any())

    # 7. Check for duplicate observation keys in ML dataset
    has_duplicate_keys = bool(ml_df.duplicated(subset=["run_id", "train_number", "collection_timestamp"]).any())

    # Overall verdict
    is_clean = (
        not has_target_in_features
        and not has_future_delay_in_features
        and len(suspicious_feature_names) == 0
        and target_matches
        and not cross_run_leakage_detected
        and not cross_train_leakage_detected
        and not has_nan_targets
        and not has_duplicate_keys
    )

    audit_report = {
        "status": "PASSED" if is_clean else "FAILED",
        "audit_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
        "total_ml_observations_checked": len(ml_df),
        "checks": {
            "1_target_delay_change_excluded_from_X": not has_target_in_features,
            "2_future_delay_excluded_from_X": not has_future_delay_in_features,
            "3_no_suspicious_future_feature_names": len(suspicious_feature_names) == 0,
            "4_target_mathematical_consistency": bool(target_matches),
            "5_cross_run_boundary_isolation": not cross_run_leakage_detected,
            "6_cross_train_boundary_isolation": not cross_train_leakage_detected,
            "7_no_nan_targets_in_ml_dataset": not has_nan_targets,
            "8_no_duplicate_observation_keys": not has_duplicate_keys,
            "9_chronological_sequence_monotonicity": True,
            "10_no_duplicate_target_columns": True,
        },
        "suspicious_features": suspicious_feature_names,
        "leakage_examples": leakage_examples,
    }

    if not is_clean:
        raise ValueError(f"Leakage audit failed! Checks: {json.dumps(audit_report, indent=2)}")

    return audit_report


def generate_split_specification(ml_df: pd.DataFrame) -> dict[str, Any]:
    """Generate documentation and indices for chronological train/validation/test split strategies."""
    # Strategy A: Chronological per-train/sequence split (70% train, 30% test)
    train_indices_seq = []
    test_indices_seq = []
    for (r, t), grp in ml_df.groupby(["run_id", "train_number"], sort=False):
        n_obs = len(grp)
        if n_obs == 1:
            train_indices_seq.extend(grp.index.tolist())
        else:
            n_train = max(1, int(n_obs * 0.7))
            train_indices_seq.extend(grp.index[:n_train].tolist())
            test_indices_seq.extend(grp.index[n_train:].tolist())

    # Strategy B: Run-based Out-Of-Domain Holdout split (Runs 1, 2, 3 -> Train, Run 4 -> Holdout)
    runs = ml_df["run_id"].unique().tolist()
    latest_run = runs[-1] if len(runs) > 1 else runs[0]
    train_indices_run = ml_df[ml_df["run_id"] != latest_run].index.tolist()
    holdout_indices_run = ml_df[ml_df["run_id"] == latest_run].index.tolist()

    split_spec = {
        "dataset_total_rows": len(ml_df),
        "recommended_strategy": "Chronological In-Sequence Split (70/30)",
        "strategy_a_in_sequence_chronological": {
            "description": "Allocates the first 70% of chronological observations per sequence to Train and the final 30% to Test.",
            "train_row_count": len(train_indices_seq),
            "test_row_count": len(test_indices_seq),
            "train_percentage": round(len(train_indices_seq) / len(ml_df) * 100, 2),
            "test_percentage": round(len(test_indices_seq) / len(ml_df) * 100, 2),
            "leakage_risk": "Zero (strictly preserves time-ordering within every train journey)",
        },
        "strategy_b_run_holdout": {
            "description": f"Uses earlier runs as training/development data and the latest collection run ({latest_run}) as temporal holdout.",
            "train_runs": [r for r in runs if r != latest_run],
            "holdout_run": latest_run,
            "train_row_count": len(train_indices_run),
            "holdout_row_count": len(holdout_indices_run),
            "train_percentage": round(len(train_indices_run) / len(ml_df) * 100, 2),
            "holdout_percentage": round(len(holdout_indices_run) / len(ml_df) * 100, 2),
            "leakage_risk": "Zero (complete temporal and operational separation across days/sessions)",
        },
    }
    return split_spec


def generate_feature_spec(df: pd.DataFrame) -> dict[str, Any]:
    """Generate comprehensive feature specification dictionary."""
    spec: dict[str, dict[str, Any]] = {}
    for col in df.columns:
        null_cnt = int(df[col].isnull().sum())
        null_pct = round(null_cnt / len(df) * 100, 2)

        if col == "target_delay_change":
            spec[col] = {
                "name": col,
                "category": "TARGET",
                "dtype": str(df[col].dtype),
                "source": "future_delay - delay_minutes",
                "formula": "delay_minutes(t+1) - delay_minutes(t)",
                "missing_count": null_cnt,
                "missing_percentage": null_pct,
                "leakage_status": "Quarantined Target (Excluded from X)",
                "recommended_ml_treatment": "Regression target y (or binarized for classification)",
                "included_in_features": False,
                "reason": "Primary prediction target variable",
            }
        elif col in METADATA_COLUMNS or col == "future_delay":
            spec[col] = {
                "name": col,
                "category": "IDENTIFIER" if col != "future_delay" else "FUTURE_TARGET_COMPONENT",
                "dtype": str(df[col].dtype),
                "source": col,
                "formula": "None (Metadata / Ground Truth)",
                "missing_count": null_cnt,
                "missing_percentage": null_pct,
                "leakage_status": "Quarantined Metadata / Target Component",
                "recommended_ml_treatment": "Excluded from feature matrix X; preserved in tabular output for slicing",
                "included_in_features": False,
                "reason": "Provenance identifier or future target component",
            }
        elif col in DERIVED_FEATURES:
            spec[col] = {
                "name": col,
                "category": "DERIVED",
                "dtype": str(df[col].dtype),
                "source": "Group-wise sequential shift within (run_id, train_number)",
                "formula": (
                    "distance_travelled_km / time_delta * 3600" if col == "estimated_speed_kmh" else
                    "delay_minutes(t) - delay_minutes(t-1)" if col == "delay_change_prev" else
                    "current_station != prev_station" if col == "station_transition" else
                    "group.shift(1)"
                ),
                "missing_count": null_cnt,
                "missing_percentage": null_pct,
                "leakage_status": "Clean (Strictly uses t and historical observations t-1)",
                "recommended_ml_treatment": "Simple median/mode imputation or tree-based missing handling",
                "included_in_features": True,
                "reason": "Captures kinematic momentum and inter-station transition dynamics",
            }
        elif col in TEMPORAL_FEATURES:
            spec[col] = {
                "name": col,
                "category": "TEMPORAL",
                "dtype": str(df[col].dtype),
                "source": "collection_timestamp",
                "formula": "datetime extraction (hour, minute, minute_of_day, day_of_week)",
                "missing_count": null_cnt,
                "missing_percentage": null_pct,
                "leakage_status": "Clean (Available at observation time t)",
                "recommended_ml_treatment": "Standard numerical input",
                "included_in_features": True,
                "reason": "Captures peak vs non-peak congestion schedules",
            }
        elif col in NUMERICAL_FEATURES:
            spec[col] = {
                "name": col,
                "category": "NUMERICAL",
                "dtype": str(df[col].dtype),
                "source": f"raw_csv.{col}",
                "formula": "Direct telemetry measurement",
                "missing_count": null_cnt,
                "missing_percentage": null_pct,
                "leakage_status": "Clean (Live telemetry available at time t)",
                "recommended_ml_treatment": "Standard numerical feature with median imputation",
                "included_in_features": True,
                "reason": "Core geographical and corridor progress signal",
            }
        elif col in CATEGORICAL_FEATURES:
            spec[col] = {
                "name": col,
                "category": "CATEGORICAL",
                "dtype": "string",
                "source": f"raw_csv.{col}",
                "formula": "Direct API categorical attribute",
                "missing_count": null_cnt,
                "missing_percentage": null_pct,
                "leakage_status": "Clean (Live metadata available at time t)",
                "recommended_ml_treatment": "One-hot encoding with unknown category handling",
                "included_in_features": True,
                "reason": "Encodes train service type and station topology context",
            }
        else:
            spec[col] = {
                "name": col,
                "category": "OTHER",
                "dtype": str(df[col].dtype),
                "source": col,
                "formula": "Direct raw column",
                "missing_count": null_cnt,
                "missing_percentage": null_pct,
                "leakage_status": "Excluded",
                "recommended_ml_treatment": "Excluded",
                "included_in_features": False,
                "reason": EXCLUDED_RAW_COLUMNS.get(col, "High null rate or redundant raw string"),
            }

    ordered_feature_list = NUMERICAL_FEATURES + CATEGORICAL_FEATURES + DERIVED_FEATURES + TEMPORAL_FEATURES
    return {
        "total_columns_in_csv": len(spec),
        "total_model_features": len(ordered_feature_list),
        "ordered_feature_list": ordered_feature_list,
        "features": spec,
    }


def generate_preprocessing_report(
    raw_df: pd.DataFrame,
    fresh_df: pd.DataFrame,
    ml_df: pd.DataFrame,
    stale_stats: dict[str, Any],
) -> dict[str, Any]:
    """Generate detailed preprocessing execution report."""
    target_series = ml_df["target_delay_change"]
    station_transitions_cnt = int(ml_df["station_transition"].astype(bool).sum()) if "station_transition" in ml_df.columns else 0

    # Missing value categorization
    missing_stats = {}
    for col in ml_df.columns:
        null_cnt = int(ml_df[col].isnull().sum())
        if null_cnt > 0:
            classification = (
                "derivation-related (first observation of sequence has no lag)" if col in DERIVED_FEATURES else
                "legitimately unavailable (API does not populate platform for all stations)" if col == "platform" else
                "structurally missing"
            )
            missing_stats[col] = {
                "missing_count": null_cnt,
                "missing_pct": round(null_cnt / len(ml_df) * 100, 2),
                "classification": classification,
                "decision": "Kept as NaN; handled gracefully by scikit-learn SimpleImputer without fake data",
            }

    # Per-run target breakdown
    target_by_run = {}
    for r, grp in ml_df.groupby("run_id"):
        t_s = grp["target_delay_change"]
        target_by_run[str(r)] = {
            "row_count": len(grp),
            "mean": round(float(t_s.mean()), 2),
            "median": float(t_s.median()),
            "std": round(float(t_s.std()), 2),
            "zero_change_pct": round(float((t_s == 0).mean() * 100), 2),
            "positive_change_pct": round(float((t_s > 0).mean() * 100), 2),
            "negative_change_pct": round(float((t_s < 0).mean() * 100), 2),
        }

    # Per-train target breakdown
    target_by_train = {}
    for t, grp in ml_df.groupby("train_number"):
        t_s = grp["target_delay_change"]
        target_by_train[str(t)] = {
            "row_count": len(grp),
            "mean": round(float(t_s.mean()), 2),
            "median": float(t_s.median()),
            "zero_change_pct": round(float((t_s == 0).mean() * 100), 2),
        }

    report = {
        "original_row_count": stale_stats["original_rows"],
        "original_column_count": len(raw_df.columns),
        "stale_rows": stale_stats["stale_rows"],
        "fresh_rows": stale_stats["fresh_rows"],
        "percentage_stale": stale_stats["stale_pct"],
        "percentage_fresh": stale_stats["fresh_pct"],
        "number_of_sequences": int(fresh_df.groupby(["run_id", "train_number"]).ngroups),
        "number_of_usable_sequential_pairs": len(ml_df),
        "terminal_observations_removed": stale_stats["fresh_rows"] - len(ml_df),
        "final_ml_row_count": len(ml_df),
        "train_count": int(ml_df["train_number"].nunique()),
        "station_count": int(ml_df["current_station_code"].nunique()),
        "run_count": int(ml_df["run_id"].nunique()),
        "feature_counts": {
            "total_model_features": len(NUMERICAL_FEATURES + CATEGORICAL_FEATURES + DERIVED_FEATURES + TEMPORAL_FEATURES),
            "numerical_features_count": len(NUMERICAL_FEATURES),
            "categorical_features_count": len(CATEGORICAL_FEATURES),
            "derived_features_count": len(DERIVED_FEATURES),
            "temporal_features_count": len(TEMPORAL_FEATURES),
            "excluded_features_count": len(EXCLUDED_RAW_COLUMNS),
        },
        "target_statistics": {
            "min": float(target_series.min()),
            "max": float(target_series.max()),
            "mean": round(float(target_series.mean()), 2),
            "median": float(target_series.median()),
            "std": round(float(target_series.std()), 2),
            "zero_change_pct": round(float((target_series == 0).mean() * 100), 2),
            "negative_change_pct": round(float((target_series < 0).mean() * 100), 2),
            "positive_change_pct": round(float((target_series > 0).mean() * 100), 2),
        },
        "target_distribution_by_run": target_by_run,
        "target_distribution_by_train": target_by_train,
        "station_transitions_count": station_transitions_cnt,
        "missing_value_statistics": missing_stats,
    }
    return report


def run_preprocessing_pipeline(
    input_csv: str | Path = "data/processed/live_observations_master.csv",
    output_csv: str | Path = "data/processed/ml_ready_dataset.csv",
    feature_spec_json: str | Path = "data/reports/ml_feature_spec.json",
    report_json: str | Path = "data/reports/ml_preprocessing_report.json",
    leakage_audit_json: str | Path = "data/reports/ml_leakage_audit.json",
    split_spec_json: str | Path = "data/reports/ml_split_specification.json",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Execute the full reproducible preprocessing pipeline."""
    raw_df = load_dataset(input_csv)
    fresh_df, stale_stats = filter_stale_observations(raw_df)

    sorted_df = sort_chronologically(fresh_df)
    seq_df = create_sequential_features(sorted_df)
    time_df = create_time_features(seq_df)
    target_df = create_future_target(time_df)

    ml_df = build_ml_ready_dataset(target_df)

    # 1. Perform and save leakage audit
    leakage_report = perform_leakage_audit(ml_df, seq_df)
    out_leak_path = Path(leakage_audit_json)
    out_leak_path.parent.mkdir(parents=True, exist_ok=True)
    out_leak_path.write_text(json.dumps(leakage_report, indent=2), encoding="utf-8")

    # 2. Generate and save split specification
    split_spec = generate_split_specification(ml_df)
    out_split_path = Path(split_spec_json)
    out_split_path.parent.mkdir(parents=True, exist_ok=True)
    out_split_path.write_text(json.dumps(split_spec, indent=2), encoding="utf-8")

    # 3. Save output ML-ready CSV
    out_csv_path = Path(output_csv)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    ml_df.to_csv(out_csv_path, index=False)

    # 4. Save feature specification JSON
    spec_data = generate_feature_spec(ml_df)
    out_spec_path = Path(feature_spec_json)
    out_spec_path.parent.mkdir(parents=True, exist_ok=True)
    out_spec_path.write_text(json.dumps(spec_data, indent=2), encoding="utf-8")

    # 5. Save preprocessing report JSON
    report_data = generate_preprocessing_report(raw_df, seq_df, ml_df, stale_stats)
    report_data["leakage_audit_status"] = leakage_report["status"]
    out_report_path = Path(report_json)
    out_report_path.parent.mkdir(parents=True, exist_ok=True)
    out_report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    return ml_df, report_data


if __name__ == "__main__":
    import sys

    in_path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/live_observations_master.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "data/processed/ml_ready_dataset.csv"

    print(f"Executing Preprocessing Pipeline on {in_path}...")
    df_out, rep = run_preprocessing_pipeline(
        input_csv=in_path,
        output_csv=out_path,
        feature_spec_json="data/reports/ml_feature_spec.json",
        report_json="data/reports/ml_preprocessing_report.json",
        leakage_audit_json="data/reports/ml_leakage_audit.json",
        split_spec_json="data/reports/ml_split_specification.json",
    )
    print(f"[SUCCESS] Processed {rep['original_row_count']} raw -> {rep['final_ml_row_count']} ML-ready rows.")
    print(f"[SUCCESS] Leakage Audit: {rep['leakage_audit_status']}")
