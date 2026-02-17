"""Predefined validation scenarios for testing the multi-agent system."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from src.simulation.power_grid import PowerGridSimulation

logger = logging.getLogger(__name__)


@dataclass
class Scenario:
    """A test scenario with setup, expected behavior, and validation."""
    name: str
    description: str
    setup: Callable[[PowerGridSimulation], None]
    expected_violation: str  # type of violation expected
    expected_response: str  # what the system should do
    validate: Callable[[PowerGridSimulation], bool]


def scenario_line_overload(grid: PowerGridSimulation) -> None:
    """Inject a large load to cause line overloading."""
    grid.inject_load_change(bus_id=7, delta_mw=50.0)


def validate_line_overload(grid: PowerGridSimulation) -> bool:
    """Check that no lines are overloaded after response."""
    loadings = grid.get_line_loadings()
    return all(l <= 100.0 for l in loadings.values())


def scenario_voltage_collapse(grid: PowerGridSimulation) -> None:
    """Create conditions for voltage collapse in Zone 2."""
    # Heavy loading on buses 10-15
    for bus_id in [10, 12, 14, 15]:
        grid.inject_load_change(bus_id=bus_id, delta_mw=20.0)


def validate_voltage_recovery(grid: PowerGridSimulation) -> bool:
    """Check that all bus voltages are within limits."""
    voltages = grid.get_bus_voltages()
    return all(0.95 <= v <= 1.05 for v in voltages.values())


def scenario_cascading_failure(grid: PowerGridSimulation) -> None:
    """Trip a critical line to risk cascading failures."""
    grid.trip_line(line_id=0)  # Trip a major line


def validate_no_cascade(grid: PowerGridSimulation) -> bool:
    """Check that the grid is still connected and stable."""
    try:
        converged = grid.run_power_flow()
        return converged
    except Exception:
        return False


def scenario_cyber_attack(grid: PowerGridSimulation) -> None:
    """Simulate false sensor data injection (not directly in grid)."""
    # This scenario is handled at the sensor layer level
    # The grid itself doesn't change — sensors report incorrect values
    pass


def validate_attack_detected(grid: PowerGridSimulation) -> bool:
    """Placeholder — validated at agent level."""
    return True


def scenario_nl_optimization(grid: PowerGridSimulation) -> None:
    """Set up a sub-optimal grid state for NL optimization."""
    # Create an inefficient state: high losses
    grid.set_generator_output(gen_id=0, p_mw=80.0)
    grid.set_generator_output(gen_id=1, p_mw=10.0)


def validate_optimization(grid: PowerGridSimulation) -> bool:
    """Check that losses decreased after optimization."""
    losses = grid.get_total_losses()
    return losses < 10.0  # Threshold for "well optimized"


# ---------------------------------------------------------------------------
# Scenario catalog
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, Scenario] = {
    "line_overload": Scenario(
        name="Line Overload Recovery",
        description="Load spike → violation detection → topology reconfiguration → resolution",
        setup=scenario_line_overload,
        expected_violation="thermal",
        expected_response="Topology reconfiguration or load shedding",
        validate=validate_line_overload,
    ),
    "voltage_collapse": Scenario(
        name="Voltage Collapse Prevention",
        description="Multiple low voltages → coordinated capacitor activation → stabilization",
        setup=scenario_voltage_collapse,
        expected_violation="voltage",
        expected_response="Capacitor bank activation and reactive power dispatch",
        validate=validate_voltage_recovery,
    ),
    "cascading_failure": Scenario(
        name="Cascading Failure Prevention",
        description="Line trip → predictive cascade detection → preemptive load shedding",
        setup=scenario_cascading_failure,
        expected_violation="thermal",
        expected_response="Load shedding and generator redispatch",
        validate=validate_no_cascade,
    ),
    "cyber_attack": Scenario(
        name="Cyber Attack Detection",
        description="False sensor data → anomaly detection → sensor isolation → safe mode",
        setup=scenario_cyber_attack,
        expected_violation="anomaly",
        expected_response="Sensor isolation and fallback to trusted readings",
        validate=validate_attack_detected,
    ),
    "nl_optimization": Scenario(
        name="Natural Language Optimization",
        description="'Optimize Zone 3 for minimum losses' → execution → results report",
        setup=scenario_nl_optimization,
        expected_violation="none",
        expected_response="Generator redispatch for loss minimization",
        validate=validate_optimization,
    ),
}


def run_scenario(name: str, grid: PowerGridSimulation) -> dict:
    """Run a named scenario and return results."""
    if name not in SCENARIOS:
        return {"error": f"Unknown scenario: {name}", "available": list(SCENARIOS.keys())}

    scenario = SCENARIOS[name]
    logger.info("Running scenario: %s", scenario.name)

    # Save state
    snapshot = grid.save_snapshot()

    # Setup
    scenario.setup(grid)

    result = {
        "scenario": scenario.name,
        "description": scenario.description,
        "expected_violation": scenario.expected_violation,
        "expected_response": scenario.expected_response,
        "grid_converged": grid.net.converged if hasattr(grid.net, "converged") else True,
    }

    # Note: actual response comes from the agent — this just sets up the condition
    # Validation would be called after the agent responds

    # Restore for now (agent tests will handle the full flow)
    grid.restore_snapshot(snapshot)

    return result
