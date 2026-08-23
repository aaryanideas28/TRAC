# Nexora — Final Numerical Sanity Check Report

**Audit Date**: August 23, 2026  
**Audited Subsystems**: Google OR-Tools CP-SAT Solver (`src/railradar/network_scheduler.py`), FastAPI Server, Vite React Command Center Web Portal  
**Corridor Scope**: Mumbai Central Line (CSMT to Thane)  
**Authoritative Benchmark Source**: `data/reports/infrastructure_aware_benchmark.json`  

---

## 1. Independent Recomputation & Canonical Benchmark Verification

The canonical 10-train Central Line benchmark was independently recomputed directly from solver execution on `data/selected_trains.json` and `data/processed/rf_optimization_inputs.csv`:

| Benchmark Metric | Baseline (`legacy_single_resource`) | Optimized (`infrastructure_aware`) | Absolute Change | Mathematical Improvement (%) | Classification | Scientific Verification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Total Completion Delay** | `200.52 min` | `195.82 min` | `-4.70 min` | `-2.34%` | `VALIDATED_BENCHMARK` | **VERIFIED MATCH** |
| **Optimizer-Added Hold** | `19.55 min` | `11.65 min` | `-7.90 min` | `-40.41%` | `VALIDATED_BENCHMARK` | **VERIFIED MATCH** |
| **Maximum Delay** | `34.32 min` | `34.32 min` | `0.00 min` | `0.00%` | `VALIDATED_BENCHMARK` | **VERIFIED MATCH** |
| **Delay Variance** | `66.36 min²` | `61.48 min²` | `-4.88 min²` | `-7.35%` | `VALIDATED_BENCHMARK` | **VERIFIED MATCH** |
| **Corridor Makespan** | `156.15 min` | `156.15 min` | `0.00 min` | `0.00%` | `VALIDATED_BENCHMARK` | **VERIFIED MATCH** |
| **Modeled Pairwise Conflicts** | `1,172 conflicts` | `710 conflicts` | `-462 conflicts` | `-39.42%` | `VALIDATED_BENCHMARK` | **VERIFIED MATCH** |
| **Zero-Hold Trains** | `3 trains` | `5 trains` | `+2 trains` | `+66.67%` | `VALIDATED_BENCHMARK` | **VERIFIED MATCH** |
| **Headway Violations** | `0 violations` | `0 violations` | `0 violations` | `0.00%` | `VALIDATED_BENCHMARK` | **100% ENFORCED** |
| **Solver Backend** | `Google OR-Tools CP-SAT` | `Google OR-Tools CP-SAT` | `N/A` | `N/A` | `OPTIMIZER_OUTPUT` | **VERIFIED MATCH** |
| **Solver Status** | `FEASIBLE` | `FEASIBLE` | `N/A` | `N/A` | `OPTIMIZER_OUTPUT` | **EXACT STATUS REPORTED** |

---

## 2. Maximum Delay Analysis (`34.32 min`)

- **Root Cause & Definition**: `34.32 min` is BOTH the Baseline Maximum Delay and the Optimized Maximum Delay.
- **Explanation**: Train `97421` enters the section with an initial Random Forest expected delay of `+34.32 min`. Because initial arrival delay at corridor entry is an exogenous input state, the optimizer cannot alter pre-entry delays. However, CP-SAT prevents additional downstream delay propagation, reducing total corridor delay by `-4.7 min` and hold delay by `-7.9 min`.

---

## 3. Explicit Metric Context Classification

| Metric Category | Displayed Values | Operational Context | Data Nature |
| :--- | :--- | :--- | :--- |
| **CURRENT REPLAY** | 6 Active Trains, 19 trains/hr Throughput, 3.1 min Average Delay, 86% Track Utilization, 2 Conflicts Detected, 2 Conflicts Resolved | Live 6-train corridor simulation state | `CURRENT_REPLAY` |
| **VALIDATED BENCHMARK** | Baseline Delay: 200.52m → Optimized Delay: 195.82m (-2.34%); Baseline Hold: 19.55m → Optimized Hold: 11.65m (-40.41%); Zero-Hold Trains: 3 → 5 | 10-train CSMT-Thane Central Line comparative benchmark | `VALIDATED_BENCHMARK` |
| **SOLVER STATUS** | `FEASIBLE` (Exact status under 10.0s time limit) | Solver termination status | `OPTIMIZER_OUTPUT` |

---

## 4. Final Numerical Verification Summary

```text
============================================================
CANONICAL BENCHMARK:
  Baseline: 200.52 min total completion delay, 19.55 min hold
  Optimized: 195.82 min total completion delay, 11.65 min hold
  Improvement: -4.70 min delay (-2.34%), -7.90 min hold (-40.41%)

MAXIMUM DELAY:
  Baseline: 34.32 min
  Optimized: 34.32 min

HOLD:
  Baseline: 19.55 min
  Optimized: 11.65 min

ZERO-HOLD TRAINS:
  Baseline: 3 trains
  Optimized: 5 trains

CURRENT REPLAY:
  Throughput: 19 trains/hr
  Average Delay: 3.1 min
  Utilization: 86%

SOLVER STATUS:
  FEASIBLE (Google OR-Tools CP-SAT)

NUMERICAL CONSISTENCY: PASS
UI DATA-BINDING: PASS
TESTS: 125 / 125 PASSED
BUILD: PASS (0 errors, 0 warnings)
============================================================
```
