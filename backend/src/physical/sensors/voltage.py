"""Voltage sensor MCP server — per-bus voltage monitoring."""

from __future__ import annotations

from src.physical.base_sensor import BaseSensorServer
from src.simulation.power_grid import PowerGridSimulation


class VoltageSensorServer(BaseSensorServer):
    """MCP server for per-bus voltage sensors."""

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(sensor_type="voltage", unit="p.u.", grid=grid, zone=zone)
        self._zone_buses = grid.get_zone_buses()

    def _read_value(self, sensor_id: str) -> float:
        bus_id = int(sensor_id.replace("voltage_bus_", ""))
        return self.grid.get_bus_voltage(bus_id)

    def _get_sensor_ids(self) -> list[str]:
        if self.zone == "system":
            buses = list(self.grid.net.bus.index)
        else:
            buses = self._zone_buses.get(self.zone, [])
        return [f"voltage_bus_{b}" for b in buses]

    def _get_sensor_metadata(self, sensor_id: str) -> dict:
        bus_id = int(sensor_id.replace("voltage_bus_", ""))
        bus = self.grid.net.bus.loc[bus_id]
        return {
            "sensor_id": sensor_id,
            "type": "voltage",
            "bus_id": bus_id,
            "bus_name": str(bus.get("name", f"Bus {bus_id}")),
            "vn_kv": float(bus.vn_kv),
            "unit": "p.u.",
            "normal_range": {"min": 0.95, "max": 1.05},
            "zone": self.zone,
        }
