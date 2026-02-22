"""Strategic LLM Agent — Multi-Agent Coordinator.

Discovers tools from the registry, reasons over the grid state,
and executes multi-step action plans via natural language.
Routes tool calls to ACTUAL server objects (sensors, actuators, coordinators).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

import httpx

from src.common.config import get_settings
from src.common.llm_client import LLMClient, create_strategic_llm
from src.common.models import AgentDecision
from src.strategic.memory import ContextMemory
from src.api.event_bus import event_bus
import asyncio

logger = logging.getLogger(__name__)


class StrategicAgent:
    """LLM-powered strategic agent that controls the grid via MCP tools.

    On startup, discovers all available tools from the MCP Registry.
    Converts natural language commands into tool invocations.
    Routes tool calls to actual in-process server objects.
    """

    def __init__(
        self,
        memory: ContextMemory | None = None,
        llm: LLMClient | None = None,
        servers: list | None = None,
    ):
        settings = get_settings()
        self.llm = llm or create_strategic_llm()
        self.memory = memory or ContextMemory()
        self._registry_url = settings.registry_url
        self._tools: list[dict] = []
        self._tool_server_map: dict[str, str] = {}     # clean_tool_name -> server_id
        self._tool_name_map: dict[str, str] = {}        # clean_tool_name -> original tool name
        self._server_objects: dict[str, Any] = {}        # server_id -> server object
        self._audit_log: list[AgentDecision] = []

        # Register live server objects for direct tool execution
        if servers:
            for server in servers:
                self._server_objects[server.server_id] = server

        logger.info(
            "Strategic agent initialized → model=%s  servers=%d",
            self.llm.model, len(self._server_objects),
        )

    # ------------------------------------------------------------------
    # Tool discovery
    # ------------------------------------------------------------------

    async def discover_tools(self) -> int:
        """Fetch all tools from the MCP Registry and build the tool catalog."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._registry_url}/tools")
                resp.raise_for_status()
                raw_tools = resp.json()
        except Exception as e:
            logger.error("Failed to discover tools: %s", e)
            return 0

        self._tools = []
        self._tool_server_map = {}
        self._tool_name_map = {}

        for tool in raw_tools:
            clean_name = (
                f"{tool['server_name']}_{tool['name']}"
                .replace(" ", "_").replace("(", "").replace(")", "").lower()
            )
            original_name = tool["name"]

            tool_def = {
                "type": "function",
                "function": {
                    "name": clean_name,
                    "description": f"[{tool['layer']}/{tool.get('zone', 'system')}] {tool['description']}",
                    "parameters": tool.get(
                        "input_schema",
                        {"type": "object", "properties": {}, "required": []},
                    ),
                },
            }
            self._tools.append(tool_def)
            self._tool_server_map[clean_name] = tool["server_id"]
            self._tool_name_map[clean_name] = original_name

        logger.info(
            "Discovered %d tools from %d servers",
            len(self._tools), len(set(self._tool_server_map.values())),
        )
        return len(self._tools)

    @property
    def actuator_tools(self) -> list[dict]:
        """Return only actuator tools to avoid overflowing the LLM context window.

        Read-only sensor tools are irrelevant during emergency escalation and
        bloat the prompt (107 tools ≈ 21k tokens vs 5 actuators ≈ 2k tokens).
        """
        # Keep tools from actuator/physical servers only (not sensors or coordinators)
        ACTUATOR_KEYWORDS = ("actuate_device", "list_devices", "get_device_status")
        filtered = [t for t in self._tools if t["function"]["name"].split("_")[-1] in {"actuate_device", "list_devices", "get_device_status"} or any(k in t["function"]["name"] for k in ("actuator", "generator", "breaker", "load_controller", "regulator", "storage"))]
        if not filtered:
            # Fallback: any tool whose description mentions actuating
            filtered = [t for t in self._tools if "actuate" in t["function"].get("description", "").lower()]
        logger.debug("Filtered to %d actuator tools (from %d total)", len(filtered), len(self._tools))
        return filtered or self._tools[:10]  # last resort: first 10

    # ------------------------------------------------------------------
    # Query / Command
    # ------------------------------------------------------------------

    async def query(self, user_message: str, *, escalation: bool = False) -> str:
        """Process a natural language query and return the agent's response.
        
        Args:
            user_message: The message or directive to process.
            escalation: If True, uses the filtered actuator-only tool list to
                avoid context window overflow with 107 full tool definitions.
        """
        recent_decisions = self.memory.get_recent_decisions(5)
        context_summary = self.memory.get_context_summary()
        context_block = self._build_context(context_summary, recent_decisions)

        full_message = f"{context_block}\n\n{user_message}" if context_block else user_message

        asyncio.create_task(event_bus.publish("agent_log", {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "analyzing",
            "message": f"Processing user query: {user_message[:200]}"
        }))

        # Use focused actuator tools during escalation to avoid context overflow
        tools_to_use = self.actuator_tools if escalation else self._tools
        logger.info("Querying LLM with %d tools (escalation=%s)", len(tools_to_use), escalation)

        final_text = await self.llm.tool_loop(
            user_message=full_message,
            tools=tools_to_use,
            tool_executor=self._execute_tool,
            tool_choice="required" if escalation and tools_to_use else None,
        )

        decision = AgentDecision(
            decision_id=uuid.uuid4().hex[:12],
            trigger=user_message[:200],
            reasoning=final_text[:500],
        )
        self._audit_log.append(decision)
        self.memory.store_decision(decision)

        asyncio.create_task(event_bus.publish("agent_log", {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "decision",
            "message": final_text or "(tool calls executed — no summary text)"
        }))

        return final_text

    async def _execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool call by routing to the actual in-process server object."""
        logger.info("Tool call: %s(%s)", tool_name, json.dumps(arguments, default=str)[:200])
        
        asyncio.create_task(event_bus.publish("agent_log", {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "tool_call",
            "message": f"Calling component: {tool_name}",
            "data": arguments
        }))

        server_id = self._tool_server_map.get(tool_name)
        original_name = self._tool_name_map.get(tool_name, tool_name)

        if not server_id:
            return {"error": f"Tool '{tool_name}' not found in registry"}

        # Look up the actual server object
        server = self._server_objects.get(server_id)
        if not server:
            logger.warning("No live server for %s (%s), returning stub", tool_name, server_id)
            return {
                "status": "no_live_server",
                "tool": tool_name,
                "server_id": server_id,
                "message": "Server not available for direct execution",
            }

        # Call the server's tool handler directly
        try:
            # All our servers register tools via MCP's call_tool decorator.
            # We invoke them through the server's internal methods.
            result = self._call_server_tool(server, original_name, arguments)
            logger.info("Tool result [%s]: %s", tool_name, json.dumps(result, default=str)[:300])
            return result
        except Exception as e:
            logger.error("Tool execution failed [%s]: %s", tool_name, e)
            return {"error": str(e), "tool": tool_name}

    def _call_server_tool(self, server: Any, tool_name: str, arguments: dict) -> dict:
        """Route a tool call to the correct handler method on the server object.

        Handles sensors, actuators, and coordinators by inspecting
        the server type and calling the appropriate internal method.
        """
        # ---- Zone Coordinator ----
        if hasattr(server, "zone_id"):
            if tool_name == "get_zone_status":
                return server._get_zone_status()
            elif tool_name == "optimize_zone_topology":
                return server.optimizer.optimize(arguments.get("objective", "min_losses"))
            elif tool_name == "handle_violation":
                return server._handle_violation(arguments)
            elif tool_name == "load_balancing":
                return server.optimizer.balance_loading(arguments.get("target_balance", 80))
            elif tool_name == "voltage_regulation":
                return server.optimizer.regulate_voltage(arguments.get("target_pu", 1.0))
            elif tool_name == "emergency_islanding":
                return server._emergency_island(arguments.get("reason", ""))
            elif tool_name == "detect_violations":
                return server._detect_violations()
            elif tool_name == "analyze_and_act":
                # THIS triggers the zone's own LLM!
                return server._llm_analyze(arguments.get("situation", ""))

        # ---- Sensor ----
        if hasattr(server, "sensor_type"):
            if tool_name == "read_sensor":
                return server._handle_read(arguments.get("sensor_id", ""))
            elif tool_name == "read_sensors_batch":
                return server._handle_batch_read(arguments.get("sensor_ids", []))
            elif tool_name == "list_sensors":
                return {"sensors": server._get_sensor_ids(), "type": server.sensor_type, "zone": server.zone}
            elif tool_name == "set_threshold":
                return server._handle_set_threshold(arguments)
            elif tool_name == "get_metadata":
                return server._get_sensor_metadata(arguments.get("sensor_id", ""))

        # ---- Actuator ----
        if hasattr(server, "device_type"):
            if tool_name == "control":
                return server._handle_control(arguments)
            elif tool_name == "validate_action":
                return server._handle_validate(arguments)
            elif tool_name == "get_status":
                return server._get_device_status(arguments.get("device_id", ""))
            elif tool_name == "list_devices":
                return {"devices": server._get_device_ids(), "type": server.device_type, "zone": server.zone}
            elif tool_name == "emergency_shutdown":
                return server._handle_emergency(arguments.get("zone_id", ""))

        return {"error": f"Unknown tool '{tool_name}' on server {server.name}"}

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def _build_context(self, context: str, recent_decisions: list[dict]) -> str:
        parts = []
        if context:
            parts.append(context)
        if recent_decisions:
            parts.append(
                "Recent decisions:\n" + json.dumps(recent_decisions[:3], indent=2, default=str)
            )
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def get_audit_log(self) -> list[dict]:
        return [d.model_dump(mode="json") for d in self._audit_log]
