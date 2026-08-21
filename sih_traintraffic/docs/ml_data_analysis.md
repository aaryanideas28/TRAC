# Nexora ML Data Analysis & Feature Engineering Report

## 1. Dataset Summary

The primary dataset evaluated is:
`data/processed/live_observations_moving_20260821T162310Z-moving-625795fa.csv`

- **Collection Window**: 2026-08-21 16:27:27Z to 16:50:49Z (~23 minutes continuous collection)
- **Total Observations (Rows)**: 101 real observations
- **Total Attributes (Columns)**: 65 columns
- **Synthetic Data**: 0% (100% genuine RailRadar live API observations)
- **Exact Duplicate Rows**: 0
- **Active Trains Tracked**: 5 Central Line suburban and long-distance trains

### Train Distribution Summary

| Train Number | Train Name | Total Observations | Journey Date |
|--------------|------------|--------------------|--------------|
| `12809` | Mumbai CSMT - Howrah Mail | 21 | 2026-08-21 |
| `95135` | S 39/ Mumbai CSMT - Karjat Fast Local | 20 | 2026-08-21 |
| `95333` | A55 / Mumbai CSMT - Ambernath Fast Local | 21 | 2026-08-21 |
| `97179` | Kalyan Jn. Mumbai EMU | 20 | 2026-08-21 |
| `97263` | Dombivli Mumbai EMU | 19 | 2026-08-21 |
| **Total** | **5 Active Central Line Trains** | **101** | |

---

## 2. Data Quality & Distribution Findings

### Missing Values Breakdown

Out of 65 total columns, 18 columns contain null/missing values:

| Column Name | Missing Count | Missing Percentage | Cause / Explanation |
|-------------|---------------|--------------------|---------------------|
| `speed_kmh` | 101 | 100.00% | Not populated by RailRadar API |
| `bearing_degrees` | 101 | 100.00% | Not populated by RailRadar API |
| `headway_seconds` | 101 | 100.00% | Requires multi-train spatial distance modeling |
| `station_to_station_travel_time_seconds` | 73 | 72.28% | Only computable on station transition events |
| `distance_from_previous_station_km` | 69 | 68.32% | Only populated when previous station distance is known |
| `estimated_speed_kmh` | 60 | 59.41% | Requires two consecutive non-stationary observations |
| `platform` | 58 | 57.43% | Platform numbers omitted by API for some stations |
| `segment_progress` | 23 | 22.77% | Null during certain station stop intervals |
| `time_since_previous_observation_seconds` | 5 | 4.95% | First observation of each train sequence has no predecessor |
| `previous_delay` | 5 | 4.95% | First observation of each train sequence has no predecessor |
| `delay_change` | 5 | 4.95% | First observation of each train sequence has no predecessor |
| `distance_travelled_km` | 5 | 4.95% | First observation of each train sequence has no predecessor |
| `actual_departure` | 3 | 2.97% | Train currently at station, departure pending |
| `actual_arrival` | 2 | 1.98% | Train currently en-route |
| `next_station` / `next_station_code` | 1 | 0.99% | Terminal station reached |
| `scheduled_departure` / `route_speed_to_next_kmh` | 1 | 0.99% | Terminal station reached |

### Categorical & State Distributions

- **Movement State (`movement_state`)**:
  - `MOVING`: 57 observations (56.44%)
  - `STATIONARY`: 39 observations (38.61%)
  - `UNKNOWN`: 5 observations (4.95%)
- **Location Status (`current_location_status`)**:
  - `at-station`: 69 observations (68.32%)
  - `departed`: 32 observations (31.68%)
- **Position Validity (`is_live` / `is_actual_position`)**:
  - `True`: 82 observations (81.19%)
  - `False`: 19 observations (18.81%)
- **Stale Status (`is_stale`)**:
  - `False` (Fresh observation): 82 observations (81.19%)
  - `True` (Stale/Repeated API data): 19 observations (18.81%)
- **Station Coverage**:
  - 25 unique current station codes (`CSMT`, `DR`, `GC`, `TNA`, `KYN`, `DIVA`, etc.)
  - 16 unique next station codes

### Delay Distribution

- **Minimum Delay**: 0.0 minutes
- **Maximum Delay**: 138.0 minutes
- **Mean Delay**: 36.65 minutes
- **Median Delay**: 14.0 minutes
- **Standard Deviation**: 51.28 minutes
- **Key Clusters**: 19 zero-delay observations, local trains clustered at 12–21 min delay, mail express (12809) at 132–138 min delay.

---

## 3. Sequential Time-Series Analysis

Each train was tracked continuously over ~20 to 23 minutes.

### Per-Train Sequential Breakdown

| Train Number | Train Name | Total Obs | Usable Sequential Pairs | Station Transitions | Collection Time Span |
|--------------|------------|-----------|------------------------|---------------------|----------------------|
| `12809` | Mumbai CSMT - Howrah Mail | 21 | 20 | 2 | 21.5 minutes |
| `95135` | S 39/ Mumbai CSMT - Karjat Fast Local | 20 | 19 | 7 | 22.1 minutes |
| `95333` | A55 / Mumbai CSMT - Ambernath Fast Local | 21 | 20 | 5 | 20.4 minutes |
| `97179` | Kalyan Jn. Mumbai EMU | 20 | 19 | 8 | 23.0 minutes |
| `97263` | Dombivli Mumbai EMU | 19 | 18 | 6 | 21.4 minutes |
| **Total** | **5 Active Central Line Trains** | **101** | **96 total (78 non-stale)** | **28** | **~23.0 minutes** |

- **Total Usable Sequential Pairs**: 96 observation pairs across all trains.
- **Non-Stale Usable Sequential Pairs**: **78 pairs** where both observation $t$ and observation $t+1$ are non-stale (`is_stale == False`).
- **Station Transitions Observed**: 28 transition events recorded.

---

## 4. Candidate ML Targets Evaluation

We evaluated three potential prediction targets for the Nexora machine learning component:

### Target Candidate 1: Future Delay Change ($\Delta delay_{t \to t+1} = delay_{t+1} - delay_t$) / Future Delay ($delay_{t+1}$)
- **Constructable from existing rows**: YES. Paired from consecutive observations ($t \to t+1$) per train.
- **Usable Sample Size**: 96 total pairs (78 non-stale pairs).
- **Target Variation**: 23 unique delay values (0 to 138 min). Delay changes $\Delta delay$ span -21 to +11 minutes (distribution: 59 zero change, 12 +1 min, 6 -1 min, 4 +2 min, 4 -2 min, 3 +3 min, 3 -3 min).
- **Data Leakage Risk**: ZERO leakage, provided feature vector $X_t$ strictly consumes observations at or before time $t$.
- **Random Forest Feasibility**: **HIGH**. Fits well as a regression task ($\Delta delay$) or 3-class classification (`DELAY_INCREASE`, `STABLE`, `DELAY_REDUCE`).

### Target Candidate 2: Next Station Code at Next Observation (`next_obs_station`)
- **Constructable from existing rows**: YES (96 total / 78 non-stale pairs).
- **Target Variation**: 21 unique station code classes.
- **Data Leakage Risk**: Low if $X_t$ does not contain future route updates.
- **Random Forest Feasibility**: **LOW**. With 78 non-stale training rows distributed across 21 classes (~3.7 samples per class), a Random Forest classifier would severely overfit due to extreme multi-class imbalance.

### Target Candidate 3: Station-to-Station Travel Time (`station_to_station_travel_time_seconds`)
- **Constructable from existing rows**: PARTIAL (only 28 valid station transition rows exist in the raw dataset).
- **Target Variation**: Continuous travel times in seconds.
- **Data Leakage Risk**: Low.
- **Random Forest Feasibility**: **UNFEASIBLE**. Sample size (28 rows) is far too small to train a Random Forest model.

---

## 5. Recommended ML Target

**RECOMMENDED TARGET: Future Delay Change ($\Delta delay_{t \to t+1} = delay_{t+1} - delay_t$)** (Regression)  
or **Delay Status Trend (`DELAY_INCREASE` / `STABLE` / `DELAY_REDUCE`)** (Classification).

### Rationale:
1. Aligns directly with rail traffic dispatching goals (predicting whether a train will suffer further delay in the next 1–5 minutes).
2. Maximizes usable training pairs (78 non-stale sequential pairs).
3. Completely avoids data leakage when paired chronologically ($X_t \to y_{t+1}$).

---

## 6. Feature Selection & Categorization

### Real API Fields (Used as Features at Time $t$)
- `delay_minutes` ($delay_t$)
- `latitude`, `longitude`
- `current_station_code`, `next_station_code`
- `distance_from_origin_km`, `distance_from_last_station_km`
- `time_of_day_minutes`
- `train_number` (Categorical identifier)
- `current_location_status` (`at-station` vs `departed`)
- `movement_state` (`MOVING`, `STATIONARY`, `UNKNOWN`)

### Derived Features (Computed strictly from history $X_{\le t}$)
- `previous_delay` ($delay_{t-1}$)
- `delay_change_prev` ($delay_t - delay_{t-1}$)
- `time_since_previous_observation_seconds` ($\Delta t$)
- `distance_travelled_km`
- `station_transition` (Boolean flag indicating if station changed)
- `route_position_change`

---

## 7. Rejected Features & Reasons

1. `speed_kmh`: **REJECTED** — 100% missing in raw RailRadar API response.
2. `bearing_degrees`: **REJECTED** — 100% missing in raw RailRadar API response.
3. `headway_seconds`: **REJECTED** — 100% missing in raw RailRadar API response.
4. `station_to_station_travel_time_seconds`: **REJECTED** — 72.28% missing (only populated on station arrival).
5. `distance_from_previous_station_km`: **REJECTED** — 68.32% missing.
6. `estimated_speed_kmh`: **REJECTED** — 59.41% missing.
7. `platform`: **REJECTED** — 57.43% missing.
8. `delay_minutes` at $t+1$: **REJECTED FROM $X$** — Prevent data leakage (this is the prediction target $y$).

---

## 8. Data Leakage Prevention Protocol

To guarantee zero data leakage:
1. **Strict Temporal Boundary**: No column from observation $t+1$ (such as future location, future timestamp, or future delay) may be present in feature matrix $X_t$.
2. **Per-Train Sequence Isolation**: Sequential shift operations (`df.groupby('train_number').shift()`) must be scoped strictly within individual train numbers to prevent lag feature corruption between different trains.
3. **No Random Shuffling Before Split**: Standard k-fold cross validation or random train/test splits cause severe autocorrelation leakage in time-series train data. Chronological splits must be enforced.

---

## 9. Train/Test Strategy

- **Strategy**: **Chronological Per-Train Split**
- **Split Ratio**: First 70% of observations per train $\to$ **Training Set** (~55 non-stale rows), Last 30% of observations per train $\to$ **Testing Set** (~23 non-stale rows).
- **Evaluation**: Simulates true deployment conditions (predicting future steps from past observed trajectory).

---

## 10. Random Forest Feasibility Assessment

**Feasibility Rating**: **PARTIALLY FEASIBLE (PROTOTYPE & BASELINE BENCHMARKING ONLY)**

### Detailed Assessment:
- **Usable Rows**: 78 non-stale sequential pairs across 5 active trains.
- **Code Pipeline Feasibility**: **YES**. The dataset is 100% sufficient to build, verify, and unit-test the end-to-end data preprocessing, feature engineering, chronological train/test split, and baseline Random Forest regressor/classifier.
- **Statistical Model Robustness**: **LIMITED**. 78 rows over a 23-minute window lack multi-hour traffic variation, peak vs non-peak congestion differences, and seasonal delay patterns.
- **Additional Data Requirement for Production Model**:
  - Extended 2 to 4 hour continuous collection window across multiple time slots (morning peak, afternoon off-peak, evening peak).
  - ~500 to 1,000 non-stale sequential pairs across 15–20 active trains to achieve high generalizability.

---

## 11. Recommended Preprocessing Pipeline Architecture

```
[Processed CSV File]
        │
        ▼
[Pandas DataFrame Loader]
        │
        ▼
[Filter Stale Observations (is_stale == False)]
        │
        ▼
[Sort Chronologically (train_number, collection_timestamp)]
        │
        ▼
[Feature Engineering: Lag Features (X_t)]
 (delay_t, delay_change_t-1, distance, location_status, time_of_day)
        │
        ▼
[Target Generation: Future Delay Change (y_t = delay_{t+1} - delay_t)]
        │
        ▼
[Categorical One-Hot / Target Encoding]
 (train_number, current_station_code, next_station_code)
        │
        ▼
[Chronological Train/Test Split (70% Train / 30% Test)]
        │
        ▼
[Random Forest Regressor Baseline Model]
```

---

## 12. Next Implementation Steps

1. Create `src/railradar/ml/` module with `preprocessing.py` and `features.py`.
2. Implement automated dataset loading, stale filtering, and chronological sorting.
3. Build lag feature transformer generating $(X_t, y_{t+1})$ pairs.
4. Implement chronological train/test split utility.
5. Create baseline script (`scripts/train_rf_baseline.py`) to benchmark Random Forest on the 78 usable pairs without touching API or raw data.
