"""Circuit breaker actuator MCP server — line switching operations."""

from __future__ import annotations

from src.common.models import ActuatorResponse
from src.physical.base_actuator import BaseActuatorServer
from src.simulation.power_grid import PowerGridSimulation


class CircuitBreakerServer(BaseActuatorServer):
    """MCP server for circuit breaker (line switching) control."""
    _valid_actions = ["open", "close", "emergency_stop"]

    def __init__(self, grid: PowerGridSimulation, zone: str = "system"):
        super().__init__(device_type="circuit_breaker", grid=grid, zone=zone)
        self._zone_lines = grid.get_zone_lines()

    def _execute_action(self, device_id: str, action: str, parameters: dict) -> ActuatorResponse:
        import re
        line_id = int(re.sub(r'\D', '', device_id) or -1)
        prev_status = bool(self.grid.net.line.in_service.at[line_id])

        if action == "open":
            result = self.grid.set_line_status(line_id, False)
        elif action == "close":
            result = self.grid.set_line_status(line_id, True)
        elif action == "emergency_stop":
            result = self.grid.set_line_status(line_id, False)
        else:
            return ActuatorResponse(
                device_id=device_id, action=action, success=False,
                message=f"Unknown action: {action}",
            )

        return ActuatorResponse(
            device_id=device_id,
            action=action,
            success=True,
            message=f"Line {line_id} {'opened' if not result['current'] else 'closed'}",
            previous_state={"in_service": prev_status},
            new_state={"in_service": result["current"]},
        )

    def _get_device_ids(self) -> list[str]:
        if self.zone == "system":
            lines = list(self.grid.net.line.index)
        else:
            lines = self._zone_lines.get(self.zone, [])
        return [f"breaker_line_{l}" for l in lines]

    def _get_device_status(self, device_id: str) -> dict:
        import re
        line_id = int(re.sub(r'\D', '', device_id) or -1)
        line = self.grid.net.line.loc[line_id]
        loading = float(self.grid.net.res_line.loading_percent.at[line_id]) if line.in_service else 0
        return {
            "device_id": device_id,
            "line_id": line_id,
            "in_service": bool(line.in_service),
            "from_bus": int(line.from_bus),
            "to_bus": int(line.to_bus),
            "loading_percent": round(loading, 2),
        }

    def _validate_in_sandbox(self, device_id: str, action: str, parameters: dict) -> dict:
        import re
        line_id = int(re.sub(r'\D', '', device_id) or -1)
        in_service = action == "close"

        def action_fn():
            self.grid.set_line_status(line_id, in_service)

        return self.grid.validate_action(action_fn)
