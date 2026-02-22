"""Continuous monitoring loop — zone-first architecture.

Each cycle:
  1. Run power flow → detect violations
  2. Group violations by zone
  3. Trigger deterministic safety rules via Zone PLC Coordinators IN PARALLEL
4. Escalate to strategic agent ONLY for cross-zone / unresolved issues
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime

import pandas as pd

from src.common.config import get_settings
from src.common.models import ViolationEvent
from src.coordination.zone_coordinator import ZoneCoordinator
from src.simulation.power_grid import PowerGridSimulation
from src.simulation.data_generator import DataGenerator
from src.strategic.agent import StrategicAgent
from src.api.event_bus import event_bus

logger = logging.getLogger(__name__)


class MonitoringLoop:
    """Async monitoring loop with zone-first violation handling.

    Zone coordinators execute deterministic protection logic independently.
    The strategic agent is only invoked for cross-zone coordination.
    """

    def __init__(
        self,
        grid: PowerGridSimulation,
        agent: StrategicAgent,
        data_gen: DataGenerator | None = None,
        coordinators: list[ZoneCoordinator] | None = None,
    ):
        self.grid = grid
        self.agent = agent
        self.data_gen = data_gen
        self._running = False
        self._violations_history: list[ViolationEvent] = []
        self._cycle_count = 0

        # Zone coordinator lookup
        self._coordinators: dict[str, ZoneCoordinator] = {}
        if coordinators:
            for c in coordinators:
                self._coordinators[c.zone_id] = c

        settings = get_settings()
        self.interval = settings.monitor_interval_seconds

    async def start(self) -> None:
        """Start the monitoring loop."""
        self._running = True
        logger.info(
            "Monitoring loop started (interval=%ds, zones=%d)",
            self.interval, len(self._coordinators),
        )

        while self._running:
            try:
                await self._check_cycle()
            except Exception as e:
                logger.error("Monitor cycle error: %s", e)

            await asyncio.sleep(self.interval)

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        logger.info("Monitoring loop stopped")

    async def _check_cycle(self) -> None:
        """One monitoring cycle: detect → zone-dispatch → escalate if needed."""
        self._cycle_count += 1

        # Vary loads slightly each cycle for realism
        if self.data_gen:
            self.data_gen.vary_loads()

        # Run power flow
        self.grid.run_power_flow()

        # Detect violations
        violations = self._detect_all_violations()

        if not violations:
            if self._cycle_count % 6 == 0:  # Log every ~3 min at 30s interval
                logger.info("Cycle %d: no violations detected ✓", self._cycle_count)
            return

        logger.warning("Cycle %d: %d violations detected", self._cycle_count, len(violations))
        self._violations_history.extend(violations)

        # --- Zone-first dispatch ---
        zone_violations = self._group_by_zone(violations)
        zone_results = {}
        escalations = []

        # Trigger each zone's safety PLC in parallel
        tasks = {}
        for zone_id, zone_viols in zone_violations.items():
            coordinator = self._coordinators.get(zone_id)
            if coordinator:
                tasks[zone_id] = asyncio.create_task(
                    self._trigger_zone_rules(coordinator)
                )
            else:
                # No coordinator for this zone — escalate immediately
                escalations.extend(zone_viols)

        # Wait for all zone PLC events to execute (fast)
        for zone_id, task in tasks.items():
            try:
                result = await asyncio.wait_for(task, timeout=10)
                zone_results[zone_id] = result
                logger.debug(
                    "Zone %s PLC executed: %s",
                    zone_id,
                    json.dumps(result, default=str)[:300],
                )

                # Check if zone PLC is escalating (via deadband)
                if result.get("status") == "escalation_required":
                    escalations.extend(zone_violations[zone_id])
                    logger.warning("Zone %s PLC escalating issues to Strategic Agent", zone_id)

            except asyncio.TimeoutError:
                logger.warning("Zone %s PLC timed out", zone_id)
                escalations.extend(zone_violations[zone_id])
            except Exception as e:
                logger.error("Zone %s PLC error: %s", zone_id, e)
                escalations.extend(zone_violations[zone_id])

        # --- Strategic escalation (only if needed) ---
        if escalations and len(escalations) >= 1:
            logger.info(
                "Escalating %d violations to strategic agent...", len(escalations)
            )
            try:
                # Build a directive prompt with pre-computed recommendations
                directive = self._build_directive(escalations, zone_results)
                response = await asyncio.wait_for(
                    self.agent.query(directive, escalation=True),
                    timeout=300,
                )
                logger.info("Strategic agent response: %s", response[:300])
            except asyncio.TimeoutError:
                logger.warning("Strategic agent timed out")
            except Exception as e:
                logger.error("Strategic agent error: %s", e)

        # --- Publish to WebSocket via Event Bus ---
        try:
            # Simple zone health eval for demo UI
            zone_health = {}
            for z_id in self._coordinators.keys():
                z_viols = len(zone_violations.get(z_id, []))
                zone_health[z_id] = "critical" if z_viols > 2 else "warning" if z_viols > 0 else "healthy"

            payload = self.grid.get_state(zone_health=zone_health)

            asyncio.create_task(event_bus.publish("grid_state", payload))
            logger.debug("Published simulated grid state to EventBus")
        except Exception as e:
            logger.error("Failed to publish grid state: %s", e)

    async def _trigger_zone_rules(self, coordinator: ZoneCoordinator) -> dict:
        """Trigger deterministic PLC safety rules in a zone."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, coordinator._evaluate_safety_rules
        )

    def _detect_all_violations(self) -> list[ViolationEvent]:
        """Check all grid constraints and return violations."""
        violations = []
        now = datetime.utcnow()

        # Voltage violations
        for bus_id, vm in self.grid.get_bus_voltages().items():
            if vm < 0.95:
                violations.append(ViolationEvent(
                    violation_id=f"v_low_{bus_id}_{now.timestamp():.0f}",
                    violation_type="voltage",
                    zone=self._bus_to_zone(bus_id),
                    severity="critical" if vm < 0.90 else "warning",
                    affected_components=[f"bus_{bus_id}"],
                    current_value=vm,
                    limit_value=0.95,
                    unit="p.u.",
                    message=f"Low voltage at bus {bus_id}: {vm:.4f} p.u.",
                    timestamp=now,
                ))
            elif vm > 1.05:
                violations.append(ViolationEvent(
                    violation_id=f"v_high_{bus_id}_{now.timestamp():.0f}",
                    violation_type="voltage",
                    zone=self._bus_to_zone(bus_id),
                    severity="critical" if vm > 1.10 else "warning",
                    affected_components=[f"bus_{bus_id}"],
                    current_value=vm,
                    limit_value=1.05,
                    unit="p.u.",
                    message=f"High voltage at bus {bus_id}: {vm:.4f} p.u.",
                    timestamp=now,
                ))

        # Thermal violations
        for line_id, loading in self.grid.get_line_loadings().items():
            if loading > 100.0:
                violations.append(ViolationEvent(
                    violation_id=f"thermal_{line_id}_{now.timestamp():.0f}",
                    violation_type="thermal",
                    zone="system",
                    severity="critical" if loading > 120 else "warning",
                    affected_components=[f"line_{line_id}"],
                    current_value=loading,
                    limit_value=100.0,
                    unit="%",
                    message=f"Line {line_id} overloaded: {loading:.1f}%",
                    timestamp=now,
                ))

        # Frequency violations
        freq = self.grid.get_frequency()
        if abs(freq - 60.0) > 0.5:
            violations.append(ViolationEvent(
                violation_id=f"freq_{now.timestamp():.0f}",
                violation_type="frequency",
                zone="system",
                severity="critical" if abs(freq - 60.0) > 1.0 else "warning",
                affected_components=["system"],
                current_value=freq,
                limit_value=60.0,
                unit="Hz",
                message=f"Frequency deviation: {freq:.4f} Hz",
                timestamp=now,
            ))

        return violations

    def _group_by_zone(self, violations: list[ViolationEvent]) -> dict[str, list[ViolationEvent]]:
        """Group violations by zone."""
        groups: dict[str, list[ViolationEvent]] = defaultdict(list)
        for v in violations:
            groups[v.zone].append(v)
        return dict(groups)

    def _build_directive(self, violations: list[ViolationEvent], zone_results: dict) -> str:
        """Build a concrete action directive for the strategic agent."""
        # Count violation types using correct ViolationEvent field names
        low_v  = [v for v in violations if "low"     in v.violation_type]
        high_v = [v for v in violations if "high"    in v.violation_type]
        thermal = [v for v in violations if "thermal" in v.violation_type]

        def _bus(v: ViolationEvent) -> str:
            return v.affected_components[0] if v.affected_components else "?"

        actions = []
        gen_ids  = [f"gen_{g}"  for g in self.grid.net.gen.index]
        load_ids = [f"load_{l}" for l in self.grid.net.load.index]

        if low_v:
            current_p = float(self.grid.net.gen.p_mw.iloc[0])
            max_p = float(self.grid.net.gen.max_p_mw.iloc[0]) if "max_p_mw" in self.grid.net.gen.columns else current_p * 1.5
            target_p  = min(current_p + 10.0, max_p)
            primary_gen = gen_ids[0] if gen_ids else "gen_0"
            actions.append(
                f"  • Call actuate_device(device_id='{primary_gen}', action='set_output', "
                f"parameters={{'p_mw': {target_p:.1f}}}) "
                f"→ Raises voltage by injecting {target_p - current_p:.1f} MW more."
            )
            if len(gen_ids) > 1:
                current_p2 = float(self.grid.net.gen.p_mw.iloc[1])
                max_p2 = float(self.grid.net.gen.max_p_mw.iloc[1]) if "max_p_mw" in self.grid.net.gen.columns else current_p2 * 1.5
                target_p2 = min(current_p2 + 5.0, max_p2)
                actions.append(
                    f"  • Also consider actuate_device(device_id='{gen_ids[1]}', action='set_output', "
                    f"parameters={{'p_mw': {target_p2:.1f}}}) "
                    f"→ Additional support from secondary generator."
                )
            # Reactive power support via capacitor banks (most effective for voltage)
            shunt_ids = [f"shunt_{s}" for s in self.grid.net.shunt.index]
            for sid in shunt_ids:
                s_idx = int(sid.replace("shunt_", ""))
                if not self.grid.net.shunt.in_service.at[s_idx]:
                    actions.append(
                        f"  • Call voltage_regulator_actuator_system_control(device_id='{sid}', action='activate') "
                        f"→ Activate capacitor bank to inject reactive power and raise voltage."
                    )

        if thermal:
            critical_loads = load_ids[:2] if len(load_ids) >= 2 else load_ids
            for lid in critical_loads:
                actions.append(
                    f"  • Call actuate_device(device_id='{lid}', action='scale', "
                    f"parameters={{'scale_factor': 0.8}}) "
                    f"→ Reduce load by 20% to relieve line overload."
                )

        if not actions:
            primary_gen = gen_ids[0] if gen_ids else "gen_0"
            actions.append(
                f"  • Call actuate_device(device_id='{primary_gen}', action='ramp', "
                f"parameters={{'delta_mw': 5.0}}) → Generic voltage support."
            )

        low_buses  = [_bus(v) for v in low_v]
        high_buses = [_bus(v) for v in high_v]
        thermal_lines = [_bus(v) for v in thermal]
        v_table = self._format_violations(violations)
        action_block = "\n".join(actions)

        # Build real device ID inventory so LLM can't hallucinate IDs
        real_gen_ids  = [f"gen_{g}"  for g in self.grid.net.gen.index]
        real_load_ids = [f"load_{l}" for l in self.grid.net.load.index]
        real_shunt_ids = [f"shunt_{s}" for s in self.grid.net.shunt.index]
        gen_status = ", ".join(
            f"{gid}={float(self.grid.net.gen.p_mw.at[g]):.1f}MW"
            for gid, g in zip(real_gen_ids, self.grid.net.gen.index)
        )
        shunt_status = ", ".join(
            f"{sid}={'ON' if self.grid.net.shunt.in_service.at[s] else 'OFF'}"
            for sid, s in zip(real_shunt_ids, self.grid.net.shunt.index)
        )

        return (
            f"GRID EMERGENCY — {len(violations)} violations across {len(zone_results)} zones.\n"
            f"Low voltage: {low_buses} | High voltage: {high_buses} | Thermal: {thermal_lines}\n\n"
            f"AVAILABLE DEVICES (use ONLY these exact IDs):\n"
            f"  Generators: {', '.join(real_gen_ids)}  (current: {gen_status})\n"
            f"  Loads (ALL of them): {', '.join(real_load_ids)}\n"
            f"  Capacitor banks (voltage_regulator): {', '.join(real_shunt_ids)}  ({shunt_status})\n"
            f"  ⚠ Do NOT use IDs like reg_X, cap_X, load_25+ — they do not exist!\n\n"
            f"Violations:\n{v_table}\n\n"
            f"PRE-COMPUTED CORRECTIVE ACTIONS (call these tools NOW):\n{action_block}\n\n"
            f"Execute the first action immediately."
        )

    def _format_violations(self, violations: list[ViolationEvent]) -> str:
        lines = []
        for v in violations:
            comp = v.affected_components[0] if v.affected_components else "?"
            lines.append(
                f"  [{v.severity.upper()}] zone={v.zone} component={comp} "
                f"type={v.violation_type} val={v.current_value:.4f} limit={v.limit_value:.2f}"
            )
        return "\n".join(lines)

    @staticmethod
    def _bus_to_zone(bus_id: int) -> str:
        if bus_id < 10:
            return "zone1"
        elif bus_id < 20:
            return "zone2"
        else:
            return "zone3"

    def get_violation_history(self) -> list[dict]:
        return [v.model_dump(mode="json") for v in self._violations_history[-50:]]
