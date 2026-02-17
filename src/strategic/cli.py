"""Natural language CLI for interacting with the strategic agent."""

from __future__ import annotations

import asyncio
import logging
import sys

from src.common.config import get_settings
from src.simulation.power_grid import PowerGridSimulation
from src.strategic.agent import StrategicAgent
from src.strategic.memory import ContextMemory
from src.strategic.monitor import MonitoringLoop

logger = logging.getLogger(__name__)

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          MCP Power Grid Strategic Agent CLI                  ║
║                                                              ║
║  Commands:                                                   ║
║    status    — System-wide overview                          ║
║    zones     — Zone health summary                           ║
║    history   — Recent agent decisions                        ║
║    monitor   — Start/stop continuous monitoring              ║
║    scenario <name> — Run a validation scenario               ║
║    quit/exit — Exit the CLI                                  ║
║                                                              ║
║  Or type any natural language query to the agent.            ║
╚══════════════════════════════════════════════════════════════╝
"""


async def run_cli() -> None:
    """Main CLI loop."""
    print(BANNER)

    # Initialize
    print("Initializing power grid simulation...")
    grid = PowerGridSimulation()

    # Create all MCP servers for live tool execution
    from src.domains.power_grid.adapter import PowerGridAdapter
    adapter = PowerGridAdapter()
    sensors = adapter.create_sensors(grid)
    actuators = adapter.create_actuators(grid)
    coordinators = adapter.create_coordinators(grid)
    all_servers = [*sensors, *actuators, *coordinators]

    memory = ContextMemory()
    agent = StrategicAgent(memory=memory, servers=all_servers)

    print("Discovering MCP tools...")
    tool_count = await agent.discover_tools()
    print(f"  → {tool_count} tools discovered ({len(all_servers)} live servers)\n")

    monitor = MonitoringLoop(grid, agent)
    monitor_task: asyncio.Task | None = None

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("🔌 > ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("quit", "exit", "q"):
            if monitor_task:
                await monitor.stop()
                monitor_task.cancel()
            memory.close()
            print("Goodbye!")
            break

        elif cmd == "status":
            _print_system_status(grid)

        elif cmd == "zones":
            _print_zone_summary(grid)

        elif cmd == "history":
            decisions = memory.get_recent_decisions(5)
            if not decisions:
                print("  No decisions recorded yet.\n")
            else:
                for d in decisions:
                    print(f"  [{d['timestamp']}] {d['trigger'][:60]}")
                    print(f"    → {d['reasoning'][:100]}\n")

        elif cmd == "monitor start":
            if monitor_task and not monitor_task.done():
                print("  Monitor already running.\n")
            else:
                monitor_task = asyncio.create_task(monitor.start())
                print("  Monitoring started.\n")

        elif cmd == "monitor stop":
            if monitor_task:
                await monitor.stop()
                monitor_task.cancel()
                monitor_task = None
                print("  Monitoring stopped.\n")
            else:
                print("  Monitor not running.\n")

        elif cmd.startswith("scenario "):
            scenario_name = cmd.split(" ", 1)[1]
            from src.simulation.scenarios import run_scenario
            result = run_scenario(scenario_name, grid)
            import json
            print(json.dumps(result, indent=2, default=str))
            print()

        else:
            # Natural language query
            print("  Thinking...")
            try:
                response = await agent.query(user_input)
                print(f"\n  {response}\n")
            except Exception as e:
                print(f"  Error: {e}\n")


def _print_system_status(grid: PowerGridSimulation) -> None:
    print("\n  === System Status ===")
    print(f"  Total Generation: {grid.get_total_generation():.1f} MW")
    print(f"  Total Load:       {grid.get_total_load():.1f} MW")
    print(f"  Total Losses:     {grid.get_total_losses():.3f} MW")
    print(f"  Frequency:        {grid.get_frequency():.4f} Hz")

    voltages = grid.get_bus_voltages()
    loadings = grid.get_line_loadings()
    print(f"  Voltage range:    {min(voltages.values()):.4f} - {max(voltages.values()):.4f} p.u.")
    print(f"  Max line loading: {max(loadings.values()):.1f}%")

    v_violations = sum(1 for v in voltages.values() if v < 0.95 or v > 1.05)
    t_violations = sum(1 for l in loadings.values() if l > 100)
    print(f"  Violations:       {v_violations} voltage, {t_violations} thermal")
    print()


def _print_zone_summary(grid: PowerGridSimulation) -> None:
    zone_buses = grid.get_zone_buses()
    print("\n  === Zone Summary ===")
    for zone, buses in zone_buses.items():
        voltages = [grid.get_bus_voltage(b) for b in buses]
        avg_v = sum(voltages) / len(voltages)
        min_v = min(voltages)
        max_v = max(voltages)

        zone_loads = grid.net.load[grid.net.load.bus.isin(buses)]
        total_load = float(zone_loads.p_mw.sum()) if len(zone_loads) > 0 else 0

        violations = sum(1 for v in voltages if v < 0.95 or v > 1.05)
        health = "🔴" if violations > 2 else "🟡" if violations > 0 else "🟢"

        print(f"  {health} {zone}: V={min_v:.3f}-{max_v:.3f} p.u. | Load={total_load:.1f} MW | Violations={violations}")
    print()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
