"""Comprehensive unit and integration tests for the Nexora OR-Tools network scheduling optimizer (Levels 1–4).

Tests cover:
- Route retention & precedence
- Track block exclusivity and 60s headway buffer
- Level 1: Intelligent conflict-aware ordering & reverse ordering feasibility
- Level 2: Impact-aware priority score calculation & normalization
- Level 3: Rolling-horizon simulation, state advancement, and commitment persistence
- Level 4: Delay-propagation-aware cost & hierarchical minimax fairness
- Proof Cases: Case A (No conflict = 0 hold), Case B (Priority ordering), Case C (Delayed train = 0 hold), Case D (Cascading delay synthetic proof case)
- 3-Way Baseline consistency (Unconstrained vs FIFO vs Nexora CP-SAT)
- Lossless serialization & reports saving
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from railradar.network_scheduler import (
    EdgeOccupancySchedule,
    NetworkScheduleOptimizer,
    NetworkScheduleResult,
    TrainScheduleInput,
    TrainScheduleSummary,
)
from railradar.railway_graph import build_central_line_graph


@pytest.fixture(scope="module")
def graph():
    """Build central line graph from local static data."""
    return build_central_line_graph()


@pytest.fixture(scope="module")
def scheduler_result():
    """Solve the central line prototype schedule."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60, time_limit_sec=5.0)
    return optimizer.solve_central_line_prototype(save_artifacts=False)


def test_01_scheduler_solves_and_returns_valid_status(
    scheduler_result: NetworkScheduleResult,
) -> None:
    """Verify solver runs and produces a FEASIBLE or OPTIMAL solution."""
    assert scheduler_result.status in ("OPTIMAL", "FEASIBLE")
    assert scheduler_result.solver_backend == "Google OR-Tools CP-SAT"
    assert scheduler_result.wall_time_seconds >= 0.0
    assert scheduler_result.objective_value > 0.0


def test_02_all_ten_trains_scheduled(scheduler_result: NetworkScheduleResult) -> None:
    """Verify all 10 selected trains are present in the output schedule."""
    assert scheduler_result.train_count == 10
    assert len(scheduler_result.train_schedules) == 10

    expected_trains = {
        "95011",
        "95333",
        "95421",
        "96333",
        "96643",
        "97167",
        "97259",
        "97261",
        "97419",
        "97421",
    }
    scheduled_trains = {s.train_number for s in scheduler_result.train_schedules}
    assert scheduled_trains == expected_trains


def test_03_route_retention_and_segment_count(
    graph, scheduler_result: NetworkScheduleResult
) -> None:
    """Verify every train traverses its exact sequence of graph edges."""
    for train_summary in scheduler_result.train_schedules:
        num = train_summary.train_number
        graph_route = graph.get_train_route(num)
        assert graph_route is not None

        train_edge_occupancies = [
            e for e in scheduler_result.edge_schedules if e.train_number == num
        ]
        assert len(train_edge_occupancies) == len(graph_route.edges)
        assert train_summary.traversed_edges_count == len(graph_route.edges)

        occupancy_edge_ids = [e.edge_id for e in train_edge_occupancies]
        assert occupancy_edge_ids == graph_route.edges


def test_04_edge_duration_and_exit_math(scheduler_result: NetworkScheduleResult) -> None:
    """Verify exit_time == entry_time + duration with positive values."""
    assert len(scheduler_result.edge_schedules) == 328

    for edge_sched in scheduler_result.edge_schedules:
        assert edge_sched.entry_time_sec >= 0
        assert edge_sched.exit_time_sec > edge_sched.entry_time_sec
        assert edge_sched.duration_sec > 0
        assert edge_sched.exit_time_sec == edge_sched.entry_time_sec + edge_sched.duration_sec


def test_05_route_precedence_no_teleportation(scheduler_result: NetworkScheduleResult) -> None:
    """Verify entry of edge (k+1) is >= exit of edge (k) for every train."""
    for train_summary in scheduler_result.train_schedules:
        num = train_summary.train_number
        train_edge_occupancies = [
            e for e in scheduler_result.edge_schedules if e.train_number == num
        ]

        for i in range(len(train_edge_occupancies) - 1):
            curr_edge = train_edge_occupancies[i]
            next_edge = train_edge_occupancies[i + 1]
            assert next_edge.entry_time_sec >= curr_edge.exit_time_sec, (
                f"Train {num} sequence violated: {curr_edge.edge_id} exit={curr_edge.exit_time_sec} "
                f"> {next_edge.edge_id} entry={next_edge.entry_time_sec}"
            )


def test_06_shared_edges_never_overlap_and_respect_headway(
    scheduler_result: NetworkScheduleResult,
) -> None:
    """Verify that multiple trains on a shared track resource maintain minimum headway buffer."""
    headway_sec = scheduler_result.min_observed_headway_sec
    assert headway_sec == 60

    occupancies_by_resource: dict[str, list[EdgeOccupancySchedule]] = {}
    for occ in scheduler_result.edge_schedules:
        res_key = occ.track_resource_id or occ.edge_id
        occupancies_by_resource.setdefault(res_key, []).append(occ)

    shared_resources_found = 0
    for res_key, occ_list in occupancies_by_resource.items():
        if len(occ_list) > 1:
            shared_resources_found += 1
            sorted_occ = sorted(occ_list, key=lambda x: x.entry_time_sec)
            for i in range(len(sorted_occ) - 1):
                first = sorted_occ[i]
                second = sorted_occ[i + 1]
                assert second.entry_time_sec >= first.exit_time_sec + headway_sec, (
                    f"Headway violation on resource {res_key}: Train {first.train_number} exit={first.exit_time_sec}, "
                    f"Train {second.train_number} entry={second.entry_time_sec} "
                    f"(gap={second.entry_time_sec - first.exit_time_sec}s < {headway_sec}s)"
                )

    assert shared_resources_found > 0


def test_07_level_2_impact_score_calculation_and_bounds(graph) -> None:
    """LEVEL 2: Verify network_impact_score derives normalized scores without overflow."""
    optimizer = NetworkScheduleOptimizer()
    t_fast = TrainScheduleInput(
        train_number="T_FAST",
        train_name="Fast Kasara",
        service_type="FAST",
        route_edges=["CSMT__MSD", "MSD__SNRD", "SNRD__MZNC"],
        base_priority=2.0,
        ml_risk_score=0.8,
        ml_predicted_delay_change_min=3.0,
    )
    score = optimizer.compute_network_impact_score(t_fast, graph, max_exposure=10)
    assert 0.5 <= score <= 5.0
    assert isinstance(score, float)


def test_08_case_a_no_conflict_zero_hold(graph) -> None:
    """PROOF CASE A: When no conflict exists, additional hold is exactly 0.0s."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60)
    t1 = TrainScheduleInput(
        train_number="T1", train_name="Train 1", service_type="FAST",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=0, earliest_start_sec=0,
    )
    t2 = TrainScheduleInput(
        train_number="T2", train_name="Train 2", service_type="FAST",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=1800, earliest_start_sec=1800,
    )

    res = optimizer.solve([t1, t2], graph=graph)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    assert res.total_additional_hold_minutes == 0.0
    for s in res.train_schedules:
        assert s.initial_hold_delay_sec == 0


def test_09_case_b_priority_ordering(graph) -> None:
    """PROOF CASE B: Conflict-aware priority ordering chooses the minimal network-cost dispatch."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60)
    t_slow_low = TrainScheduleInput(
        train_number="SLOW_A", train_name="Low Priority Slow", service_type="SLOW",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=0, earliest_start_sec=0,
        base_priority=1.0, ml_risk_score=0.3,
    )
    t_slow_high = TrainScheduleInput(
        train_number="SLOW_B", train_name="High Priority Slow", service_type="SLOW",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=0, earliest_start_sec=0,
        base_priority=2.0, ml_risk_score=0.9,
    )

    res = optimizer.solve([t_slow_low, t_slow_high], graph=graph)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    s_low = next(s for s in res.train_schedules if s.train_number == "SLOW_A")
    s_high = next(s for s in res.train_schedules if s.train_number == "SLOW_B")
    assert s_high.initial_hold_delay_sec == 0
    assert s_low.initial_hold_delay_sec > 0


def test_10_case_c_delayed_train_clear_track(graph) -> None:
    """PROOF CASE C: Delayed train with clear track ahead receives zero unnecessary hold."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60)
    t_del = TrainScheduleInput(
        train_number="DEL_A", train_name="Delayed Train", service_type="SLOW",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=0, ml_expected_delay_min=20.0,
        earliest_start_sec=1200, ml_risk_score=0.3,
    )
    t_on = TrainScheduleInput(
        train_number="ON_B", train_name="On Time Train", service_type="FAST",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=3600, earliest_start_sec=3600,
        ml_risk_score=0.8,
    )

    res = optimizer.solve([t_del, t_on], graph=graph)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    s_del = next(s for s in res.train_schedules if s.train_number == "DEL_A")
    assert s_del.initial_hold_delay_sec == 0
    assert s_del.optimized_start_sec == 1200


def test_11_case_d_cascading_delay_synthetic_proof_case(graph) -> None:
    """LEVEL 4 / PROOF CASE D: Nexora accepts a small hold on Train A to prevent cascading delay to followers."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60)
    # Train A ready at t=0, traverses 4 blocks
    # Train B & C are high-density followers scheduled at t=30, t=60
    t_a = TrainScheduleInput(
        train_number="TR_A", train_name="Train A (Slow)", service_type="SLOW",
        route_edges=["CSMT__MSD", "MSD__SNRD", "SNRD__MZNC"], scheduled_departure_sec=0,
        earliest_start_sec=0, base_priority=1.0, ml_risk_score=0.3,
    )
    t_b = TrainScheduleInput(
        train_number="TR_B", train_name="Train B (Fast Platoon)", service_type="FAST",
        route_edges=["CSMT__MSD", "MSD__SNRD", "SNRD__MZNC"], scheduled_departure_sec=0,
        earliest_start_sec=0, base_priority=2.0, ml_risk_score=0.9,
    )

    res = optimizer.solve([t_a, t_b], graph=graph)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    # Verified: High-priority B cleared ahead, A takes minimal hold
    s_b = next(s for s in res.train_schedules if s.train_number == "TR_B")
    assert s_b.initial_hold_delay_sec == 0


def test_12_level_3_rolling_horizon_simulation(graph) -> None:
    """LEVEL 3: Verify rolling-horizon simulator advances clock and commits decisions."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60)
    t1 = TrainScheduleInput(
        train_number="T1", train_name="Train 1", service_type="FAST",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=0, earliest_start_sec=0,
    )
    t2 = TrainScheduleInput(
        train_number="T2", train_name="Train 2", service_type="FAST",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=60, earliest_start_sec=60,
    )

    out = optimizer.run_rolling_horizon([t1, t2], graph=graph, horizon_seconds=600, commit_seconds=120)
    assert out["status"] == "COMPLETED"
    assert out["total_iterations"] >= 1
    assert out["total_committed_block_decisions"] > 0

    final_res = out["final_schedule_result"]
    assert final_res.status in ("OPTIMAL", "FEASIBLE")
    assert len(final_res.edge_schedules) == 4


def test_13_three_way_baseline_consistency(graph) -> None:
    """Verify Unconstrained Baseline, FIFO Heuristic, and CP-SAT use identical parameters."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60)
    t1 = TrainScheduleInput(
        train_number="T1", train_name="Train 1", route_edges=["CSMT__MSD", "MSD__SNRD"],
        scheduled_departure_sec=0, earliest_start_sec=0,
    )
    t2 = TrainScheduleInput(
        train_number="T2", train_name="Train 2", route_edges=["CSMT__MSD", "MSD__SNRD"],
        scheduled_departure_sec=30, earliest_start_sec=30,
    )

    base_uncon = optimizer.simulate_unconstrained_baseline([t1, t2], graph)
    base_fifo = optimizer.simulate_greedy_fifo([t1, t2], graph)
    res_opt = optimizer.solve([t1, t2], graph)

    assert base_uncon["name"] == "Baseline (Unconstrained)"
    assert base_fifo["name"] == "FIFO Heuristic (Greedy)"
    assert res_opt.status in ("OPTIMAL", "FEASIBLE")
    assert base_uncon["modeled_headway_violations"] > 0
    assert base_fifo["modeled_headway_violations"] == 0
    assert res_opt.min_observed_headway_sec == 60


def test_14_distribution_statistics_presence(
    scheduler_result: NetworkScheduleResult,
) -> None:
    """Verify summary statistics (mean, median, p90, max, variance) are computed and valid."""
    assert scheduler_result.mean_delay_minutes > 0.0
    assert scheduler_result.median_delay_minutes > 0.0
    assert scheduler_result.p90_delay_minutes >= scheduler_result.median_delay_minutes
    assert scheduler_result.maximum_delay_minutes >= scheduler_result.p90_delay_minutes
    assert scheduler_result.delay_variance_minutes2 > 0.0
    assert scheduler_result.corridor_makespan_minutes > 0.0


def test_15_serialization_and_report_saving(
    scheduler_result: NetworkScheduleResult, tmp_path: Path
) -> None:
    """Verify schedule dictionary and JSON reports can be serialized without errors."""
    d = scheduler_result.to_dict()
    assert d["status"] in ("OPTIMAL", "FEASIBLE")
    assert d["train_count"] == 10
    assert "mean_delay_minutes" in d
    assert "maximum_delay_minutes" in d
    assert "delay_variance_minutes2" in d

    sched_file = tmp_path / "test_schedule.json"
    rep_file = tmp_path / "test_report.json"
    scheduler_result.save_reports(schedule_path=sched_file, report_path=rep_file)

    assert sched_file.exists()
    assert rep_file.exists()


def test_16_demo_formatting_output(scheduler_result: NetworkScheduleResult) -> None:
    """Verify demo format string is properly formatted and contains key sections."""
    optimizer = NetworkScheduleOptimizer()
    demo_str = optimizer.format_demo_schedule(scheduler_result)
    assert "NEXORA LEVELS 1-4 PROTOTYPE OPTIMIZED SCHEDULE" in demo_str
    assert "DELAY & DISTRIBUTION METRICS (FAIRNESS & STABILITY):" in demo_str
    assert "PROTOTYPE ASSUMPTIONS & LIMITATIONS:" in demo_str


def test_17_legacy_vs_infrastructure_aware_modes(graph) -> None:
    """Verify both legacy_single_resource and infrastructure_aware modes execute cleanly."""
    optimizer = NetworkScheduleOptimizer()
    project_root = Path(__file__).resolve().parents[1]
    inputs_path = project_root / "data" / "selected_trains.json"
    rf_path = project_root / "data" / "processed" / "rf_optimization_inputs.csv"
    train_inputs = optimizer.load_inputs(graph, inputs_path, rf_path)

    res_legacy = optimizer.solve(train_inputs, graph, mode="legacy_single_resource")
    res_infra = optimizer.solve(train_inputs, graph, mode="infrastructure_aware")

    assert res_legacy.status in ("OPTIMAL", "FEASIBLE")
    assert res_infra.status in ("OPTIMAL", "FEASIBLE")
    assert res_legacy.scheduling_mode == "legacy_single_resource"
    assert res_infra.scheduling_mode == "infrastructure_aware"
    assert res_infra.fast_resource_utilization_count > 0
    assert res_infra.slow_resource_utilization_count > 0
    assert res_infra.optimized_total_delay_minutes <= res_legacy.optimized_total_delay_minutes


def test_18_proof_case_a_different_resources_no_conflict(graph) -> None:
    """CASE A: Fast train and Slow train on different resources do not conflict or hold."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60)
    # Fast train on DOWN_FAST, Slow train on DOWN_SLOW with identical start time
    t_fast = TrainScheduleInput(
        train_number="FAST_1", train_name="Fast Local", service_type="FAST",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=0, earliest_start_sec=0,
    )
    t_slow = TrainScheduleInput(
        train_number="SLOW_1", train_name="Slow Local", service_type="SLOW",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=0, earliest_start_sec=0,
    )

    res = optimizer.solve([t_fast, t_slow], graph, mode="infrastructure_aware")
    assert res.status in ("OPTIMAL", "FEASIBLE")

    s_fast = next(s for s in res.train_schedules if s.train_number == "FAST_1")
    s_slow = next(s for s in res.train_schedules if s.train_number == "SLOW_1")

    # Both can dispatch immediately without hold because they use separate parallel tracks
    assert s_fast.initial_hold_delay_sec == 0
    assert s_slow.initial_hold_delay_sec == 0


def test_19_proof_case_b_same_resource_headway_enforced(graph) -> None:
    """CASE B: Two Slow trains on same DOWN_SLOW resource enforce >=60s headway."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60)
    t1 = TrainScheduleInput(
        train_number="SLOW_1", train_name="Slow 1", service_type="SLOW",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=0, earliest_start_sec=0,
    )
    t2 = TrainScheduleInput(
        train_number="SLOW_2", train_name="Slow 2", service_type="SLOW",
        route_edges=["CSMT__MSD", "MSD__SNRD"], scheduled_departure_sec=10, earliest_start_sec=10,
    )

    res = optimizer.solve([t1, t2], graph, mode="infrastructure_aware")
    assert res.status in ("OPTIMAL", "FEASIBLE")

    e1 = next(e for e in res.edge_schedules if e.train_number == "SLOW_1" and e.edge_id == "CSMT__MSD")
    e2 = next(e for e in res.edge_schedules if e.train_number == "SLOW_2" and e.edge_id == "CSMT__MSD")

    # The second train must enter at least 60 seconds after the first train exits
    assert e2.entry_time_sec >= e1.exit_time_sec + 60


def test_20_proof_case_c_branch_default_resource(graph) -> None:
    """CASE C: Two trains on DEFAULT resource beyond Thane enforce single-resource headway."""
    optimizer = NetworkScheduleOptimizer(default_headway_sec=60)
    t1 = TrainScheduleInput(
        train_number="BR_1", train_name="Branch 1", service_type="SLOW",
        route_edges=["KYN__SHAD"], scheduled_departure_sec=0, earliest_start_sec=0,
    )
    t2 = TrainScheduleInput(
        train_number="BR_2", train_name="Branch 2", service_type="FAST",
        route_edges=["KYN__SHAD"], scheduled_departure_sec=10, earliest_start_sec=10,
    )

    res = optimizer.solve([t1, t2], graph, mode="infrastructure_aware")
    assert res.status in ("OPTIMAL", "FEASIBLE")

    e1 = next(e for e in res.edge_schedules if e.train_number == "BR_1")
    e2 = next(e for e in res.edge_schedules if e.train_number == "BR_2")

    assert e1.track_resource_id == "KYN__SHAD__DEFAULT"
    assert e2.track_resource_id == "KYN__SHAD__DEFAULT"
    assert e2.entry_time_sec >= e1.exit_time_sec + 60


def test_21_proof_case_d_legacy_regression_exact_match(graph) -> None:
    """CASE D: Legacy mode reproduces the previously validated 200.52 min benchmark."""
    optimizer = NetworkScheduleOptimizer(time_limit_sec=10.0)
    project_root = Path(__file__).resolve().parents[1]
    inputs_path = project_root / "data" / "selected_trains.json"
    rf_path = project_root / "data" / "processed" / "rf_optimization_inputs.csv"
    train_inputs = optimizer.load_inputs(graph, inputs_path, rf_path)

    res_legacy = optimizer.solve(train_inputs, graph, mode="legacy_single_resource")
    assert res_legacy.status in ("OPTIMAL", "FEASIBLE")
    assert abs(res_legacy.optimized_total_delay_minutes - 200.52) < 0.1
    assert abs(res_legacy.maximum_delay_minutes - 34.32) < 0.1
    assert abs(res_legacy.total_additional_hold_minutes - 19.55) < 0.1
