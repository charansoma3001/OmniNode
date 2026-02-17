"""Strategic LLM Agent — Claude as MCP Client.

Discovers tools from the registry, reasons over the grid state,
and executes multi-step action plans via natural language.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

import anthropic
import httpx

from src.common.config import get_settings
from src.common.models import AgentDecision
from src.strategic.memory import ContextMemory

logger = logging.getLogger(__name__)


class StrategicAgent:
    """LLM-powered strategic agent that controls the grid via MCP tools.

    On startup, discovers all available tools from the MCP Registry.
    Converts natural language commands into tool invocations.
    Maintains context memory for decision continuity.
    """

    def __init__(self, memory: ContextMemory | None = None):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.agent_model
        self.memory = memory or ContextMemory()
        self._registry_url = settings.registry_url
        self._tools: list[dict] = []
        self._tool_server_map: dict[str, str] = {}  # tool_name -> server_id
        self._audit_log: list[AgentDecision] = []

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

        for tool in raw_tools:
            # Convert to Anthropic tool format
            anthropic_tool = {
                "name": f"{tool['server_name']}_{tool['name']}".replace(" ", "_").replace("(", "").replace(")", "").lower(),
                "description": f"[{tool['layer']}/{tool.get('zone', 'system')}] {tool['description']}",
                "input_schema": tool.get("input_schema", {"type": "object", "properties": {}}),
            }
            self._tools.append(anthropic_tool)
            self._tool_server_map[anthropic_tool["name"]] = tool["server_id"]

        logger.info("Discovered %d tools from %d servers", len(self._tools), len(set(self._tool_server_map.values())))
        return len(self._tools)

    # ------------------------------------------------------------------
    # Query / Command
    # ------------------------------------------------------------------

    async def query(self, user_message: str) -> str:
        """Process a natural language query and return the agent's response.

        The agent may invoke multiple tools to answer the query.
        """
        # Build context from memory
        recent_decisions = self.memory.get_recent_decisions(5)
        context_summary = self.memory.get_context_summary()

        system_prompt = self._build_system_prompt(context_summary, recent_decisions)

        messages = [{"role": "user", "content": user_message}]

        # Iterative tool-use loop
        max_iterations = 10
        for iteration in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=self._tools if self._tools else None,
                messages=messages,
            )

            # Check if we need to handle tool calls
            if response.stop_reason == "tool_use":
                # Extract tool use blocks
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_result = await self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(tool_result, default=str),
                        })

                # Add assistant response and tool results to messages
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Final text response
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text

                # Log decision
                decision = AgentDecision(
                    decision_id=uuid.uuid4().hex[:12],
                    trigger=user_message,
                    reasoning=final_text[:500],
                )
                self._audit_log.append(decision)
                self.memory.store_decision(decision)

                return final_text

        return "Max iterations reached. The query may be too complex."

    async def _execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool call (placeholder — actual execution goes through MCP).

        In the full system, this routes to the appropriate MCP server.
        For the prototype, we return a simulated response.
        """
        logger.info("Tool call: %s(%s)", tool_name, json.dumps(arguments)[:200])

        # Route to appropriate server via registry
        server_id = self._tool_server_map.get(tool_name)
        if not server_id:
            return {"error": f"Tool '{tool_name}' not found in registry"}

        # Placeholder: in production, this would invoke the MCP server's tool
        return {
            "status": "executed",
            "tool": tool_name,
            "server_id": server_id,
            "arguments": arguments,
            "result": "Tool execution routed to MCP server",
        }

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _build_system_prompt(self, context: str, recent_decisions: list[dict]) -> str:
        decisions_text = ""
        if recent_decisions:
            decisions_text = "\n\nRecent decisions:\n" + json.dumps(recent_decisions[:3], indent=2, default=str)

        return f"""You are a strategic power grid management agent. You monitor and control
a simulated IEEE 30-bus power grid through MCP tools.

Your responsibilities:
1. Monitor grid health (voltages, line loadings, frequency, temperatures)
2. Detect and respond to violations (voltage limits, thermal limits, frequency deviation)
3. Optimize grid operation (minimize losses, balance loading)
4. Execute natural language commands from operators
5. Explain your reasoning clearly

Safety rules:
- Always validate actuations before executing (use validate_action tools)
- For HIGH_RISK actions, explain the consequences before proceeding
- Never bypass safety checks
- Log all decisions for audit

Grid zones:
- Zone 1: Buses 0-9 (generation-heavy)
- Zone 2: Buses 10-19 (mixed)
- Zone 3: Buses 20-29 (load-heavy)

Normal operating limits:
- Voltage: 0.95 - 1.05 p.u.
- Line loading: < 100%
- Frequency: 59.5 - 60.5 Hz
- Transformer temperature: < 85°C (alarm), < 105°C (trip)

{context}
{decisions_text}"""

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def get_audit_log(self) -> list[dict]:
        return [d.model_dump(mode="json") for d in self._audit_log]
