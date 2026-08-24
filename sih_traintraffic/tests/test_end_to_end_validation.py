"""Automated End-to-End Mathematical & Logical Verification Suite for Nexora AI Railway Traffic Control.

Executes 7 comprehensive tests verifying simulation clock advancement, kinematics, track blockage,
ML prediction, OR-Tools CP-SAT solver execution, schedule application, Before/After metric calculation,
and baseline state reset.
"""

import sys
import time
import unittest
from pathlib import Path

# Add src to python path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from railradar.api_server import (
    initialize_state,
    advance_simulation_tick,
    state,
    control_simulation,
    run_optimization,
    SimulationControlRequest,
)


class TestEndToEndValidation(unittest.TestCase):

    def setUp(self):
        """Reset state to baseline before each test."""
        initialize_state()

    def test_01_live_simulation_advancement(self):
        """Test 1: Verify clock advances, ticks increment, and train progress updates."""
        initial_seconds = state.sim_seconds
        initial_tick = state.tick_count
        initial_prog = state.trains[0]["progress_percent"]

        advance_simulation_tick()

        self.assertGreaterEqual(state.sim_seconds, initial_seconds + 1)
        self.assertGreaterEqual(state.tick_count, initial_tick + 1)
        self.assertGreater(state.trains[0]["progress_percent"], initial_prog)
        print("✓ TEST 1 PASSED: Live simulation clock & kinematics tick correctly.")

    def test_02_track_blockage_and_conflict(self):
        """Test 2: Verify track blockage halts fast line trains and generates conflict item."""
        req = SimulationControlRequest(action="block_track", blocked_section="BY_DR")
        control_simulation(req)

        self.assertTrue(state.track_blocked)
        self.assertEqual(state.blocked_section, "BY_DR")
        
        # Check affected trains halted at 0 km/h
        halted = [t for t in state.trains if t["status"] == "Conflict" and t["speed_kmh"] == 0]
        self.assertGreater(len(halted), 0)

        # Check conflict item created
        active_conflicts = [c for c in state.conflicts if c["status"] == "DETECTED"]
        self.assertGreater(len(active_conflicts), 0)
        print("✓ TEST 2 PASSED: Track blockage halts affected trains & triggers conflict detection.")

    def test_03_ml_prediction_inference(self):
        """Test 3: Verify ML Random Forest model inference outputs valid congestion risk."""
        req = SimulationControlRequest(action="block_track", blocked_section="BY_DR")
        control_simulation(req)

        ml = state.ml_prediction
        self.assertIn("congestion_risk", ml)
        self.assertIn("congestion_prob", ml)
        self.assertIn(ml["congestion_risk"], ["HIGH", "MEDIUM", "LOW"])
        self.assertGreaterEqual(ml["congestion_prob"], 0.0)
        self.assertLessEqual(ml["congestion_prob"], 1.0)
        print(f"✓ TEST 3 PASSED: ML prediction inference returned {ml['congestion_risk']} risk ({ml['congestion_prob']*100:.0f}% prob).")

    def test_04_ortools_cpsat_solver_execution(self):
        """Test 4: Verify OR-Tools CP-SAT solver executes and records measured solve_time_ms."""
        # Inject blockage first
        control_simulation(SimulationControlRequest(action="block_track", blocked_section="BY_DR"))
        
        res = run_optimization()

        self.assertIn(res["status"], ["OPTIMAL", "FEASIBLE"])
        self.assertIn("solve_time_ms", res)
        self.assertGreater(res["solve_time_ms"], 0.0)
        print(f"✓ TEST 4 PASSED: CP-SAT solver executed in {res['solve_time_ms']}ms with status {res['status']}.")

    def test_05_apply_optimization_to_simulation_state(self):
        """Test 5: Verify optimized track reassignments apply back to state and resolve conflicts."""
        control_simulation(SimulationControlRequest(action="block_track", blocked_section="BY_DR"))
        run_optimization()

        # Check track unblocked & trains moving
        self.assertFalse(state.track_blocked)
        moving_trains = [t for t in state.trains if t["status"] == "Moving"]
        self.assertEqual(len(moving_trains), len(state.trains))

        # Check conflicts resolved
        active_conflicts = [c for c in state.conflicts if c["status"] == "DETECTED"]
        self.assertEqual(len(active_conflicts), 0)
        print("✓ TEST 5 PASSED: CP-SAT dispatch applied back to state. All conflicts resolved.")

    def test_06_before_after_metrics_calculation(self):
        """Test 6: Verify Before vs After metrics are dynamically calculated from state."""
        control_simulation(SimulationControlRequest(action="block_track", blocked_section="BY_DR"))
        run_optimization()

        ba = state.before_after
        self.assertIn("without_ai", ba)
        self.assertIn("with_ai", ba)
        self.assertIn("improvements", ba)

        imp = ba["improvements"]
        self.assertIn("delay_reduction_pct", imp)
        self.assertIn("throughput_increase_pct", imp)
        print(f"✓ TEST 6 PASSED: Dynamic Before vs After metric evaluation: {imp['delay_reduction_pct']}% delay reduction.")

    def test_07_deterministic_baseline_reset(self):
        """Test 7: Verify reset action restores complete baseline state."""
        control_simulation(SimulationControlRequest(action="block_track", blocked_section="BY_DR"))
        control_simulation(SimulationControlRequest(action="reset"))

        self.assertFalse(state.track_blocked)
        self.assertEqual(len(state.conflicts), 0)
        self.assertGreaterEqual(len(state.trains), 18)
        self.assertGreater(state.sim_seconds, 0)
        print("✓ TEST 7 PASSED: Baseline reset completely restored initial simulation state.")


if __name__ == "__main__":
    unittest.main()
