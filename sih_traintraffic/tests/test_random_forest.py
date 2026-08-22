"""Comprehensive unit tests for Random Forest Regressor & Classifier, optimization preparation, and leakage safety."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from railradar.ml_random_forest import (
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
    TARGET_COLUMN,
    build_classifier_pipeline,
    build_model_pipeline,
    build_preprocessor,
    calculate_risk_score,
    evaluate_classification_predictions,
    evaluate_predictions,
    extract_feature_importances,
    generate_optimization_signals,
    load_ml_dataset,
    prepare_feature_target_split,
    run_optimization_preparation_pipeline,
    split_chronologically_per_train,
    train_and_evaluate_classifier,
    train_and_evaluate_random_forest,
)

ML_DATASET_CSV = Path("data/processed/ml_ready_dataset.csv")
MODEL_PATH = Path("models/random_forest_delay_change.joblib")
CLF_MODEL_PATH = Path("models/random_forest_classifier.joblib")
REPORT_PATH = Path("data/reports/random_forest_report.json")
PRED_PATH = Path("data/processed/rf_test_predictions.csv")
OPT_INPUTS_PATH = Path("data/processed/rf_optimization_inputs.csv")


@pytest.fixture
def ml_df() -> pd.DataFrame:
    return load_ml_dataset(ML_DATASET_CSV)


# 1. Dataset loads
def test_1_dataset_loads(ml_df: pd.DataFrame):
    assert len(ml_df) == 470
    assert TARGET_COLUMN in ml_df.columns
    assert ml_df["train_number"].nunique() == 30
    assert ml_df["run_id"].nunique() == 4


# 2. X and y are separated correctly
def test_2_x_y_separation(ml_df: pd.DataFrame):
    X, y = prepare_feature_target_split(ml_df)
    assert len(X) == len(y) == len(ml_df)
    assert len(X.columns) == len(CATEGORICAL_FEATURES + NUMERICAL_FEATURES)
    for col in CATEGORICAL_FEATURES + NUMERICAL_FEATURES:
        assert col in X.columns


# 3. No target leakage
def test_3_no_target_leakage(ml_df: pd.DataFrame):
    X, y = prepare_feature_target_split(ml_df)
    assert TARGET_COLUMN not in X.columns
    assert "future_delay" not in X.columns
    for forbidden in ["target_delay_change", "future_delay", "next_delay"]:
        assert forbidden not in X.columns


# 4. Preprocessor fits only on training data
def test_4_preprocessor_fits_only_on_train_data(ml_df: pd.DataFrame):
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)
    X_train, y_train = prepare_feature_target_split(train_df)
    X_test, y_test = prepare_feature_target_split(test_df)

    preprocessor = build_preprocessor(CATEGORICAL_FEATURES, NUMERICAL_FEATURES)
    preprocessor.fit(X_train, y_train)

    X_train_trans = preprocessor.transform(X_train)
    X_test_trans = preprocessor.transform(X_test)

    assert X_train_trans.shape[0] == len(train_df)
    assert X_test_trans.shape[0] == len(test_df)
    assert X_train_trans.shape[1] == X_test_trans.shape[1]


# 5. Categorical encoding handles unknown categories
def test_5_categorical_encoding_handles_unknowns():
    preprocessor = build_preprocessor(CATEGORICAL_FEATURES, NUMERICAL_FEATURES)

    train_data = pd.DataFrame([{
        "train_number": "12809",
        "train_type": "Superfast",
        "train_category": "Express",
        "current_station_code": "CSMT",
        "next_station_code": "DR",
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
    }])
    preprocessor.fit(train_data)

    test_unknown_data = train_data.copy()
    test_unknown_data["current_station_code"] = "UNKNOWN_STATION_XYZ"
    test_unknown_data["train_type"] = "BRAND_NEW_TRAIN_TYPE"

    transformed = preprocessor.transform(test_unknown_data)
    assert transformed.shape[0] == 1
    assert not np.isnan(transformed).any()


# 6. Missing numerical values are handled
def test_6_missing_numerical_values_imputed(ml_df: pd.DataFrame):
    X, y = prepare_feature_target_split(ml_df)
    preprocessor = build_preprocessor(CATEGORICAL_FEATURES, NUMERICAL_FEATURES)
    transformed = preprocessor.fit_transform(X)
    assert not np.isnan(transformed).any()


# 7. Train/test split is chronological
def test_7_train_test_split_chronological(ml_df: pd.DataFrame):
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)
    assert len(train_df) + len(test_df) == len(ml_df)
    assert len(train_df) == 315
    assert len(test_df) == 155


# 8. No test timestamps precede relevant training boundary
def test_8_no_test_timestamps_precede_train(ml_df: pd.DataFrame):
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)

    for (r, t), grp in ml_df.groupby(["run_id", "train_number"]):
        train_grp = train_df[(train_df["run_id"] == r) & (train_df["train_number"] == t)]
        test_grp = test_df[(test_df["run_id"] == r) & (test_df["train_number"] == t)]

        if len(test_grp) > 0 and len(train_grp) > 0:
            max_train_ts = pd.to_datetime(train_grp["collection_timestamp"]).max()
            min_test_ts = pd.to_datetime(test_grp["collection_timestamp"]).min()
            assert max_train_ts <= min_test_ts


# 9. Model trains successfully
def test_9_model_trains_successfully(ml_df: pd.DataFrame):
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)
    X_train, y_train = prepare_feature_target_split(train_df)

    pipeline = build_model_pipeline(
        categorical_cols=CATEGORICAL_FEATURES,
        numerical_cols=NUMERICAL_FEATURES,
        n_estimators=10,
        max_depth=3,
        random_state=42,
    )
    pipeline.fit(X_train, y_train)
    assert hasattr(pipeline.named_steps["regressor"], "estimators_")


# 10. Predictions have the correct length
def test_10_predictions_correct_length(ml_df: pd.DataFrame):
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)
    X_train, y_train = prepare_feature_target_split(train_df)
    X_test, y_test = prepare_feature_target_split(test_df)

    pipeline = build_model_pipeline(n_estimators=10, max_depth=3, random_state=42)
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    assert len(preds) == len(test_df)


# 11. Predictions contain finite values
def test_11_predictions_finite(ml_df: pd.DataFrame):
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)
    X_train, y_train = prepare_feature_target_split(train_df)
    X_test, y_test = prepare_feature_target_split(test_df)

    pipeline = build_model_pipeline(n_estimators=10, max_depth=3, random_state=42)
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    assert np.isfinite(preds).all()


# 12. Evaluation metrics calculate successfully
def test_12_evaluation_metrics_calculation():
    y_true = np.array([0.0, 2.0, -1.0, 0.0, 3.0])
    y_pred = np.array([0.1, 1.8, -0.8, 0.0, 2.5])

    metrics = evaluate_predictions(y_true, y_pred)
    assert "mae" in metrics
    assert "rmse" in metrics
    assert "r2" in metrics
    assert "bias" in metrics
    assert "directional_accuracy_pct" in metrics
    assert metrics["mae"] > 0
    assert metrics["directional_accuracy_pct"] == 100.0


# 13. Saved model artifact can be loaded
def test_13_saved_model_artifact_loadable():
    assert MODEL_PATH.exists()
    loaded_pipeline = joblib.load(MODEL_PATH)
    assert isinstance(loaded_pipeline, Pipeline)
    assert "preprocessor" in loaded_pipeline.named_steps
    assert "regressor" in loaded_pipeline.named_steps


# 14. Loaded pipeline can make predictions
def test_14_loaded_pipeline_makes_predictions(ml_df: pd.DataFrame):
    loaded_pipeline = joblib.load(MODEL_PATH)
    X, _ = prepare_feature_target_split(ml_df.head(10))
    preds = loaded_pipeline.predict(X)
    assert len(preds) == 10
    assert np.isfinite(preds).all()


# 15. Risk score properties and bounds
def test_15_risk_score_properties_and_bounds():
    current_delay = np.array([0.0, 5.0, 15.0, 30.0, 60.0])
    pred_change = np.array([-2.0, 0.0, 1.0, 3.0, 5.0])
    prob_worsen = np.array([0.1, 0.3, 0.5, 0.8, 0.95])

    scores = calculate_risk_score(current_delay, pred_change, prob_worsen)
    assert len(scores) == 5
    assert not np.isnan(scores).any()
    assert (scores >= 0.0).all()
    assert (scores <= 1.0).all()
    # Monotonic increase across worst-case scenarios
    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i + 1]


# 16. Optimization signals interface function
def test_16_generate_optimization_signals_interface(ml_df: pd.DataFrame, tmp_path: Path):
    out_csv = tmp_path / "opt_test.csv"
    reg_pipe = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
    clf_pipe = joblib.load(CLF_MODEL_PATH) if CLF_MODEL_PATH.exists() else None

    signals_df = generate_optimization_signals(
        ml_df.head(20),
        reg_pipeline=reg_pipe,
        clf_pipeline=clf_pipe,
        output_csv=out_csv,
    )

    assert len(signals_df) == 20
    assert out_csv.exists()
    required_cols = [
        "train_number",
        "collection_timestamp",
        "current_station_code",
        "next_station_code",
        "current_delay",
        "predicted_delay_change",
        "probability_delay_worsening",
        "risk_score",
        "movement_state",
        "distance_from_origin_km",
        "route_sequence",
    ]
    for c in required_cols:
        assert c in signals_df.columns
    assert (signals_df["risk_score"] >= 0.0).all()
    assert (signals_df["risk_score"] <= 1.0).all()


# 17. Classifier training and evaluation
def test_17_classifier_pipeline(ml_df: pd.DataFrame):
    train_df, test_df = split_chronologically_per_train(ml_df, train_ratio=0.7)
    X_train, y_train = prepare_feature_target_split(train_df)
    X_test, y_test = prepare_feature_target_split(test_df)

    y_train_clf = (y_train > 0).astype(int)
    y_test_clf = (y_test > 0).astype(int)

    clf_pipe = build_classifier_pipeline(n_estimators=10, max_depth=3, random_state=42)
    clf_pipe.fit(X_train, y_train_clf)

    preds = clf_pipe.predict(X_test)
    probs = clf_pipe.predict_proba(X_test)[:, 1]

    metrics = evaluate_classification_predictions(y_test_clf, preds, probs)
    assert "accuracy" in metrics
    assert "balanced_accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert metrics["accuracy"] >= 0.0


# 18. Full optimization preparation pipeline execution
def test_18_optimization_preparation_pipeline():
    assert OPT_INPUTS_PATH.exists()
    opt_df = pd.read_csv(OPT_INPUTS_PATH)
    assert len(opt_df) == 470
    assert not opt_df["risk_score"].isnull().any()
    assert (opt_df["risk_score"] >= 0.0).all()
    assert (opt_df["risk_score"] <= 1.0).all()


# 19. Hard safety check: OR-Tools must NOT be installed or imported
def test_19_hard_safety_check_no_ortools():
    import sys
    assert "ortools" not in sys.modules
