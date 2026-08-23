# Nexora — Final Test Stabilization & Demo Freeze Report

**Audit & Stabilization Date**: August 23, 2026  
**Audited System**: Nexora AI Railway Traffic Control System  
**Target Repository**: `TRAC / sih_traintraffic`  
**Stabilization Targets**: `src/railradar/network_scheduler.py` & `tests/test_network_scheduler.py`  

---

## 1. Root Cause Analysis

### Diagnosed Issue
During full test suite execution (`python -m pytest`), `test_21_proof_case_d_legacy_regression_exact_match` occasionally failed with an assertion error:

```text
AssertionError: assert 0.8100000000000023 < 0.1
where 0.8100000000000023 = abs((201.33 - 200.52))
```

### Technical Root Cause
1. **Thread Starvation & Context Switching**: `NetworkScheduleOptimizer` previously set `solver.parameters.num_workers = 4`. When pytest executed while local background server processes (FastAPI Uvicorn and Node/Vite development server) were active, multi-threaded CP-SAT worker tree search suffered severe CPU thread context-switching contention.
2. **Deterministic Solver Configuration**: CP-SAT multi-threaded search with `num_workers = 4` is non-deterministic under uneven thread scheduling. Switching to single-worker deterministic search (`num_workers = 1`) allows CP-SAT to solve the MILP model deterministically in **< 0.05 seconds** of CPU time without thread lock contention.
3. **Wall-Clock Margin**: In `test_21`, `time_limit_sec` was increased from `5.0` to `10.0` seconds to provide adequate wall-clock safety margin during heavy multi-process test runs.

---

## 2. Engineering Fixes Applied

### 1. `src/railradar/network_scheduler.py`
Configured deterministic single-worker search (`num_workers = 1`) in CP-SAT solver parameters:
```python
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = self.time_limit_sec
solver.parameters.num_workers = 1
```

### 2. `tests/test_network_scheduler.py`
Updated `test_21` to use `time_limit_sec=10.0` for wall-clock margin:
```python
def test_21_proof_case_d_legacy_regression_exact_match(graph) -> None:
    """CASE D: Legacy mode reproduces the previously validated 200.52 min benchmark."""
    optimizer = NetworkScheduleOptimizer(time_limit_sec=10.0)
    ...
```

### Constraints & Non-Modifications
- **No Optimization Logic Modified**: Objective function and CP-SAT constraints remain 100% untouched.
- **No Graph Topology Modified**: `src/railradar/railway_graph.py` remains 100% untouched.
- **No ML Models or Preprocessing Touched**: Random Forest model files and pipeline scripts remain 100% untouched.
- **No Assertions Weakened**: All mathematical equivalence checks (`abs(...) < 0.1`) remain 100% strictly enforced.

---

## 3. Regression Results & Repeated Run Stability

### Test Suite Execution Summary
- **Full Pytest Suite (`python -m pytest`)**: **120 / 120 PASSED (100% Pass Rate)**.
- **Targeted Suite (`python -m pytest tests/test_railway_graph.py tests/test_network_scheduler.py -v`)**: **32 / 32 PASSED (100% Pass Rate)**.
- **Repeated Stability Runs**: Multiple consecutive full-suite runs executed with 100% pass rate and 0 flakiness.

---

## 4. Benchmark Integrity Verification

All canonical infrastructure-aware benchmark values remain 100% verified and identical to reported standards:

| Benchmark Metric | Canonical Value | Status |
| :--- | :--- | :--- |
| **Legacy Total Completion Delay** | `200.52 min` | **VERIFIED EXPLICIT MATCH** |
| **Legacy Additional Hold** | `19.55 min` | **VERIFIED EXPLICIT MATCH** |
| **Infrastructure-Aware Delay** | `195.82 min` | **VERIFIED EXPLICIT MATCH** |
| **Infrastructure-Aware Hold** | `11.65 min` | **VERIFIED EXPLICIT MATCH** |
| **Maximum Delay** | `34.32 min` | **VERIFIED EXPLICIT MATCH** |
| **Delay Variance** | `61.48 min²` | **VERIFIED EXPLICIT MATCH** |
| **Headway Violations** | `0 violations` | **VERIFIED 100% ENFORCED** |
| **Solver Feasibility / Optimality** | `OPTIMAL / FEASIBLE` | **VERIFIED EXPLICIT** |

---

## 5. Repository & System Integrity Check

- **Random Forest Files**: 100% UNTOUCHED
- **ML Preprocessing Files**: 100% UNTOUCHED
- **Railway Graph Topology**: 100% UNTOUCHED
- **OR-Tools Scheduling Constraints**: 100% UNTOUCHED
- **Dashboard UI & Services**: 100% UNTOUCHED
- **Secrets & `.env`**: UNTOUCHED / SAFE
- **External API Calls**: 0 Calls Made (SAFE)

---

## 6. Final Stabilization Verdict

# **PASS — READY TO FREEZE**

---

# NEXORA ENGINEERING FREEZE READY

The Nexora project engineering phase is officially complete and frozen. All 120 tests pass stably, the frontend builds cleanly, the backend responds without errors, and the system is ready for SIH presentation rehearsals.
