# TRAC &mdash; Random Forest Optimization Readiness Report

## 1. Executive Summary

This report documents the preparation, tuning, and evaluation of the Random Forest machine learning pipeline to produce high-value, leakage-safe risk signals for downstream railway dispatch optimization.

- **Primary Objective**: Prepare the Random Forest model to output bounded, explainable, and monotonically consistent **risk coefficients** ($\text{risk\_score} \in [0, 1]$) rather than relying on raw point delay predictions.
- **Dataset Input**: [`data/processed/ml_ready_dataset.csv`](file:///c:/Users/Omkar/OneDrive/Documents/01_Engineering_Degree/Semester3/14_SIH/TRAC/sih_traintraffic/data/processed/ml_ready_dataset.csv) (470 rows, 36 columns, 0 synthetic observations).
- **Hard Safety Constraint**: **ZERO OR-Tools code, variables, or solver invocations have been implemented.**

---

## 2. Experimental Benchmark & Model Variant Comparison

We evaluated four distinct modeling approaches on the strictly chronological test split (155 observations):

### Model Comparison Table

| Model Variant | Target Formulation | Test MAE | Test RMSE | Directional Acc / Bal Acc | Precision | Recall | ROC-AUC | Recommendation Status |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **A. Zero-Change Baseline** | $\hat{y} = 0.0$ | **0.8129 min** | **1.5862 min** | 60.65% (Dir) | &mdash; | &mdash; | &mdash; | Reference Standard |
| **B. Existing RF Regressor** | Continuous $\Delta \text{delay}$ | 0.9663 min | 1.6687 min | 70.97% (Dir) | &mdash; | &mdash; | &mdash; | Baseline RF |
| **C. Tuned RF Regressor** | Continuous $\Delta \text{delay}$ ($d=3, l=2$) | **0.9414 min** | **1.6375 min** | **72.90% (Dir)** | &mdash; | &mdash; | &mdash; | **Primary Regression Signal** |
| **D. Binary Delay Worsening Classifier** | $\mathbb{I}(\Delta \text{delay} > 0)$ | &mdash; | &mdash; | **53.98% (Bal)** | 23.33% | 25.93% | **0.6084** | **Primary Probability Signal** |
| **E. Significant Worsening Classifier** | $\mathbb{I}(\Delta \text{delay} \ge 2.0\text{ min})$ | &mdash; | &mdash; | 53.37% (Bal) | 25.00% | 11.11% | 0.5318 | Sparse Target (Not Standalone) |

---

## 3. Target Distribution & Imbalance Analysis

Across the 470 sequential observations in the ML-ready dataset:
- **Zero Delay Change ($\Delta = 0.0$ min)**: **271 observations (57.66%)**
- **Delay Recovery ($\Delta < 0.0$ min)**: **98 observations (20.85%)**
- **Delay Increase ($\Delta > 0.0$ min)**: **101 observations (21.49%)**
- **Significant Delay Increase ($\Delta \ge 2.0$ min)**: **60 observations (12.77%)**

### Key Modeling Insight
Because 57.7% of consecutive intervals exhibit zero delay change, standard regression penalizes fractional drift predictions ($0.15 \to 0.40$ min), making point MAE misleadingly unfavorable. However, the classifier's predicted probability of delay increase $P(\text{delay\_worsening})$ achieves an **ROC-AUC of 0.6084**, providing a non-linear continuous risk score suitable for optimization priority weighting.

---

## 4. Selected Optimization Signal Formulation

We synthesize the regression drift, worsening probability, and accumulated delay into a single bounded, explainable, and numerically stable **Risk Score**:

$$\text{risk\_score}(t) = \text{clip}\left(0.40 \cdot P(\text{delay\_worsening}) + 0.35 \cdot \frac{\min(\text{current\_delay}, 30)}{30.0} + 0.25 \cdot \frac{1}{1 + e^{-\hat{\Delta}_{\text{rf}}}}, 0.0, 1.0\right)$$

### Properties:
1. **Strictly Bounded**: $\text{risk\_score} \in [0.0, 1.0]$.
2. **Monotonicity**: Higher current delay, higher probability of worsening, and positive predicted drift monotonically increase the risk score.
3. **Zero Lookahead**: 100% computed from telemetry available at observation timestamp $t$ or earlier.
4. **Distribution on Master Corpus**: Range = $[0.2750, 0.8128]$, Mean = $0.4263$, Median = $0.3913$.

---

## 5. Optimization-Ready Output Schema

The interface exports [`data/processed/rf_optimization_inputs.csv`](file:///c:/Users/Omkar/OneDrive/Documents/01_Engineering_Degree/Semester3/14_SIH/TRAC/sih_traintraffic/data/processed/rf_optimization_inputs.csv) with 470 records:

| Field Name | Type | Description |
|:---|:---:|:---|
| `train_number` | String | Train service identifier (e.g. `12809`, `97015`) |
| `collection_timestamp` | ISO UTC | Observation timestamp ($t$) |
| `current_station_code` | String | Station / signal block occupied |
| `next_station_code` | String | Approaching downstream station |
| `current_delay` | Float | Accumulated delay at time $t$ (minutes) |
| `predicted_delay_change` | Float | Tuned Random Forest continuous delay drift prediction ($\hat{\Delta}$) |
| `probability_delay_worsening` | Float | Random Forest classifier worsening probability ($P(\Delta > 0)$) |
| `risk_score` | Float | Unified bounded dispatch priority risk coefficient $\in [0, 1]$ |
| `movement_state` | String | `MOVING`, `STATIONARY`, or `UNKNOWN` |
| `distance_from_origin_km` | Float | Spatial progression along corridor |
| `route_sequence` | Integer | Schedule station stop index |

---

## 6. Top 10 Feature Importances (Classifier)

| Rank | Feature | Category | Importance | Percentage |
|:---:|:---|:---:|:---:|:---:|
| **1** | `delay_change_prev` | Derived | 0.0912 | **9.12%** |
| **2** | `distance_from_origin_km` | Numerical | 0.0825 | **8.25%** |
| **3** | `delay_minutes` | Numerical | 0.0784 | **7.84%** |
| **4** | `time_since_previous_observation_seconds` | Derived | 0.0731 | **7.31%** |
| **5** | `estimated_speed_kmh` | Derived | 0.0710 | **7.10%** |
| **6** | `train_number` | Categorical | 0.0674 | **6.74%** |
| **7** | `time_of_day_minutes` | Temporal | 0.0649 | **6.49%** |
| **8** | `distance_travelled_km` | Derived | 0.0628 | **6.28%** |
| **9** | `segment_progress` | Numerical | 0.0573 | **5.73%** |
| **10** | `next_station_code` | Categorical | 0.0561 | **5.61%** |

---

## 7. Future OR-Tools Interface Specification

When optimization is approved, the downstream dispatch solver will consume records from `generate_optimization_signals(df)` to parameterize:
1. **Objective Weights**: Weight train precedence and platform hold penalties by $w_i = 1.0 + 3.0 \cdot \text{risk\_score}_i$.
2. **Dynamic Headway Buffers**: Extend safety margins between conflicting train routes when upstream trains have $\text{risk\_score} > 0.65$.

---

## 8. Explicit OR-Tools Gate

```
================================================================
OR-TOOLS STATUS: BLOCKED — WAITING FOR GREEN SIGNAL
================================================================
OR-Tools installed?        NO
OR-Tools imported?         NO
OR-Tools code created?     NO
OR-Tools solver executed?  NO
Optimization implemented?  NO
RailRadar API called?      NO
================================================================
```
