# Nexora Dual-Track Railway Network Graph Extension

This document provides architectural and scientific documentation for the **Dual-Track Directional Graph Extension** implemented in Nexora.

---

## 1. Overview & Architectural Motivation

In the previous prototype, the railway graph modeled a single logical track edge per station pair (e.g. `CSMT__MSD`, capacity = 1). While mathematically valid for single-line corridors, this forced all 10 Central Line trains (both Fast Express and Slow Local services) to queue on a single bottleneck track out of Mumbai CSMT.

The infrastructure data audit of `csmt_thane_railway_infrastructure.csv` verified that:
- The **CSMT to Sion** corridor has **4 parallel physical tracks** (2 Slow + 2 Fast lines).
- The **Kurla to Thane** corridor has **6 parallel physical tracks** (2 Slow + 2 Fast + 2 5th/6th long-distance lines).

This extension introduces `TrackResource` objects to represent parallel directional track capacity over the verified CSMT–Thane corridor without breaking backward compatibility or altering the OR-Tools scheduler.

---

## 2. Scientific Demarcation: Real Data vs Prototype Assumptions

```
+----------------------------------------------------------------------------------------------------+
|                                      SCIENTIFIC DEMARCATION                                        |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  1. VERIFIED REAL DATA (from csmt_thane_railway_infrastructure.csv):                               |
|     * Station chainages and 19 physical stations between CSMT and Thane.                          |
|     * 4-track quad capacity from CSMT to Sion.                                                     |
|     * 6-track sextuple capacity from Kurla to Thane.                                               |
|                                                                                                    |
|  2. PROTOTYPE ASSUMPTION (clearly tagged in code and artifacts):                                   |
|     * The CSV proves multi-track corridor capacity. The prototype models DOWN_FAST and DOWN_SLOW   |
|       as separate logical resources using service-type mapping as an EXPLICIT ASSUMPTION because    |
|       individual track identities, platform tracks, and directional assignments are not present   |
|       in the CSV.                                                                                  |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Data Structures & Abstractions

### 3.1 `TrackResource` Dataclass
```python
@dataclass
class TrackResource:
  resource_id: str  # e.g., "CSMT__MSD__DOWN_SLOW"
  from_station: str  # "CSMT"
  to_station: str  # "MSD"
  direction: str = "DOWN"
  track_type: str = "DOWN_SLOW"  # "DOWN_SLOW", "DOWN_FAST", "DEFAULT"
  capacity: int = 1
  physical_corridor_tracks: int = 4
  serving_trains: list[str] = field(default_factory=list)
  source: str = "csmt_thane_railway_infrastructure.csv"
  is_prototype_assumption: bool = True
  track_assignment_status: str = "PROTOTYPE_ASSUMPTION"
```

### 3.2 Graph Query API Methods
- `get_track_resources()`: Returns all 86 track resources in the network.
- `get_track_resource(resource_id)`: Look up a specific track resource by ID.
- `get_resources_between(from_station, to_station)`: Returns parallel resources connecting a station pair (e.g., returns both `DOWN_SLOW` and `DOWN_FAST` for `CSMT` $\to$ `MSD`).
- `get_train_track_resource(train_number, from_station, to_station)`: Routes a train to its designated track resource based on service type.
- `get_trains_on_resource(resource_id)`: Returns the list of trains utilizing a resource.

---

## 4. Coverage Summary

| Corridor Segment | Physical Track Count | Modeled Track Resources | Resource IDs |
| :--- | :---: | :---: | :--- |
| **CSMT $\to$ Sion** | 4 tracks | 2 parallel resources (`DOWN_SLOW` & `DOWN_FAST`) | `CSMT__MSD__DOWN_SLOW`, `CSMT__MSD__DOWN_FAST`, etc. |
| **Kurla $\to$ Thane** | 6 tracks | 2 parallel resources (`DOWN_SLOW` & `DOWN_FAST`) | `CLA__VVH__DOWN_SLOW`, `CLA__VVH__DOWN_FAST`, etc. |
| **Thane $\to$ Kalyan / Branches** | 2 tracks (default) | 1 logical resource (`DEFAULT`) | `KYN__VSD__DEFAULT`, `DI__KYN__DEFAULT`, etc. |

**Total Network Metrics**:
- Station Nodes: **61**
- Logical Track Edges: **62**
- Track Resources: **86** (24 dual-track pairs = 48 resources + 38 single-track resources)
- Train Routes: **10**

---

## 5. What This Enables & What It Does NOT Enable

### What This Enables:
1. **Separation of Fast vs Slow Suburban Services**: Fast trains (`95011`, `95421`, `95333`) can run on `DOWN_FAST` track resources without being delayed by Slow locals on `DOWN_SLOW`.
2. **Elimination of Origin Dispatch Contention**: Enables simultaneous departure of a Fast train and a Slow train on separate parallel tracks out of CSMT.

### What This Does NOT Enable (Why Overtaking Remains Unsupported):
- **No Physical Crossovers / Turnouts**: The infrastructure CSV does not contain crossover switch locations, turnout geometry, or interlocking route tables.
- A train cannot dynamically switch from `DOWN_SLOW` to `DOWN_FAST` mid-journey without fabricating crossover locations.
- Physical overtaking remains **unsupported** until interlocking turnout data is acquired.

---

## 6. Generated Static Artifacts
- [`data/static/csmt_thane_railway_infrastructure.csv`](file:///c:/Users/joshi/OneDrive/Desktop/Nexora/TRAC/TRAC/sih_traintraffic/data/static/csmt_thane_railway_infrastructure.csv)
- [`data/static/track_resources.json`](file:///c:/Users/joshi/OneDrive/Desktop/Nexora/TRAC/TRAC/sih_traintraffic/data/static/track_resources.json)
- [`data/static/railway_graph.json`](file:///c:/Users/joshi/OneDrive/Desktop/Nexora/TRAC/TRAC/sih_traintraffic/data/static/railway_graph.json)
