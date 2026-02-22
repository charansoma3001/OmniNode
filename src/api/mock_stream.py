"""Mock event generators for demoing the UI without LLM keys."""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime

from src.api.event_bus import event_bus

logger = logging.getLogger(__name__)

async def _publish_agent_log(message: str, data: dict | None = None, delay: float = 1.0) -> None:
    """Publish an agent log event with an optional delay to simulate thinking."""
    if delay:
        await asyncio.sleep(delay)
    
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "info",
        "message": message,
        "data": data
    }
    await event_bus.publish("agent_log", event)

async def _publish_guardian_event(command: dict, safe: bool, reasoning: str, conditions: list[str]) -> None:
    """Publish a guardian intercept event."""
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "command": command,
        "safe": safe,
        "risk_level": "LOW" if safe else "HIGH",
        "reasoning": reasoning,
        "conditions": conditions
    }
    await event_bus.publish("guardian_event", event)


async def trigger_mock_scenario_peak_load() -> None:
    """Simulates a peak load crisis resulting in cascading voltage drops."""
    logger.info("Triggering mock scenario: Peak Load")
    
    await _publish_agent_log("⚠️ ESCALATION RECEIVED: Zone 3 reporting severe voltage degradation.")
    await _publish_agent_log("🧠 ANALYZING: Peak load at Bus 21 has exhausted local capacitor banks.")
    await _publish_agent_log("🧠 ANALYZING: Cascading failure imminent on lines 21-22 and 22-24.")
    
    # Tool call
    action_1 = {"action": "scale_load", "target": "load_21", "parameters": {"scale_factor": 0.5}}
    await _publish_agent_log(f"🔧 CALLING MCP TOOL: `scale_load(load_21, 0.5)`")
    await _publish_agent_log("⏳ WAITING FOR GUARDIAN VALIDATION...")
    
    # Guardian approves
    await _publish_guardian_event(
        command=action_1,
        safe=True,
        reasoning="Load shedding of 50% at Bus 21 is within safe operating margins and prevents voltage collapse.",
        conditions=["Must not exceed 50% shedding", "Must restore within 2 hours"]
    )
    
    await _publish_agent_log("✅ ACTION COMPLETED: Load shed at Bus 21. Voltage stabilizing.")

async def trigger_mock_scenario_malicious_command() -> None:
    """Simulates a user injecting a dangerous command that the Guardian intercepts."""
    logger.info("Triggering mock scenario: Malicious Command")
    
    await _publish_agent_log("USER COMMAND: 'Open all breakers in Zone 1 to isolate generators.'", delay=0.5)
    await _publish_agent_log("🧠 ANALYZING: User requested full isolation of generation zone.")
    
    # Dangerous tool call
    action = {"action": "open_all_breakers", "target": "zone_1", "parameters": {}}
    await _publish_agent_log(f"🔧 CALLING MCP TOOL: `open_all_breakers(zone_1)`")
    await _publish_agent_log("⏳ WAITING FOR GUARDIAN VALIDATION...")
    
    # Guardian BLOCKS
    await _publish_guardian_event(
        command=action,
        safe=False,
        reasoning="Opening all breakers in Zone 1 violates constitution rule: 'Agents shall not execute commands resulting in >50% blackout or total loss of generation.'",
        conditions=["Action permanently blocked", "Operator alerted"]
    )
    
    await _publish_agent_log("🛑 ACTION BLOCKED BY GUARDIAN.", delay=0.5)
    await _publish_agent_log("Generating revised safe plan...", delay=1.0)
    

# ── IEEE 30-bus layout for React Flow (hand-tuned positions) ──────────────
_BUS_POSITIONS = {
    0: (100, 50), 1: (250, 50), 2: (400, 100), 3: (250, 200), 4: (400, 250),
    5: (100, 200), 6: (550, 100), 7: (550, 250), 8: (700, 100), 9: (700, 250),
    10: (850, 50), 11: (850, 200), 12: (100, 400), 13: (250, 400), 14: (400, 400),
    15: (550, 400), 16: (700, 400), 17: (850, 400), 18: (100, 550), 19: (250, 550),
    20: (400, 550), 21: (550, 550), 22: (700, 550), 23: (850, 550), 24: (100, 700),
    25: (250, 700), 26: (400, 700), 27: (550, 700), 28: (700, 700), 29: (850, 700),
}

_LINE_CONNECTIONS = [
    (0, 1), (0, 2), (1, 3), (1, 4), (1, 5), (2, 3), (3, 5), (4, 6),
    (4, 7), (5, 7), (5, 9), (5, 10), (8, 10), (8, 11), (9, 10), (9, 11),
    (11, 12), (12, 14), (15, 16), (14, 15), (9, 20), (9, 21), (14, 11),
    (15, 17), (17, 19), (20, 21), (14, 22), (21, 23), (23, 24), (24, 25),
    (25, 26), (26, 27), (27, 28), (27, 29), (28, 29), (5, 27), (24, 27),
    (21, 24), (9, 19), (3, 11),
]


def _bus_to_zone(bus_id: int) -> str:
    if bus_id < 10:
        return "zone1"
    elif bus_id < 20:
        return "zone2"
    return "zone3"


async def _publish_mock_grid_state(crisis_buses: set[int] | None = None) -> None:
    """Generate and publish a synthetic IEEE 30-bus grid state."""
    nodes = []
    violations = []
    for bus_id in range(30):
        # Nominal voltage with small noise
        vm = round(random.gauss(1.0, 0.012), 4)
        # If this bus is in a crisis, drop its voltage
        if crisis_buses and bus_id in crisis_buses:
            vm = round(random.uniform(0.85, 0.93), 4)
        x, y = _BUS_POSITIONS.get(bus_id, (bus_id * 30, bus_id * 30))
        zone = _bus_to_zone(bus_id)
        nodes.append({"id": bus_id, "vm_pu": vm, "x": x, "y": y, "zone": zone})

        if vm < 0.95:
            violations.append({
                "violation_type": "voltage",
                "zone": zone,
                "severity": "critical" if vm < 0.90 else "warning",
                "message": f"Low voltage at bus {bus_id}: {vm:.4f} p.u.",
            })

    edges = []
    for idx, (fb, tb) in enumerate(_LINE_CONNECTIONS):
        loading = round(random.gauss(55, 20), 1)
        loading = max(5, min(loading, 130))
        if crisis_buses and (fb in crisis_buses or tb in crisis_buses):
            loading = round(random.uniform(90, 125), 1)
        edges.append({"id": idx, "loading_percent": loading, "from_bus": fb, "to_bus": tb})

    total_gen = round(random.gauss(190, 5), 1)
    total_load = round(random.gauss(180, 5), 1)
    freq = round(random.gauss(60.0, 0.05), 3)

    zone_health = {}
    for z in ["zone1", "zone2", "zone3"]:
        z_viols = sum(1 for v in violations if v["zone"] == z)
        zone_health[z] = "critical" if z_viols > 2 else "warning" if z_viols > 0 else "healthy"

    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_generation_mw": total_gen,
        "total_load_mw": total_load,
        "total_losses_mw": round(total_gen - total_load, 2),
        "frequency_hz": freq,
        "nodes": nodes,
        "edges": edges,
        "zone_health": zone_health,
        "violations": violations,
    }
    await event_bus.publish("grid_state", payload)


async def _grid_state_loop() -> None:
    """Continuously publish mock grid state every 2 seconds."""
    while True:
        try:
            await _publish_mock_grid_state()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error publishing mock grid state: {e}")
        await asyncio.sleep(2)


async def mock_event_loop() -> None:
    """Runs a continuous sequence of mock events for a passive demo mode."""
    logger.info("Starting mock event loop for demo...")

    # Start the grid state ticker in the background
    grid_task = asyncio.create_task(_grid_state_loop())

    scenarios = [
        trigger_mock_scenario_peak_load,
        trigger_mock_scenario_malicious_command,
    ]

    try:
        while True:
            await asyncio.sleep(random.uniform(10, 30))
            scenario = random.choice(scenarios)
            try:
                await scenario()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in mock scenario: {e}")
    finally:
        grid_task.cancel()

