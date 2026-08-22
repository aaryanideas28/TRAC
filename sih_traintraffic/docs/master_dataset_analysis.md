# Nexora Master Dataset Analysis & Feature Engineering Report

## 1. Master Dataset Summary

The canonical master dataset is:
`data/processed/live_observations_master.csv`

This dataset consolidates multiple genuine live telemetry collection runs from the Central Line Mumbai suburban railway corridor via the RailRadar API:

- **Total Canonical Rows**: **798 genuine observations** (0% synthetic data, 0 duplicate rows)
- **Total Attributes (Columns)**: 65 columns
- **Timestamp Coverage**: `2026-08-21T16:11:44Z` to `2026-08-22T14:03:40Z`
- **Total Unique Runs**: 4 collection runs
- **Total Unique Trains Tracked**: 32 distinct trains (EMU Slow Locals, Fast Locals, AC Fast Locals, Superfast Mail/Express)
- **Total Unique Stations**: 42 stations along the CSMT &ndash; Kalyan &ndash; Karjat/Kasara corridor

---

## 2. Collection Run Breakdown

| Run ID | Collection Start / End | Rows | Fresh Rows | Stale Rows | Train Count | Description |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| `20260821T160834Z-moving-38f8f31b` | 2026-08-21 16:11 to 16:21 UTC | 177 | 107 (60.5%) | 70 (39.5%) | 22 trains | Initial corridor multi-train scan |
| `20260821T162310Z-moving-625795fa` | 2026-08-21 16:27 to 16:50 UTC | 101 | 82 (81.2%) | 19 (18.8%) | 5 trains | 23-minute focused sequential run |
| `20260822T085927Z-moving-6809face` | 2026-08-22 09:03 to 10:03 UTC | 305 | 197 (64.6%) | 108 (35.4%) | 5 trains | 60-minute daytime sequential run |
| `20260822T131216Z-moving-7b8b8e46` | 2026-08-22 13:16 to 14:03 UTC | 215 | 119 (55.3%) | 96 (44.7%) | 5 trains | 50-minute evening peak sequential run |
| **Total Master Dataset** | **Multi-Day Telemetry Corpus** | **798** | **505 (63.3%)** | **293 (36.7%)** | **32 trains** | **Canonical Master Dataset** |

---

## 3. Data Integrity, Sequences & Boundary Isolation

### The Fundamental Sequence Key: `(run_id, train_number)`
Because observations span multiple distinct collection runs across two different days, the chronological time-series sequence is strictly indexed by the compound key:
$$\text{Sequence Key} = (\text{run\_id}, \text{train\_number})$$

- **Total Fresh Train Sequences**: 35 distinct sequence groups
- **Sequence Length Range**: 1 to 59 observations (Median: 7.0, Mean: 14.4)
- **Sequence Monotonicity**: 100% strictly monotonic increasing in time per sequence
- **Usable Sequential Pairs ($t, t+1$)**: **470 valid transitions** (each of the 35 sequences has exactly 1 terminal row without a $t+1$ observation, $505 - 35 = 470$).

### Cross-Run & Cross-Train Isolation Rules
1. **Zero Cross-Run Lags**: The first observation of any run never references telemetry from a prior run. Lag values (`previous_delay`, `delay_change_prev`, `time_since_previous_observation_seconds`, `distance_travelled_km`) are strictly initialized to `NaN`.
2. **Zero Cross-Train Lags**: Sequence groupings strictly isolate trains from each other.
3. **Zero Target Boundary Bleed**: `future_delay` and `target_delay_change` are computed strictly via `shift(-1)` within the `(run_id, train_number)` partition.

---

## 4. Stale Observation Handling

- **Stale Rows in Master CSV**: 293 rows (36.72%)
- **Fresh Rows in Master CSV**: 505 rows (63.28%)
- **Handling Strategy**:
  - The master CSV (`live_observations_master.csv`) preserves all 798 rows byte-for-byte untouched.
  - The preprocessing pipeline filters `is_stale == False` prior to sequence generation.
  - Zero synthetic data or artificial imputation is introduced for stale intervals.

---

## 5. Target Construction & Distribution Analysis

The target variable for machine learning is defined strictly as:
$$\text{target\_delay\_change}(t) = \text{delay\_minutes}(t+1) - \text{delay\_minutes}(t)$$

### Target Statistics across 470 ML-Ready Observations
- **Range**: $-19.0$ minutes to $+14.0$ minutes
- **Mean**: $+0.11$ minutes
- **Median**: $0.00$ minutes
- **Standard Deviation**: $2.15$ minutes
- **Zero Change ($\Delta = 0$ min)**: **271 observations (57.66%)**
- **Delay Reduction ($\Delta < 0$ min)**: **98 observations (20.85%)**
- **Delay Growth ($\Delta > 0$ min)**: **101 observations (21.49%)**

### Target Breakdown by Collection Run

| Run ID | ML-Ready Rows | Mean $\Delta$ | Median $\Delta$ | Zero-Change % | Delay Growth % | Delay Reduction % |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `20260821T160834Z` | 99 | +0.22 min | 0.0 min | 59.6% | 23.2% | 17.2% |
| `20260821T162310Z` | 77 | +0.08 min | 0.0 min | 68.8% | 15.6% | 15.6% |
| `20260822T085927Z` | 192 | +0.10 min | 0.0 min | 58.9% | 21.9% | 19.3% |
| `20260822T131216Z` | 102 | +0.07 min | 0.0 min | 45.1% | 23.5% | 31.4% |

---

## 6. Engineered Feature Specification

The ML feature matrix $X$ is composed of 25 strictly non-leaky input features:

### A. Numerical Telemetry Features (7)
1. `latitude`: Raw GPS latitude
2. `longitude`: Raw GPS longitude
3. `segment_progress`: Inter-station block progression fraction ($0.0 \to 1.0$)
4. `delay_minutes`: Current accumulated delay at time $t$
5. `distance_from_origin_km`: Total distance traversed from CSMT terminus
6. `distance_from_last_station_km`: Distance past the last scheduled station
7. `route_sequence`: Station stop index in the train schedule

### B. Categorical Context Features (7)
1. `train_number`: Train service identifier
2. `train_type`: Train physical profile (EMU, Superfast Express)
3. `train_category`: Operational category (Local vs Express)
4. `current_station_code`: Current/last station code
5. `next_station_code`: Upcoming approach station code
6. `current_location_status`: Physical status (`at-station` vs `departed`)
7. `movement_state`: Kinematic state (`MOVING`, `STATIONARY`, `UNKNOWN`)

### C. Derived Historical Features (7)
1. `previous_delay`: Delay at time $t-1$ ($\text{delay\_minutes}_{t-1}$)
2. `delay_change_prev`: Recent delay slope ($\text{delay}_t - \text{delay}_{t-1}$)
3. `time_since_previous_observation_seconds`: Inter-sample elapsed duration ($\Delta t$)
4. `distance_travelled_km`: Distance traversed between observations ($\Delta x$)
5. `station_transition`: Boolean flag ($1$ if train crossed into a new station block)
6. `route_position_change`: Schedule sequence step change ($\Delta \text{seq}$)
7. `estimated_speed_kmh`: Telemetry-derived physical speed ($\frac{\Delta x}{\Delta t} \times 3600$)

### D. Temporal Features (4)
1. `hour`: Hour of observation (0 to 23)
2. `minute`: Minute of observation (0 to 59)
3. `time_of_day_minutes`: Minute of day ($0 \to 1440$)
4. `day_of_week`: Day index (0 = Monday, 6 = Sunday)

---

## 7. Data Leakage Audit Results

The formal leakage audit (`data/reports/ml_leakage_audit.json`) verified all 10 integrity points:

| Audit Check | Status | Verification Detail |
|:---|:---:|:---|
| **1. Target Excluded from $X$** | **PASSED** | `target_delay_change` quarantined from feature list |
| **2. Future Delay Excluded from $X$** | **PASSED** | `future_delay` quarantined from feature list |
| **3. No $t+1$ Future Columns** | **PASSED** | Zero future coordinates, timestamps, or stations in $X$ |
| **4. Target Consistency** | **PASSED** | $\text{target\_delay\_change} == \text{future\_delay} - \text{delay\_minutes}$ for 100% of rows |
| **5. Cross-Run Isolation** | **PASSED** | Lags for sequence index 0 are strictly NaN across all runs |
| **6. Cross-Train Isolation** | **PASSED** | Sequences grouped strictly by `(run_id, train_number)` |
| **7. No NaN Targets in ML Set** | **PASSED** | 35 terminal observations without $t+1$ cleanly dropped |
| **8. No Duplicate Observation Keys** | **PASSED** | Zero duplicate keys on `(run_id, train_number, collection_timestamp)` |
| **9. Monotonic Timestamps** | **PASSED** | All sequence partitions are strictly monotonically increasing |
| **10. No Duplicate Targets** | **PASSED** | Single unified target column |

---

## 8. Train / Validation / Test Split Strategies

Two non-leaky chronological split strategies are documented in `data/reports/ml_split_specification.json`:

1. **Strategy A (Chronological In-Sequence Split - Recommended)**:
   - Allocates the first 70% of observations per `(run_id, train_number)` sequence to Train (**313 rows, 66.6%**) and the final 30% to Test (**157 rows, 33.4%**).
   - Guarantees that every train's past predicts its own future without cross-temporal contamination.
2. **Strategy B (Run Holdout Out-of-Domain Split)**:
   - Uses Runs 1, 2, and 3 as Development Data (**368 rows, 78.3%**) and Run 4 (Evening Peak) as Temporal Holdout (**102 rows, 21.7%**).
