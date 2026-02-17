"""Load controller actuator MCP server — demand response."""

from __future__ import annotations

from src.common.models import ActuatorResponse
from src.physical.base_actuator import BaseActuatorServer
from src.simulation.power_grid import PowerGridSimulation


class LoadControllerServer(BaseActuatorServer):
    """MCP server for load control (demand response)."""

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(device_type="load_controller", grid=grid, zone=zone)

    def _execute_action(self, device_id: str, action: str, parameters: dict) -> ActuatorResponse:
        load_id = int(device_id.replace("load_", ""))
        prev_p = float(self.grid.net.load.p_mw.at[load_id])

        if action == "scale":
            factor = parameters.get("scale_factor", 1.0)
            result = self.grid.scale_load(load_id, factor)
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Load {load_id} scaled by {factor}x",
                previous_state={"p_mw": prev_p},
                new_state={"p_mw": result["current_p_mw"]},
            )
        elif action == "shed":
            result = self.grid.scale_load(load_id, 0.0)
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Load {load_id} shed (disconnected)",
                previous_state={"p_mw": prev_p},
                new_state={"p_mw": 0},
            )
        elif action == "restore":
            # Restore to nominal (scale factor 1.0 relative to current is a no-op)
            # Use parameters to specify target
            target = parameters.get("target_mw", prev_p)
            self.grid.net.load.p_mw.at[load_id] = target
            self.grid.run_power_flow()
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Load {load_id} restored to {target} MW",
                previous_state={"p_mw": prev_p},
                new_state={"p_mw": target},
            )
        elif action == "emergency_stop":
            result = self.grid.scale_load(load_id, 0.0)
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Load {load_id} emergency disconnection",
                previous_state={"p_mw": prev_p},
                new_state={"p_mw": 0},
            )
        else:
            return ActuatorResponse(
                device_id=device_id, action=action, success=False,
                message=f"Unknown action: {action}",
            )

    def _get_device_ids(self) -> list[str]:
        return [f"load_{l}" for l in self.grid.net.load.index]

    def _get_device_status(self, device_id: str) -> dict:
        load_id = int(device_id.replace("load_", ""))
        load = self.grid.net.load.loc[load_id]
        return {
            "device_id": device_id,
            "load_id": load_id,
            "bus": int(load.bus),
            "in_service": bool(load.in_service),
            "p_mw": round(float(load.p_mw), 2),
            "q_mvar": round(float(load.q_mvar), 2),
        }

    def _validate_in_sandbox(self, device_id: str, action: str, parameters: dict) -> dict:
        load_id = int(device_id.replace("load_", ""))
        factor = parameters.get("scale_factor", 0.0 if action == "shed" else 1.0)

        def action_fn():
            self.grid.scale_load(load_id, factor)

        return self.grid.validate_action(action_fn)
