# Nexora Railway Network Graph Layer Specification

## 1. Overview & Purpose

Nexora is an AI-powered railway traffic management prototype designed for suburban corridors (focusing on the Mumbai Central Line).

The conceptual system architecture consists of five decoupled layers:

```
+-------------------------------------------------------------+
|                     1. RailRadar Data                       |
|   (Static Route Snapshots & Empirical Live Observations)    |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                2. Railway Network Graph Layer               |
|  (Physical Topology: Station Nodes & Directed Track Edges)  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 3. Random Forest Predictor                  |
|          (Delay Progression & Risk Classification)          |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|              4. OR-Tools Scheduling / Optimizer             |
|   (Block Occupancy, Platform Allocation, Conflict Solving)  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                  5. Conflict-Free Schedule                  |
|              (Optimized Train Dispatch Timetable)           |
+-------------------------------------------------------------+
```

The **Railway Network Graph Layer** serves as the deterministic physical and logical foundation of the network. It models stations as nodes, track blocks between consecutive stations as directed edges, and train routes as ordered sequences of station nodes and track edges. It provides topological query capabilities and conflict mapping without embedding any optimization solver logic or making runtime API calls.

---

## 2. Graph Topology & Model Definition

### 2.1 Graph Formulation
The network is modeled as a **Directed Multigraph / DiGraph** $G = (V, E)$ where:
- **Node $v \in V$ (Station Node)**: Represents an operational station, passenger stop, or junction cabin.
- **Edge $e = (u, v) \in E$ (Track Edge)**: Represents a directed, unshared track block segment connecting station $u$ to consecutive station $v$ established by real train schedule routes.

### 2.2 Directionality
All 10 available static route snapshots in the current dataset represent **DOWN direction** trains (outbound from Mumbai CSMT toward suburban destinations). Consequently, all 62 constructed edges are directed in the Down direction (`direction: "DOWN"`). The graph design fully supports bidirectional topologies once UP-direction route snapshots are incorporated.

### 2.3 Unique Edge Identifier Convention
Edges utilize a standardized, deterministic string identifier format:
$$\text{edge\_id} = \text{FROM\_STATION}\_\_\text{TO\_STATION}$$
*(e.g., `CSMT__MSD`, `TNA__XX-TNAB`, `TNA__KLVA`)*

---

## 3. Network Topology Statistics

| Metric | Value | Description |
| :--- | :--- | :--- |
| **Station Nodes** | **61** | Unique physical stations and junction cabins |
| **Directed Track Edges** | **62** | Unique directed consecutive track segments |
| **Train Routes Mapped** | **10** | Selected Central Line EMU services |
| **Total Track Length** | **182.09 km** | Sum of Great-Circle (Haversine) segment distances |
| **Edges with Distance** | **62 (100%)** | All edges have numeric Haversine distances |
| **Edges with Empirical Travel Time** | **22 (35.5%)** | Supported by $\ge 2$ observed live transitions in master dataset |
| **Directionality** | `DOWN` | Outbound from CSMT |

---

## 4. Node & Edge Attributes

### 4.1 Station Node Attributes (`StationNode`)

| Attribute | Type | Status | Source / Description |
| :--- | :--- | :--- | :--- |
| `station_code` | `str` | **Available** | Official Indian Railways station code (*e.g., `CSMT`, `TNA`, `KYN`*) |
| `station_name` | `str` | **Available** | Station name from RailRadar station directory |
| `latitude` | `float` | **Available** | Real GPS latitude coordinate |
| `longitude` | `float` | **Available** | Real GPS longitude coordinate |
| `line_corridor` | `str` | **Available** | Suburban line identifier (`"Central Line"`) |
| `is_terminal` | `bool` | **Available** | Flag indicating whether the node serves as a service terminus |
| `is_halt` | `bool` | **Available** | Flag indicating whether trains halt at this location |
| *Platform Count* | `int` | **Unavailable** | Not present in source data |
| *Track Count* | `int` | **Unavailable** | Not present in source data |
| *Signal Positions* | `list` | **Unavailable** | Not present in source data |

### 4.2 Track Edge Attributes (`TrackEdge`)

| Attribute | Type | Status | Source / Description |
| :--- | :--- | :--- | :--- |
| `edge_id` | `str` | **Available** | Deterministic ID: `<from_station>__<to_station>` |
| `from_station` | `str` | **Available** | Origin station code |
| `to_station` | `str` | **Available** | Destination station code |
| `distance_km` | `float` | **Available** | Great-Circle Haversine distance computed from station GPS coordinates |
| `direction` | `str` | **Available** | Movement direction (`"DOWN"`) |
| `serving_trains` | `list[str]` | **Available** | Train numbers using this track segment |
| `service_types` | `list[str]` | **Available** | Service categories (`"SLOW"`, `"FAST"`, `"EMU"`) |
| `scheduled_travel_time_seconds` | `float` | **Unavailable / Null** | Null when individual segment schedules are not explicitly demarcated |
| `historical_travel_time_seconds` | `float` | **Partially Available** | Derived median transit time for segments with $\ge 2$ observations |
| `route_speed_kmh` | `float` | **Unavailable / Null** | Speed limit not present in source data |
| `capacity` | `int` (1) | **Prototype Assumption** | Default block capacity = 1 train at any time |
| `capacity_is_prototype_assumption` | `bool` (True) | **Explicit Flag** | Clearly distinguishes prototype constraint from physical railway data |

---

## 5. Corridor & Route Coverage

### 5.1 Main Trunk & Branch Segments

```
                                    +--> KLVA -> KLVC -> MBQ -> DIVA (Slow line) --+
                                    |                                               |
CSMT === (22 consecutive segments) ===> TNA                                         +==> KYN ===> Branch A (Khopoli: 15 stops)
                                    |                                               |        ===> Branch B (Kasara: 11 stops)
                                    +--> XX-TNAB ---------------> DIVA (Fast line) --+
```

1. **CSMT to Thane Trunk (23 Stations, 22 Edges)**:
   `CSMT` -> `MSD` -> `SNRD` -> `MZNC` -> `BY` -> `CHG` -> `CRD` -> `PRLW` -> `PR` -> `DR` -> `MTN` -> `SION` -> `CLA` -> `CLAS` -> `VVH` -> `GC` -> `VK` -> `KJRD` -> `BND` -> `NHU` -> `CRNM` -> `MLND` -> `TNA`
   *Shared by all 10 train services.*

2. **Thane to Kalyan — Slow Route (Kalva/Mumbra)**:
   `TNA` -> `KLVA` -> `KLVC` -> `MBQ` -> `DIVA` -> `DWJN` -> `KOPR` -> `DDCL` -> `DI` -> `THK` -> `KYNX` -> `KYN`
   *Traversed by slow locals: 96333, 96643, 97167, 97259, 97261.*

3. **Thane to Kalyan — Fast Route (Thane B Cabin Bypass)**:
   `TNA` -> `XX-TNAB` -> `DIVA` -> `DWJN` -> `DDCL` -> `DI` -> `THK` -> `KYNX` -> `KYN`
   *Traversed by fast locals: 95011, 95333, 95421.*

4. **South-East Branch (Kalyan to Khopoli, 15 Stations)**:
   `KYN` -> `VLDI` -> `ULNR` -> `ABH` -> `CHLI` -> `BUD` -> `VGI` -> `SHLU` -> `NRL` -> `BVS` -> `KJT` -> `PDI` -> `KLY` -> `DLV` -> `LWJ` -> `KHPI`

5. **North-East Branch (Kalyan to Kasara, 11 Stations)**:
   `KYN` -> `SHAD` -> `ABY` -> `TLA` -> `KDV` -> `VSD` -> `ASO` -> `ATG` -> `THS` -> `KE` -> `OMB` -> `KSRA`

### 5.2 Mapped Train Services (10 Trains)

| Train No. | Service Name | Stops | Segments | Terminus | Route Type |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **95011** | CSMT - Khopoli Fast Local | 46 | 45 | `KHPI` | Fast (via XX-TNAB) |
| **95333** | CSMT - Ambernath Fast Local | 34 | 33 | `ABH` | Fast (via XX-TNAB) |
| **95421** | CSMT - Kasara Fast Local | 42 | 41 | `KSRA` | Fast (via XX-TNAB) |
| **96333** | CSMT - Ambernath Slow Local | 37 | 36 | `ABH` | Slow (via KLVA) |
| **96643** | CSMT - Titvala Slow Local | 37 | 36 | `TLA` | Slow (via KLVA) |
| **97167** | Kalyan Jn. Slow Local | 34 | 33 | `KYN` | Slow (via KLVA) |
| **97259** | CSMT - Dombivli Slow Local | 31 | 30 | `DI` | Slow (via KLVA) |
| **97261** | CSMT - Dombivli Slow Local | 31 | 30 | `DI` | Slow (via KLVA) |
| **97419** | CSMT - Thane Slow Local | 23 | 22 | `TNA` | Slow (terminates at TNA) |
| **97421** | CSMT - Thane Slow Local | 23 | 22 | `TNA` | Slow (terminates at TNA) |

---

## 6. Conflict Detection & Downstream OR-Tools Consumption

### 6.1 Conflict Detection Architecture
A railway schedule conflict between two trains $T_A$ and $T_B$ occurs when:
1. **Shared Segment**: Both trains traverse an identical directed track edge $e$:
   $$e \in \text{Edges}(T_A) \cap \text{Edges}(T_B)$$
2. **Temporal Overlap**: The planned time interval during which $T_A$ occupies edge $e$ overlaps with the time interval of $T_B$, violating minimum headway $\Delta t_{\text{headway}}$:
   $$[\tau_{\text{entry}}(T_A, e), \tau_{\text{exit}}(T_A, e)] \cap [\tau_{\text{entry}}(T_B, e), \tau_{\text{exit}}(T_B, e)] \neq \emptyset$$

The `RailwayNetworkGraph` provides direct query methods for conflict analysis:
- `get_shared_edges(train_a, train_b)`: Identifies all segments shared between any pair of trains.
- `get_trains_on_edge(edge_id)`: Identifies all trains competing for a specific track segment.
- `get_train_edges(train_number)`: Returns the exact ordered list of `TrackEdge` objects a train must occupy.

### 6.2 OR-Tools Interface Preparation
When OR-Tools is integrated in subsequent iterations, it will consume the graph as follows:

```python
# Conceptual OR-Tools Consumption Pattern (DO NOT IMPLEMENT YET)
graph = RailwayNetworkGraph.from_json("data/static/railway_graph.json")

for train in selected_trains:
    edges = graph.get_train_edges(train.number)
    for edge in edges:
        # Create OR-Tools IntervalVar for track block occupancy
        # start_time = model.NewIntVar(...)
        # duration = estimated_traversal_time(edge, rf_predicted_delay)
        # interval = model.NewIntervalVar(start_time, duration, end_time, ...)
        pass

for edge in graph.all_edges():
    # Enforce non-overlapping occupancy for shared edges
    # model.AddNoOverlap(edge_interval_vars)
    pass
```

---

## 7. Assumptions & Known Limitations

1. **Prototype Coverage**: The graph represents the Central Line routes available in the static snapshots (61 stations, 10 train services). It is a prototype network layer, not a complete model of all Indian Railways or Western Line corridors.
2. **Directionality Scope**: Only Down-direction routes exist in the initial snapshot. Up-direction route definitions will be added when Up-direction snapshots are collected.
3. **Infrastructure Simplification**: Platform assignments, crossover switches, signal aspects, and track counts are not fabricated and remain unmodeled.
4. **Block Capacity Assumption**: Track edge capacity defaults to 1 block segment and is explicitly tagged with `capacity_is_prototype_assumption: True`.
