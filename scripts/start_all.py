"""Startup script — launches the full multi-agent MCP system.

Agent roster:
  • 1× Strategic Agent  (configurable model, e.g. qwen3-coder:30b)
  • 3× Zone Coordinators (PLC deterministic safety logic via MCP)
  • 1× Safety Guardian   (e.g. llama-guard3)
  • 11 Sensor MCP servers
  • 5  Actuator MCP servers
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from src.common.config import get_settings
from src.simulation.power_grid import PowerGridSimulation
from src.simulation.data_generator import DataGenerator
from src.domains.power_grid.adapter import PowerGridAdapter
from src.strategic.agent import StrategicAgent
from src.strategic.guardian import SafetyGuardian
from src.strategic.memory import ContextMemory
from src.strategic.monitor import MonitoringLoop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("  MCP Multi-Agent Power Grid System — Starting Up")
    logger.info("=" * 60)

    # 1. Initialize simulation
    logger.info("Initializing IEEE 30-bus power grid simulation...")
    grid = PowerGridSimulation()
    logger.info("  ✓ Grid: %d buses, %d lines, %d generators",
                len(grid.net.bus), len(grid.net.line), len(grid.net.gen))

    # 2. Initialize domain adapter
    adapter = PowerGridAdapter()
    logger.info("  ✓ Domain adapter: %s", adapter.domain_name)

    # 3. Create sensor servers
    sensors = adapter.create_sensors(grid)
    logger.info("  ✓ Created %d sensor MCP servers", len(sensors))

    # 4. Create actuator servers
    actuators = adapter.create_actuators(grid)
    logger.info("  ✓ Created %d actuator MCP servers", len(actuators))

    # 5. Create coordinators (deterministic PLC relays)
    coordinators = adapter.create_coordinators(grid)
    logger.info("  ✓ Created %d zone coordinator PLCs (Deterministic)", len(coordinators))
    for coord in coordinators:
        logger.info("    • %s", coord.name)

    # 6. Register all servers with the MCP Registry
    logger.info("Registering with MCP Registry...")
    for server in [*sensors, *actuators, *coordinators]:
        try:
            await server.register_with_registry()
        except Exception as e:
            logger.warning("  Failed to register %s: %s", server.name, e)

    # 7. Initialize Safety Guardian
    logger.info("Initializing Safety Guardian agent...")
    guardian = SafetyGuardian()
    logger.info("  ✓ Guardian → model=%s", guardian.llm.model)

    # 8. Initialize strategic agent (with live server references for direct tool execution)
    logger.info("Initializing Strategic Agent...")
    all_servers = [*sensors, *actuators, *coordinators]
    memory = ContextMemory()
    agent = StrategicAgent(memory=memory, servers=all_servers)
    logger.info("  ✓ Strategic Agent → model=%s", agent.llm.model)
    tool_count = await agent.discover_tools()
    logger.info("  ✓ Agent discovered %d tools (%d with live servers)", tool_count, len(all_servers))

    # 9. Start monitoring loop (zone-first architecture)
    logger.info("Starting monitoring loop (interval=%ds)...", settings.monitor_interval_seconds)
    data_gen = DataGenerator(grid)
    monitor = MonitoringLoop(grid, agent, data_gen=data_gen, coordinators=coordinators)

    # --- Summary ---
    logger.info("")
    logger.info("=" * 60)
    logger.info("  ✅ System ready!  Multi-Agent Roster:")
    logger.info("  ┌──────────────────────────────────────────────────────┐")
    logger.info("  │  Strategic Agent  │ model: %-25s │", settings.strategic_model)
    logger.info("  │  Safety Guardian  │ model: %-25s │", settings.guardian_model)
    logger.info("  │  Zone 1 PLC       │ Deterministic (IEC 60255)       │")
    logger.info("  │  Zone 2 PLC       │ Deterministic (IEC 60255)       │")
    logger.info("  │  Zone 3 PLC       │ Deterministic (IEC 60255)       │")
    logger.info("  └──────────────────────────────────────────────────────┘")
    logger.info("  MCP servers: %d  │  Tools: %d",
                len(sensors) + len(actuators) + len(coordinators), tool_count)
    logger.info("  Run 'mcp-cli' in another terminal for interactive control")
    logger.info("=" * 60)

    # Handle shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(monitor, memory)))

    await monitor.start()


async def shutdown(monitor: MonitoringLoop, memory: ContextMemory) -> None:
    logger.info("Shutting down...")
    await monitor.stop()
    memory.close()
    logger.info("Goodbye!")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
