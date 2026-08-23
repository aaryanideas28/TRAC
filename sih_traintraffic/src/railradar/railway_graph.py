"""Railway network graph modeling and topology abstraction for Nexora.

This module constructs a directed graph representing the railway network layout
(stations as nodes, consecutive track segments as directed edges, and track resources)
and the mapped train routes traversing them. It is designed to serve as the topological
input layer for downstream optimization and scheduling models without embedding solver logic.

Enhanced Features:
------------------
- Dual-Track / Multi-Track Resource Extension:
  Models parallel directional track resources (e.g., DOWN_SLOW and DOWN_FAST)
  along corridors where multi-track physical capacity is verified by infrastructure data.
- Explicit Scientific Demarcation:
  Verified physical track counts (4-track CSMT-Sion, 6-track Kurla-Thane) are recorded as REAL DATA,
  while Fast/Slow service allocations are explicitly tagged as PROTOTYPE_ASSUMPTION.
"""

from __future__ import annotations

import glob
import json
import logging
import math
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

logger = logging.getLogger(__name__)


def _haversine_distance_km(
    lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None
) -> float | None:
    """Compute Great-Circle / Haversine distance in kilometers between two GPS points."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    r_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return round(r_km * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a))), 4)


@dataclass(frozen=True)
class StationNode:
    """Represents a physical or operational station / cabin node in the network."""

    station_code: str
    station_name: str
    latitude: float | None = None
    longitude: float | None = None
    line_corridor: str = "Central Line"
    is_terminal: bool = False
    is_halt: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "station_code": self.station_code,
            "station_name": self.station_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "line_corridor": self.line_corridor,
            "is_terminal": self.is_terminal,
            "is_halt": self.is_halt,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StationNode:
        return cls(
            station_code=str(data["station_code"]),
            station_name=str(data.get("station_name", data["station_code"])),
            latitude=float(data["latitude"]) if data.get("latitude") is not None else None,
            longitude=float(data["longitude"]) if data.get("longitude") is not None else None,
            line_corridor=str(data.get("line_corridor", "Central Line")),
            is_terminal=bool(data.get("is_terminal", False)),
            is_halt=bool(data.get("is_halt", True)),
        )


@dataclass
class TrackResource:
    """Represents a directional parallel track resource between two consecutive stations.

    Distinguishes verified physical multi-track capacity (from infrastructure CSV) from
    the prototype assumption of allocating Fast vs Slow services to separate parallel tracks.
    """

    resource_id: str
    from_station: str
    to_station: str
    direction: str = "DOWN"
    track_type: str = "DOWN_SLOW"  # "DOWN_SLOW", "DOWN_FAST", "DEFAULT"
    capacity: int = 1
    physical_corridor_tracks: int = 4
    serving_trains: list[str] = field(default_factory=list)
    source: str = "csmt_thane_railway_infrastructure.csv"
    is_prototype_assumption: bool = True
    track_assignment_status: str = "PROTOTYPE_ASSUMPTION"

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "from_station": self.from_station,
            "to_station": self.to_station,
            "direction": self.direction,
            "track_type": self.track_type,
            "capacity": self.capacity,
            "physical_corridor_tracks": self.physical_corridor_tracks,
            "serving_trains": sorted(list(self.serving_trains)),
            "source": self.source,
            "is_prototype_assumption": self.is_prototype_assumption,
            "track_assignment_status": self.track_assignment_status,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TrackResource:
        return cls(
            resource_id=str(data["resource_id"]),
            from_station=str(data["from_station"]),
            to_station=str(data["to_station"]),
            direction=str(data.get("direction", "DOWN")),
            track_type=str(data.get("track_type", "DEFAULT")),
            capacity=int(data.get("capacity", 1)),
            physical_corridor_tracks=int(data.get("physical_corridor_tracks", 2)),
            serving_trains=list(data.get("serving_trains", [])),
            source=str(data.get("source", "csmt_thane_railway_infrastructure.csv")),
            is_prototype_assumption=bool(
                data.get("is_prototype_assumption", True)
            ),
            track_assignment_status=str(
                data.get("track_assignment_status", "PROTOTYPE_ASSUMPTION")
            ),
        )


@dataclass
class TrackEdge:
    """Represents a directed track block segment between two consecutive stations."""

    edge_id: str
    from_station: str
    to_station: str
    distance_km: float | None = None
    direction: str = "DOWN"
    serving_trains: list[str] = field(default_factory=list)
    service_types: list[str] = field(default_factory=list)
    scheduled_travel_time_seconds: float | None = None
    historical_travel_time_seconds: float | None = None
    route_speed_kmh: float | None = None
    capacity: int = 1
    capacity_is_prototype_assumption: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "from_station": self.from_station,
            "to_station": self.to_station,
            "distance_km": self.distance_km,
            "direction": self.direction,
            "serving_trains": sorted(list(self.serving_trains)),
            "service_types": sorted(list(set(self.service_types))),
            "scheduled_travel_time_seconds": self.scheduled_travel_time_seconds,
            "historical_travel_time_seconds": self.historical_travel_time_seconds,
            "route_speed_kmh": self.route_speed_kmh,
            "capacity": self.capacity,
            "capacity_is_prototype_assumption": self.capacity_is_prototype_assumption,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TrackEdge:
        return cls(
            edge_id=str(data["edge_id"]),
            from_station=str(data["from_station"]),
            to_station=str(data["to_station"]),
            distance_km=float(data["distance_km"]) if data.get("distance_km") is not None else None,
            direction=str(data.get("direction", "DOWN")),
            serving_trains=list(data.get("serving_trains", [])),
            service_types=list(data.get("service_types", [])),
            scheduled_travel_time_seconds=(
                float(data["scheduled_travel_time_seconds"])
                if data.get("scheduled_travel_time_seconds") is not None
                else None
            ),
            historical_travel_time_seconds=(
                float(data["historical_travel_time_seconds"])
                if data.get("historical_travel_time_seconds") is not None
                else None
            ),
            route_speed_kmh=(
                float(data["route_speed_kmh"]) if data.get("route_speed_kmh") is not None else None
            ),
            capacity=int(data.get("capacity", 1)),
            capacity_is_prototype_assumption=bool(
                data.get("capacity_is_prototype_assumption", True)
            ),
        )


@dataclass
class TrainRoute:
    """Ordered sequence of stations and track segment edges traversed by a train."""

    train_number: str
    train_name: str
    service_type: str
    origin_code: str
    destination_code: str
    stations: list[str] = field(default_factory=list)
    edges: list[str] = field(default_factory=list)
    stop_count: int = 0
    total_distance_km: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "train_number": self.train_number,
            "train_name": self.train_name,
            "service_type": self.service_type,
            "origin_code": self.origin_code,
            "destination_code": self.destination_code,
            "stations": list(self.stations),
            "edges": list(self.edges),
            "stop_count": self.stop_count or len(self.stations),
            "total_distance_km": self.total_distance_km,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TrainRoute:
        stations = list(data.get("stations", []))
        return cls(
            train_number=str(data["train_number"]),
            train_name=str(data.get("train_name", data["train_number"])),
            service_type=str(data.get("service_type", "EMU")),
            origin_code=str(data.get("origin_code", stations[0] if stations else "")),
            destination_code=str(data.get("destination_code", stations[-1] if stations else "")),
            stations=stations,
            edges=list(data.get("edges", [])),
            stop_count=int(data.get("stop_count", len(stations))),
            total_distance_km=(
                float(data["total_distance_km"])
                if data.get("total_distance_km") is not None
                else None
            ),
        )


class RailwayNetworkGraph:
    """Directed railway network graph containing station nodes, track edges, and track resources."""

    def __init__(
        self,
        nodes: dict[str, StationNode] | None = None,
        edges: dict[str, TrackEdge] | None = None,
        train_routes: dict[str, TrainRoute] | None = None,
        track_resources: dict[str, TrackResource] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._nodes: dict[str, StationNode] = dict(nodes) if nodes else {}
        self._edges: dict[str, TrackEdge] = dict(edges) if edges else {}
        self._train_routes: dict[str, TrainRoute] = dict(train_routes) if train_routes else {}
        self._track_resources: dict[str, TrackResource] = (
            dict(track_resources) if track_resources else {}
        )
        self._metadata: dict[str, Any] = dict(metadata) if metadata else {}
        self._build_adjacency()

    def _build_adjacency(self) -> None:
        self._adjacency: dict[str, list[str]] = {code: [] for code in self._nodes}
        self._predecessors: dict[str, list[str]] = {code: [] for code in self._nodes}
        for edge in self._edges.values():
            if edge.from_station in self._adjacency:
                if edge.to_station not in self._adjacency[edge.from_station]:
                    self._adjacency[edge.from_station].append(edge.to_station)
            else:
                self._adjacency[edge.from_station] = [edge.to_station]

            if edge.to_station in self._predecessors:
                if edge.from_station not in self._predecessors[edge.to_station]:
                    self._predecessors[edge.to_station].append(edge.from_station)
            else:
                self._predecessors[edge.to_station] = [edge.from_station]

    # Node Accessors
    def get_node(self, station_code: str) -> StationNode | None:
        return self._nodes.get(station_code)

    def has_node(self, station_code: str) -> bool:
        return station_code in self._nodes

    def all_nodes(self) -> list[StationNode]:
        return list(self._nodes.values())

    # Edge Accessors
    def get_edge(self, from_station: str, to_station: str) -> TrackEdge | None:
        edge_id = f"{from_station}__{to_station}"
        return self._edges.get(edge_id)

    def get_edge_by_id(self, edge_id: str) -> TrackEdge | None:
        return self._edges.get(edge_id)

    def has_edge(self, from_station: str, to_station: str) -> bool:
        return f"{from_station}__{to_station}" in self._edges

    def all_edges(self) -> list[TrackEdge]:
        return list(self._edges.values())

    # TrackResource Accessors
    def get_track_resources(self) -> list[TrackResource]:
        """Return list of all track resources (parallel slow/fast lines and default segments)."""
        return list(self._track_resources.values())

    def get_track_resource(self, resource_id: str) -> TrackResource | None:
        """Lookup track resource by unique resource ID."""
        return self._track_resources.get(resource_id)

    def get_resources_between(
        self, from_station: str, to_station: str
    ) -> list[TrackResource]:
        """Return all parallel track resources connecting two consecutive stations."""
        return [
            r
            for r in self._track_resources.values()
            if r.from_station == from_station and r.to_station == to_station
        ]

    def get_train_track_resource(
        self, train_number: str, from_station: str, to_station: str
    ) -> TrackResource | None:
        """Return the specific track resource assigned to a train on a station pair."""
        resources = self.get_resources_between(from_station, to_station)
        for r in resources:
            if str(train_number) in r.serving_trains:
                return r
        return resources[0] if resources else None

    def get_trains_on_resource(self, resource_id: str) -> list[str]:
        """Return list of trains utilizing a specific track resource."""
        res = self.get_track_resource(resource_id)
        return list(res.serving_trains) if res else []

    # Topology Queries
    def get_successors(self, station_code: str) -> list[str]:
        return list(self._adjacency.get(station_code, []))

    def get_predecessors(self, station_code: str) -> list[str]:
        return list(self._predecessors.get(station_code, []))

    def get_outgoing_edges(self, station_code: str) -> list[TrackEdge]:
        return [
            edge
            for edge in self._edges.values()
            if edge.from_station == station_code
        ]

    def get_incoming_edges(self, station_code: str) -> list[TrackEdge]:
        return [
            edge
            for edge in self._edges.values()
            if edge.to_station == station_code
        ]

    # Train Route Queries
    def get_train_route(self, train_number: str) -> TrainRoute | None:
        return self._train_routes.get(str(train_number))

    def all_train_routes(self) -> list[TrainRoute]:
        return list(self._train_routes.values())

    def get_train_edges(self, train_number: str) -> list[TrackEdge]:
        route = self.get_train_route(train_number)
        if not route:
            return []
        edges: list[TrackEdge] = []
        for edge_id in route.edges:
            edge = self.get_edge_by_id(edge_id)
            if edge:
                edges.append(edge)
        return edges

    def get_train_stations(self, train_number: str) -> list[StationNode]:
        route = self.get_train_route(train_number)
        if not route:
            return []
        nodes: list[StationNode] = []
        for code in route.stations:
            node = self.get_node(code)
            if node:
                nodes.append(node)
        return nodes

    # Conflict-Ready Analysis Helpers
    def get_trains_on_edge(self, edge_id: str) -> list[str]:
        edge = self.get_edge_by_id(edge_id)
        if not edge:
            return []
        return list(edge.serving_trains)

    def get_shared_edges(self, train_a: str, train_b: str) -> list[str]:
        """Return list of edge IDs that both train_a and train_b traverse."""
        route_a = self.get_train_route(train_a)
        route_b = self.get_train_route(train_b)
        if not route_a or not route_b:
            return []
        set_b = set(route_b.edges)
        return [e for e in route_a.edges if e in set_b]

    def summary(self) -> dict[str, Any]:
        """Return topological summary statistics of the network graph."""
        edges_with_distance = sum(1 for e in self._edges.values() if e.distance_km is not None)
        edges_with_hist_tt = sum(
            1 for e in self._edges.values() if e.historical_travel_time_seconds is not None
        )
        total_track_length_km = round(
            sum(e.distance_km for e in self._edges.values() if e.distance_km is not None), 2
        )
        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "track_resource_count": len(self._track_resources),
            "train_route_count": len(self._train_routes),
            "edges_with_distance": edges_with_distance,
            "edges_with_historical_travel_time": edges_with_hist_tt,
            "total_track_length_km": total_track_length_km,
            "directionality": "DOWN (outbound from CSMT)",
            "corridor": "Central Line",
        }

    # Serialization
    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self._metadata,
            "summary": self.summary(),
            "nodes": {code: node.to_dict() for code, node in sorted(self._nodes.items())},
            "edges": {edge_id: edge.to_dict() for edge_id, edge in sorted(self._edges.items())},
            "track_resources": {
                res_id: res.to_dict() for res_id, res in sorted(self._track_resources.items())
            },
            "train_routes": {
                num: route.to_dict() for num, route in sorted(self._train_routes.items())
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RailwayNetworkGraph:
        nodes = {
            code: StationNode.from_dict(val)
            for code, val in data.get("nodes", {}).items()
        }
        edges = {
            edge_id: TrackEdge.from_dict(val)
            for edge_id, val in data.get("edges", {}).items()
        }
        train_routes = {
            num: TrainRoute.from_dict(val)
            for num, val in data.get("train_routes", {}).items()
        }
        track_resources = {
            res_id: TrackResource.from_dict(val)
            for res_id, val in data.get("track_resources", {}).items()
        }
        metadata = dict(data.get("metadata", {}))
        return cls(
            nodes=nodes,
            edges=edges,
            train_routes=train_routes,
            track_resources=track_resources,
            metadata=metadata,
        )

    def to_json(self, filepath: str | Path | None = None, indent: int = 2) -> str:
        payload = json.dumps(self.to_dict(), indent=indent)
        if filepath is not None:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(payload)
        return payload

    @classmethod
    def from_json(cls, filepath_or_json: str | Path) -> RailwayNetworkGraph:
        content = str(filepath_or_json)
        if os.path.exists(content):
            with open(content, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(content)
        return cls.from_dict(data)

    def save_static_artifacts(self, output_dir: str | Path) -> dict[str, Path]:
        """Save separate JSON artifacts for graph, nodes, edges, track resources, and train routes."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        graph_path = out / "railway_graph.json"
        nodes_path = out / "station_nodes.json"
        edges_path = out / "track_edges.json"
        resources_path = out / "track_resources.json"
        routes_path = out / "train_routes.json"

        # 1. Full graph
        self.to_json(graph_path)

        # 2. Nodes
        with open(nodes_path, "w", encoding="utf-8") as f:
            json.dump([n.to_dict() for n in self.all_nodes()], f, indent=2)

        # 3. Edges
        with open(edges_path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self.all_edges()], f, indent=2)

        # 4. Track Resources
        with open(resources_path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.get_track_resources()], f, indent=2)

        # 5. Train Routes
        with open(routes_path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.all_train_routes()], f, indent=2)

        return {
            "railway_graph": graph_path,
            "station_nodes": nodes_path,
            "track_edges": edges_path,
            "track_resources": resources_path,
            "train_routes": routes_path,
        }

    def to_networkx(self) -> Any:
        """Convert to a NetworkX DiGraph instance if networkx is available."""
        try:
            import networkx as nx
        except ImportError as err:
            raise ImportError(
                "networkx is required for to_networkx(). Install via pip install networkx."
            ) from err

        graph = nx.DiGraph()
        for node in self.all_nodes():
            graph.add_node(
                node.station_code,
                name=node.station_name,
                latitude=node.latitude,
                longitude=node.longitude,
                is_terminal=node.is_terminal,
            )
        for edge in self.all_edges():
            graph.add_edge(
                edge.from_station,
                edge.to_station,
                edge_id=edge.edge_id,
                distance_km=edge.distance_km,
                direction=edge.direction,
                serving_trains=edge.serving_trains,
                capacity=edge.capacity,
            )
        return graph


def build_central_line_graph(
    routes_dir: str | Path | None = None,
    master_csv_path: str | Path | None = None,
    selected_trains_path: str | Path | None = None,
    infra_csv_path: str | Path | None = None,
) -> RailwayNetworkGraph:
    """Build the Central Line railway network graph from static route JSON files and observation data."""
    current_dir = Path(__file__).resolve().parent
    repo_root = current_dir.parent.parent

    if routes_dir is None:
        routes_dir = repo_root / "data" / "static" / "routes"
    else:
        routes_dir = Path(routes_dir)

    if master_csv_path is None:
        master_csv_path = repo_root / "data" / "processed" / "live_observations_master.csv"
    else:
        master_csv_path = Path(master_csv_path)

    if selected_trains_path is None:
        selected_trains_path = repo_root / "data" / "selected_trains.json"
    else:
        selected_trains_path = Path(selected_trains_path)

    if infra_csv_path is None:
        infra_csv_path = repo_root / "data" / "static" / "csmt_thane_railway_infrastructure.csv"
    else:
        infra_csv_path = Path(infra_csv_path)

    # 1. Load train metadata if available
    train_metadata: dict[str, dict[str, Any]] = {}
    if selected_trains_path.exists():
        try:
            with open(selected_trains_path, "r", encoding="utf-8") as f:
                st_data = json.load(f)
                for item in st_data.get("selected_trains", []):
                    num = str(item.get("number", ""))
                    if num:
                        name = item.get("name", "")
                        stype = "FAST" if "Fast" in name else ("SLOW" if "Slow" in name else "EMU")
                        train_metadata[num] = {
                            "name": name,
                            "train_type": item.get("train_type", "EMU"),
                            "service_type": stype,
                            "source_code": item.get("source", {}).get("code", "CSMT"),
                            "dest_code": item.get("destination", {}).get("code", "TNA"),
                        }
        except Exception as e:
            logger.warning("Could not parse selected_trains.json: %s", e)

    # 2. Extract empirical travel times from master CSV if available
    empirical_travel_times: dict[str, float] = {}
    if master_csv_path.exists():
        try:
            df = pd.read_csv(master_csv_path)
            if (
                "previous_station_code" in df.columns
                and "current_station_code" in df.columns
                and "station_to_station_travel_time_seconds" in df.columns
            ):
                valid = df.dropna(
                    subset=[
                        "previous_station_code",
                        "current_station_code",
                        "station_to_station_travel_time_seconds",
                    ]
                )
                valid = valid[valid["station_to_station_travel_time_seconds"] > 0]
                grouped = valid.groupby(["previous_station_code", "current_station_code"])[
                    "station_to_station_travel_time_seconds"
                ].agg(["count", "median"])
                for (prev_code, curr_code), row in grouped.iterrows():
                    if row["count"] >= 2:
                        edge_id = f"{prev_code}__{curr_code}"
                        empirical_travel_times[edge_id] = round(float(row["median"]), 1)
        except Exception as e:
            logger.warning("Could not extract empirical travel times: %s", e)

    # 3. Load infrastructure multi-track verification data
    station_track_counts: dict[str, int] = {}
    if infra_csv_path.exists():
        try:
            df_infra = pd.read_csv(infra_csv_path)
            # Map station names to codes
            stn_map = {
                "CSMT": "CSMT", "Masjid": "MSD", "Sandhurst Road": "SNRD", "Byculla": "BY",
                "Chinchpokli": "CHG", "Currey Road": "CRD", "Parel": "PR", "Dadar": "DR",
                "Matunga": "MTN", "Sion": "SION", "Kurla": "CLA", "Vidyavihar": "VVH",
                "Ghatkopar": "GC", "Vikhroli": "VK", "Kanjurmarg": "KJRD", "Bhandup": "BND",
                "Nahur": "NHU", "Mulund": "MLND", "Thane": "TNA",
            }
            for _, r in df_infra.iterrows():
                stn_name = str(r["Station"])
                code = stn_map.get(stn_name, stn_name)
                tracks = int(r["Tracks"])
                station_track_counts[code] = tracks
        except Exception as e:
            logger.warning("Could not parse infrastructure CSV: %s", e)

    # 4. Parse static route files
    route_files = sorted(glob.glob(str(routes_dir / "*.json")))
    if not route_files:
        logger.warning("No route JSON files found in %s", routes_dir)

    raw_nodes: dict[str, StationNode] = {}
    raw_edges: dict[str, TrackEdge] = {}
    train_routes: dict[str, TrainRoute] = {}

    for rf in route_files:
        fname = Path(rf).name
        train_num = fname.split("_")[-1].replace(".json", "")
        with open(rf, "r", encoding="utf-8") as f:
            content = json.load(f)

        data = content.get("response", {}).get("data", {})
        stops = data.get("stops", [])
        if not stops:
            continue

        meta = train_metadata.get(train_num, {})
        train_name = meta.get("name", f"Local {train_num}")
        service_type = meta.get("service_type", "FAST" if "Fast" in train_name else "SLOW")

        station_seq: list[str] = []
        for s in stops:
            code = str(s.get("code"))
            name = str(s.get("name", code))
            lat = float(s["lat"]) if s.get("lat") is not None else None
            lng = float(s["lng"]) if s.get("lng") is not None else None
            station_seq.append(code)

            if code not in raw_nodes:
                raw_nodes[code] = StationNode(
                    station_code=code,
                    station_name=name,
                    latitude=lat,
                    longitude=lng,
                    line_corridor="Central Line",
                    is_terminal=False,
                    is_halt=True,
                )

        if station_seq:
            last_code = station_seq[-1]
            if last_code in raw_nodes:
                orig = raw_nodes[last_code]
                raw_nodes[last_code] = StationNode(
                    station_code=orig.station_code,
                    station_name=orig.station_name,
                    latitude=orig.latitude,
                    longitude=orig.longitude,
                    line_corridor=orig.line_corridor,
                    is_terminal=True,
                    is_halt=orig.is_halt,
                )

        edge_ids: list[str] = []
        total_dist_km = 0.0
        for i in range(len(stops) - 1):
            s_from = stops[i]
            s_to = stops[i + 1]
            c_from = str(s_from.get("code"))
            c_to = str(s_to.get("code"))
            edge_id = f"{c_from}__{c_to}"
            edge_ids.append(edge_id)

            dist = _haversine_distance_km(
                s_from.get("lat"), s_from.get("lng"), s_to.get("lat"), s_to.get("lng")
            )
            if dist is not None:
                total_dist_km += dist

            hist_tt = empirical_travel_times.get(edge_id)

            if edge_id not in raw_edges:
                raw_edges[edge_id] = TrackEdge(
                    edge_id=edge_id,
                    from_station=c_from,
                    to_station=c_to,
                    distance_km=dist,
                    direction="DOWN",
                    serving_trains=[train_num],
                    service_types=[service_type],
                    scheduled_travel_time_seconds=None,
                    historical_travel_time_seconds=hist_tt,
                    route_speed_kmh=None,
                    capacity=1,
                    capacity_is_prototype_assumption=True,
                )
            else:
                existing = raw_edges[edge_id]
                if train_num not in existing.serving_trains:
                    existing.serving_trains.append(train_num)
                if service_type not in existing.service_types:
                    existing.service_types.append(service_type)
                if hist_tt is not None and existing.historical_travel_time_seconds is None:
                    existing.historical_travel_time_seconds = hist_tt

        train_routes[train_num] = TrainRoute(
            train_number=train_num,
            train_name=train_name,
            service_type=service_type,
            origin_code=station_seq[0] if station_seq else "CSMT",
            destination_code=station_seq[-1] if station_seq else "TNA",
            stations=station_seq,
            edges=edge_ids,
            stop_count=len(station_seq),
            total_distance_km=round(total_dist_km, 2) if total_dist_km > 0 else None,
        )

    # 5. Build Track Resources (Dual-Track Extension)
    raw_track_resources: dict[str, TrackResource] = {}
    for edge in raw_edges.values():
        c_from = edge.from_station
        c_to = edge.to_station
        tracks_count = station_track_counts.get(c_from, 2)

        # In CSMT-Thane corridor (where 4 or 6 tracks exist)
        if c_from in station_track_counts or c_to in station_track_counts or tracks_count >= 4:
            # Create DOWN_SLOW resource
            slow_res_id = f"{c_from}__{c_to}__DOWN_SLOW"
            slow_trains = [
                t_num for t_num in edge.serving_trains
                if train_routes.get(t_num) and train_routes[t_num].service_type != "FAST"
            ]
            raw_track_resources[slow_res_id] = TrackResource(
                resource_id=slow_res_id,
                from_station=c_from,
                to_station=c_to,
                direction="DOWN",
                track_type="DOWN_SLOW",
                capacity=1,
                physical_corridor_tracks=tracks_count,
                serving_trains=slow_trains,
                source="csmt_thane_railway_infrastructure.csv",
                is_prototype_assumption=True,
                track_assignment_status="PROTOTYPE_ASSUMPTION",
            )

            # Create DOWN_FAST resource
            fast_res_id = f"{c_from}__{c_to}__DOWN_FAST"
            fast_trains = [
                t_num for t_num in edge.serving_trains
                if train_routes.get(t_num) and train_routes[t_num].service_type == "FAST"
            ]
            raw_track_resources[fast_res_id] = TrackResource(
                resource_id=fast_res_id,
                from_station=c_from,
                to_station=c_to,
                direction="DOWN",
                track_type="DOWN_FAST",
                capacity=1,
                physical_corridor_tracks=tracks_count,
                serving_trains=fast_trains,
                source="csmt_thane_railway_infrastructure.csv",
                is_prototype_assumption=True,
                track_assignment_status="PROTOTYPE_ASSUMPTION",
            )
        else:
            # Beyond Thane / Suburbs without explicit multi-track data
            default_res_id = f"{c_from}__{c_to}__DEFAULT"
            raw_track_resources[default_res_id] = TrackResource(
                resource_id=default_res_id,
                from_station=c_from,
                to_station=c_to,
                direction="DOWN",
                track_type="DEFAULT",
                capacity=1,
                physical_corridor_tracks=2,
                serving_trains=list(edge.serving_trains),
                source="railway_graph_default",
                is_prototype_assumption=True,
                track_assignment_status="PROTOTYPE_ASSUMPTION",
            )

    # 6. Metadata
    metadata = {
        "source": "RailRadar static route snapshots + csmt_thane_railway_infrastructure.csv",
        "corridor": "Central Line (CSMT - TNA / KYN / KHPI / KSRA)",
        "builder": "Nexora Railway Network Graph Builder",
        "direction": "DOWN",
        "track_resource_extension": "Dual-Track Directional Resources (DOWN_SLOW / DOWN_FAST / DEFAULT)",
    }

    return RailwayNetworkGraph(
        nodes=raw_nodes,
        edges=raw_edges,
        train_routes=train_routes,
        track_resources=raw_track_resources,
        metadata=metadata,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    graph = build_central_line_graph()
    repo_root = Path(__file__).resolve().parent.parent.parent
    static_dir = repo_root / "data" / "static"
    artifacts = graph.save_static_artifacts(static_dir)
    print("Graph built successfully:")
    print(json.dumps(graph.summary(), indent=2))
    print("Artifacts generated:")
    for name, path in artifacts.items():
        print(f"  {name}: {path}")
