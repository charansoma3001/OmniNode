"""Zone/Substation Coordinator MCP Server.

Each zone coordinator manages a subset of buses/lines and provides:
- Local optimization with its own LLM brain
- Autonomous violation handling
- Inter-zone coordination
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.common.config import get_settings
from src.common.llm_client import LLMClient, create_coordinator_llm
from src.common.models import (
    MCPServerRegistration,
    SafetyLevel,
    ToolDescriptor,
    ViolationEvent,
)
from src.simulation.power_grid import PowerGridSimulation
from src.coordination.optimizer import ZoneOptimizer

logger = logging.getLogger(__name__)


class ZoneCoordinator:
    """MCP server for a geographic zone of the power grid.

    Aggregates sensor data, runs local optimization, handles violations,
    and coordinates with peer zones.
    """

    def __init__(
        self,
        zone_id: str,
        grid: PowerGridSimulation,
        buses: list[int],
        lines: list[int],
        llm: LLMClient | None = None,
    ):
        self.zone_id = zone_id
        self.grid = grid
        self.buses = buses
        self.lines = lines
        self.server_id = f"coordinator_{zone_id}_{uuid.uuid4().hex[:8]}"
        self.name = f"Zone Coordinator ({zone_id})"
        self.optimizer = ZoneOptimizer(grid, zone_id, buses, lines)
        self._peer_states: dict[str, dict] = {}

        # Each coordinator gets its own LLM brain
        self.llm = llm or create_coordinator_llm(zone_id)

        self.mcp = Server(self.name)
        self._register_tools()

    def _register_tools(self) -> None:
        @self.mcp.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="get_zone_status",
                    description=f"Get comprehensive status of {self.zone_id}",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="optimize_zone_topology",
                    description=f"Optimize {self.zone_id} for a given objective",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "objective": {
                                "type": "string",
                                "enum": ["min_losses", "min_voltage_deviation", "balance_loading"],
                                "description": "Optimization objective",
                            }
                        },
                        "required": ["objective"],
                    },
                ),
                Tool(
                    name="handle_violation",
                    description=f"Handle a constraint violation in {self.zone_id}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "violation_type": {"type": "string", "enum": ["voltage", "thermal", "frequency"]},
                            "affected_components": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["violation_type"],
                    },
                ),
                Tool(
                    name="load_balancing",
                    description=f"Redistribute load within {self.zone_id}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target_balance": {"type": "number", "description": "Target loading % per line (0-100)"}
                        },
                    },
                ),
                Tool(
                    name="voltage_regulation",
                    description=f"Adjust voltage profile in {self.zone_id}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target_pu": {"type": "number", "description": "Target voltage in p.u.", "default": 1.0}
                        },
                    },
                ),
                Tool(
                    name="emergency_islanding",
                    description=f"Isolate {self.zone_id} from the rest of the grid",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string"}
                        },
                        "required": ["reason"],
                    },
                ),
                Tool(
                    name="detect_violations",
                    description=f"Scan {self.zone_id} for constraint violations",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="analyze_and_act",
                    description=f"Use the zone's local LLM to analyze current state and autonomously take corrective action in {self.zone_id}",
                    inputSchema={"type": "object", "properties": {
                        "situation": {"type": "string", "description": "Optional description of what to analyze"},
                    }},
                ),
            ]

        @self.mcp.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            try:
                if name == "get_zone_status":
                    result = self._get_zone_status()
                elif name == "optimize_zone_topology":
                    result = self.optimizer.optimize(arguments["objective"])
                elif name == "handle_violation":
                    result = self._handle_violation(arguments)
                elif name == "load_balancing":
                    result = self.optimizer.balance_loading(arguments.get("target_balance", 80))
                elif name == "voltage_regulation":
                    result = self.optimizer.regulate_voltage(arguments.get("target_pu", 1.0))
                elif name == "emergency_islanding":
                    result = self._emergency_island(arguments.get("reason", ""))
                elif name == "detect_violations":
                    result = self._detect_violations()
                elif name == "analyze_and_act":
                    result = self._llm_analyze(arguments.get("situation", ""))
                else:
                    result = {"error": f"Unknown tool: {name}"}
                return [TextContent(type="text", text=json.dumps(result, default=str))]
            except Exception as e:
                logger.error("Error in coordinator %s.%s: %s", self.zone_id, name, e)
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _get_zone_status(self) -> dict:
        voltages = {b: self.grid.get_bus_voltage(b) for b in self.buses}
        loadings = {}
        for lid in self.lines:
            try:
                loadings[lid] = float(self.grid.net.res_line.loading_percent.at[lid])
            except (KeyError, IndexError):
                pass

        # Loads in zone
        zone_loads = self.grid.net.load[self.grid.net.load.bus.isin(self.buses)]
        total_load = float(zone_loads.p_mw.sum()) if len(zone_loads) > 0 else 0

        # Generators in zone
        zone_gens = self.grid.net.gen[self.grid.net.gen.bus.isin(self.buses)]
        total_gen = float(zone_gens.p_mw.sum()) if len(zone_gens) > 0 else 0

        violations = self._detect_violations()

        return {
            "zone_id": self.zone_id,
            "buses": self.buses,
            "num_lines": len(self.lines),
            "voltages": {str(k): round(v, 4) for k, v in voltages.items()},
            "min_voltage": round(min(voltages.values()), 4) if voltages else None,
            "max_voltage": round(max(voltages.values()), 4) if voltages else None,
            "avg_line_loading": round(sum(loadings.values()) / max(len(loadings), 1), 2),
            "max_line_loading": round(max(loadings.values()), 2) if loadings else 0,
            "total_load_mw": round(total_load, 2),
            "total_gen_mw": round(total_gen, 2),
            "violations": violations,
            "health": "critical" if violations.get("count", 0) > 2 else "warning" if violations.get("count", 0) > 0 else "normal",
        }

    # ------------------------------------------------------------------
    # Violation handling
    # ------------------------------------------------------------------

    def _detect_violations(self) -> dict:
        violations = []
        for b in self.buses:
            try:
                vm = self.grid.get_bus_voltage(b)
                if vm < 0.95:
                    violations.append({"type": "voltage_low", "bus": b, "value": round(vm, 4), "limit": 0.95})
                elif vm > 1.05:
                    violations.append({"type": "voltage_high", "bus": b, "value": round(vm, 4), "limit": 1.05})
            except (KeyError, IndexError):
                pass

        for lid in self.lines:
            try:
                loading = float(self.grid.net.res_line.loading_percent.at[lid])
                if loading > 100:
                    violations.append({"type": "thermal", "line": lid, "value": round(loading, 2), "limit": 100})
            except (KeyError, IndexError):
                pass

        return {"violations": violations, "count": len(violations), "zone": self.zone_id}

    def _handle_violation(self, args: dict) -> dict:
        vtype = args["violation_type"]
        affected = args.get("affected_components", [])

        if vtype == "voltage":
            return self.optimizer.regulate_voltage(1.0)
        elif vtype == "thermal":
            return self.optimizer.balance_loading(80)
        elif vtype == "frequency":
            return {"action": "frequency_response", "message": "Frequency handled at system level"}
        else:
            return {"error": f"Unknown violation type: {vtype}"}

    def _emergency_island(self, reason: str) -> dict:
        """Isolate the zone by opening all tie lines."""
        all_lines = list(self.grid.net.line.index)
        tie_lines = []
        for lid in all_lines:
            fb = int(self.grid.net.line.from_bus.at[lid])
            tb = int(self.grid.net.line.to_bus.at[lid])
            in_zone = fb in self.buses or tb in self.buses
            both_in = fb in self.buses and tb in self.buses
            if in_zone and not both_in:
                tie_lines.append(lid)

        # Validate first
        snapshot = self.grid.save_snapshot()
        for lid in tie_lines:
            self.grid.net.line.in_service.at[lid] = False

        converged = self.grid.run_power_flow()
        if not converged:
            self.grid.restore_snapshot(snapshot)
            return {"islanded": False, "reason": "Power flow does not converge after islanding", "tie_lines": tie_lines}

        return {
            "islanded": True,
            "reason": reason,
            "tie_lines_opened": tie_lines,
            "converged": converged,
        }

    # ------------------------------------------------------------------
    # LLM-powered analysis (zone-local agent)
    # ------------------------------------------------------------------

    def _llm_analyze(self, situation: str = "") -> dict:
        """Use the zone's local LLM to analyze current state and recommend actions."""
        status = self._get_zone_status()
        violations = self._detect_violations()

        prompt = f"""Analyze the current state of {self.zone_id} and recommend corrective actions.

Zone Status:
{json.dumps(status, indent=2, default=str)}

Violations:
{json.dumps(violations, indent=2, default=str)}

{f'Situation: {situation}' if situation else ''}

Respond with:
1. Assessment of zone health (1-2 sentences)
2. Recommended actions (be specific: which buses, which controls)
3. Whether the strategic agent needs to be involved (yes/no)"""

        try:
            response = self.llm.complete(prompt, temperature=0.3)
            return {
                "zone": self.zone_id,
                "model": self.llm.model,
                "analysis": response,
                "violations_count": violations.get("count", 0),
                "autonomous": True,
            }
        except Exception as e:
            logger.error("LLM analysis failed for %s: %s", self.zone_id, e)
            return {"zone": self.zone_id, "error": str(e), "autonomous": False}

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def get_registration(self) -> MCPServerRegistration:
        tools = [
            ToolDescriptor(name="get_zone_status", description="Zone status overview", safety_level=SafetyLevel.READ_ONLY),
            ToolDescriptor(name="optimize_zone_topology", description="Local optimization", safety_level=SafetyLevel.MEDIUM_RISK),
            ToolDescriptor(name="handle_violation", description="Violation response", safety_level=SafetyLevel.MEDIUM_RISK),
            ToolDescriptor(name="load_balancing", description="Load redistribution", safety_level=SafetyLevel.MEDIUM_RISK),
            ToolDescriptor(name="voltage_regulation", description="Voltage control", safety_level=SafetyLevel.MEDIUM_RISK),
            ToolDescriptor(name="emergency_islanding", description="Zone isolation", safety_level=SafetyLevel.HIGH_RISK),
            ToolDescriptor(name="detect_violations", description="Violation scan", safety_level=SafetyLevel.READ_ONLY),
            ToolDescriptor(name="analyze_and_act", description="LLM-powered autonomous analysis", safety_level=SafetyLevel.READ_ONLY),
        ]
        return MCPServerRegistration(
            server_id=self.server_id,
            name=self.name,
            layer="coordination",
            domain="power_grid",
            zone=self.zone_id,
            transport="stdio",
            tools=tools,
        )

    async def register_with_registry(self) -> None:
        settings = get_settings()
        reg = self.get_registration()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{settings.registry_url}/register",
                    json=reg.model_dump(mode="json"),
                )
                resp.raise_for_status()
                logger.info("Registered %s with registry", self.name)
        except Exception as e:
            logger.warning("Failed to register with registry: %s", e)

    async def run(self) -> None:
        await self.register_with_registry()
        async with stdio_server() as (read, write):
            await self.mcp.run(read, write, self.mcp.create_initialization_options())
