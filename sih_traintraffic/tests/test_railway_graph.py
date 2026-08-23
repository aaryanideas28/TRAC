"""Unit and validation tests for the Nexora railway network graph layer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from railradar.railway_graph import (
    RailwayNetworkGraph,
    StationNode,
    TrackEdge,
    TrainRoute,
    build_central_line_graph,
)


@pytest.fixture(scope="module")
def graph() -> RailwayNetworkGraph:
    """Build the Central Line network graph from repository data."""
    return build_central_line_graph()


def test_01_graph_builds_and_has_expected_scale(graph: RailwayNetworkGraph) -> None:
    """Verify graph constructs with valid node, edge, and train route counts."""
    summary = graph.summary()
    assert summary["node_count"] == 61
    assert summary["edge_count"] == 62
    assert summary["train_route_count"] == 10
    assert summary["edges_with_distance"] == 62
    assert summary["directionality"] == "DOWN (outbound from CSMT)"
    assert summary["corridor"] == "Central Line"


def test_02_all_nodes_have_valid_attributes(graph: RailwayNetworkGraph) -> None:
    """Verify every node has a non-empty code, name, and valid GPS coordinates."""
    nodes = graph.all_nodes()
    assert len(nodes) == 61

    for node in nodes:
        assert isinstance(node.station_code, str) and len(node.station_code) > 0
        assert isinstance(node.station_name, str) and len(node.station_name) > 0
        assert isinstance(node.latitude, float)
        assert isinstance(node.longitude, float)
        assert 18.0 <= node.latitude <= 20.5  # Mumbai / Maharashtra geographic bounding box
        assert 72.0 <= node.longitude <= 74.0
        assert node.line_corridor == "Central Line"


def test_03_all_edges_connect_known_nodes_and_have_positive_distances(
    graph: RailwayNetworkGraph,
) -> None:
    """Verify every directed edge connects two existing nodes without self-loops."""
    edges = graph.all_edges()
    assert len(edges) == 62

    edge_ids = set()
    for edge in edges:
        assert edge.edge_id not in edge_ids, f"Duplicate edge ID: {edge.edge_id}"
        edge_ids.add(edge.edge_id)

        assert edge.edge_id == f"{edge.from_station}__{edge.to_station}"
        assert edge.from_station != edge.to_station, f"Self-loop on station {edge.from_station}"
        assert graph.has_node(edge.from_station), f"Unknown from_station: {edge.from_station}"
        assert graph.has_node(edge.to_station), f"Unknown to_station: {edge.to_station}"
        assert edge.distance_km is not None and edge.distance_km > 0.0
        assert edge.direction == "DOWN"
        assert len(edge.serving_trains) > 0


def test_04_prototype_capacity_is_explicitly_flagged(graph: RailwayNetworkGraph) -> None:
    """Verify edge capacity is explicitly flagged as a prototype assumption."""
    for edge in graph.all_edges():
        assert edge.capacity == 1
        assert edge.capacity_is_prototype_assumption is True


def test_05_train_routes_match_graph_edges(graph: RailwayNetworkGraph) -> None:
    """Verify that every train route's consecutive station pairs match valid graph edges."""
    routes = graph.all_train_routes()
    assert len(routes) == 10

    for route in routes:
        assert len(route.stations) >= 2
        assert len(route.edges) == len(route.stations) - 1
        assert route.origin_code == route.stations[0]
        assert route.destination_code == route.stations[-1]

        for i in range(len(route.stations) - 1):
            s_from = route.stations[i]
            s_to = route.stations[i + 1]
            expected_edge_id = f"{s_from}__{s_to}"
            assert route.edges[i] == expected_edge_id

            edge = graph.get_edge(s_from, s_to)
            assert edge is not None, f"Missing edge {expected_edge_id} for train {route.train_number}"
            assert route.train_number in edge.serving_trains


def test_06_fast_and_slow_route_divergence(graph: RailwayNetworkGraph) -> None:
    """Verify fast vs slow routes correctly branch at Thane (TNA)."""
    # Fast train 95333 uses Thane B Cabin (XX-TNAB) bypass
    route_fast = graph.get_train_route("95333")
    assert route_fast is not None
    assert "TNA__XX-TNAB" in route_fast.edges
    assert "XX-TNAB__DIVA" in route_fast.edges
    assert "TNA__KLVA" not in route_fast.edges

    # Slow train 96333 uses Kalva (KLVA) / Mumbra (MBQ) route
    route_slow = graph.get_train_route("96333")
    assert route_slow is not None
    assert "TNA__KLVA" in route_slow.edges
    assert "KLVA__KLVC" in route_slow.edges
    assert "MBQ__DIVA" in route_slow.edges
    assert "TNA__XX-TNAB" not in route_slow.edges


def test_07_shared_edges_conflict_helper(graph: RailwayNetworkGraph) -> None:
    """Verify conflict query correctly finds shared segments between trains."""
    shared = graph.get_shared_edges("95333", "96333")
    # Both trains share the CSMT -> TNA trunk (22 edges)
    assert len(shared) >= 22
    assert "CSMT__MSD" in shared
    assert "MLND__TNA" in shared
    # They do NOT share TNA outbound segments
    assert "TNA__XX-TNAB" not in shared
    assert "TNA__KLVA" not in shared


def test_08_graph_query_accessors(graph: RailwayNetworkGraph) -> None:
    """Verify query accessors return accurate topological and route details."""
    # Successors of TNA should be both XX-TNAB (Fast) and KLVA (Slow)
    successors = graph.get_successors("TNA")
    assert set(successors) == {"XX-TNAB", "KLVA"}

    # Outgoing edges from TNA
    out_edges = graph.get_outgoing_edges("TNA")
    out_ids = {e.edge_id for e in out_edges}
    assert out_ids == {"TNA__XX-TNAB", "TNA__KLVA"}

    # Incoming edges to DIVA
    in_edges = graph.get_incoming_edges("DIVA")
    in_froms = {e.from_station for e in in_edges}
    assert "XX-TNAB" in in_froms
    assert "MBQ" in in_froms

    # Trains on edge CSMT__MSD
    trains_on_trunk = graph.get_trains_on_edge("CSMT__MSD")
    assert len(trains_on_trunk) == 10

    # Train edges query
    train_edges = graph.get_train_edges("97419")
    assert len(train_edges) == 22
    assert train_edges[0].edge_id == "CSMT__MSD"
    assert train_edges[-1].edge_id == "MLND__TNA"


def test_09_serialization_roundtrip(graph: RailwayNetworkGraph, tmp_path: Path) -> None:
    """Verify complete lossless JSON serialization and deserialization."""
    json_path = tmp_path / "test_graph.json"
    json_str = graph.to_json(json_path)

    reloaded_from_file = RailwayNetworkGraph.from_json(json_path)
    reloaded_from_str = RailwayNetworkGraph.from_json(json_str)

    assert reloaded_from_file.summary() == graph.summary()
    assert reloaded_from_str.summary() == graph.summary()
    assert len(reloaded_from_file.all_nodes()) == len(graph.all_nodes())
    assert len(reloaded_from_file.all_edges()) == len(graph.all_edges())
    assert len(reloaded_from_file.all_train_routes()) == len(graph.all_train_routes())

    # Verify identical edge attributes
    for edge in graph.all_edges():
        reloaded_edge = reloaded_from_file.get_edge_by_id(edge.edge_id)
        assert reloaded_edge is not None
        assert reloaded_edge.distance_km == edge.distance_km
        assert reloaded_edge.serving_trains == edge.serving_trains
        assert reloaded_edge.capacity == edge.capacity


def test_10_networkx_conversion(graph: RailwayNetworkGraph) -> None:
    """Verify conversion to NetworkX DiGraph retains all nodes and edges."""
    nx_graph = graph.to_networkx()
    assert nx_graph.number_of_nodes() == 61
    assert nx_graph.number_of_edges() == 62
    assert nx_graph.has_node("CSMT")
    assert nx_graph.has_node("TNA")
    assert nx_graph.has_edge("CSMT", "MSD")
    assert nx_graph.has_edge("MLND", "TNA")


def test_11_static_artifact_files_exist_and_match(graph: RailwayNetworkGraph) -> None:
    """Verify saved static JSON artifacts exist and match graph structure."""
    repo_root = Path(__file__).resolve().parent.parent
    static_dir = repo_root / "data" / "static"

    graph_file = static_dir / "railway_graph.json"
    nodes_file = static_dir / "station_nodes.json"
    edges_file = static_dir / "track_edges.json"
    routes_file = static_dir / "train_routes.json"

    assert graph_file.exists()
    assert nodes_file.exists()
    assert edges_file.exists()
    assert routes_file.exists()

    with open(nodes_file, "r", encoding="utf-8") as f:
        nodes_data = json.load(f)
        assert len(nodes_data) == 61

    with open(edges_file, "r", encoding="utf-8") as f:
        edges_data = json.load(f)
        assert len(edges_data) == 62

    with open(routes_file, "r", encoding="utf-8") as f:
        routes_data = json.load(f)
        assert len(routes_data) == 10
