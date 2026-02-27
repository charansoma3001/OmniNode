"""Energy storage actuator MCP server — charge/discharge with SoC tracking."""

from __future__ import annotations

from src.common.models import ActuatorResponse
from src.physical.base_actuator import BaseActuatorServer
from src.simulation.power_grid import PowerGridSimulation


class EnergyStorageServer(BaseActuatorServer):
    """MCP server for energy storage systems (battery).

    Simulated as a controllable load/generator on a bus with SoC tracking.
    """
    _valid_actions = ["charge", "discharge", "stop", "emergency_stop"]

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(device_type="energy_storage", grid=grid, zone=zone)
        # Simulated storage: bus_id -> {capacity_mwh, soc, max_power_mw}
        self._storage_units: dict[str, dict] = {
            "storage_0": {"bus": 10, "capacity_mwh": 20.0, "soc": 0.5, "max_power_mw": 5.0, "current_mw": 0.0},
            "storage_1": {"bus": 24, "capacity_mwh": 15.0, "soc": 0.7, "max_power_mw": 3.0, "current_mw": 0.0},
        }

    def _execute_action(self, device_id: str, action: str, parameters: dict) -> ActuatorResponse:
        if device_id not in self._storage_units:
            return ActuatorResponse(
                device_id=device_id, action=action, success=False,
                message=f"Unknown storage unit: {device_id}",
            )

        unit = self._storage_units[device_id]
        prev_soc = unit["soc"]
        prev_mw = unit["current_mw"]

        if action == "charge":
            power_mw = min(parameters.get("power_mw", unit["max_power_mw"]), unit["max_power_mw"])
            unit["current_mw"] = -abs(power_mw)  # Negative = charging (acts as load)
            # Simulate SoC change (simplified: assume 1 minute at this power)
            energy_mwh = abs(power_mw) / 60
            unit["soc"] = min(1.0, unit["soc"] + energy_mwh / unit["capacity_mwh"])
            self.grid.inject_load_change(unit["bus"], abs(power_mw))
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Storage {device_id} charging at {power_mw} MW, SoC: {unit['soc']:.1%}",
                previous_state={"soc": prev_soc, "power_mw": prev_mw},
                new_state={"soc": unit["soc"], "power_mw": unit["current_mw"]},
            )
        elif action == "discharge":
            power_mw = min(parameters.get("power_mw", unit["max_power_mw"]), unit["max_power_mw"])
            if unit["soc"] <= 0.05:
                return ActuatorResponse(
                    device_id=device_id, action=action, success=False,
                    message="SoC too low to discharge",
                )
            unit["current_mw"] = abs(power_mw)  # Positive = discharging (acts as generator)
            energy_mwh = abs(power_mw) / 60
            unit["soc"] = max(0.0, unit["soc"] - energy_mwh / unit["capacity_mwh"])
            self.grid.inject_load_change(unit["bus"], -abs(power_mw))
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Storage {device_id} discharging at {power_mw} MW, SoC: {unit['soc']:.1%}",
                previous_state={"soc": prev_soc, "power_mw": prev_mw},
                new_state={"soc": unit["soc"], "power_mw": unit["current_mw"]},
            )
        elif action in ("stop", "emergency_stop"):
            unit["current_mw"] = 0.0
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Storage {device_id} stopped",
                previous_state={"soc": prev_soc, "power_mw": prev_mw},
                new_state={"soc": unit["soc"], "power_mw": 0.0},
            )
        else:
            return ActuatorResponse(
                device_id=device_id, action=action, success=False,
                message=f"Unknown action: {action}",
            )

    def _get_device_ids(self) -> list[str]:
        return list(self._storage_units.keys())

    def _get_device_status(self, device_id: str) -> dict:
        if device_id not in self._storage_units:
            return {"error": f"Unknown device: {device_id}"}
        unit = self._storage_units[device_id]
        return {
            "device_id": device_id,
            "bus": unit["bus"],
            "capacity_mwh": unit["capacity_mwh"],
            "soc": round(unit["soc"], 3),
            "soc_percent": f"{unit['soc']:.1%}",
            "max_power_mw": unit["max_power_mw"],
            "current_power_mw": unit["current_mw"],
            "mode": "charging" if unit["current_mw"] < 0 else "discharging" if unit["current_mw"] > 0 else "idle",
        }

    def _validate_in_sandbox(self, device_id: str, action: str, parameters: dict) -> dict:
        unit = self._storage_units.get(device_id)
        if not unit:
            return {"safe": False, "violations": [{"type": "config", "message": "Unknown device"}]}

        power = parameters.get("power_mw", unit["max_power_mw"])
        delta = -power if action == "charge" else power if action == "discharge" else 0

        def action_fn():
            self.grid.inject_load_change(unit["bus"], delta)

        return self.grid.validate_action(action_fn)
