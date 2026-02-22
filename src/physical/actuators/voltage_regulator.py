"""Voltage regulator actuator MCP server — shunt capacitor bank control."""

from __future__ import annotations

from src.common.models import ActuatorResponse
from src.physical.base_actuator import BaseActuatorServer
from src.simulation.power_grid import PowerGridSimulation


class VoltageRegulatorServer(BaseActuatorServer):
    """MCP server for voltage regulation via shunt capacitor banks."""
    _valid_actions = ["activate", "deactivate", "emergency_stop"]

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(device_type="voltage_regulator", grid=grid, zone=zone)

    # Aliases → normalized action names so LLM variants all work
    _ACTION_ALIASES = {
        "activate": "activate",
        "enable": "activate",
        "on": "activate",
        "bank_toggle": "activate",
        "switch_on": "activate",
        "open": "activate",
        "close": "deactivate",   # closing the breaker disconnects capacitor from perspective
        "deactivate": "deactivate",
        "disable": "deactivate",
        "off": "deactivate",
        "switch_off": "deactivate",
        "emergency_stop": "deactivate",
    }

    def _execute_action(self, device_id: str, action: str, parameters: dict) -> ActuatorResponse:
        action = self._ACTION_ALIASES.get(action, action)  # normalize
        shunt_id = int(device_id.replace("shunt_", ""))
        prev = bool(self.grid.net.shunt.in_service.at[shunt_id])

        if action == "activate":
            result = self.grid.set_shunt_status(shunt_id, True)
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Capacitor bank {shunt_id} activated",
                previous_state={"in_service": prev},
                new_state={"in_service": True},
            )
        elif action in ("deactivate", "emergency_stop"):
            result = self.grid.set_shunt_status(shunt_id, False)
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Capacitor bank {shunt_id} deactivated",
                previous_state={"in_service": prev},
                new_state={"in_service": False},
            )
        else:
            return ActuatorResponse(
                device_id=device_id, action=action, success=False,
                message=f"Unknown action: {action}",
            )

    def _get_device_ids(self) -> list[str]:
        return [f"shunt_{s}" for s in self.grid.net.shunt.index]

    def _get_device_status(self, device_id: str) -> dict:
        shunt_id = int(device_id.replace("shunt_", ""))
        shunt = self.grid.net.shunt.loc[shunt_id]
        return {
            "device_id": device_id,
            "shunt_id": shunt_id,
            "bus": int(shunt.bus),
            "in_service": bool(shunt.in_service),
            "q_mvar": float(shunt.q_mvar),
            "name": str(shunt.get("name", "")),
        }

    def _validate_in_sandbox(self, device_id: str, action: str, parameters: dict) -> dict:
        action = self._ACTION_ALIASES.get(action, action)  # normalize before validation
        shunt_id = int(device_id.replace("shunt_", ""))
        in_service = action == "activate"

        def action_fn():
            self.grid.set_shunt_status(shunt_id, in_service)

        return self.grid.validate_action(action_fn)
