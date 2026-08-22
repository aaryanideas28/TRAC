"""Reproducible End-to-End ML + Optimization Pipeline for Nexora.

Pipeline Stages:
1. Load Master RailRadar Observation Dataset
2. Pandas Preprocessing & Stale Filtering
3. Sequential & Temporal Feature Engineering (Grouped by Train & Run)
4. Leakage-Safe Chronological Train/Test Split
5. Random Forest Regression (Predict Delay Change) & Baseline Benchmarking
6. Random Forest Classification (Predict Delay Increase Risk) & Baseline Benchmarking
7. Feature Importance Ranking & CSV Generation
8. Station Platform & Dispatch Optimization (MILP Solver)
9. Final Traffic Decision Generation

100% Offline: 0 External API Calls Made.
"""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import numpy as np

from railradar.ml_preprocessing import run_preprocessing_pipeline
from railradar.ml_random_forest import (
    train_and_evaluate_random_forest,
    train_and_evaluate_classifier,
    save_feature_importance_csv,
    load_ml_dataset,
    prepare_feature_target_split,
    split_chronologically_per_train,
)
from railradar.optimization import (
    StationTrafficOptimizer,
    TrainTrafficRequest,
    recommend_traffic_decisions,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_full_pipeline() -> dict:
    print("=" * 80)
    print("NEXORA: END-TO-END ML & TRAIN TRAFFIC OPTIMIZATION PIPELINE")
    print("=" * 80)

    # 1. Paths
    master_csv = PROJECT_ROOT / "data" / "processed" / "live_observations_master.csv"
    ml_ready_csv = PROJECT_ROOT / "data" / "processed" / "ml_ready_dataset.csv"
    feature_spec_json = PROJECT_ROOT / "data" / "reports" / "ml_feature_spec.json"
    prep_report_json = PROJECT_ROOT / "data" / "reports" / "ml_preprocessing_report.json"
    rf_reg_report_json = PROJECT_ROOT / "data" / "reports" / "random_forest_report.json"
    rf_clf_report_json = PROJECT_ROOT / "data" / "reports" / "random_forest_classification_report.json"
    feat_imp_csv = PROJECT_ROOT / "data" / "reports" / "feature_importance.csv"
    reg_model_path = PROJECT_ROOT / "data" / "models" / "random_forest_pipeline.joblib"
    clf_model_path = PROJECT_ROOT / "data" / "models" / "random_forest_classifier.joblib"

    # 2. Preprocessing
    print("\n[Stage 1/5] Executing Pandas Preprocessing on Master CSV...")
    ml_df, prep_report = run_preprocessing_pipeline(
        input_csv=master_csv,
        output_csv=ml_ready_csv,
        feature_spec_json=feature_spec_json,
        report_json=prep_report_json,
    )
    print(f"  [OK] Master Observations Processed: {prep_report['original_rows']}")
    print(f"  [OK] Stale Observations Excluded: {prep_report['stale_rows']}")
    print(f"  [OK] Valid ML-Ready Sequential Observations: {prep_report['final_ml_row_count']}")
    print(f"  [OK] Unique Trains: {prep_report['train_count']} | Unique Stations: {prep_report['unique_stations_count']}")

    # 3. Random Forest Regression Experiment
    print("\n[Stage 2/5] Training Random Forest Regressor (target: target_delay_change)...")
    reg_report = train_and_evaluate_random_forest(
        dataset_csv=ml_ready_csv,
        report_output_path=rf_reg_report_json,
        model_output_path=reg_model_path,
        n_estimators=100,
        max_depth=3,
        min_samples_split=2,
        min_samples_leaf=2,
        train_ratio=0.7,
    )
    base_reg = reg_report["baseline_model"]["test_metrics"]
    rf_reg = reg_report["random_forest_model"]["test_metrics"]
    rf_train_reg = reg_report["random_forest_model"]["train_metrics"]
    mae_gap = round(float(rf_reg["mae"] - rf_train_reg["mae"]), 4)
    print(f"  [OK] Zero-Change Baseline Test: MAE = {base_reg['mae']}, RMSE = {base_reg['rmse']}, R2 = {base_reg['r2']}")
    print(f"  [OK] Random Forest Regressor Test: MAE = {rf_reg['mae']}, RMSE = {rf_reg['rmse']}, R2 = {rf_reg['r2']}")
    print(f"  [OK] Regressor Train/Test Gap: Train MAE = {rf_train_reg['mae']} vs Test MAE = {rf_reg['mae']} (Gap = {mae_gap})")


    # 4. Random Forest Classification Experiment
    print("\n[Stage 3/5] Training Random Forest Classifier (target: delay_increase)...")
    clf_report = train_and_evaluate_classifier(
        dataset_csv=ml_ready_csv,
        report_output_path=rf_clf_report_json,
        model_output_path=clf_model_path,
        n_estimators=100,
        max_depth=3,
        min_samples_split=2,
        min_samples_leaf=2,
        class_weight="balanced",
        train_ratio=0.7,
    )
    base_clf = clf_report["majority_class_baseline"]["test_metrics"]
    rf_clf = clf_report["random_forest_classifier"]["test_metrics"]
    print(f"  [OK] Majority Baseline Test: Acc = {base_clf['accuracy']}, F1 = {base_clf['f1']}")
    print(f"  [OK] RF Classifier Test: Acc = {rf_clf['accuracy']}, Precision = {rf_clf['precision']}, Recall = {rf_clf['recall']}, F1 = {rf_clf['f1']}")
    print(f"  [OK] Confusion Matrix: {rf_clf['confusion_matrix']}")

    # 5. Save Feature Importance CSV
    print("\n[Stage 4/5] Exporting Top Feature Importances...")
    save_feature_importance_csv(clf_report["top_10_features"], feat_imp_csv)
    print("  [OK] Top 5 Predictive Features:")
    for idx, f in enumerate(clf_report["top_10_features"][:5], start=1):
        print(f"    {idx}. {f['feature']:<38} : {f['percentage']}% importance")

    # 6. Station Traffic Optimization Demonstration
    print("\n[Stage 5/5] Running MILP Station Platform & Dispatch Optimization...")
    # Select the 5 most recent distinct active trains from the dataset
    recent_sample = ml_df.drop_duplicates(subset=["train_number"], keep="last").tail(5).copy()
    
    # Generate requests with ML delay risk predictions
    import joblib
    clf_model = joblib.load(clf_model_path)
    X_sample, _ = prepare_feature_target_split(recent_sample)
    risk_probs = clf_model.predict_proba(X_sample)[:, 1]
    
    traffic_requests = []
    for idx, (row, risk) in enumerate(zip(recent_sample.itertuples(), risk_probs)):
        t_type = getattr(row, "train_type", "EMU")
        priority = 3.0 if "superfast" in str(t_type).lower() or "mail" in str(t_type).lower() else (
            2.0 if "fast" in str(t_type).lower() else 1.0
        )
        traffic_requests.append(
            TrainTrafficRequest(
                train_number=str(getattr(row, "train_number", f"T{idx}")),
                train_name=str(getattr(row, "train_name", f"Train {idx}")),
                train_type=str(t_type),
                arrival_time_min=idx * 1.5,
                dwell_time_min=2.0,
                delay_minutes=float(getattr(row, "delay_minutes", 0.0)),
                predicted_delay_change=0.0,
                delay_risk_prob=float(risk),
                priority_weight=priority,
            )
        )

    optimizer = StationTrafficOptimizer(default_platforms=2, min_headway_min=2.0)
    opt_result = optimizer.solve(traffic_requests, platforms=2, min_headway_min=2.0)

    print(f"  [OK] Solver Status: {opt_result.status.upper()} (Backend: {opt_result.solver_backend})")
    print(f"  [OK] Total Weighted Delay Penalty: {opt_result.total_delay_penalty}")
    print(f"  [OK] Total Station Hold Delay: {opt_result.total_hold_delay_minutes} minutes")

    print("\n  Optimized Platform & Dispatch Schedule:")
    print("  " + "-" * 110)
    print(f"  {'Plat':<6} {'Arr(m)':<8} {'Dep(m)':<8} {'Hold(m)':<8} {'Train No':<10} {'Train Name':<32} {'Risk':<8} {'Action Note'}")
    print("  " + "-" * 110)
    for s in opt_result.schedule:
        print(f"  P{s.assigned_platform:<4} {s.scheduled_arrival_min:<8.2f} {s.scheduled_departure_min:<8.2f} {s.station_hold_delay_min:<8.2f} {s.train_number:<10} {s.train_name[:30]:<32} {s.delay_risk_score:<8.2f} {s.recommendation_note}")
    print("  " + "-" * 110)

    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
    print("=" * 80)

    return {
        "preprocessing_report": prep_report,
        "regression_report": reg_report,
        "classification_report": clf_report,
        "optimization_result": opt_result.to_dict(),
    }


if __name__ == "__main__":
    run_full_pipeline()
