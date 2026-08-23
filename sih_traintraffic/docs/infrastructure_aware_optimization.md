# Nexora Stage 2: Infrastructure-Aware OR-Tools Scheduling

This document details the mathematical architecture, resource-aware occupancy constraints, benchmark results, and scientific evaluation of the **Infrastructure-Aware OR-Tools CP-SAT Scheduler**.

---

## 1. Executive Summary & Scientific Verdict

```
+----------------------------------------------------------------------------------------------------+
|                                    1. SCIENTIFIC VERDICT                                           |
|                                                                                                    |
|    "A. MATERIAL IMPROVEMENT"                                                                       |
|                                                                                                    |
|    Infrastructure-aware resource allocation materially reduces total delay (-4.70 min / -2.34%),   |
|    slashes unnecessary optimizer holding time (-7.90 min / -40.41%), decreases maximum train hold  |
|    (-2.11 min / -32.56%), cuts delay variance (-7.35%), and reduces potential resource conflicts    |
|    (-39.42%) compared with the legacy single-resource model.                                       |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Scientific Demarcation & Integrity

> [!IMPORTANT]
> **Mandatory Scientific Statement**:
>
> "The infrastructure CSV establishes multi-track capacity (4 physical tracks between CSMT and Sion; 6 physical tracks between Kurla and Thane) but does not provide individual physical track identities, crossover topology, signal blocks, or interlocking routes. `DOWN_FAST` and `DOWN_SLOW` are therefore prototype logical resources, not verified physical track IDs."

---

## 3. Mathematical Formulation & Resource-Aware Occupancies

### 3.1 Logical Track Resource Assignment
For each train $t \in \mathcal{T}$ and directed graph edge $e = (u, v) \in \mathcal{E}_t$:
$$\text{Resource}(t, e) = \begin{cases} 
(u, v, \text{DOWN\_FAST}) & \text{if } t \in \mathcal{T}_{\text{FAST}} \text{ and } (u, v) \text{ has dual-track support} \\
(u, v, \text{DOWN\_SLOW}) & \text{if } t \in \mathcal{T}_{\text{SLOW}} \text{ and } (u, v) \text{ has dual-track support} \\
(u, v, \text{DEFAULT}) & \text{if } (u, v) \text{ is on suburban branch beyond Thane}
\end{cases}$$

### 3.2 Resource-Based Occupancy Intervals
For each train $t$ and edge $e$, the occupancy interval $[s_{t, e}, e_{t, e}]$ is padded by the safety headway buffer $H = 60\text{s}$:
$$\text{Interval}_{t, e} = [s_{t, e}, e_{t, e} + H]$$

- **Different Resources (No Conflict)**: If Train $A$ occupies $(u, v, \text{DOWN\_FAST})$ and Train $B$ occupies $(u, v, \text{DOWN\_SLOW})$, their intervals belong to distinct resource sets. They may operate concurrently without causing a block conflict or artificial hold.
- **Same Resource (Headway Enforced)**: If two trains $A, B$ occupy the *same* resource $r = (u, v, \text{DOWN\_SLOW})$:
$$\text{AddNoOverlap}\left(\{\text{Interval}_{t, e} \mid \text{Resource}(t, e) = r\}\right)$$
$$\implies s_{B, e} \ge e_{A, e} + 60\text{s} \quad \lor \quad s_{A, e} \ge e_{B, e} + 60\text{s}$$

### 3.3 Preserved Objective Function
Both `legacy_single_resource` and `infrastructure_aware` modes evaluate the **identical hierarchical objective**:
$$\min \quad W_{\text{delay}} \sum_{t} D_t + W_{\text{max}} D_{\text{max}} + W_{\text{hold}} \sum_{t} H_t + W_{\text{prop}} \sum_{t} C_{\text{prop}}(t) + \sum_{t} w_{\text{impact}}(t) D_t$$
where $W_{\text{delay}} = 10000, W_{\text{max}} = 2000, W_{\text{hold}} = 500, W_{\text{prop}} = 100$.

---

## 4. Three-Way Benchmark Results

Identical inputs (10 Central Line trains, frozen Random Forest risk predictions, 60s safety headway, empirical median travel times):

| Benchmark Metric | Greedy FIFO (Single Resource) | Nexora Legacy (Single Resource) | Nexora Infrastructure-Aware (Multi-Track) | Delta vs Legacy | Delta vs FIFO |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total Completion Delay** | $200.52\text{ min}$ | $200.52\text{ min}$ | **$195.82\text{ min}$** | **$-4.70\text{ min}$ ($-2.34\%$)** | **$-4.70\text{ min}$ ($-2.34\%$)** |
| **Mean Delay** | $20.05\text{ min}$ | $20.05\text{ min}$ | **$19.58\text{ min}$** | **$-0.47\text{ min}$** | **$-0.47\text{ min}$** |
| **Median Delay** | $20.08\text{ min}$ | $20.08\text{ min}$ | **$19.74\text{ min}$** | **$-0.34\text{ min}$** | **$-0.34\text{ min}$** |
| **P90 Delay** | $28.23\text{ min}$ | $28.23\text{ min}$ | **$27.91\text{ min}$** | **$-0.32\text{ min}$** | **$-0.32\text{ min}$** |
| **Maximum Individual Delay** | $34.32\text{ min}$ | $34.32\text{ min}$ | **$34.32\text{ min}$** | $0.00\text{ min}$ | $0.00\text{ min}$ |
| **Delay Variance** | $66.36\text{ min}^2$ | $66.36\text{ min}^2$ | **$61.48\text{ min}^2$** | **$-4.88\text{ min}^2$ ($-7.35\%$)** | **$-4.88\text{ min}^2$ ($-7.35\%$)** |
| **Total Optimizer Hold Added** | $19.55\text{ min}$ | $19.55\text{ min}$ | **$11.65\text{ min}$** | **$-7.90\text{ min}$ ($-40.41\%$)** | **$-7.90\text{ min}$ ($-40.41\%$)** |
| **Maximum Hold on Single Train** | $6.48\text{ min}$ | $6.48\text{ min}$ | **$4.37\text{ min}$** | **$-2.11\text{ min}$ ($-32.56\%$)** | **$-2.11\text{ min}$** |
| **Trains with Zero Hold** | 3 / 10 | 3 / 10 | **5 / 10** | **$+2\text{ trains}$ ($+66.7\%$)** | **$+2\text{ trains}$** |
| **Propagated Delay Cost** | $25,837.59$ | $25,837.59$ | **$25,183.06$** | **$-654.53$ ($-2.53\%$)** | - |
| **Modeled Conflicts Prevented** | - | 1172 | **710** | **$-462$ ($-39.42\%$)** | - |
| **Modeled Headway Violations** | 0 | 0 | **0** | $0$ | $0$ |
| **Corridor Makespan** | $156.15\text{ min}$ | $156.15\text{ min}$ | **$156.15\text{ min}$** | $0.00\text{ min}$ | $0.00\text{ min}$ |
| **Solver Runtime** | - | $5.06\text{s}$ | **$5.50\text{s}$** | $+0.44\text{s}$ | - |

---

## 5. Track Resource Utilization Breakdown

Along the 328 total edge traversals across the 10 train routes:
- **`DOWN_FAST` Resource Traversals**: **69** (Fast trains 95011, 95421, 95333 on CSMT–Thane)
- **`DOWN_SLOW` Resource Traversals**: **159** (Slow trains 96333, 96643, 97167, 97259, 97419, 97261, 97421 on CSMT–Thane)
- **`DEFAULT` Resource Traversals**: **100** (Beyond Thane to Kalyan, Kasara, Khopoli)

---

## 6. Key Proof Cases Verified by Unit Tests

1. **CASE A (Different Resources $\implies$ Zero Hold)**: Fast Train (`DOWN_FAST`) and Slow Train (`DOWN_SLOW`) scheduled at the exact same second $(t=0)$ on `CSMT__MSD` both dispatch immediately with $0\text{s}$ hold.
2. **CASE B (Same Resource $\implies$ Headway Enforced)**: Two Slow Trains on `DOWN_SLOW` enforce a strict $\ge 60\text{s}$ spacing. The higher priority/risk train is dispatched first.
3. **CASE C (Branch Resource $\implies$ Single Resource Preserved)**: Beyond Thane on `KYN__SHAD__DEFAULT`, Fast and Slow services share the single resource and maintain $\ge 60\text{s}$ spacing.
4. **CASE D (Legacy Regression Exact Match)**: `legacy_single_resource` mode deterministic solve reproduces $200.52\text{ min}$ total delay and $19.55\text{ min}$ hold with $<0.1\text{ min}$ numerical tolerance.

---

## 7. Main Limitations & Recommended Next Steps

### Main Limitation:
- **No Mid-Journey Track Switching / Overtaking**: Because crossover turnout locations and signal interlocking route tables are absent in the infrastructure data, a Slow train cannot be dynamically switched to the Fast line to allow an express to pass, and vice versa.

### Recommended Next Step:
- Acquire or model station platform track assignments (e.g. at major junctions Dadar `DR`, Kurla `CLA`, and Thane `TNA`) to enable station dwell platform multiplexing without inventing intermediate mainline crossovers.
