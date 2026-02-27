"""Current sensor MCP server — line current monitoring."""

from __future__ import annotations

from src.physical.base_sensor import BaseSensorServer
from src.simulation.power_grid import PowerGridSimulation


class CurrentSensorServer(BaseSensorServer):
    """MCP server for line current sensors."""

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(sensor_type="current", unit="kA", grid=grid, zone=zone)
        self._zone_lines = grid.get_zone_lines()

    def _read_value(self, sensor_id: str) -> float:
        line_id = int(sensor_id.replace("current_line_", ""))
        return self.grid.get_line_current(line_id)

    def _get_sensor_ids(self) -> list[str]:
        if self.zone == "system":
            lines = list(self.grid.net.line.index)
        else:
            lines = self._zone_lines.get(self.zone, [])
        return [f"current_line_{l}" for l in lines]

    def _get_sensor_metadata(self, sensor_id: str) -> dict:
        line_id = int(sensor_id.replace("current_line_", ""))
        line = self.grid.net.line.loc[line_id]
        return {
            "sensor_id": sensor_id,
            "type": "current",
            "line_id": line_id,
            "from_bus": int(line.from_bus),
            "to_bus": int(line.to_bus),
            "max_i_ka": float(line.max_i_ka),
            "unit": "kA",
            "zone": self.zone,
        }
