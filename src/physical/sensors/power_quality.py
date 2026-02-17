"""Power quality sensor MCP server — THD and flicker monitoring."""

from __future__ import annotations

import random

from src.physical.base_sensor import BaseSensorServer
from src.simulation.power_grid import PowerGridSimulation


class PowerQualitySensorServer(BaseSensorServer):
    """MCP server for power quality (THD) sensors, one per zone."""

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(sensor_type="power_quality", unit="%", grid=grid, zone=zone)
        self._zone_buses = grid.get_zone_buses()

    def _read_value(self, sensor_id: str) -> float:
        # Simulated THD — loosely correlated with line loading in the zone
        zone = sensor_id.replace("thd_", "")
        buses = self._zone_buses.get(zone, [])
        if not buses:
            return random.uniform(1.0, 3.0)

        # Higher loading → higher THD
        avg_voltage = sum(self.grid.get_bus_voltage(b) for b in buses) / len(buses)
        deviation = abs(1.0 - avg_voltage)
        base_thd = 2.0 + deviation * 20.0  # % THD
        return round(base_thd + random.gauss(0, 0.3), 2)

    def _get_sensor_ids(self) -> list[str]:
        return [f"thd_{zone}" for zone in self._zone_buses]

    def _get_sensor_metadata(self, sensor_id: str) -> dict:
        zone = sensor_id.replace("thd_", "")
        return {
            "sensor_id": sensor_id,
            "type": "power_quality",
            "measurement": "THD",
            "zone": zone,
            "unit": "%",
            "normal_range": {"min": 0.0, "max": 5.0},
            "alarm_threshold": 8.0,
        }
