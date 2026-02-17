"""Startup script to launch all MCP servers and services."""

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
from src.strategic.memory import ContextMemory
from src.strategic.monitor import MonitoringLoop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
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

    # 5. Create coordinators
    coordinators = adapter.create_coordinators(grid)
    logger.info("  ✓ Created %d coordinator MCP servers", len(coordinators))

    # 6. Register all servers
    logger.info("Registering with MCP Registry...")
    for server in [*sensors, *actuators, *coordinators]:
        try:
            await server.register_with_registry()
        except Exception as e:
            logger.warning("  Failed to register %s: %s", server.name, e)

    # 7. Initialize strategic agent
    logger.info("Initializing strategic agent...")
    memory = ContextMemory()
    agent = StrategicAgent(memory=memory)
    tool_count = await agent.discover_tools()
    logger.info("  ✓ Agent discovered %d tools", tool_count)

    # 8. Start monitoring loop
    logger.info("Starting monitoring loop (interval=%ds)...", get_settings().monitor_interval_seconds)
    monitor = MonitoringLoop(grid, agent, DataGenerator(grid))

    logger.info("")
    logger.info("=" * 60)
    logger.info("  System ready! %d MCP servers, %d tools",
                len(sensors) + len(actuators) + len(coordinators), tool_count)
    logger.info("  Run 'mcp-cli' in another terminal for interactive control")
    logger.info("  Run 'mcp-dashboard' for the monitoring dashboard")
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
