"""Temperature sensor MCP server — transformer thermal monitoring."""

from __future__ import annotations

from src.physical.base_sensor import BaseSensorServer
from src.simulation.power_grid import PowerGridSimulation


class TemperatureSensorServer(BaseSensorServer):
    """MCP server for transformer temperature sensors."""

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(sensor_type="temperature", unit="°C", grid=grid, zone=zone)

    def _read_value(self, sensor_id: str) -> float:
        trafo_id = int(sensor_id.replace("temp_trafo_", ""))
        return self.grid.get_transformer_temperature(trafo_id)

    def _get_sensor_ids(self) -> list[str]:
        return [f"temp_trafo_{t}" for t in self.grid.net.trafo.index]

    def _get_sensor_metadata(self, sensor_id: str) -> dict:
        trafo_id = int(sensor_id.replace("temp_trafo_", ""))
        trafo = self.grid.net.trafo.loc[trafo_id]
        return {
            "sensor_id": sensor_id,
            "type": "temperature",
            "trafo_id": trafo_id,
            "hv_bus": int(trafo.hv_bus),
            "lv_bus": int(trafo.lv_bus),
            "sn_mva": float(trafo.sn_mva),
            "unit": "°C",
            "alarm_threshold": 85.0,
            "trip_threshold": 105.0,
            "zone": self.zone,
        }
