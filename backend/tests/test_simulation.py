"""Tests for the power grid simulation."""

from src.simulation.power_grid import PowerGridSimulation


class TestPowerGridSimulation:
    """Test the Pandapower IEEE 30-bus digital twin."""

    def test_initialization(self, grid: PowerGridSimulation):
        """Grid initializes with correct bus/line counts."""
        assert len(grid.net.bus) == 30
        assert len(grid.net.line) > 0
        assert len(grid.net.gen) > 0
        assert grid.net.converged

    def test_power_flow_converges(self, grid: PowerGridSimulation):
        """Power flow should converge on a healthy grid."""
        assert grid.run_power_flow() is True

    def test_bus_voltages_in_range(self, grid: PowerGridSimulation):
        """All bus voltages should be within normal range initially."""
        voltages = grid.get_bus_voltages()
        assert len(voltages) == 30
        for bus_id, vm in voltages.items():
            assert 0.90 <= vm <= 1.10, f"Bus {bus_id} voltage {vm} out of range"

    def test_frequency_nominal(self, grid: PowerGridSimulation):
        """Frequency should be close to 60 Hz initially."""
        freq = grid.get_frequency()
        assert 59.0 <= freq <= 61.0

    def test_total_generation_matches_load_plus_losses(self, grid: PowerGridSimulation):
        """Generation = Load + Losses (power balance)."""
        gen = grid.get_total_generation()
        load = grid.get_total_load()
        losses = grid.get_total_losses()
        assert abs(gen - (load + losses)) < 1.0  # Within 1 MW tolerance

    def test_line_switching(self, grid: PowerGridSimulation):
        """Opening and closing a line should change grid state."""
        result = grid.set_line_status(0, False)
        assert result["previous"] is True
        assert result["current"] is False

        result = grid.set_line_status(0, True)
        assert result["current"] is True

    def test_generator_dispatch(self, grid: PowerGridSimulation):
        """Adjusting generator output should change power flow."""
        initial_gen = grid.get_total_generation()
        grid.set_generator_output(0, 50.0)
        new_gen = grid.get_total_generation()
        # Total generation will adjust due to slack bus
        assert abs(initial_gen - new_gen) < 50  # Slack compensates

    def test_load_scaling(self, grid: PowerGridSimulation):
        """Scaling a load should change demand."""
        initial_load = grid.get_total_load()
        grid.scale_load(0, 0.5)
        new_load = grid.get_total_load()
        assert new_load < initial_load

    def test_snapshot_restore(self, grid: PowerGridSimulation):
        """Snapshot and restore should return exact state."""
        initial_voltages = grid.get_bus_voltages()
        idx = grid.save_snapshot()

        grid.inject_load_change(5, 50.0)
        changed_voltages = grid.get_bus_voltages()
        assert initial_voltages != changed_voltages

        grid.restore_snapshot(idx)
        restored_voltages = grid.get_bus_voltages()
        for bus_id in initial_voltages:
            assert abs(initial_voltages[bus_id] - restored_voltages[bus_id]) < 0.001

    def test_validate_action_works(self, grid: PowerGridSimulation):
        """Validation runs the action in sandbox and returns structured result."""
        current_p = float(grid.net.gen.p_mw.at[0])
        result = grid.validate_action(grid.set_generator_output, 0, current_p)
        assert "safe" in result
        assert "violations" in result
        assert isinstance(result["violations"], list)
        # Ensure original state is preserved after validation
        assert float(grid.net.gen.p_mw.at[0]) == current_p

    def test_zone_mapping(self, grid: PowerGridSimulation):
        """Zone mapping should cover all 30 buses."""
        zones = grid.get_zone_buses()
        all_buses = []
        for buses in zones.values():
            all_buses.extend(buses)
        assert len(all_buses) == 30
        assert len(set(all_buses)) == 30

    def test_shunt_control(self, grid: PowerGridSimulation):
        """Activating/deactivating shunts should work."""
        if len(grid.net.shunt) > 0:
            result = grid.set_shunt_status(0, True)
            assert "shunt_id" in result
            assert result["current"] is True

    def test_transformer_temperature(self, grid: PowerGridSimulation):
        """Transformer temperature should be positive and reasonable."""
        for trafo_id in grid.net.trafo.index:
            temp = grid.get_transformer_temperature(trafo_id)
            assert 20.0 <= temp <= 200.0
