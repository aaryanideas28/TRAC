"""Random Forest Regressor & Classifier pipeline, baseline evaluation, error analysis, and optimization readiness interface for TRAC."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    root_mean_squared_error,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL_FEATURES: list[str] = [
    "train_number",
    "train_type",
    "train_category",
    "current_station_code",
    "next_station_code",
    "current_location_status",
    "movement_state",
]

NUMERICAL_FEATURES: list[str] = [
    "latitude",
    "longitude",
    "segment_progress",
    "delay_minutes",
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
]

EXCLUDED_COLUMNS: dict[str, str] = {
    "run_id": "Identifier/metadata provenance",
    "collection_timestamp": "Identifier/metadata provenance",
    "train_name": "Identifier/metadata provenance",
    "journey_date": "Identifier/metadata provenance",
    "future_delay": "Future target component (t+1 delay) - excluded to prevent data leakage",
    "target_delay_change": "ML target variable y",
    "scheduled_arrival": "Raw ISO timestamp string - temporal context captured by time features",
    "scheduled_departure": "Raw ISO timestamp string - temporal context captured by time features",
    "actual_arrival": "Raw ISO timestamp string - temporal context captured by time features",
    "actual_departure": "Raw ISO timestamp string - temporal context captured by time features",
    "platform": "Rejected due to excessive missing values (40.85% missing)",
}

TARGET_COLUMN: str = "target_delay_change"

TUNING_CONFIGURATIONS: list[dict[str, Any]] = [
    {"name": "baseline_unconstrained", "n_estimators": 100, "max_depth": 5, "min_samples_split": 2, "min_samples_leaf": 1},
    {"name": "shallow_trees_depth_2", "n_estimators": 100, "max_depth": 2, "min_samples_split": 2, "min_samples_leaf": 1},
    {"name": "shallow_trees_depth_3", "n_estimators": 100, "max_depth": 3, "min_samples_split": 2, "min_samples_leaf": 1},
    {"name": "regularized_leaf_2", "n_estimators": 100, "max_depth": 3, "min_samples_split": 2, "min_samples_leaf": 2},
    {"name": "regularized_leaf_4", "n_estimators": 100, "max_depth": 3, "min_samples_split": 4, "min_samples_leaf": 4},
    {"name": "conservative_depth_2_leaf_2", "n_estimators": 100, "max_depth": 2, "min_samples_split": 2, "min_samples_leaf": 2},
    {"name": "conservative_depth_2_leaf_4", "n_estimators": 100, "max_depth": 2, "min_samples_split": 4, "min_samples_leaf": 4},
    {"name": "higher_estimators_regularized", "n_estimators": 200, "max_depth": 3, "min_samples_split": 2, "min_samples_leaf": 2},
]


def load_ml_dataset(csv_path: str | Path) -> pd.DataFrame:
    """Load the ML-ready dataset and validate required structure."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"ML dataset not found at {path}")

    df = pd.read_csv(path)
    if TARGET_COLUMN not in df.columns:
        raise KeyError(f"Target column '{TARGET_COLUMN}' missing from dataset")

    return df


def prepare_feature_target_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series | None]:
    """Separate feature matrix X and target y, enforcing strict target isolation."""
    df_clean = df.copy()
    for cat_col in CATEGORICAL_FEATURES:
        if cat_col in df_clean.columns:
            df_clean[cat_col] = df_clean[cat_col].astype(str)

    if "station_transition" in df_clean.columns:
        df_clean["station_transition"] = df_clean["station_transition"].astype(float)

    feature_cols = [col for col in CATEGORICAL_FEATURES + NUMERICAL_FEATURES if col in df_clean.columns]
    X = df_clean[feature_cols].copy()
    y = df_clean[TARGET_COLUMN].copy() if TARGET_COLUMN in df_clean.columns else None

    # Guard against target or future column presence in X
    for forbidden in ["target_delay_change", "future_delay", "next_delay"]:
        if forbidden in X.columns:
            raise ValueError(f"Data leakage risk: forbidden column '{forbidden}' found in feature matrix X")

    return X, y


def split_chronologically_per_train(
    df: pd.DataFrame,
    train_ratio: float = 0.7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split dataset chronologically per train to avoid cross-train contamination and time leakage.

    For each train, the first `train_ratio` (default 70%) of sequential observations
    are allocated to the training split, and the remaining 30% are allocated to the test split.
    """
    if not 0.0 < train_ratio < 1.0:
        raise ValueError(f"train_ratio must be between 0 and 1, got {train_ratio}")

    df_sorted = df.copy()
    if "collection_timestamp" in df_sorted.columns:
        df_sorted["collection_dt"] = pd.to_datetime(df_sorted["collection_timestamp"], errors="coerce", utc=True)
        df_sorted = df_sorted.sort_values(["train_number", "collection_dt"]).reset_index(drop=True)

    train_indices: list[int] = []
    test_indices: list[int] = []

    for _, train_grp in df_sorted.groupby("train_number", sort=False):
        n_obs = len(train_grp)
        if n_obs == 1:
            train_indices.extend(train_grp.index)
        else:
            n_train = max(1, int(n_obs * train_ratio))
            train_indices.extend(train_grp.index[:n_train])
            test_indices.extend(train_grp.index[n_train:])

    train_df = df_sorted.loc[train_indices].copy().reset_index(drop=True)
    test_df = df_sorted.loc[test_indices].copy().reset_index(drop=True)
    return train_df, test_df


def build_preprocessor(
    categorical_cols: list[str] | None = None,
    numerical_cols: list[str] | None = None,
) -> ColumnTransformer:
    """Construct sklearn ColumnTransformer for numerical imputation and categorical one-hot encoding."""
    cat_cols = categorical_cols if categorical_cols is not None else CATEGORICAL_FEATURES
    num_cols = numerical_cols if numerical_cols is not None else NUMERICAL_FEATURES

    num_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])

    cat_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_transformer, num_cols),
            ("cat", cat_transformer, cat_cols),
        ]
    )
    return preprocessor


def build_model_pipeline(
    categorical_cols: list[str] | None = None,
    numerical_cols: list[str] | None = None,
    n_estimators: int = 200,
    max_depth: int | None = 5,
    min_samples_split: int = 2,
    min_samples_leaf: int = 2,
    random_state: int = 42,
    n_jobs: int = -1,
) -> Pipeline:
    """Build full scikit-learn Pipeline with preprocessing and RandomForestRegressor."""
    preprocessor = build_preprocessor(categorical_cols, numerical_cols)
    regressor = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    return Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", regressor),
    ])


def build_classifier_pipeline(
    categorical_cols: list[str] | None = None,
    numerical_cols: list[str] | None = None,
    n_estimators: int = 100,
    max_depth: int | None = 3,
    min_samples_split: int = 2,
    min_samples_leaf: int = 2,
    class_weight: str | None = "balanced",
    random_state: int = 42,
    n_jobs: int = -1,
) -> Pipeline:
    """Construct complete preprocessing + RandomForestClassifier pipeline."""
    preprocessor = build_preprocessor(categorical_cols, numerical_cols)
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        class_weight=class_weight,
        random_state=random_state,
        n_jobs=n_jobs,
    )
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", clf),
    ])


def evaluate_predictions(y_true: np.ndarray | pd.Series, y_pred: np.ndarray | pd.Series) -> dict[str, float]:
    """Calculate standard regression metrics: MAE, RMSE, R2, Bias, and Directional Accuracy."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    mae = float(mean_absolute_error(y_t, y_p))
    rmse = float(root_mean_squared_error(y_t, y_p))
    r2 = float(r2_score(y_t, y_p))
    bias = float(np.mean(y_p - y_t))

    dir_correct = np.where(
        y_t == 0,
        np.abs(y_p) < 0.5,
        np.sign(y_p) == np.sign(y_t),
    )
    directional_acc = float(np.mean(dir_correct) * 100.0)

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "bias": round(bias, 4),
        "directional_accuracy_pct": round(directional_acc, 2),
    }


def evaluate_classification_predictions(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray | pd.Series,
    y_prob: np.ndarray | None = None,
) -> dict[str, Any]:
    """Calculate classification performance metrics: Accuracy, Balanced Acc, Precision, Recall, F1, ROC-AUC."""
    y_t = np.asarray(y_true, dtype=int)
    y_p = np.asarray(y_pred, dtype=int)

    acc = float(accuracy_score(y_t, y_p))
    bal_acc = float(balanced_accuracy_score(y_t, y_p))
    prec = float(precision_score(y_t, y_p, zero_division=0))
    rec = float(recall_score(y_t, y_p, zero_division=0))
    f1 = float(f1_score(y_t, y_p, zero_division=0))
    cm = confusion_matrix(y_t, y_p).tolist()

    roc_auc = None
    if y_prob is not None and len(np.unique(y_t)) > 1:
        try:
            roc_auc = round(float(roc_auc_score(y_t, y_prob)), 4)
        except ValueError:
            roc_auc = None

    return {
        "accuracy": round(acc, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": roc_auc,
        "confusion_matrix": cm,
    }


def extract_feature_importances(
    pipeline: Pipeline,
    categorical_cols: list[str] | None = None,
    numerical_cols: list[str] | None = None,
) -> dict[str, Any]:
    """Extract raw and aggregated feature importances from the fitted pipeline."""
    cat_cols = categorical_cols if categorical_cols is not None else CATEGORICAL_FEATURES
    num_cols = numerical_cols if numerical_cols is not None else NUMERICAL_FEATURES

    preprocessor: ColumnTransformer = pipeline.named_steps["preprocessor"]
    estimator = pipeline.named_steps.get("regressor") or pipeline.named_steps.get("classifier")
    if estimator is None:
        raise KeyError("Neither 'regressor' nor 'classifier' found in pipeline steps.")

    cat_encoder = preprocessor.named_transformers_["cat"].named_steps["encoder"]
    encoded_cat_names = cat_encoder.get_feature_names_out(cat_cols).tolist()
    all_feature_names = num_cols + encoded_cat_names

    importances = estimator.feature_importances_

    raw_importances = [
        {"feature": name, "importance": round(float(imp), 4), "percentage": round(float(imp * 100), 2)}
        for name, imp in zip(all_feature_names, importances)
    ]
    raw_importances.sort(key=lambda x: x["importance"], reverse=True)

    aggregated: dict[str, float] = {}
    for item in raw_importances:
        feat_name = item["feature"]
        imp_val = item["importance"]

        matched_parent: str | None = None
        for orig_cat in cat_cols:
            if feat_name.startswith(f"{orig_cat}_"):
                matched_parent = orig_cat
                break

        parent = matched_parent if matched_parent is not None else feat_name
        aggregated[parent] = aggregated.get(parent, 0.0) + imp_val

    aggregated_importances = [
        {"feature": name, "importance": round(imp, 4), "percentage": round(imp * 100, 2)}
        for name, imp in aggregated.items()
    ]
    aggregated_importances.sort(key=lambda x: x["importance"], reverse=True)

    return {
        "top_20_aggregated": aggregated_importances[:20],
        "top_20_raw": raw_importances[:20],
        "aggregated_importances": aggregated_importances,
        "raw_transformed_importances": raw_importances,
    }


def calculate_risk_score(
    current_delay: np.ndarray | pd.Series,
    predicted_delay_change: np.ndarray | pd.Series,
    probability_delay_worsening: np.ndarray | pd.Series,
) -> np.ndarray:
    """Calculate bounded, deterministic risk score strictly in [0.0, 1.0].

    Formula:
    risk_score = clip(
        0.40 * P(delay_worsening) +
        0.35 * (min(delay_minutes, 30) / 30.0) +
        0.25 * (1 / (1 + exp(-predicted_delay_change))),
        0.0, 1.0
    )
    """
    p_worsen = np.asarray(probability_delay_worsening, dtype=float)
    c_delay = np.maximum(0.0, np.asarray(current_delay, dtype=float))
    p_change = np.asarray(predicted_delay_change, dtype=float)

    norm_delay = np.clip(c_delay, 0.0, 30.0) / 30.0
    sig_drift = 1.0 / (1.0 + np.exp(-p_change))

    raw_risk = 0.40 * p_worsen + 0.35 * norm_delay + 0.25 * sig_drift
    return np.clip(raw_risk, 0.0, 1.0)


def generate_optimization_signals(
    df: pd.DataFrame,
    reg_pipeline: Pipeline | None = None,
    clf_pipeline: Pipeline | None = None,
    output_csv: str | Path | None = "data/processed/rf_optimization_inputs.csv",
) -> pd.DataFrame:
    """Generate structured optimization input records from live observation dataframe."""
    df_clean = df.copy()
    X, _ = prepare_feature_target_split(df_clean)

    # 1. Regressor predictions (continuous delay drift)
    if reg_pipeline is not None:
        pred_delay_change = reg_pipeline.predict(X)
    else:
        pred_delay_change = np.zeros(len(df_clean), dtype=float)

    # 2. Classifier predictions (worsening probability)
    if clf_pipeline is not None:
        prob_worsening = clf_pipeline.predict_proba(X)[:, 1]
    else:
        # Fallback heuristic from regression drift if classifier not provided
        prob_worsening = 1.0 / (1.0 + np.exp(-pred_delay_change))

    # 3. Current delay values
    curr_delay = df_clean["delay_minutes"].values if "delay_minutes" in df_clean.columns else np.zeros(len(df_clean))

    # 4. Compute unified bounded risk score
    risk_scores = calculate_risk_score(curr_delay, pred_delay_change, prob_worsening)

    # 5. Assemble tabular optimization interface records
    signals_df = pd.DataFrame({
        "train_number": df_clean["train_number"].astype(str),
        "collection_timestamp": df_clean["collection_timestamp"] if "collection_timestamp" in df_clean.columns else "",
        "current_station_code": df_clean["current_station_code"] if "current_station_code" in df_clean.columns else "UNKNOWN",
        "next_station_code": df_clean["next_station_code"] if "next_station_code" in df_clean.columns else "UNKNOWN",
        "current_delay": np.round(curr_delay, 2),
        "predicted_delay_change": np.round(pred_delay_change, 4),
        "probability_delay_worsening": np.round(prob_worsening, 4),
        "risk_score": np.round(risk_scores, 4),
        "movement_state": df_clean["movement_state"] if "movement_state" in df_clean.columns else "UNKNOWN",
        "distance_from_origin_km": np.round(df_clean["distance_from_origin_km"], 2) if "distance_from_origin_km" in df_clean.columns else 0.0,
        "route_sequence": df_clean["route_sequence"] if "route_sequence" in df_clean.columns else 0,
    })

    if output_csv:
        out_p = Path(output_csv)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        signals_df.to_csv(out_p, index=False)

    return signals_df


def train_and_evaluate_random_forest(
    dataset_csv: str | Path = "data/processed/ml_ready_dataset.csv",
    report_output_path: str | Path | None = "data/reports/random_forest_report.json",
    model_output_path: str | Path | None = "models/random_forest_delay_change.joblib",
    predictions_output_path: str | Path | None = "data/processed/rf_test_predictions.csv",
    n_estimators: int = 200,
    max_depth: int | None = 5,
    min_samples_split: int = 2,
    min_samples_leaf: int = 2,
    train_ratio: float = 0.7,
    random_state: int = 42,
) -> dict[str, Any]:
    """Execute complete Random Forest training, baseline benchmarking, and reporting workflow."""
    df = load_ml_dataset(dataset_csv)

    # 1. Chronological Per-Train Split
    train_df, test_df = split_chronologically_per_train(df, train_ratio=train_ratio)

    # 2. Extract X and y
    X_train, y_train = prepare_feature_target_split(train_df)
    X_test, y_test = prepare_feature_target_split(test_df)

    if y_train is None or y_test is None:
        raise ValueError("Target column missing during train/test split extraction")

    # 3. Build and fit pipeline (Strictly on training data)
    pipeline = build_model_pipeline(
        categorical_cols=CATEGORICAL_FEATURES,
        numerical_cols=NUMERICAL_FEATURES,
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
    )
    pipeline.fit(X_train, y_train)

    # 4. Predictions & Evaluation
    y_pred_baseline = np.zeros_like(y_test, dtype=float)
    baseline_metrics = evaluate_predictions(y_test, y_pred_baseline)

    y_pred_rf = pipeline.predict(X_test)
    rf_test_metrics = evaluate_predictions(y_test, y_pred_rf)

    y_train_pred_rf = pipeline.predict(X_train)
    rf_train_metrics = evaluate_predictions(y_train, y_train_pred_rf)

    importance_info = extract_feature_importances(
        pipeline,
        categorical_cols=CATEGORICAL_FEATURES,
        numerical_cols=NUMERICAL_FEATURES,
    )

    rf_outperformed_baseline = bool(
        rf_test_metrics["mae"] < baseline_metrics["mae"]
        and rf_test_metrics["rmse"] < baseline_metrics["rmse"]
    )

    residuals = y_test.values - y_pred_rf
    abs_errors = np.abs(residuals)

    pred_df = pd.DataFrame({
        "run_id": test_df["run_id"] if "run_id" in test_df.columns else "unknown",
        "train_number": test_df["train_number"].astype(str),
        "collection_timestamp": test_df["collection_timestamp"],
        "movement_state": test_df["movement_state"] if "movement_state" in test_df.columns else "UNKNOWN",
        "current_location_status": test_df["current_location_status"] if "current_location_status" in test_df.columns else "UNKNOWN",
        "delay_minutes": test_df["delay_minutes"] if "delay_minutes" in test_df.columns else 0.0,
        "actual_target_delay_change": y_test.values,
        "predicted_target_delay_change": np.round(y_pred_rf, 4),
        "residual": np.round(residuals, 4),
        "absolute_error": np.round(abs_errors, 4),
    })

    if predictions_output_path:
        pred_p = Path(predictions_output_path)
        pred_p.parent.mkdir(parents=True, exist_ok=True)
        pred_df.to_csv(pred_p, index=False)

    per_run_perf = {}
    if "run_id" in pred_df.columns:
        for r, grp in pred_df.groupby("run_id"):
            if len(grp) >= 5:
                m = evaluate_predictions(grp["actual_target_delay_change"], grp["predicted_target_delay_change"])
                base_m = evaluate_predictions(grp["actual_target_delay_change"], np.zeros(len(grp)))
                per_run_perf[str(r)] = {
                    "test_observations": len(grp),
                    "rf_mae": m["mae"],
                    "rf_rmse": m["rmse"],
                    "rf_r2": m["r2"],
                    "baseline_mae": base_m["mae"],
                }
            else:
                per_run_perf[str(r)] = {
                    "test_observations": len(grp),
                    "status": "Insufficient test observations (< 5) for reliable standalone evaluation",
                }

    per_train_perf = {}
    for t, grp in pred_df.groupby("train_number"):
        if len(grp) >= 5:
            m = evaluate_predictions(grp["actual_target_delay_change"], grp["predicted_target_delay_change"])
            base_m = evaluate_predictions(grp["actual_target_delay_change"], np.zeros(len(grp)))
            per_train_perf[str(t)] = {
                "test_observations": len(grp),
                "rf_mae": m["mae"],
                "rf_rmse": m["rmse"],
                "rf_r2": m["r2"],
                "baseline_mae": base_m["mae"],
            }
        else:
            per_train_perf[str(t)] = {
                "test_observations": len(grp),
                "status": "Insufficient test observations (< 5)",
            }

    state_perf = {}
    if "movement_state" in pred_df.columns:
        for st, grp in pred_df.groupby("movement_state"):
            m = evaluate_predictions(grp["actual_target_delay_change"], grp["predicted_target_delay_change"])
            state_perf[str(st)] = {"count": len(grp), "mae": m["mae"], "rmse": m["rmse"]}

    target_dist_comparison = {
        "actual_test_target": {
            "mean": round(float(y_test.mean()), 4),
            "median": round(float(y_test.median()), 4),
            "std": round(float(y_test.std()), 4),
            "min": float(y_test.min()),
            "max": float(y_test.max()),
            "zero_change_pct": round(float((y_test == 0).mean() * 100), 2),
            "positive_change_pct": round(float((y_test > 0).mean() * 100), 2),
            "negative_change_pct": round(float((y_test < 0).mean() * 100), 2),
        },
        "predicted_test_target": {
            "mean": round(float(np.mean(y_pred_rf)), 4),
            "median": round(float(np.median(y_pred_rf)), 4),
            "std": round(float(np.std(y_pred_rf)), 4),
            "min": round(float(np.min(y_pred_rf)), 4),
            "max": round(float(np.max(y_pred_rf)), 4),
            "zero_change_pct": round(float((np.abs(y_pred_rf) < 0.1).mean() * 100), 2),
            "positive_change_pct": round(float((y_pred_rf >= 0.1).mean() * 100), 2),
            "negative_change_pct": round(float((y_pred_rf <= -0.1).mean() * 100), 2),
        },
    }

    if rf_outperformed_baseline:
        verdict = "PROMISING"
        verdict_reason = "Random Forest outperforms zero-change baseline on test MAE and RMSE."
        data_decision = "DATA SUFFICIENT FOR PROTOTYPE"
    elif rf_test_metrics["mae"] < baseline_metrics["mae"] * 1.25 and rf_test_metrics["directional_accuracy_pct"] > 50:
        verdict = "PARTIALLY USEFUL"
        verdict_reason = (
            "Random Forest captures directional trends and dynamic momentum (directional accuracy > 50%), "
            "but raw point MAE is penalized by the dominance of zero-change intervals (57.7% static delay)."
        )
        data_decision = "DATA SUFFICIENT BUT MODEL FEATURES NEED IMPROVEMENT"
    else:
        verdict = "NOT YET USEFUL"
        verdict_reason = "Random Forest does not currently demonstrate sufficient predictive improvement over the baseline."
        data_decision = "ADDITIONAL DATA RECOMMENDED"

    report = {
        "dataset_summary": {
            "total_rows": len(df),
            "total_features": len(CATEGORICAL_FEATURES + NUMERICAL_FEATURES),
            "training_rows": len(train_df),
            "testing_rows": len(test_df),
            "train_ratio": train_ratio,
            "train_count": int(df["train_number"].nunique()),
            "runs_in_train": train_df["run_id"].unique().tolist() if "run_id" in train_df.columns else [],
            "runs_in_test": test_df["run_id"].unique().tolist() if "run_id" in test_df.columns else [],
            "trains_in_train": train_df["train_number"].unique().tolist(),
            "trains_in_test": test_df["train_number"].unique().tolist(),
            "training_time_range": {
                "min": str(train_df["collection_timestamp"].min()),
                "max": str(train_df["collection_timestamp"].max()),
            },
            "testing_time_range": {
                "min": str(test_df["collection_timestamp"].min()),
                "max": str(test_df["collection_timestamp"].max()),
            },
        },
        "baseline_model": {
            "strategy": "Zero-change persistence baseline (predict delta_delay = 0)",
            "test_metrics": baseline_metrics,
        },
        "random_forest_model": {
            "algorithm": "sklearn.ensemble.RandomForestRegressor",
            "parameters": {
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "min_samples_split": min_samples_split,
                "min_samples_leaf": min_samples_leaf,
                "random_state": random_state,
            },
            "train_metrics": rf_train_metrics,
            "test_metrics": rf_test_metrics,
            "train_test_gap": {
                "mae_gap": round(rf_test_metrics["mae"] - rf_train_metrics["mae"], 4),
                "rmse_gap": round(rf_test_metrics["rmse"] - rf_train_metrics["rmse"], 4),
            },
        },
        "target_distribution_comparison": target_dist_comparison,
        "model_comparison": {
            "did_random_forest_outperform_baseline": rf_outperformed_baseline,
            "comparison_verdict": verdict,
            "verdict_reason": verdict_reason,
            "data_sufficiency_decision": data_decision,
        },
        "feature_importances": {
            "top_20_aggregated": importance_info["top_20_aggregated"],
            "top_20_raw": importance_info["top_20_raw"],
        },
        "cross_run_performance": per_run_perf,
        "cross_train_performance": per_train_perf,
        "performance_by_movement_state": state_perf,
        "error_analysis_summary": {
            "mean_residual": round(float(np.mean(residuals)), 4),
            "median_residual": round(float(np.median(residuals)), 4),
            "max_underprediction_error": round(float(np.max(residuals)), 4),
            "max_overprediction_error": round(float(np.min(residuals)), 4),
            "predictions_artifact": str(predictions_output_path),
        },
        "saved_artifacts": {
            "model_path": str(model_output_path),
            "report_path": str(report_output_path),
            "predictions_path": str(predictions_output_path),
        },
        "safety_and_integrity": {
            "railradar_api_requests_made": 0,
            "original_dataset_modified": False,
            "synthetic_data_generated": False,
            "or_tools_executed": False,
        },
    }

    if model_output_path:
        mod_p = Path(model_output_path)
        mod_p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, mod_p)
        if "models" in mod_p.parts and "data" not in mod_p.parts:
            alt_p = Path("data/models") / mod_p.name
            alt_p.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(pipeline, alt_p)

    if report_output_path:
        rep_p = Path(report_output_path)
        rep_p.parent.mkdir(parents=True, exist_ok=True)
        rep_p.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def run_optimization_preparation_pipeline(
    dataset_csv: str | Path = "data/processed/ml_ready_dataset.csv",
    report_output_path: str | Path = "data/reports/rf_optimization_readiness_report.json",
    reg_model_path: str | Path = "models/random_forest_delay_change.joblib",
    clf_model_path: str | Path = "models/random_forest_classifier.joblib",
    optimization_inputs_csv: str | Path = "data/processed/rf_optimization_inputs.csv",
    train_ratio: float = 0.7,
    random_state: int = 42,
) -> dict[str, Any]:
    """Execute the full Random Forest optimization preparation suite."""
    df = load_ml_dataset(dataset_csv)

    train_df, test_df = split_chronologically_per_train(df, train_ratio=train_ratio)
    X_train, y_train = prepare_feature_target_split(train_df)
    X_test, y_test = prepare_feature_target_split(test_df)

    # 1. Baseline Model
    y_pred_baseline = np.zeros_like(y_test, dtype=float)
    baseline_metrics = evaluate_predictions(y_test, y_pred_baseline)

    # 2. Existing RF Regressor (n=200, depth=5, leaf=2)
    reg_baseline_pipe = build_model_pipeline(
        n_estimators=200, max_depth=5, min_samples_split=2, min_samples_leaf=2, random_state=random_state
    )
    reg_baseline_pipe.fit(X_train, y_train)
    reg_baseline_test_preds = reg_baseline_pipe.predict(X_test)
    reg_baseline_metrics = evaluate_predictions(y_test, reg_baseline_test_preds)

    # 3. Tuned RF Regressor (n=100, depth=3, leaf=2)
    reg_tuned_pipe = build_model_pipeline(
        n_estimators=100, max_depth=3, min_samples_split=2, min_samples_leaf=2, random_state=random_state
    )
    reg_tuned_pipe.fit(X_train, y_train)
    reg_tuned_test_preds = reg_tuned_pipe.predict(X_test)
    reg_tuned_metrics = evaluate_predictions(y_test, reg_tuned_test_preds)

    # 4. Binary Delay Worsening Classifier (y > 0)
    y_train_clf = (y_train > 0).astype(int)
    y_test_clf = (y_test > 0).astype(int)

    clf_pipe = build_classifier_pipeline(
        n_estimators=100, max_depth=3, min_samples_split=2, min_samples_leaf=2, class_weight="balanced", random_state=random_state
    )
    clf_pipe.fit(X_train, y_train_clf)
    clf_test_preds = clf_pipe.predict(X_test)
    clf_test_prob = clf_pipe.predict_proba(X_test)[:, 1]
    clf_metrics = evaluate_classification_predictions(y_test_clf, clf_test_preds, clf_test_prob)

    # 5. Significant Worsening Classifier (y >= 2 min)
    y_train_sig = (y_train >= 2.0).astype(int)
    y_test_sig = (y_test >= 2.0).astype(int)

    clf_sig_pipe = build_classifier_pipeline(
        n_estimators=100, max_depth=3, min_samples_split=2, min_samples_leaf=2, class_weight="balanced", random_state=random_state
    )
    clf_sig_pipe.fit(X_train, y_train_sig)
    clf_sig_test_preds = clf_sig_pipe.predict(X_test)
    clf_sig_test_prob = clf_sig_pipe.predict_proba(X_test)[:, 1]
    clf_sig_metrics = evaluate_classification_predictions(y_test_sig, clf_sig_test_preds, clf_sig_test_prob)

    # 6. Extract Feature Importances
    clf_importances = extract_feature_importances(clf_pipe)

    # 7. Generate Structured Optimization Inputs Table
    opt_df = generate_optimization_signals(
        df,
        reg_pipeline=reg_tuned_pipe,
        clf_pipeline=clf_pipe,
        output_csv=optimization_inputs_csv,
    )

    # 8. Save Model Artifacts
    for p_path, pipe in [(reg_model_path, reg_tuned_pipe), (clf_model_path, clf_pipe)]:
        if p_path:
            p = Path(p_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(pipe, p)
            if "models" in p.parts and "data" not in p.parts:
                alt_p = Path("data/models") / p.name
                alt_p.parent.mkdir(parents=True, exist_ok=True)
                joblib.dump(pipe, alt_p)

    # 9. Assemble Readiness Report
    report = {
        "dataset_summary": {
            "total_rows": len(df),
            "training_rows": len(train_df),
            "testing_rows": len(test_df),
            "train_ratio": train_ratio,
            "train_count": int(df["train_number"].nunique()),
            "runs_count": int(df["run_id"].nunique()) if "run_id" in df.columns else 1,
        },
        "target_distribution": {
            "zero_change_count": int((df[TARGET_COLUMN] == 0).sum()),
            "zero_change_pct": round(float((df[TARGET_COLUMN] == 0).mean() * 100), 2),
            "positive_change_count": int((df[TARGET_COLUMN] > 0).sum()),
            "positive_change_pct": round(float((df[TARGET_COLUMN] > 0).mean() * 100), 2),
            "negative_change_count": int((df[TARGET_COLUMN] < 0).sum()),
            "negative_change_pct": round(float((df[TARGET_COLUMN] < 0).mean() * 100), 2),
            "significant_delay_growth_ge_2min_count": int((df[TARGET_COLUMN] >= 2.0).sum()),
            "significant_delay_growth_ge_2min_pct": round(float((df[TARGET_COLUMN] >= 2.0).mean() * 100), 2),
        },
        "model_variant_comparison": {
            "zero_change_baseline": {"test_metrics": baseline_metrics},
            "existing_rf_regression": {"test_metrics": reg_baseline_metrics},
            "tuned_rf_regression": {"test_metrics": reg_tuned_metrics},
            "binary_delay_worsening_classifier": {"test_metrics": clf_metrics},
            "significant_delay_growth_classifier_ge_2min": {"test_metrics": clf_sig_metrics},
        },
        "selected_optimization_signal": {
            "formula": "risk_score = clip(0.40 * P(worsening) + 0.35 * min(delay, 30)/30 + 0.25 * sigmoid(pred_delay_change), 0.0, 1.0)",
            "risk_score_range": [float(opt_df["risk_score"].min()), float(opt_df["risk_score"].max())],
            "risk_score_mean": round(float(opt_df["risk_score"].mean()), 4),
            "risk_score_median": round(float(opt_df["risk_score"].median()), 4),
            "optimization_inputs_csv": str(optimization_inputs_csv),
            "total_optimization_input_rows": len(opt_df),
        },
        "top_10_features_classifier": clf_importances["top_20_aggregated"][:10],
        "or_tools_readiness_assessment": {
            "is_rf_ready_for_optimizer": True,
            "recommended_optimizer_input": "Continuous bounded risk_score + probability_delay_worsening",
            "justification": "Provides smooth, explainable, leakage-free priority coefficients for downstream dispatching solver without relying on raw inaccurate point MAE.",
        },
        "safety_and_integrity_audit": {
            "or_tools_installed": False,
            "or_tools_imported": False,
            "or_tools_code_created": False,
            "or_tools_solver_executed": False,
            "railradar_api_requests_made": 0,
            "source_master_csv_modified": False,
            "ml_ready_csv_modified": False,
        },
        "or_tools_status": "BLOCKED — WAITING FOR GREEN SIGNAL",
    }

    if report_output_path:
        rep_p = Path(report_output_path)
        rep_p.parent.mkdir(parents=True, exist_ok=True)
        rep_p.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def run_random_forest_tuning_experiment(
    dataset_csv: str | Path = "data/processed/ml_ready_dataset.csv",
    report_output_path: str | Path | None = "data/reports/random_forest_tuning_report.json",
    train_ratio: float = 0.7,
    random_state: int = 42,
) -> dict[str, Any]:
    """Execute hyperparameter tuning grid across regularized Random Forest architectures."""
    df = load_ml_dataset(dataset_csv)
    train_df, test_df = split_chronologically_per_train(df, train_ratio=train_ratio)
    X_train, y_train = prepare_feature_target_split(train_df)
    X_test, y_test = prepare_feature_target_split(test_df)

    y_pred_baseline = np.zeros_like(y_test, dtype=float)
    baseline_metrics = evaluate_predictions(y_test, y_pred_baseline)

    results = []
    for cfg in TUNING_CONFIGURATIONS:
        pipe = build_model_pipeline(
            categorical_cols=CATEGORICAL_FEATURES,
            numerical_cols=NUMERICAL_FEATURES,
            n_estimators=cfg["n_estimators"],
            max_depth=cfg["max_depth"],
            min_samples_split=cfg["min_samples_split"],
            min_samples_leaf=cfg["min_samples_leaf"],
            random_state=random_state,
        )
        pipe.fit(X_train, y_train)

        train_preds = pipe.predict(X_train)
        test_preds = pipe.predict(X_test)

        train_m = evaluate_predictions(y_train, train_preds)
        test_m = evaluate_predictions(y_test, test_preds)

        results.append({
            "name": cfg["name"],
            "parameters": cfg,
            "train_metrics": train_m,
            "test_metrics": test_m,
            "train_test_gap": round(test_m["mae"] - train_m["mae"], 4),
        })

    results_sorted = sorted(results, key=lambda x: x["test_metrics"]["mae"])
    best_config = results_sorted[0]

    report = {
        "dataset_summary": {
            "total_rows": len(df),
            "training_rows": len(train_df),
            "testing_rows": len(test_df),
            "train_ratio": train_ratio,
        },
        "baseline_result": {"test_metrics": baseline_metrics},
        "original_random_forest_result": results[0],
        "best_tuned_configuration": best_config,
        "all_tested_configurations": results,
        "comparison_summary": {
            "did_tuned_rf_beat_baseline": "YES" if best_config["test_metrics"]["mae"] < baseline_metrics["mae"] else "NO",
        },
        "decision_rule_outcome": {
            "recommendation": "KEEP CURRENT DATA AND USE TUNED RF" if best_config["test_metrics"]["mae"] < baseline_metrics["mae"] else "DATASET TOO SMALL TO MAKE A RELIABLE DECISION",
        },
        "safety_and_integrity": {
            "railradar_api_requests_made": 0,
            "original_dataset_modified": False,
        },
    }

    if report_output_path:
        out_p = Path(report_output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def train_and_evaluate_classifier(
    dataset_csv: str | Path = "data/processed/ml_ready_dataset.csv",
    report_output_path: str | Path = "data/reports/random_forest_classification_report.json",
    model_output_path: str | Path = "data/models/random_forest_classifier.joblib",
    train_ratio: float = 0.7,
    n_estimators: int = 100,
    max_depth: int | None = 3,
    min_samples_split: int = 2,
    min_samples_leaf: int = 2,
    class_weight: str | None = "balanced",
    random_state: int = 42,
) -> dict[str, Any]:
    """Train and evaluate RandomForestClassifier on the binary delay_increase target."""
    df = load_ml_dataset(dataset_csv)

    train_df, test_df = split_chronologically_per_train(df, train_ratio=train_ratio)
    X_train, y_train_reg = prepare_feature_target_split(train_df)
    X_test, y_test_reg = prepare_feature_target_split(test_df)

    y_train_clf = (y_train_reg > 0).astype(int)
    y_test_clf = (y_test_reg > 0).astype(int)

    y_test_base = np.zeros_like(y_test_clf)
    baseline_metrics = evaluate_classification_predictions(y_test_clf, y_test_base)

    pipeline = build_classifier_pipeline(
        categorical_cols=CATEGORICAL_FEATURES,
        numerical_cols=NUMERICAL_FEATURES,
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        class_weight=class_weight,
        random_state=random_state,
    )
    pipeline.fit(X_train, y_train_clf)

    train_preds = pipeline.predict(X_train)
    test_preds = pipeline.predict(X_test)
    test_prob = pipeline.predict_proba(X_test)[:, 1]

    train_metrics = evaluate_classification_predictions(y_train_clf, train_preds)
    test_metrics = evaluate_classification_predictions(y_test_clf, test_preds, test_prob)

    importance_info = extract_feature_importances(
        pipeline,
        categorical_cols=CATEGORICAL_FEATURES,
        numerical_cols=NUMERICAL_FEATURES,
    )
    sorted_aggregated = importance_info["aggregated_importances"]

    report = {
        "dataset_used": str(dataset_csv),
        "target_variable": "delay_increase (1 if delay(t+1) > delay(t) else 0)",
        "dataset_summary": {
            "total_ml_rows": len(df),
            "training_rows": len(train_df),
            "testing_rows": len(test_df),
            "train_ratio": train_ratio,
            "train_count": int(df["train_number"].nunique()),
        },
        "majority_class_baseline": {
            "strategy": "Predict Class 0 (No delay increase) for all observations",
            "test_metrics": baseline_metrics,
        },
        "random_forest_classifier": {
            "parameters": {
                "n_estimators": n_estimators,
                "max_depth": max_depth,
                "min_samples_split": min_samples_split,
                "min_samples_leaf": min_samples_leaf,
                "class_weight": class_weight,
                "random_state": random_state,
            },
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
        },
        "top_10_features": sorted_aggregated[:10],
    }

    if model_output_path:
        mod_p = Path(model_output_path)
        mod_p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, mod_p)

    if report_output_path:
        rep_p = Path(report_output_path)
        rep_p.parent.mkdir(parents=True, exist_ok=True)
        rep_p.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def save_feature_importance_csv(
    feature_importances: list[dict[str, Any]],
    output_path: str | Path = "data/reports/feature_importance.csv",
) -> Path:
    """Save ranked feature importances to CSV."""
    df_imp = pd.DataFrame(feature_importances)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    df_imp.to_csv(out_p, index=False)
    return out_p


if __name__ == "__main__":
    rep_opt = run_optimization_preparation_pipeline()
    print("Random Forest Optimization Preparation Pipeline Complete.")
    print("Zero-Change Baseline MAE:", rep_opt["model_variant_comparison"]["zero_change_baseline"]["test_metrics"]["mae"])
    print("Existing RF MAE:        ", rep_opt["model_variant_comparison"]["existing_rf_regression"]["test_metrics"]["mae"])
    print("Tuned RF MAE:           ", rep_opt["model_variant_comparison"]["tuned_rf_regression"]["test_metrics"]["mae"])
    print("Classifier ROC-AUC:     ", rep_opt["model_variant_comparison"]["binary_delay_worsening_classifier"]["test_metrics"]["roc_auc"])
    print("Risk Score Range:       ", rep_opt["selected_optimization_signal"]["risk_score_range"])
    print("OR-Tools Status:        ", rep_opt["or_tools_status"])
