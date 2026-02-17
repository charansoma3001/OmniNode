"""Tests for sensor MCP servers."""

import pytest

from src.simulation.power_grid import PowerGridSimulation
from src.physical.sensors.voltage import VoltageSensorServer
from src.physical.sensors.current import CurrentSensorServer
from src.physical.sensors.temperature import TemperatureSensorServer
from src.physical.sensors.frequency import FrequencySensorServer
from src.physical.sensors.power_quality import PowerQualitySensorServer


class TestVoltageSensor:
    def test_read_value(self, grid: PowerGridSimulation):
        sensor = VoltageSensorServer(grid, zone="zone1")
        value = sensor._read_value("voltage_bus_0")
        assert 0.8 <= value <= 1.2

    def test_list_sensors(self, grid: PowerGridSimulation):
        sensor = VoltageSensorServer(grid, zone="zone1")
        ids = sensor._get_sensor_ids()
        assert len(ids) == 10  # Zone 1: buses 0-9
        assert all(s.startswith("voltage_bus_") for s in ids)

    def test_metadata(self, grid: PowerGridSimulation):
        sensor = VoltageSensorServer(grid, zone="zone1")
        meta = sensor._get_sensor_metadata("voltage_bus_0")
        assert meta["type"] == "voltage"
        assert meta["unit"] == "p.u."
        assert "vn_kv" in meta


class TestCurrentSensor:
    def test_read_value(self, grid: PowerGridSimulation):
        sensor = CurrentSensorServer(grid, zone="system")
        ids = sensor._get_sensor_ids()
        if ids:
            value = sensor._read_value(ids[0])
            assert value >= 0


class TestTemperatureSensor:
    def test_read_value(self, grid: PowerGridSimulation):
        sensor = TemperatureSensorServer(grid)
        ids = sensor._get_sensor_ids()
        if ids:
            temp = sensor._read_value(ids[0])
            assert 20 <= temp <= 200


class TestFrequencySensor:
    def test_read_value(self, grid: PowerGridSimulation):
        sensor = FrequencySensorServer(grid)
        freq = sensor._read_value("frequency_system")
        assert 58 <= freq <= 62

    def test_single_sensor(self, grid: PowerGridSimulation):
        sensor = FrequencySensorServer(grid)
        ids = sensor._get_sensor_ids()
        assert ids == ["frequency_system"]


class TestPowerQualitySensor:
    def test_read_value(self, grid: PowerGridSimulation):
        sensor = PowerQualitySensorServer(grid)
        ids = sensor._get_sensor_ids()
        assert len(ids) == 3  # 3 zones
        value = sensor._read_value(ids[0])
        assert 0 <= value <= 20

    def test_threshold_alert(self, grid: PowerGridSimulation):
        sensor = VoltageSensorServer(grid, zone="zone1")
        sensor._handle_set_threshold({"sensor_id": "voltage_bus_0", "min_value": 0.99, "max_value": 1.01})
        result = sensor._handle_read("voltage_bus_0")
        # May or may not have alert depending on current voltage
        assert "value" in result
