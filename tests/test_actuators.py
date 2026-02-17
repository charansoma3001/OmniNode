"""Tests for actuator MCP servers."""

import pytest

from src.simulation.power_grid import PowerGridSimulation
from src.physical.actuators.circuit_breaker import CircuitBreakerServer
from src.physical.actuators.generator import GeneratorServer
from src.physical.actuators.load_controller import LoadControllerServer
from src.physical.actuators.voltage_regulator import VoltageRegulatorServer
from src.physical.actuators.energy_storage import EnergyStorageServer


class TestCircuitBreaker:
    def test_list_devices(self, grid: PowerGridSimulation):
        cb = CircuitBreakerServer(grid)
        devices = cb._get_device_ids()
        assert len(devices) > 0
        assert all(d.startswith("breaker_line_") for d in devices)

    def test_open_close(self, grid: PowerGridSimulation):
        cb = CircuitBreakerServer(grid)
        resp = cb._execute_action("breaker_line_0", "open", {})
        assert resp.success is True
        assert resp.new_state["in_service"] is False

        resp = cb._execute_action("breaker_line_0", "close", {})
        assert resp.success is True
        assert resp.new_state["in_service"] is True

    def test_validate(self, grid: PowerGridSimulation):
        cb = CircuitBreakerServer(grid)
        result = cb._validate_in_sandbox("breaker_line_0", "open", {})
        assert "safe" in result


class TestGenerator:
    def test_list_devices(self, grid: PowerGridSimulation):
        gen = GeneratorServer(grid)
        devices = gen._get_device_ids()
        assert len(devices) > 0

    def test_set_output(self, grid: PowerGridSimulation):
        gen = GeneratorServer(grid)
        devices = gen._get_device_ids()
        resp = gen._execute_action(devices[0], "set_output", {"p_mw": 40.0})
        assert resp.success is True

    def test_get_status(self, grid: PowerGridSimulation):
        gen = GeneratorServer(grid)
        devices = gen._get_device_ids()
        status = gen._get_device_status(devices[0])
        assert "p_mw" in status
        assert "bus" in status


class TestLoadController:
    def test_scale_load(self, grid: PowerGridSimulation):
        lc = LoadControllerServer(grid)
        devices = lc._get_device_ids()
        resp = lc._execute_action(devices[0], "scale", {"scale_factor": 0.8})
        assert resp.success is True

    def test_shed_load(self, grid: PowerGridSimulation):
        lc = LoadControllerServer(grid)
        devices = lc._get_device_ids()
        resp = lc._execute_action(devices[0], "shed", {})
        assert resp.success is True
        assert resp.new_state["p_mw"] == 0


class TestVoltageRegulator:
    def test_activate_shunt(self, grid: PowerGridSimulation):
        vr = VoltageRegulatorServer(grid)
        devices = vr._get_device_ids()
        if devices:
            resp = vr._execute_action(devices[0], "activate", {})
            assert resp.success is True


class TestEnergyStorage:
    def test_charge_discharge(self, grid: PowerGridSimulation):
        es = EnergyStorageServer(grid)
        resp = es._execute_action("storage_0", "charge", {"power_mw": 2.0})
        assert resp.success is True
        assert "SoC" in resp.message

        resp = es._execute_action("storage_0", "discharge", {"power_mw": 2.0})
        assert resp.success is True

    def test_status(self, grid: PowerGridSimulation):
        es = EnergyStorageServer(grid)
        status = es._get_device_status("storage_0")
        assert "soc" in status
        assert "mode" in status
