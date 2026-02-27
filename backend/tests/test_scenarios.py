"""Tests for validation scenarios."""

import pytest

from src.simulation.power_grid import PowerGridSimulation
from src.simulation.scenarios import SCENARIOS, run_scenario


class TestScenarios:
    def test_all_scenarios_defined(self):
        assert "line_overload" in SCENARIOS
        assert "voltage_collapse" in SCENARIOS
        assert "cascading_failure" in SCENARIOS
        assert "cyber_attack" in SCENARIOS
        assert "nl_optimization" in SCENARIOS

    def test_run_line_overload(self, grid: PowerGridSimulation):
        result = run_scenario("line_overload", grid)
        assert result["scenario"] == "Line Overload Recovery"
        assert "expected_violation" in result

    def test_run_voltage_collapse(self, grid: PowerGridSimulation):
        result = run_scenario("voltage_collapse", grid)
        assert result["scenario"] == "Voltage Collapse Prevention"

    def test_run_cascading_failure(self, grid: PowerGridSimulation):
        result = run_scenario("cascading_failure", grid)
        assert result["scenario"] == "Cascading Failure Prevention"

    def test_run_unknown_scenario(self, grid: PowerGridSimulation):
        result = run_scenario("nonexistent", grid)
        assert "error" in result

    def test_scenario_restores_state(self, grid: PowerGridSimulation):
        """Running a scenario should restore the grid to original state."""
        initial_voltages = grid.get_bus_voltages()
        run_scenario("line_overload", grid)
        final_voltages = grid.get_bus_voltages()
        for bus_id in initial_voltages:
            assert abs(initial_voltages[bus_id] - final_voltages[bus_id]) < 0.01
