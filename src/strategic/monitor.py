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

from src.common.config import get_settings
from src.common.models import ViolationEvent
from src.coordination.zone_coordinator import ZoneCoordinator
from src.simulation.power_grid import PowerGridSimulation
from src.simulation.data_generator import DataGenerator
from src.strategic.agent import StrategicAgent

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
        if escalations and len(escalations) > 2:
            logger.info(
                "Escalating %d violations to strategic agent...", len(escalations)
            )
            try:
                summary = self._format_violations(escalations)
                zone_context = json.dumps(zone_results, default=str, indent=2)
                response = await asyncio.wait_for(
                    self.agent.query(
                        f"ESCALATION: Zone coordinators flagged the following issues.\n\n"
                        f"Zone Analysis Results:\n{zone_context}\n\n"
                        f"Violations:\n{summary}"
                    ),
                    timeout=300,
                )
                logger.info("Strategic agent response: %s", response[:300])
            except asyncio.TimeoutError:
                logger.warning("Strategic agent timed out")
            except Exception as e:
                logger.error("Strategic agent error: %s", e)

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

    def _format_violations(self, violations: list[ViolationEvent]) -> str:
        lines = []
        for v in violations:
            lines.append(f"- [{v.severity.upper()}] {v.message} (zone: {v.zone})")
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
