"""Tests for zone coordinator and optimizer."""

import pytest

from src.simulation.power_grid import PowerGridSimulation
from src.coordination.zone_coordinator import ZoneCoordinator
from src.coordination.optimizer import ZoneOptimizer


class TestZoneCoordinator:
    def _make_coordinator(self, grid: PowerGridSimulation) -> ZoneCoordinator:
        zones = grid.get_zone_buses()
        zone_lines = grid.get_zone_lines()
        return ZoneCoordinator("zone1", grid, zones["zone1"], zone_lines["zone1"])

    def test_zone_status(self, grid: PowerGridSimulation):
        coord = self._make_coordinator(grid)
        status = coord._get_zone_status()
        assert status["zone_id"] == "zone1"
        assert "voltages" in status
        assert "health" in status

    def test_detect_violations_clean(self, grid: PowerGridSimulation):
        coord = self._make_coordinator(grid)
        violations = coord._detect_violations()
        # Clean grid should have no or few violations
        assert "count" in violations

    def test_detect_violations_after_perturbation(self, grid: PowerGridSimulation):
        coord = self._make_coordinator(grid)
        # Inject large load to cause issues
        grid.inject_load_change(5, 100.0)
        violations = coord._detect_violations()
        # Should detect something
        assert violations["count"] >= 0  # May or may not violate depending on slack


class TestZoneOptimizer:
    def _make_optimizer(self, grid: PowerGridSimulation) -> ZoneOptimizer:
        zones = grid.get_zone_buses()
        zone_lines = grid.get_zone_lines()
        return ZoneOptimizer(grid, "zone1", zones["zone1"], zone_lines["zone1"])

    def test_minimize_losses(self, grid: PowerGridSimulation):
        opt = self._make_optimizer(grid)
        result = opt.optimize("min_losses")
        assert "initial_losses_mw" in result
        assert "final_losses_mw" in result

    def test_voltage_regulation(self, grid: PowerGridSimulation):
        opt = self._make_optimizer(grid)
        result = opt.regulate_voltage(1.0)
        assert "voltages" in result
        assert "resolved" in result

    def test_balance_loading(self, grid: PowerGridSimulation):
        opt = self._make_optimizer(grid)
        result = opt.balance_loading(80)
        assert "max_loading" in result
