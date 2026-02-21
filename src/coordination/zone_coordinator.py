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
from src.common.mqtt_client import MQTTClient
from src.common.models import (
    MCPServerRegistration,
    SafetyLevel,
    ToolDescriptor,
    ViolationEvent,
)
from src.simulation.power_grid import PowerGridSimulation
from src.coordination.optimizer import ZoneOptimizer
from src.coordination.audit import ZoneAuditLogger

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
        lines: list[int]
    ):
        self.zone_id = zone_id
        self.grid = grid
        self.buses = buses
        self.lines = lines
        self.server_id = f"coordinator_{zone_id}_{uuid.uuid4().hex[:8]}"
        self.name = f"Zone Coordinator PLC ({zone_id})"
        self.optimizer = ZoneOptimizer(grid, zone_id, buses, lines)
        self.audit_log = ZoneAuditLogger()
        self.mqtt: MQTTClient | None = None
        
        # Deterministic Protection Thresholds (adjustable via MCP)
        self.protection_settings = {
            "under_voltage_pu": 0.95,
            "over_voltage_pu": 1.05,
            "max_line_loading_pct": 100.0,
        }
        
        # State tracking for deadband/escalation
        self._consecutive_violations = 0

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
                    name="execute_safety_rules",
                    description=f"Evaluate deterministic IEC 60255 protection rules for {self.zone_id} and execute hardware actions",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="update_protection_settings",
                    description=f"Update protection relay trip thresholds for {self.zone_id}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "under_voltage_pu": {"type": "number", "description": "Trip threshold for under-voltage"},
                            "over_voltage_pu": {"type": "number", "description": "Trip threshold for over-voltage"},
                            "max_line_loading_pct": {"type": "number", "description": "Trip threshold for thermal overload"},
                        },
                    },
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
                elif name == "execute_safety_rules":
                    result = self._evaluate_safety_rules()
                elif name == "update_protection_settings":
                    self.protection_settings.update({k: v for k, v in arguments.items() if v is not None})
                    self.audit_log.log_event(self.zone_id, "SETTINGS_UPDATED", "Protection thresholds revised", details=self.protection_settings)
                    self._broadcast_state("settings_updated", self.protection_settings)
                    result = {"status": "success", "settings": self.protection_settings}
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
                if vm < self.protection_settings["under_voltage_pu"]:
                    violations.append({"type": "voltage_low", "bus": b, "value": round(vm, 4), "limit": self.protection_settings["under_voltage_pu"]})
                elif vm > self.protection_settings["over_voltage_pu"]:
                    violations.append({"type": "voltage_high", "bus": b, "value": round(vm, 4), "limit": self.protection_settings["over_voltage_pu"]})
            except (KeyError, IndexError):
                pass

        for lid in self.lines:
            try:
                loading = float(self.grid.net.res_line.loading_percent.at[lid])
                if loading > self.protection_settings["max_line_loading_pct"]:
                    violations.append({"type": "thermal", "line": lid, "value": round(loading, 2), "limit": self.protection_settings["max_line_loading_pct"]})
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
    # Deterministic PLC Logic (IEC 60255 Emulation)
    # ------------------------------------------------------------------

    def _evaluate_safety_rules(self) -> dict:
        """Deterministic rule engine executing hard-coded safety logic."""
        status = self._get_zone_status()
        violations = self._detect_violations()
        v_list = violations.get("violations", [])
        
        actions_taken = []
        events_logged = []
        escalate = False
        
        if violations["count"] > 0:
            self._consecutive_violations += 1
        else:
            self._consecutive_violations = 0
            
        topics = []
            
        # Rule 4: Strategic Escalation Deadband
        if self._consecutive_violations >= 3:
            msg = f"Escalating: Unable to resolve {violations['count']} violations after 3 cycles."
            self.audit_log.log_event(self.zone_id, "ESCALATION", msg, details=violations)
            self._broadcast_state("escalation", {"violations": violations})
            return {
                "zone": self.zone_id,
                "status": "escalation_required",
                "violations": violations,
                "message": msg
            }

        # Rule 1 & Rule 2: Voltage Protection (ANSI 27 & 59 / IEC 60255-127)
        if any(v["type"] in ("voltage_low", "voltage_high") for v in v_list):
            msg = "IEC 60255-127 Voltage Relay Triggered."
            result = self.optimizer.regulate_voltage(1.0)
            act = "Capacitor banks switched to regulate voltage."
            actions_taken.append({"action": "voltage_regulation", "result": result})
            self.audit_log.log_event(self.zone_id, "RELAY_TRIP", msg, action_taken=act, details=result)
            topics.append("relay_trip")
            events_logged.append(msg)

        # Rule 3: Thermal Overload (ANSI 50/51 / IEC 60255-151)
        if any(v["type"] == "thermal" for v in v_list):
            msg = "IEC 60255-151 Overcurrent Relay Triggered."
            # Shed load dynamically, aiming for 95% of limit to create buffer
            target = self.protection_settings["max_line_loading_pct"] * 0.95
            result = self.optimizer.balance_loading(target)
            act = f"Local demand response triggered (Target: {target}%)."
            actions_taken.append({"action": "thermal_protection", "result": result})
            self.audit_log.log_event(self.zone_id, "RELAY_TRIP", msg, action_taken=act, details=result)
            topics.append("relay_trip")
            events_logged.append(msg)

        post_violations = self._detect_violations()
        
        result_payload = {
            "zone": self.zone_id,
            "violations_before": violations.get("count", 0),
            "violations_after": post_violations.get("count", 0),
            "actions_taken": actions_taken,
            "events": events_logged,
            "mode": "deterministic_plc",
        }
        
        # Broadcast status updates
        self._broadcast_state("status", self._get_zone_status())
        for topic in topics:
            self._broadcast_state(topic, result_payload)

        return result_payload

    # ------------------------------------------------------------------
    # MQTT Communication
    # ------------------------------------------------------------------
    
    def _broadcast_state(self, topic_suffix: str, payload: dict) -> None:
        """Broadcast an event or state over MQTT to all subscribers."""
        if not self.mqtt:
            return
        
        topic = f"grid/{self.zone_id}/{topic_suffix}"
        
        # We fire and forget asynchronously in the background
        import asyncio
        asyncio.create_task(self._publish_async(topic, payload))
        
    async def _publish_async(self, topic: str, payload: dict) -> None:
        try:
            msg = json.dumps(payload, default=str)
            await self.mqtt.publish(topic, msg)
        except Exception as e:
            logger.error("Failed to broadcast on %s: %s", topic, e)

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
            ToolDescriptor(name="execute_safety_rules", description="PLC Deterministic Rules Evaluation", safety_level=SafetyLevel.MEDIUM_RISK),
            ToolDescriptor(name="update_protection_settings", description="Revise safety thresholds", safety_level=SafetyLevel.HIGH_RISK),
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
        settings = get_settings()
        self.mqtt = MQTTClient(
            settings.mqtt_broker,
            settings.mqtt_port,
            client_id=f"zone_{self.zone_id}_{uuid.uuid4().hex[:4]}"
        )
        await self.mqtt.connect()
        self.audit_log.log_event(self.zone_id, "SYSTEM_START", "Zone PLC Relay Initialized Offline", details={"buses": self.buses})
        
        await self.register_with_registry()
        
        async with stdio_server() as (read, write):
            await self.mcp.run(read, write, self.mcp.create_initialization_options())
