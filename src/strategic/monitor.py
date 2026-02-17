"""Continuous monitoring loop for proactive grid management."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from src.common.config import get_settings
from src.common.models import ViolationEvent
from src.simulation.power_grid import PowerGridSimulation
from src.simulation.data_generator import DataGenerator
from src.strategic.agent import StrategicAgent

logger = logging.getLogger(__name__)


class MonitoringLoop:
    """Async monitoring loop that periodically checks grid health.

    On violation detection, triggers the LLM agent for decision-making.
    """

    def __init__(
        self,
        grid: PowerGridSimulation,
        agent: StrategicAgent,
        data_gen: DataGenerator | None = None,
    ):
        self.grid = grid
        self.agent = agent
        self.data_gen = data_gen
        self._running = False
        self._violations_history: list[ViolationEvent] = []

        settings = get_settings()
        self.interval = settings.monitor_interval_seconds

    async def start(self) -> None:
        """Start the monitoring loop."""
        self._running = True
        logger.info("Monitoring loop started (interval=%ds)", self.interval)

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
        """One monitoring cycle: read sensors, check thresholds, trigger agent."""
        # Run power flow to update state
        self.grid.run_power_flow()

        # Check for violations
        violations = self._detect_all_violations()

        if violations:
            logger.warning("Detected %d violations", len(violations))
            self._violations_history.extend(violations)

            # Build violation summary for agent
            violation_summary = self._format_violations(violations)
            logger.info("Triggering agent for violation response...")

            try:
                response = await self.agent.query(
                    f"ALERT: The following violations have been detected. "
                    f"Please analyze and recommend corrective actions.\n\n{violation_summary}"
                )
                logger.info("Agent response: %s", response[:200])
            except Exception as e:
                logger.error("Agent failed to respond: %s", e)

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
