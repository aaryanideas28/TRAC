"""ML-driven train traffic optimization and platform allocation for Nexora.

This module integrates machine learning predictions (delay change or risk of delay increase)
with mathematical optimization (Mixed Integer Linear Programming / Constraint Programming)
to solve station platform assignment, conflict-free headway scheduling, and traffic sequencing.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

logger = logging.getLogger(__name__)


@dataclass
class TrainTrafficRequest:
    """Represents a train requesting station entry / segment passage."""

    train_number: str
    train_name: str
    train_type: str = "EMU"
    arrival_time_min: float = 0.0
    dwell_time_min: float = 2.0
    delay_minutes: float = 0.0
    predicted_delay_change: float = 0.0
    delay_risk_prob: float = 0.5
    priority_weight: float = 1.0


@dataclass
class ScheduledTrainDispatch:
    """Represents an optimized train dispatch decision."""

    train_number: str
    train_name: str
    train_type: str
    planned_arrival_min: float
    assigned_platform: int
    scheduled_arrival_min: float
    scheduled_departure_min: float
    station_hold_delay_min: float
    delay_risk_score: float
    priority_weight: float
    recommendation_note: str


@dataclass
class OptimizationResult:
    """Outcome of the station traffic optimization solver."""

    status: str
    solver_backend: str
    total_delay_penalty: float
    total_hold_delay_minutes: float
    platform_count: int
    train_count: int
    schedule: list[ScheduledTrainDispatch] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "solver_backend": self.solver_backend,
            "total_delay_penalty": self.total_delay_penalty,
            "total_hold_delay_minutes": self.total_hold_delay_minutes,
            "platform_count": self.platform_count,
            "train_count": self.train_count,
            "schedule": [asdict(s) for s in self.schedule],
        }


class StationTrafficOptimizer:
    """MILP-based Traffic Optimizer incorporating ML delay and risk predictions."""

    def __init__(self, default_platforms: int = 2, min_headway_min: float = 2.0) -> None:
        self.default_platforms = default_platforms
        self.min_headway_min = min_headway_min

    def solve(
        self,
        trains: list[TrainTrafficRequest | dict[str, Any]],
        platforms: int | None = None,
        min_headway_min: float | None = None,
    ) -> OptimizationResult:
        """Optimize station platform allocation and headway sequencing.

        Formulation:
        ------------
        Minimize sum over i of: [Priority_i * (1 + 2 * ML_Risk_i) * HoldDelay_i]

        Subject to:
        - Platform exclusivity: Exactly 1 platform per train.
        - Station arrival feasibility: Entry time s_i >= planned arrival a_i.
        - Track safety: For trains i, j on same platform p, departure of i + headway <= entry of j
          (enforced via Big-M precedence binary variables).
        """
        M = platforms if platforms is not None else self.default_platforms
        headway = min_headway_min if min_headway_min is not None else self.min_headway_min

        # Normalize train objects
        train_objs: list[TrainTrafficRequest] = []
        for t in trains:
            if isinstance(t, TrainTrafficRequest):
                train_objs.append(t)
            elif isinstance(t, dict):
                train_objs.append(TrainTrafficRequest(**t))
            else:
                raise TypeError(f"Unsupported train item type: {type(t)}")

        N = len(train_objs)
        if N == 0:
            return OptimizationResult(
                status="optimal",
                solver_backend="scipy_milp",
                total_delay_penalty=0.0,
                total_hold_delay_minutes=0.0,
                platform_count=M,
                train_count=0,
                schedule=[],
            )

        if N == 1:
            t0 = train_objs[0]
            arr = float(t0.arrival_time_min)
            dwell = float(t0.dwell_time_min)
            single_sched = [
                ScheduledTrainDispatch(
                    train_number=t0.train_number,
                    train_name=t0.train_name,
                    train_type=t0.train_type,
                    planned_arrival_min=arr,
                    assigned_platform=1,
                    scheduled_arrival_min=arr,
                    scheduled_departure_min=arr + dwell,
                    station_hold_delay_min=0.0,
                    delay_risk_score=float(t0.delay_risk_prob),
                    priority_weight=float(t0.priority_weight),
                    recommendation_note="Immediate platform docking (no congestion).",
                )
            ]
            return OptimizationResult(
                status="optimal",
                solver_backend="scipy_milp",
                total_delay_penalty=0.0,
                total_hold_delay_minutes=0.0,
                platform_count=M,
                train_count=1,
                schedule=single_sched,
            )

        # Variables:
        # s_i (N continuous) : actual arrival start time at station
        # x_{i, p} (N * M binary) : platform assignment
        # z_{i, j} (N*(N-1)//2 binary) : precedence between i and j
        # d_i (N continuous) : hold delay (s_i - arr_i)
        num_pairs = N * (N - 1) // 2
        total_vars = N + (N * M) + num_pairs + N

        s_idx = lambda i: i
        x_idx = lambda i, p: N + i * M + p
        z_idx_map = {}
        pair_cnt = 0
        for i in range(N):
            for j in range(i + 1, N):
                z_idx_map[(i, j)] = N + (N * M) + pair_cnt
                pair_cnt += 1
        d_idx = lambda i: N + (N * M) + num_pairs + i

        # Objective vector c
        c = np.zeros(total_vars)
        for i, t in enumerate(train_objs):
            risk = float(t.delay_risk_prob)
            priority = float(t.priority_weight)
            # Cost scales with priority and ML-predicted risk
            weight = priority * (1.0 + 2.0 * risk)
            c[d_idx(i)] = weight
            c[s_idx(i)] = 0.001  # small tie-breaker for earlier dispatch

        # Integrality vector: 0 = continuous, 1 = integer/binary
        integrality = np.zeros(total_vars)
        for i in range(N):
            for p in range(M):
                integrality[x_idx(i, p)] = 1
        for idx in z_idx_map.values():
            integrality[idx] = 1

        # Variable bounds
        lb = np.zeros(total_vars)
        ub = np.full(total_vars, np.inf)

        for i, t in enumerate(train_objs):
            lb[s_idx(i)] = float(t.arrival_time_min)
            lb[d_idx(i)] = 0.0
            for p in range(M):
                ub[x_idx(i, p)] = 1.0
        for idx in z_idx_map.values():
            ub[idx] = 1.0

        bounds = Bounds(lb, ub)

        # Linear constraints
        A_rows = []
        rhs_lb = []
        rhs_ub = []

        # 1. Exactly one platform per train: sum_p x_{i, p} = 1
        for i in range(N):
            row = np.zeros(total_vars)
            for p in range(M):
                row[x_idx(i, p)] = 1.0
            A_rows.append(row)
            rhs_lb.append(1.0)
            rhs_ub.append(1.0)

        # 2. Hold delay definition: s_i - d_i = arr_i
        for i, t in enumerate(train_objs):
            row = np.zeros(total_vars)
            row[s_idx(i)] = 1.0
            row[d_idx(i)] = -1.0
            A_rows.append(row)
            rhs_lb.append(float(t.arrival_time_min))
            rhs_ub.append(float(t.arrival_time_min))

        # 3. Same platform non-overlap with headway (Big-M formulation)
        BIG_M = 2000.0
        for i in range(N):
            for j in range(i + 1, N):
                dwell_i = float(train_objs[i].dwell_time_min)
                dwell_j = float(train_objs[j].dwell_time_min)
                z_var = z_idx_map[(i, j)]

                for p in range(M):
                    # If z_ij = 1: s_j - s_i >= dwell_i + headway - BIG_M*(2 - x_ip - x_jp) - BIG_M*(1 - z_ij)
                    # => s_j - s_i - BIG_M*x_ip - BIG_M*x_jp - BIG_M*z_ij >= dwell_i + headway - 3*BIG_M
                    row1 = np.zeros(total_vars)
                    row1[s_idx(j)] = 1.0
                    row1[s_idx(i)] = -1.0
                    row1[x_idx(i, p)] = -BIG_M
                    row1[x_idx(j, p)] = -BIG_M
                    row1[z_var] = -BIG_M
                    A_rows.append(row1)
                    rhs_lb.append(dwell_i + headway - 3.0 * BIG_M)
                    rhs_ub.append(np.inf)

                    # If z_ij = 0: s_i - s_j >= dwell_j + headway - BIG_M*(2 - x_ip - x_jp) - BIG_M*z_ij
                    # => s_i - s_j - BIG_M*x_ip - BIG_M*x_jp + BIG_M*z_ij >= dwell_j + headway - 2*BIG_M
                    row2 = np.zeros(total_vars)
                    row2[s_idx(i)] = 1.0
                    row2[s_idx(j)] = -1.0
                    row2[x_idx(i, p)] = -BIG_M
                    row2[x_idx(j, p)] = -BIG_M
                    row2[z_var] = BIG_M
                    A_rows.append(row2)
                    rhs_lb.append(dwell_j + headway - 2.0 * BIG_M)
                    rhs_ub.append(np.inf)

        A = np.array(A_rows)
        constraints = LinearConstraint(A, rhs_lb, rhs_ub)

        res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints, options={"time_limit": 1.0})

        if not res.success:
            logger.warning(f"MILP solver returned non-success code {res.status}: {res.message}")
            return OptimizationResult(
                status="infeasible",
                solver_backend="scipy_milp",
                total_delay_penalty=float("inf"),
                total_hold_delay_minutes=float("inf"),
                platform_count=M,
                train_count=N,
                schedule=[],
            )

        sol = res.x
        schedule = []
        total_hold = 0.0
        for i, t in enumerate(train_objs):
            assigned_platform = 1
            for p in range(M):
                if sol[x_idx(i, p)] > 0.5:
                    assigned_platform = p + 1
                    break
            start_t = sol[s_idx(i)]
            dwell = float(t.dwell_time_min)
            dep_t = start_t + dwell
            hold = max(0.0, sol[d_idx(i)])
            total_hold += hold

            if hold > 0.05:
                note = f"Held {hold:.1f}m at outer signal for Platform {assigned_platform} clearance."
            else:
                note = f"Direct clear entry to Platform {assigned_platform}."

            schedule.append(
                ScheduledTrainDispatch(
                    train_number=str(t.train_number),
                    train_name=str(t.train_name),
                    train_type=str(t.train_type),
                    planned_arrival_min=round(float(t.arrival_time_min), 2),
                    assigned_platform=assigned_platform,
                    scheduled_arrival_min=round(start_t, 2),
                    scheduled_departure_min=round(dep_t, 2),
                    station_hold_delay_min=round(hold, 2),
                    delay_risk_score=round(float(t.delay_risk_prob), 4),
                    priority_weight=float(t.priority_weight),
                    recommendation_note=note,
                )
            )

        schedule = sorted(schedule, key=lambda x: (x.scheduled_arrival_min, x.assigned_platform))
        return OptimizationResult(
            status="optimal",
            solver_backend="scipy_milp",
            total_delay_penalty=round(float(res.fun), 4),
            total_hold_delay_minutes=round(float(total_hold), 2),
            platform_count=M,
            train_count=N,
            schedule=schedule,
        )


def recommend_traffic_decisions(
    recent_observations_df: pd.DataFrame,
    ml_model_pipeline: Any,
    platforms: int = 2,
    min_headway_min: float = 2.0,
) -> OptimizationResult:
    """End-to-end integration: Run ML inference on recent observations and solve station dispatch."""
    from .ml_random_forest import prepare_feature_target_split

    df = recent_observations_df.copy()
    X, _ = prepare_feature_target_split(df)

    # ML Inference
    if hasattr(ml_model_pipeline, "predict_proba"):
        probs = ml_model_pipeline.predict_proba(X)[:, 1]
        preds = ml_model_pipeline.predict(X)
    else:
        probs = np.full(len(df), 0.5)
        preds = ml_model_pipeline.predict(X)

    train_requests: list[TrainTrafficRequest] = []
    for idx, (row, risk, pred) in enumerate(zip(df.itertuples(), probs, preds)):
        t_type = getattr(row, "train_type", "EMU")
        priority = 3.0 if "superfast" in str(t_type).lower() or "mail" in str(t_type).lower() else (
            2.0 if "fast" in str(t_type).lower() else 1.0
        )
        # Synthesize relative arrival spacing based on position along corridor
        arr_time = idx * 1.5
        train_requests.append(
            TrainTrafficRequest(
                train_number=str(getattr(row, "train_number", f"T{idx}")),
                train_name=str(getattr(row, "train_name", f"Train {idx}")),
                train_type=str(t_type),
                arrival_time_min=arr_time,
                dwell_time_min=2.0,
                delay_minutes=float(getattr(row, "delay_minutes", 0.0)),
                predicted_delay_change=float(pred),
                delay_risk_prob=float(risk),
                priority_weight=priority,
            )
        )

    optimizer = StationTrafficOptimizer(default_platforms=platforms, min_headway_min=min_headway_min)
    return optimizer.solve(train_requests, platforms=platforms, min_headway_min=min_headway_min)
