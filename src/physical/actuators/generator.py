"""Generator dispatch actuator MCP server."""

from __future__ import annotations

from src.common.models import ActuatorResponse
from src.physical.base_actuator import BaseActuatorServer
from src.simulation.power_grid import PowerGridSimulation


class GeneratorServer(BaseActuatorServer):
    """MCP server for generator dispatch control."""

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(device_type="generator", grid=grid, zone=zone)

    def _execute_action(self, device_id: str, action: str, parameters: dict) -> ActuatorResponse:
        gen_id = int(device_id.replace("gen_", ""))
        prev_p = float(self.grid.net.gen.p_mw.at[gen_id])

        if action == "set_output":
            p_mw = parameters.get("p_mw", prev_p)
            q_mvar = parameters.get("q_mvar")
            result = self.grid.set_generator_output(gen_id, p_mw, q_mvar)
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Generator {gen_id} output set to {p_mw} MW",
                previous_state={"p_mw": prev_p},
                new_state={"p_mw": result["current_p_mw"]},
            )
        elif action == "ramp":
            delta = parameters.get("delta_mw", 0)
            new_p = prev_p + delta
            result = self.grid.set_generator_output(gen_id, new_p)
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Generator {gen_id} ramped by {delta} MW",
                previous_state={"p_mw": prev_p},
                new_state={"p_mw": result["current_p_mw"]},
            )
        elif action == "emergency_stop":
            result = self.grid.set_generator_output(gen_id, 0)
            return ActuatorResponse(
                device_id=device_id, action=action, success=True,
                message=f"Generator {gen_id} emergency stop",
                previous_state={"p_mw": prev_p},
                new_state={"p_mw": 0},
            )
        else:
            return ActuatorResponse(
                device_id=device_id, action=action, success=False,
                message=f"Unknown action: {action}",
            )

    def _get_device_ids(self) -> list[str]:
        return [f"gen_{g}" for g in self.grid.net.gen.index]

    def _get_device_status(self, device_id: str) -> dict:
        gen_id = int(device_id.replace("gen_", ""))
        gen = self.grid.net.gen.loc[gen_id]
        res = self.grid.net.res_gen.loc[gen_id]
        return {
            "device_id": device_id,
            "gen_id": gen_id,
            "bus": int(gen.bus),
            "in_service": bool(gen.in_service),
            "p_mw": round(float(res.p_mw), 2),
            "q_mvar": round(float(res.q_mvar), 2),
            "max_p_mw": float(gen.max_p_mw) if "max_p_mw" in gen.index else None,
            "min_p_mw": float(gen.min_p_mw) if "min_p_mw" in gen.index else None,
        }

    def _validate_in_sandbox(self, device_id: str, action: str, parameters: dict) -> dict:
        gen_id = int(device_id.replace("gen_", ""))
        p_mw = parameters.get("p_mw", float(self.grid.net.gen.p_mw.at[gen_id]))

        def action_fn():
            self.grid.set_generator_output(gen_id, p_mw)

        return self.grid.validate_action(action_fn)
