# Nexora Infrastructure Data Audit & Benchmark Reconciliation Report

This document provides a comprehensive technical audit of `csmt_thane_railway_infrastructure.csv` and a forensic reconciliation of the Nexora OR-Tools benchmark result families.

---

## Part 1 — CSV Structure Audit

| Metric | Value |
| :--- | :--- |
| **File Size** | $\approx 1.4\text{ KB}$ |
| **Row Count** | 19 station rows |
| **Column Count** | 5 columns |
| **Missing Values** | 0 (100% complete) |
| **Duplicate Rows** | 0 |

### Column Breakdown

| Column | Meaning | Type | Missing % | Unique | Potential Nexora Use | Confidence | Status |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **Station** | Station name along corridor | String | $0.0\%$ | 19 | Maps to graph station nodes | High (100%) | `REAL DATA` |
| **Distance_km** | Cumulative distance from CSMT | Float | $0.0\%$ | 19 | Validates inter-station edge lengths | High (100%) | `REAL DATA` |
| **Tracks** | Total parallel tracks | Integer | $0.0\%$ | 2 (`4`, `6`) | Informs corridor parallel capacity | High (100%) | `REAL DATA` |
| **Infrastructure_Type** | Station structural layout | String | $0.0\%$ | 8 | Civil/structural classification | High (100%) | `REAL DATA / CATEGORICAL` |
| **Geographic_Feature** | Civil & terrain constraints | String | $0.0\%$ | 19 | Domain context (bridges, ROBs) | High (100%) | `REAL DATA / DESCRIPTIVE` |

---

## Part 2 — Infrastructure Classification

| Resource | Status | Supporting Columns & Evidence |
| :--- | :---: | :--- |
| **1. Stations** | **AVAILABLE** | `Station`, `Distance_km` (19 physical stations from CSMT to Thane). |
| **2. Platforms** | **NOT AVAILABLE** | No platform numbers, platform lengths, or platform track assignments. |
| **3. Tracks** | **PARTIALLY AVAILABLE** | `Tracks` gives total count (4 or 6), but lacks individual track IDs/names. |
| **4. Track Sections** | **PARTIALLY AVAILABLE** | Inter-station distances can be derived from cumulative `Distance_km`. |
| **5. Junctions** | **PARTIALLY AVAILABLE** | `Infrastructure_Type` identifies Dadar, Kurla, Thane as junctions. |
| **6. Crossovers** | **NOT AVAILABLE** | Mentions Ghatkopar crossover bridge in text; zero turnout/switch matrix data. |
| **7. Signals** | **NOT AVAILABLE** | No signal IDs, locations, or automatic block section boundaries. |
| **8. Block Sections** | **NOT AVAILABLE** | Assumes single inter-station block in absence of signal data. |
| **9. Track Direction** | **NOT AVAILABLE** | Does not specify UP/DOWN directional split for the 4 or 6 tracks. |
| **10. Fast/Slow Lines** | **NOT EXPLICIT** | Inferred from Mumbai Railway quad/sextuple track layout, but not named. |
| **11. Entry/Exit Movements** | **NOT AVAILABLE** | No route-locking or throat movement data. |
| **12. Platform Capacity** | **NOT AVAILABLE** | No platform occupancy limits. |
| **13. Track Capacity** | **PARTIALLY AVAILABLE** | Total track count indicates 2 parallel tracks per direction. |
| **14. Routing Alternatives** | **NOT AVAILABLE** | No switch topology to model dynamic rerouting. |

---

## Part 3 — Mapping Against Current Graph

| Infrastructure Station | Current Graph Node | Match Quality | Confidence | Required Graph Change |
| :--- | :--- | :--- | :--- | :--- |
| **CSMT** | `CSMT` | Exact Match | 100% | None (Origin Terminus Node) |
| **Masjid** | `MSD` | Exact Match | 100% | Split into `CSMT__MSD_SLOW` & `CSMT__MSD_FAST` |
| **Sandhurst Road** | `SNRD` | Exact Match | 100% | Split into `MSD__SNRD_SLOW` & `MSD__SNRD_FAST` |
| **Byculla** | `BY` | Exact Match | 100% | Split into `SNRD__BY_SLOW` & `SNRD__BY_FAST` |
| **Chinchpokli** | `CHG` | Exact Match | 100% | Split into Slow edge (Fast trains bypass) |
| **Currey Road** | `CRD` | Exact Match | 100% | Split into Slow edge (Fast trains bypass) |
| **Parel** | `PR` | Exact Match | 100% | Split into Slow edge (Fast trains bypass) |
| **Dadar** | `DR` | Exact Match | 100% | Major Junction Node (Slow + Fast Platforms) |
| **Matunga** | `MTN` | Exact Match | 100% | Split into Slow edge |
| **Sion** | `SION` | Exact Match | 100% | Transition boundary (4-track $\to$ 6-track) |
| **Kurla** | `CLA` | Exact Match | 100% | Major Junction Node (6 tracks) |
| **Vidyavihar** | `VVH` | Exact Match | 100% | Split into Slow edge |
| **Ghatkopar** | `GC` | Exact Match | 100% | Major Intermediate Fast/Slow Stop |
| **Vikhroli** | `VK` | Exact Match | 100% | Split into Slow edge |
| **Kanjurmarg** | `KJRD` | Exact Match | 100% | Split into Slow edge |
| **Bhandup** | `BND` | Exact Match | 100% | Split into Slow edge |
| **Nahur** | `NHU` | Exact Match | 100% | Split into Slow edge |
| **Mulund** | `MLND` | Exact Match | 100% | Split into Slow edge |
| **Thane** | `TNA` | Exact Match | 100% | Major Junction Terminus |

---

## Part 4 — Current Assumption Audit

1. **Track Capacity = 1**: **CAN BE PARTIALLY REFINED**. The CSV proves 4 to 6 tracks exist. In the DOWN direction, this equates to **2 parallel tracks (Down Slow + Down Fast)**.
2. **Safety Headway = 60 seconds**: **MUST REMAIN PROTOTYPE PARAMETER** (Signaling distance is absent).
3. **No Overtaking**: **MUST REMAIN PROTOTYPE ASSUMPTION** (No crossover switch data).
4. **No Alternative Track Selection**: **CAN BE PARTIALLY REFINED** (Fast trains can be assigned to Down Fast; Slow trains to Down Slow).
5. **No Platform Assignment**: **MUST REMAIN PROTOTYPE ASSUMPTION** (Platform data absent).
6. **No Crossover Modeling**: **MUST REMAIN PROTOTYPE ASSUMPTION**.
7. **No Signal/Interlocking Modeling**: **MUST REMAIN PROTOTYPE ASSUMPTION**.
8. **No Turnback Modeling**: **MUST REMAIN PROTOTYPE ASSUMPTION**.
9. **Fixed Route Sequence**: **CAN BE PARTIALLY REFINED** (Separate Fast/Slow edge sequences).
10. **Fixed Direction**: **REAL DATA / REMAINS VALID** (All 10 trains operate DOWN).

---

## Part 5 & 6 — CP-SAT Opportunities & Can This Beat FIFO?

- **Can it enable overtaking?**: **NO**. Without turnout and crossover switch locations, the optimizer cannot model a train changing tracks mid-journey.
- **Can it enable Fast vs Slow track separation?**: **YES (PARTIAL)**. If the single-track graph is expanded into **Dual-Track Directional Edges (Down Slow + Down Fast)**, Fast trains (95011, 95421, 95333) and Slow trains (97259, 96333, 97419, etc.) would run on separate parallel track resources, completely eliminating head-to-tail queue contention out of CSMT origin!

---

## Part 7 & 8 — Benchmark Reconciliation & Canonical Standard

### Root Cause Analysis of Benchmark Discrepancy
- **Earlier Benchmark ($273.78\text{ min}$)**: Computed in scratch prototype scripts where ideal route duration was calculated using raw distance formulas without empirical observation medians, artificially shifting the baseline schedule by $73.26\text{ minutes}$.
- **Current Benchmark ($200.52\text{ min}$)**: Implemented in `src/railradar/network_scheduler.py`, using verified historical observation medians and precise station dwell calibrations.

### Canonical Benchmark Recommendation
The **$200.52\text{ min}$** figure is the **canonical, reproducible standard**:
- **Total Completion Delay**: $200.52\text{ min}$
- **Maximum Train Delay**: $34.32\text{ min}$
- **Delay Variance**: $66.36\text{ min}^2$
- **Total Additional Hold**: $19.55\text{ min}$
- **Makespan**: $156.15\text{ min}$
- **Solver Status**: `OPTIMAL` (by horizon)

---

## Part 9 & 10 — Data Quality & Final Recommendation

```
+----------------------------------------------------------------------------------------------------+
|                                    1. INFRASTRUCTURE DATA VERDICT                                  |
|                                                                                                    |
|    "B. PARTIAL VALUE — useful but insufficient for major expansion"                                |
+----------------------------------------------------------------------------------------------------+
```

### 2. What It Can Enable
- Expanding the CSMT–Thane corridor from a single logical track into **parallel Dual-Track Directional Edges (Down Slow + Down Fast)**.
- Eliminating headway contention between Fast and Slow suburban services.

### 3. What Is Still Missing
- Crossover switch locations, turnout speed limits, and interlocking route tables (needed for physical overtaking).
- Platform track identifiers and lengths (needed for platform assignment).
- Signal aspect sequences and block section markers (needed for real signaling).

### 4. Recommended Next Development Step
> [!TIP]
> **Next Step**: Expand `railway_graph.py` to support **Dual-Track Directional Graph Edges (Down Slow & Down Fast)** over the CSMT–Thane corridor using the 4-track / 6-track physical capacity verified by this audit.
