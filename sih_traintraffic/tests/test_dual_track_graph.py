"""Unit tests for the Dual-Track Graph Extension and TrackResource abstractions.

Verifies:
1. Existing 61 station nodes remain valid.
2. Existing 62 logical edges remain valid.
3. Track resources have valid endpoints.
4. No invalid station references.
5. No duplicate resource IDs.
6. Resource direction is explicit ('DOWN').
7. Capacity is positive.
8. Fast/Slow assignment is explicitly marked as prototype assumption.
9. Existing graph serialization still works.
10. Resource lookup queries (get_track_resources, get_resources_between, get_train_track_resource, get_trains_on_resource).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from railradar.railway_graph import (
    RailwayNetworkGraph,
    StationNode,
    TrackEdge,
    TrackResource,
    TrainRoute,
    build_central_line_graph,
)


@pytest.fixture(scope="module")
def graph() -> RailwayNetworkGraph:
    """Build the extended railway network graph."""
    return build_central_line_graph()


def test_01_existing_nodes_and_edges_preserved(graph: RailwayNetworkGraph) -> None:
    """Verify 61 station nodes and 62 logical directed edges remain intact."""
    assert len(graph.all_nodes()) == 61
    assert len(graph.all_edges()) == 62
    assert graph.has_node("CSMT")
    assert graph.has_node("TNA")
    assert graph.has_node("KYN")
    assert graph.has_node("KSRA")
    assert graph.has_node("KHPI")
    assert graph.has_edge("CSMT", "MSD")
    assert graph.has_edge("MLND", "TNA")


def test_02_track_resources_count_and_valid_endpoints(graph: RailwayNetworkGraph) -> None:
    """Verify track resources are created and have valid endpoints matching graph nodes."""
    resources = graph.get_track_resources()
    assert len(resources) == 86  # 24 dual-track pairs (48) + 38 single-track pairs

    for res in resources:
        assert graph.has_node(res.from_station), f"Invalid from_station: {res.from_station}"
        assert graph.has_node(res.to_station), f"Invalid to_station: {res.to_station}"
        assert res.direction in ("DOWN", "UP", "BOTH")
        assert res.capacity > 0
        assert res.physical_corridor_tracks >= 2


def test_03_no_duplicate_resource_ids(graph: RailwayNetworkGraph) -> None:
    """Verify all resource IDs are unique strings."""
    resources = graph.get_track_resources()
    res_ids = [r.resource_id for r in resources]
    assert len(res_ids) == len(set(res_ids))


def test_04_csmt_thane_corridor_has_slow_and_fast_resources(graph: RailwayNetworkGraph) -> None:
    """Verify CSMT to Thane edges have both DOWN_SLOW and DOWN_FAST track resources."""
    csmt_msd_resources = graph.get_resources_between("CSMT", "MSD")
    assert len(csmt_msd_resources) == 2
    types = {r.track_type for r in csmt_msd_resources}
    assert types == {"DOWN_SLOW", "DOWN_FAST"}

    slow_res = next(r for r in csmt_msd_resources if r.track_type == "DOWN_SLOW")
    fast_res = next(r for r in csmt_msd_resources if r.track_type == "DOWN_FAST")

    assert slow_res.physical_corridor_tracks == 4
    assert fast_res.physical_corridor_tracks == 4


def test_05_explicit_prototype_assumption_markers(graph: RailwayNetworkGraph) -> None:
    """Verify Fast/Slow track assignment is explicitly marked as PROTOTYPE_ASSUMPTION."""
    resources = graph.get_track_resources()
    for res in resources:
        assert res.is_prototype_assumption is True
        assert res.track_assignment_status == "PROTOTYPE_ASSUMPTION"


def test_06_train_resource_lookups_and_service_segregation(graph: RailwayNetworkGraph) -> None:
    """Verify get_train_track_resource routes Fast trains to DOWN_FAST and Slow trains to DOWN_SLOW."""
    # Train 95011 is Fast Khopoli
    fast_res = graph.get_train_track_resource("95011", "CSMT", "MSD")
    assert fast_res is not None
    assert fast_res.track_type == "DOWN_FAST"
    assert "95011" in fast_res.serving_trains

    # Train 97259 is Slow Dombivli
    slow_res = graph.get_train_track_resource("97259", "CSMT", "MSD")
    assert slow_res is not None
    assert slow_res.track_type == "DOWN_SLOW"
    assert "97259" in slow_res.serving_trains

    # Query trains on resource
    trains_on_fast = graph.get_trains_on_resource(fast_res.resource_id)
    assert "95011" in trains_on_fast
    assert "97259" not in trains_on_fast


def test_07_graph_serialization_backward_compatibility(
    graph: RailwayNetworkGraph, tmp_path: Path
) -> None:
    """Verify graph can be serialized and deserialized with track_resources without data loss."""
    json_path = tmp_path / "test_graph_dual_track.json"
    graph.to_json(json_path)

    loaded_graph = RailwayNetworkGraph.from_json(json_path)
    assert len(loaded_graph.all_nodes()) == 61
    assert len(loaded_graph.all_edges()) == 62
    assert len(loaded_graph.get_track_resources()) == 86

    # Verify summary includes track resources
    summ = loaded_graph.summary()
    assert summ["track_resource_count"] == 86
    assert summ["node_count"] == 61
    assert summ["edge_count"] == 62
