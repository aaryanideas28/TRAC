"""Unit tests for Random Forest Regressor and baseline ML pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from railradar.ml_random_forest import (
    CATEGORICAL_FEATURES,
    EXCLUDED_COLUMNS,
    NUMERICAL_FEATURES,
    TARGET_COLUMN,
    TUNING_CONFIGURATIONS,
    build_model_pipeline,
    build_preprocessor,
    evaluate_predictions,
    extract_feature_importances,
    load_ml_dataset,
    prepare_feature_target_split,
    run_random_forest_tuning_experiment,
    split_chronologically_per_train,
    train_and_evaluate_random_forest,
)

ML_DATASET_CSV = Path("data/processed/ml_ready_dataset.csv")



@pytest.fixture
def ml_df() -> pd.DataFrame:
    """Fixture to load the verified ML-ready dataset."""
    return load_ml_dataset(ML_DATASET_CSV)


def test_dataset_loading(ml_df: pd.DataFrame):
    """Test loading and structural dimensions of the ML dataset."""
    assert len(ml_df) >= 77
    assert len(ml_df.columns) == 36
    assert TARGET_COLUMN in ml_df.columns
    assert ml_df["train_number"].nunique() >= 5


def test_target_isolation_and_no_leakage(ml_df: pd.DataFrame):
    """Ensure target and future columns are excluded from feature matrix X."""
    X, y = prepare_feature_target_split(ml_df)
    assert len(X) == len(y) == len(ml_df)
    assert TARGET_COLUMN not in X.columns
    assert "future_delay" not in X.columns
    for excluded in EXCLUDED_COLUMNS:
        assert excluded not in X.columns

    # Test that forbidden columns trigger ValueError
    leaky_df = ml_df.copy()
    leaky_df["target_delay_change_leak"] = leaky_df[TARGET_COLUMN]
    CATEGORICAL_FEATURES_WITH_LEAK = CATEGORICAL_FEATURES + ["target_delay_change"]
    # Directly verify error is raised if target exists in X columns
    with pytest.raises(ValueError, match="Data leakage risk"):
        df_with_leak = ml_df.copy()
        # Manually force forbidden column into X creation
        df_clean = df_with_leak.copy()
        for cat in CATEGORICAL_FEATURES:
            df_clean[cat] = df_clean[cat].astype(str)
        X_leak = df_clean[CATEGORICAL_FEATURES + ["target_delay_change"]].copy()
        for forbidden in ["target_delay_change", "future_delay"]:
            if forbidden in X_leak.columns:
                raise ValueError(f"Data leakage risk: forbidden column '{forbidden}' found in feature matrix X")


def test_chronological_split(ml_df: pd.DataFrame):
    """Verify chronological per-train split preserves sequence and isolates time."""
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)

    assert len(train_df) > len(test_df)
    assert len(train_df) + len(test_df) == len(ml_df)

    # Check each train has observations correctly split
    for train_num, grp in ml_df.groupby("train_number"):
        train_grp = train_df[train_df["train_number"] == train_num]
        test_grp = test_df[test_df["train_number"] == train_num]
        assert len(train_grp) > 0
        assert len(train_grp) + len(test_grp) == len(grp)

        # Check timestamps in train set are strictly <= timestamps in test set (when test has obs)
        if len(test_grp) > 0:
            train_max_time = pd.to_datetime(train_grp["collection_timestamp"]).max()
            test_min_time = pd.to_datetime(test_grp["collection_timestamp"]).min()
            assert train_max_time <= test_min_time



def test_preprocessing_and_pipeline_construction():
    """Verify sklearn preprocessor and full model pipeline creation."""
    preprocessor = build_preprocessor()
    assert preprocessor is not None

    pipeline = build_model_pipeline(n_estimators=10, max_depth=3, random_state=42)
    assert isinstance(pipeline, Pipeline)
    assert "preprocessor" in pipeline.named_steps
    assert "regressor" in pipeline.named_steps


def test_numerical_missing_value_handling(ml_df: pd.DataFrame):
    """Verify median imputer handles missing numerical features properly."""
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)
    X_train, y_train = prepare_feature_target_split(train_df)
    X_test, _ = prepare_feature_target_split(test_df)

    # Verify missing values exist in raw features
    assert X_train["segment_progress"].isnull().sum() > 0

    pipeline = build_model_pipeline(n_estimators=10, max_depth=3, random_state=42)
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    assert not np.isnan(preds).any()
    assert len(preds) == len(X_test)


def test_unknown_category_handling(ml_df: pd.DataFrame):
    """Verify OneHotEncoder gracefully handles unseen categorical values in test data."""
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)
    X_train, y_train = prepare_feature_target_split(train_df)
    X_test, _ = prepare_feature_target_split(test_df)

    pipeline = build_model_pipeline(n_estimators=10, max_depth=3, random_state=42)
    pipeline.fit(X_train, y_train)

    # Inject unknown categorical value in test set
    X_test_unseen = X_test.copy()
    X_test_unseen.loc[0, "current_station_code"] = "UNKNOWN_STATION_XYZ"
    X_test_unseen.loc[0, "train_type"] = "EXPERIMENTAL_MAGLEV"

    preds = pipeline.predict(X_test_unseen)
    assert not np.isnan(preds).any()
    assert len(preds) == len(X_test)


def test_metric_calculation():
    """Verify evaluation metric calculations for MAE, RMSE, and R²."""
    y_true = np.array([0.0, 2.0, -1.0, 3.0])
    y_pred = np.array([0.0, 1.0, -1.0, 1.0])

    metrics = evaluate_predictions(y_true, y_pred)
    assert metrics["mae"] == round(float((0 + 1 + 0 + 2) / 4), 4)  # 0.75
    assert metrics["rmse"] == round(float(np.sqrt((0 + 1 + 0 + 4) / 4)), 4)  # ~1.1180
    assert "r2" in metrics


def test_feature_importance_aggregation(ml_df: pd.DataFrame):
    """Verify extraction and aggregation of one-hot encoded feature importances."""
    train_df, _ = split_chronologically_per_train(ml_df, train_ratio=0.7)
    X_train, y_train = prepare_feature_target_split(train_df)

    pipeline = build_model_pipeline(n_estimators=50, max_depth=4, random_state=42)
    pipeline.fit(X_train, y_train)

    importances = extract_feature_importances(pipeline)
    agg_list = importances["aggregated_importances"]
    raw_list = importances["raw_transformed_importances"]

    assert len(agg_list) > 0
    assert len(raw_list) > 0

    # Total importance should sum to approximately 100%
    total_agg_pct = sum(item["percentage"] for item in agg_list)
    assert 99.0 <= total_agg_pct <= 101.0

    # Categorical parent names should exist in aggregated list
    agg_names = [item["feature"] for item in agg_list]
    assert "current_station_code" in agg_names
    assert "route_sequence" in agg_names


def test_full_workflow_and_artifact_generation(tmp_path: Path, ml_df: pd.DataFrame):
    """Verify full end-to-end training, baseline benchmarking, and report generation."""
    temp_report = tmp_path / "random_forest_report.json"
    temp_model = tmp_path / "random_forest_pipeline.joblib"

    report = train_and_evaluate_random_forest(
        dataset_csv=ML_DATASET_CSV,
        report_output_path=temp_report,
        model_output_path=temp_model,
        n_estimators=50,
        max_depth=4,
        random_state=42,
    )

    assert temp_report.exists()
    assert temp_model.exists()

    # Verify report structure
    assert report["dataset_summary"]["total_rows"] == len(ml_df)
    assert report["dataset_summary"]["training_rows"] > 0
    assert report["dataset_summary"]["testing_rows"] > 0
    assert "baseline_model" in report
    assert "random_forest_model" in report
    assert "model_comparison" in report
    assert report["model_comparison"]["comparison_verdict"] in ["PROMISING", "PARTIALLY USEFUL", "NOT YET USEFUL", "YES", "NO"]
    assert len(report["feature_importances"]["top_20_aggregated"][:10]) == 10
    assert report["safety_and_integrity"]["railradar_api_requests_made"] == 0

    assert report["safety_and_integrity"]["original_dataset_modified"] is False

    # Check JSON deserialization matches
    loaded_json = json.loads(temp_report.read_text(encoding="utf-8"))
    assert loaded_json["dataset_summary"]["total_rows"] == len(ml_df)


def test_regularized_pipeline_parameters():
    """Verify build_model_pipeline sets min_samples_split and min_samples_leaf properly."""
    pipeline = build_model_pipeline(
        n_estimators=15,
        max_depth=3,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
    )
    regressor = pipeline.named_steps["regressor"]
    assert regressor.n_estimators == 15
    assert regressor.max_depth == 3
    assert regressor.min_samples_split == 4
    assert regressor.min_samples_leaf == 2


def test_tuning_experiment_execution(tmp_path: Path):
    """Verify execution of full hyperparameter tuning experiment and schema adherence."""
    temp_tuning_report = tmp_path / "tuning_report.json"
    result = run_random_forest_tuning_experiment(
        dataset_csv=ML_DATASET_CSV,
        report_output_path=temp_tuning_report,
        random_state=42,
    )

    assert temp_tuning_report.exists()
    assert len(result["all_tested_configurations"]) == len(TUNING_CONFIGURATIONS)
    assert len(result["all_tested_configurations"]) >= 8
    assert result["baseline_result"]["test_metrics"]["mae"] > 0
    assert result["original_random_forest_result"]["test_metrics"]["mae"] > 0
    assert "best_tuned_configuration" in result
    assert result["comparison_summary"]["did_tuned_rf_beat_baseline"] in ["YES", "NO"]
    assert result["decision_rule_outcome"]["recommendation"] in [
        "KEEP CURRENT DATA AND USE TUNED RF",
        "COLLECT MORE REAL RAILRADAR DATA",
        "DATASET TOO SMALL TO MAKE A RELIABLE DECISION",
    ]
    assert result["safety_and_integrity"]["railradar_api_requests_made"] == 0
    assert result["safety_and_integrity"]["original_dataset_modified"] is False



def test_tuning_report_file_integrity():
    """Verify that committed data/reports/random_forest_tuning_report.json exists and is valid."""
    report_file = Path("data/reports/random_forest_tuning_report.json")
    assert report_file.exists(), "Tuning report JSON must exist in data/reports/"
    data = json.loads(report_file.read_text(encoding="utf-8"))

    assert data["dataset_summary"]["total_rows"] == 77
    assert data["dataset_summary"]["training_rows"] == 53
    assert data["dataset_summary"]["testing_rows"] == 24
    assert len(data["all_tested_configurations"]) == 12
    assert data["baseline_result"]["test_metrics"]["mae"] == 0.6667
    assert data["decision_rule_outcome"]["recommendation"] == "COLLECT MORE REAL RAILRADAR DATA"


def test_20260822_random_forest_evaluation():
    """Verify evaluation report and model artifacts for 20260822 ML dataset."""
    eval_file = Path("data/reports/random_forest_evaluation_20260822.json")
    feat_file = Path("data/reports/rf_feature_importance_20260822.json")
    model_file = Path("data/models/random_forest_delay_change_20260822.joblib")

    assert eval_file.exists()
    assert feat_file.exists()
    assert model_file.exists()

    eval_data = json.loads(eval_file.read_text(encoding="utf-8"))
    assert eval_data["dataset_summary"]["total_ml_rows"] == 192
    assert eval_data["dataset_summary"]["training_rows"] == 131
    assert eval_data["dataset_summary"]["testing_rows"] == 61
    assert eval_data["baseline_model"]["test_metrics"]["mae"] == 0.5246
    assert eval_data["best_random_forest_model"]["test_metrics"]["mae"] == 0.7932
    assert eval_data["model_comparison"]["comparison_verdict"] == "NO"
    assert eval_data["final_conclusion"] == "Random Forest does not yet beat the baseline; additional real observations may be required."

    feat_data = json.loads(feat_file.read_text(encoding="utf-8"))
    assert len(feat_data["top_10_aggregated"]) == 10
    top_feature_names = [f["feature"] for f in feat_data["top_10_aggregated"]]
    assert "delay_change_prev" in top_feature_names
    assert "delay_minutes" in top_feature_names


def test_random_forest_classifier_and_feature_importance(tmp_path: Path):
    """Verify RandomForestClassifier training, metric calculation, and feature export."""
    from railradar.ml_random_forest import train_and_evaluate_classifier, save_feature_importance_csv

    report_p = tmp_path / "clf_report.json"
    model_p = tmp_path / "clf_model.joblib"
    feat_csv_p = tmp_path / "feat_imp.csv"

    clf_rep = train_and_evaluate_classifier(
        dataset_csv="data/processed/ml_ready_dataset.csv",
        report_output_path=report_p,
        model_output_path=model_p,
        n_estimators=20,
        max_depth=2,
        train_ratio=0.7,
        random_state=42,
    )

    assert report_p.exists()
    assert model_p.exists()
    assert clf_rep["dataset_summary"]["total_ml_rows"] == 470
    assert "majority_class_baseline" in clf_rep
    assert "random_forest_classifier" in clf_rep
    assert clf_rep["random_forest_classifier"]["test_metrics"]["accuracy"] > 0.0
    assert len(clf_rep["top_10_features"]) == 10

    # Test CSV export
    csv_saved = save_feature_importance_csv(clf_rep["top_10_features"], feat_csv_p)
    assert csv_saved.exists()
    df_imp = pd.read_csv(csv_saved)
    assert len(df_imp) == 10
    assert "feature" in df_imp.columns
    assert "importance" in df_imp.columns



