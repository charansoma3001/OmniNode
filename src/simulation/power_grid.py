"""Pandapower-based IEEE 30-bus power grid digital twin."""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field

import numpy as np
import pandapower as pp
import pandapower.networks as pn
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class GridSnapshot:
    """Immutable snapshot of the grid state for rollback."""
    net_json: str
    timestamp: str


class PowerGridSimulation:
    """Digital twin of an IEEE 30-bus power grid using Pandapower.

    Provides:
    - Power flow simulation
    - Sensor data extraction (voltages, currents, temperatures, frequency)
    - Actuator control (breakers, generators, loads, shunts, storage)
    - State snapshot/restore for safety validation
    """

    def __init__(self) -> None:
        self.net: pp.pandapowerNet = pn.case_ieee30()
        self._base_frequency: float = 60.0  # Hz
        self._frequency_deviation: float = 0.0
        self._snapshots: list[GridSnapshot] = []
        self._storage_soc: dict[int, float] = {}  # storage index -> SoC (0-1)

        # Add shunt capacitor banks if not present
        if len(self.net.shunt) == 0:
            pp.create_shunt(self.net, bus=10, q_mvar=-5.0, p_mw=0.0, name="CapBank_Zone1")
            pp.create_shunt(self.net, bus=24, q_mvar=-5.0, p_mw=0.0, name="CapBank_Zone2")
            pp.create_shunt(self.net, bus=29, q_mvar=-5.0, p_mw=0.0, name="CapBank_Zone3")

        # Set realistic line limits (default 1.0 kA)
        self.net.line["max_i_ka"] = 1.0

        # Run initial power flow
        self.run_power_flow()
        logger.info(
            "IEEE 30-bus grid initialized: %d buses, %d lines, %d gens, %d loads",
            len(self.net.bus), len(self.net.line), len(self.net.gen), len(self.net.load),
        )

    # ------------------------------------------------------------------
    # Power flow
    # ------------------------------------------------------------------

    def run_power_flow(self) -> bool:
        """Run AC power flow and return True if converged."""
        try:
            pp.runpp(self.net, enforce_q_lims=True, max_iteration=50)
            converged = self.net.converged
            if converged:
                self._update_frequency()
            else:
                logger.warning("Power flow did not converge")
            return converged
        except Exception as e:
            logger.error("Power flow failed: %s", e)
            return False

    def _update_frequency(self) -> None:
        """Simulate frequency deviation based on gen/load balance."""
        total_gen = self.net.res_gen.p_mw.sum() + self.net.res_ext_grid.p_mw.sum()
        total_load = self.net.res_load.p_mw.sum()
        imbalance_pct = (total_gen - total_load) / max(total_load, 1.0)
        # Droop characteristic: ~5% freq change per 100% power imbalance
        self._frequency_deviation = imbalance_pct * 3.0  # Hz

    # ------------------------------------------------------------------
    # Sensor readings (Perception)
    # ------------------------------------------------------------------

    def get_bus_voltages(self) -> dict[int, float]:
        """Get per-bus voltage magnitudes in p.u."""
        return self.net.res_bus.vm_pu.to_dict()

    def get_bus_voltage(self, bus_id: int) -> float:
        """Get voltage at a specific bus in p.u."""
        return float(self.net.res_bus.vm_pu.at[bus_id])

    def get_line_loadings(self) -> dict[int, float]:
        """Get line loading percentages."""
        return self.net.res_line.loading_percent.to_dict()

    def get_line_current(self, line_id: int) -> float:
        """Get line current in kA."""
        return float(self.net.res_line.i_ka.at[line_id])

    def get_transformer_loadings(self) -> dict[int, float]:
        """Get transformer loading percentages."""
        return self.net.res_trafo.loading_percent.to_dict()

    def get_transformer_temperature(self, trafo_id: int) -> float:
        """Estimate transformer temperature from loading (simplified thermal model)."""
        loading = float(self.net.res_trafo.loading_percent.at[trafo_id])
        # Simple exponential thermal: ambient 25°C + loading-dependent rise
        ambient = 25.0
        max_rise = 65.0  # °C at 100% loading
        temp = ambient + max_rise * (loading / 100.0) ** 1.6
        return round(temp, 1)

    def get_frequency(self) -> float:
        """Get simulated grid frequency in Hz."""
        return round(self._base_frequency + self._frequency_deviation, 4)

    def get_total_generation(self) -> float:
        """Total active power generation in MW."""
        return float(self.net.res_gen.p_mw.sum() + self.net.res_ext_grid.p_mw.sum())

    def get_total_load(self) -> float:
        """Total active power demand in MW."""
        return float(self.net.res_load.p_mw.sum())

    def get_total_losses(self) -> float:
        """Total active power losses in MW."""
        return float(self.net.res_line.pl_mw.sum() + self.net.res_trafo.pl_mw.sum())

    # ------------------------------------------------------------------
    # Actuator control (Agency)
    # ------------------------------------------------------------------

    def set_line_status(self, line_id: int, in_service: bool) -> dict:
        """Open/close a line (circuit breaker operation)."""
        prev = bool(self.net.line.in_service.at[line_id])
        self.net.line.in_service.at[line_id] = in_service
        self.run_power_flow()
        return {"line_id": line_id, "previous": prev, "current": in_service}

    def set_generator_output(self, gen_id: int, p_mw: float, q_mvar: float | None = None) -> dict:
        """Adjust generator dispatch."""
        prev_p = float(self.net.gen.p_mw.at[gen_id])
        self.net.gen.p_mw.at[gen_id] = p_mw
        if q_mvar is not None:
            self.net.gen.q_mvar.at[gen_id] = q_mvar
        self.run_power_flow()
        return {"gen_id": gen_id, "previous_p_mw": prev_p, "current_p_mw": p_mw}

    def scale_load(self, load_id: int, scale_factor: float) -> dict:
        """Scale a load by a factor (demand response)."""
        prev_p = float(self.net.load.p_mw.at[load_id])
        self.net.load.p_mw.at[load_id] = prev_p * scale_factor
        self.net.load.q_mvar.at[load_id] *= scale_factor
        self.run_power_flow()
        return {
            "load_id": load_id,
            "previous_p_mw": prev_p,
            "current_p_mw": float(self.net.load.p_mw.at[load_id]),
            "scale_factor": scale_factor,
        }

    def set_shunt_status(self, shunt_id: int, in_service: bool) -> dict:
        """Activate/deactivate a shunt capacitor bank."""
        prev = bool(self.net.shunt.in_service.at[shunt_id])
        self.net.shunt.in_service.at[shunt_id] = in_service
        self.run_power_flow()
        return {"shunt_id": shunt_id, "previous": prev, "current": in_service}

    # ------------------------------------------------------------------
    # Perturbation methods (for scenarios)
    # ------------------------------------------------------------------

    def inject_load_change(self, bus_id: int, delta_mw: float) -> None:
        """Add a load perturbation at a specific bus."""
        loads_at_bus = self.net.load[self.net.load.bus == bus_id]
        if len(loads_at_bus) > 0:
            load_id = loads_at_bus.index[0]
            self.net.load.loc[load_id, 'p_mw'] += delta_mw
        else:
            pp.create_load(self.net, bus=bus_id, p_mw=delta_mw, q_mvar=delta_mw * 0.3)
        self.run_power_flow()

    def trip_line(self, line_id: int) -> None:
        """Simulate a line trip (fault)."""
        self.net.line.in_service.at[line_id] = False
        self.run_power_flow()

    # ------------------------------------------------------------------
    # Snapshot / Rollback (Safety)
    # ------------------------------------------------------------------

    def save_snapshot(self) -> int:
        """Save current grid state; return snapshot index."""
        from datetime import datetime
        snapshot = GridSnapshot(
            net_json=pp.to_json(self.net),
            timestamp=datetime.utcnow().isoformat(),
        )
        self._snapshots.append(snapshot)
        return len(self._snapshots) - 1

    def save_to_file(self, path: str = "grid_state.json") -> None:
        """Save current grid state to a JSON file (for dashboard sync)."""
        import os
        # Atomic write to avoid partial reads
        temp_path = f"{path}.tmp"
        pp.to_json(self.net, temp_path)
        os.replace(temp_path, path)

    def restore_snapshot(self, index: int) -> bool:
        """Restore grid state from a snapshot."""
        if 0 <= index < len(self._snapshots):
            self.net = pp.from_json_string(self._snapshots[index].net_json)
            self.run_power_flow()
            logger.info("Restored grid snapshot %d", index)
            return True
        return False

    def validate_action(self, action_fn, *args, **kwargs) -> dict:
        """Run an action in sandbox mode: save → execute → check delta → restore.

        Only blocks actions that introduce NEW violations beyond pre-existing ones.
        This is critical for corrective actions (e.g. ramping a generator when the
        grid is already in a degraded state with violations).
        """
        snapshot_idx = self.save_snapshot()
        try:
            # Capture pre-action violation fingerprints
            pre_violations = self._check_violations()
            pre_components = {v["component"] for v in pre_violations}

            action_fn(*args, **kwargs)

            post_violations = self._check_violations()

            # Only flag violations on components that were NOT already in violation
            new_violations = [v for v in post_violations if v["component"] not in pre_components]

            # Also block if a metric got significantly WORSE on an existing violation
            worsened = []
            pre_by_comp = {v["component"]: v for v in pre_violations}
            for v in post_violations:
                if v["component"] in pre_by_comp:
                    old_val = pre_by_comp[v["component"]]["value"]
                    new_val = v["value"]
                    # Worsened if deviation from limit grew by >5%
                    if abs(new_val - 1.0) > abs(old_val - 1.0) + 0.05:
                        worsened.append(v)

            blocking = new_violations + worsened
            safe = len(blocking) == 0
            return {
                "safe": safe,
                "violations": blocking,
                "pre_existing_violations": len(pre_violations),
                "note": "Only new/worsened violations are blocking; pre-existing violations are ignored.",
            }
        finally:
            self.restore_snapshot(snapshot_idx)

    def _check_violations(self) -> list[dict]:
        """Check for constraint violations in current state."""
        violations = []

        # Voltage violations (0.95 - 1.05 p.u.)
        for bus_id, vm in self.get_bus_voltages().items():
            if vm < 0.95 or vm > 1.05:
                violations.append({
                    "type": "voltage",
                    "component": f"bus_{bus_id}",
                    "value": vm,
                    "limit": "0.95-1.05 p.u.",
                    "severity": "critical" if (vm < 0.90 or vm > 1.10) else "warning",
                })

        # Thermal violations (line loading > 100%)
        for line_id, loading in self.get_line_loadings().items():
            if loading > 100.0:
                violations.append({
                    "type": "thermal",
                    "component": f"line_{line_id}",
                    "value": loading,
                    "limit": "100%",
                    "severity": "critical" if loading > 120 else "warning",
                })

        # Frequency violations
        freq = self.get_frequency()
        if abs(freq - self._base_frequency) > 0.5:
            violations.append({
                "type": "frequency",
                "component": "system",
                "value": freq,
                "limit": f"{self._base_frequency} ± 0.5 Hz",
                "severity": "critical" if abs(freq - self._base_frequency) > 1.0 else "warning",
            })

        return violations

    # ------------------------------------------------------------------
    # Zone mapping
    # ------------------------------------------------------------------

    def get_zone_buses(self) -> dict[str, list[int]]:
        """Return bus-to-zone mapping for the IEEE 30-bus network.

        Divided into 3 zones roughly by geography:
        - Zone1: Buses 0-9   (generation-heavy area)
        - Zone2: Buses 10-19 (mixed area)
        - Zone3: Buses 20-29 (load-heavy area)
        """
        return {
            "zone1": list(range(0, 10)),
            "zone2": list(range(10, 20)),
            "zone3": list(range(20, 30)),
        }

    def get_zone_lines(self) -> dict[str, list[int]]:
        """Return lines belonging to each zone (both endpoints in zone)."""
        zone_buses = self.get_zone_buses()
        zone_lines: dict[str, list[int]] = {z: [] for z in zone_buses}

        for line_id in self.net.line.index:
            from_bus = int(self.net.line.from_bus.at[line_id])
            to_bus = int(self.net.line.to_bus.at[line_id])
            for zone, buses in zone_buses.items():
                if from_bus in buses and to_bus in buses:
                    zone_lines[zone].append(line_id)
                    break
        return zone_lines

    def get_state(self, zone_health: dict | None = None) -> dict:
        """Generate a JSON-serializable dict of the current grid state for the UI."""
        from datetime import datetime
        import json as _json

        nodes_data = []
        for b, v in self.get_bus_voltages().items():
            x, y = 0, 0
            if 'geo' in self.net.bus.columns and not pd.isna(self.net.bus.geo.at[b]):
                try:
                    geo_dict = _json.loads(self.net.bus.geo.at[b])
                    coords = geo_dict.get('coordinates', [0, 0])
                    x = float(coords[0]) * 150
                    y = float(coords[1]) * 150
                except Exception:
                    pass
            
            # Find which zone this bus belongs to
            bus_zone = "system"
            for z_name, z_buses in self.get_zone_buses().items():
                if b in z_buses:
                    bus_zone = z_name
                    break

            nodes_data.append({"id": b, "vm_pu": v, "x": x, "y": y, "zone": bus_zone})

        edges_data = []
        for l, ld in self.get_line_loadings().items():
            try:
                from_b = int(self.net.line.at[l, "from_bus"])
                to_b = int(self.net.line.at[l, "to_bus"])
                edges_data.append({"id": l, "loading_percent": ld, "from_bus": from_b, "to_bus": to_b})
            except Exception:
                pass

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_generation_mw": self.get_total_generation(),
            "total_load_mw": self.get_total_load(),
            "total_losses_mw": self.get_total_losses(),
            "frequency_hz": self.get_frequency(),
            "nodes": nodes_data,
            "edges": edges_data,
            "zone_health": zone_health or {},
            "violations": self._check_violations()
        }
