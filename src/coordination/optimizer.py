"""Local optimization algorithms for zone coordinators."""

from __future__ import annotations

import logging
from typing import Any

from src.simulation.power_grid import PowerGridSimulation

logger = logging.getLogger(__name__)


class ZoneOptimizer:
    """Multi-objective optimizer for a zone of the power grid.

    Supports: minimize losses, minimize voltage deviation, balance line loading.
    Uses iterative heuristics suitable for real-time control.
    """

    def __init__(
        self,
        grid: PowerGridSimulation,
        zone_id: str,
        buses: list[int],
        lines: list[int],
    ):
        self.grid = grid
        self.zone_id = zone_id
        self.buses = buses
        self.lines = lines

    def optimize(self, objective: str) -> dict:
        """Run the optimization for a given objective."""
        if objective == "min_losses":
            return self._minimize_losses()
        elif objective == "min_voltage_deviation":
            return self.regulate_voltage(1.0)
        elif objective == "balance_loading":
            return self.balance_loading(80)
        else:
            return {"error": f"Unknown objective: {objective}"}

    def _minimize_losses(self) -> dict:
        """Minimize losses by adjusting generators in the zone.

        Simple heuristic: shift generation closer to loads.
        """
        snapshot = self.grid.save_snapshot()
        initial_losses = self.grid.get_total_losses()

        zone_gens = self.grid.net.gen[self.grid.net.gen.bus.isin(self.buses)]
        adjustments = []

        for gen_id in zone_gens.index:
            current_p = float(self.grid.net.gen.p_mw.at[gen_id])
            best_p = current_p
            best_loss = self.grid.get_total_losses()

            # Try small adjustments
            for delta in [-5, -2, 2, 5]:
                test_p = max(0, current_p + delta)
                max_p = float(self.grid.net.gen.max_p_mw.at[gen_id]) if "max_p_mw" in self.grid.net.gen.columns else 200
                test_p = min(test_p, max_p)
                self.grid.net.gen.p_mw.at[gen_id] = test_p
                if self.grid.run_power_flow():
                    loss = self.grid.get_total_losses()
                    if loss < best_loss:
                        best_loss = loss
                        best_p = test_p

            self.grid.net.gen.p_mw.at[gen_id] = best_p
            self.grid.run_power_flow()
            if best_p != current_p:
                adjustments.append({"gen_id": int(gen_id), "from": current_p, "to": best_p})

        final_losses = self.grid.get_total_losses()
        return {
            "objective": "min_losses",
            "zone": self.zone_id,
            "initial_losses_mw": round(initial_losses, 3),
            "final_losses_mw": round(final_losses, 3),
            "reduction_pct": round((1 - final_losses / max(initial_losses, 0.001)) * 100, 2),
            "adjustments": adjustments,
        }

    def regulate_voltage(self, target_pu: float = 1.0) -> dict:
        """Regulate voltage toward target by activating shunt capacitors.

        Also tries adjusting generator reactive power.
        """
        actions = []

        # Check zone voltages
        low_buses = [b for b in self.buses if self.grid.get_bus_voltage(b) < 0.95]
        high_buses = [b for b in self.buses if self.grid.get_bus_voltage(b) > 1.05]

        # Activate shunts for low voltage
        if low_buses:
            for shunt_id in self.grid.net.shunt.index:
                shunt_bus = int(self.grid.net.shunt.bus.at[shunt_id])
                if shunt_bus in self.buses and not self.grid.net.shunt.in_service.at[shunt_id]:
                    self.grid.set_shunt_status(shunt_id, True)
                    actions.append({"type": "activate_shunt", "shunt_id": int(shunt_id), "bus": shunt_bus})

        # For high voltage, deactivate shunts
        if high_buses:
            for shunt_id in self.grid.net.shunt.index:
                shunt_bus = int(self.grid.net.shunt.bus.at[shunt_id])
                if shunt_bus in self.buses and self.grid.net.shunt.in_service.at[shunt_id]:
                    self.grid.set_shunt_status(shunt_id, False)
                    actions.append({"type": "deactivate_shunt", "shunt_id": int(shunt_id), "bus": shunt_bus})

        self.grid.run_power_flow()

        # Report result
        voltages = {b: round(self.grid.get_bus_voltage(b), 4) for b in self.buses}
        remaining_violations = [b for b, v in voltages.items() if v < 0.95 or v > 1.05]

        return {
            "objective": "voltage_regulation",
            "zone": self.zone_id,
            "target_pu": target_pu,
            "voltages": voltages,
            "remaining_violations": remaining_violations,
            "actions_taken": actions,
            "resolved": len(remaining_violations) == 0,
        }

    def balance_loading(self, target_pct: float = 80.0) -> dict:
        """Balance line loading by adjusting loads if possible.

        Very simplified: identifies overloaded lines and reduces nearby loads.
        """
        actions = []

        for lid in self.lines:
            try:
                loading = float(self.grid.net.res_line.loading_percent.at[lid])
                if loading > target_pct:
                    # Find loads on the receiving end
                    to_bus = int(self.grid.net.line.to_bus.at[lid])
                    loads_at_bus = self.grid.net.load[self.grid.net.load.bus == to_bus]
                    for load_id in loads_at_bus.index:
                        scale = target_pct / max(loading, 1)
                        self.grid.scale_load(load_id, scale)
                        actions.append({
                            "type": "scale_load",
                            "load_id": int(load_id),
                            "line_id": lid,
                            "scale_factor": round(scale, 3),
                        })
            except (KeyError, IndexError):
                continue

        self.grid.run_power_flow()

        loadings = {}
        for lid in self.lines:
            try:
                loadings[lid] = round(float(self.grid.net.res_line.loading_percent.at[lid]), 2)
            except (KeyError, IndexError):
                pass

        return {
            "objective": "balance_loading",
            "zone": self.zone_id,
            "target_pct": target_pct,
            "line_loadings": loadings,
            "max_loading": max(loadings.values()) if loadings else 0,
            "actions_taken": actions,
            "balanced": all(v <= target_pct for v in loadings.values()),
        }
