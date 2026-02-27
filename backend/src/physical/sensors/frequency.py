"""Frequency sensor MCP server — grid frequency monitoring."""

from __future__ import annotations

from src.physical.base_sensor import BaseSensorServer
from src.simulation.power_grid import PowerGridSimulation


class FrequencySensorServer(BaseSensorServer):
    """MCP server for grid frequency sensor (system-wide)."""

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(sensor_type="frequency", unit="Hz", grid=grid, zone=zone)

    def _read_value(self, sensor_id: str) -> float:
        return self.grid.get_frequency()

    def _get_sensor_ids(self) -> list[str]:
        return ["frequency_system"]

    def _get_sensor_metadata(self, sensor_id: str) -> dict:
        return {
            "sensor_id": "frequency_system",
            "type": "frequency",
            "nominal": 60.0,
            "unit": "Hz",
            "normal_range": {"min": 59.5, "max": 60.5},
            "zone": "system",
        }
