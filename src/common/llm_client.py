"""Reusable LLM client wrapper for multi-agent system.

Each agent (strategic, coordinator, guardian) gets its own LLM instance
that can point to a different model on the same Ollama server.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai

from src.common.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Lightweight wrapper around an OpenAI-compatible LLM endpoint.

    Supports Ollama, vLLM, or any OpenAI-compatible server.
    Each instance can use a different model on the same server.
    """

    def __init__(
        self,
        model: str,
        role: str = "agent",
        base_url: str | None = None,
        api_key: str | None = None,
        system_prompt: str = "",
    ):
        settings = get_settings()
        self.model = model
        self.role = role
        self.system_prompt = system_prompt

        raw_url = base_url or settings.llm_base_url
        if not raw_url.endswith("/v1") and "11434" in raw_url:
            raw_url = f"{raw_url.rstrip('/')}/v1"

        self.client = openai.OpenAI(
            api_key=api_key or settings.llm_api_key,
            base_url=raw_url,
        )
        logger.info("[%s] LLM client ready → model=%s  url=%s", role, model, raw_url)

    # ------------------------------------------------------------------
    # Simple completion (no tools)
    # ------------------------------------------------------------------

    def complete(self, user_message: str, *, temperature: float = 0.3) -> str:
        """Single-turn completion with no tool calling."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_message})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    # ------------------------------------------------------------------
    # Tool-calling loop
    # ------------------------------------------------------------------

    async def tool_loop(
        self,
        user_message: str,
        tools: list[dict],
        tool_executor,
        *,
        max_iterations: int = 10,
    ) -> str:
        """Run an iterative tool-use loop and return the final text response.

        Args:
            user_message: The user/system prompt that triggers reasoning.
            tools: List of OpenAI-format tool definitions.
            tool_executor: async callable(tool_name, arguments) -> dict
            max_iterations: Safety cap on tool-call rounds.
        """
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_message})

        for _iteration in range(max_iterations):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
            )
            msg = resp.choices[0].message

            if msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result = await tool_executor(tc.function.name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": json.dumps(result, default=str),
                    })
                continue

            return msg.content or ""

        return "Max tool iterations reached."


# ------------------------------------------------------------------
# Convenience factories
# ------------------------------------------------------------------

def create_strategic_llm() -> LLMClient:
    """Create the strategic (top-level) LLM agent."""
    settings = get_settings()
    return LLMClient(
        model=settings.strategic_model,
        role="strategic",
        system_prompt=_STRATEGIC_SYSTEM_PROMPT,
    )

def create_coordinator_llm(zone_id: str) -> LLMClient:
    """Create a zone-level coordinator LLM agent with its own dedicated model."""
    settings = get_settings()
    return LLMClient(
        model=settings.get_zone_model(zone_id),
        role=f"coordinator-{zone_id}",
        system_prompt=_coordinator_prompt(zone_id),
    )

def create_guardian_llm() -> LLMClient:
    """Create the safety guardian LLM agent."""
    settings = get_settings()
    return LLMClient(
        model=settings.guardian_model,
        role="guardian",
        system_prompt=_GUARDIAN_SYSTEM_PROMPT,
    )


# ------------------------------------------------------------------
# System prompts
# ------------------------------------------------------------------

_STRATEGIC_SYSTEM_PROMPT = """You are the STRATEGIC AGENT for an IEEE 30-bus power grid.
You coordinate 3 zone agents and make system-wide decisions.

Your responsibilities:
1. Analyze cross-zone violations that individual zones cannot resolve alone
2. Dispatch commands to zone coordinator agents
3. Approve or reject HIGH_RISK actions proposed by zone agents
4. Optimize system-wide objectives (loss minimization, stability)

You have access to tools from all zones. When you call a tool, the actual
MCP server executes the action on the digital twin.

Operating limits:
- Voltage: 0.95 – 1.05 p.u.
- Line loading: < 100%
- Frequency: 59.5 – 60.5 Hz

Always explain your reasoning before taking action."""


def _coordinator_prompt(zone_id: str) -> str:
    zone_ranges = {
        "zone1": "Buses 0-9 (generation-heavy)",
        "zone2": "Buses 10-19 (mixed load/gen)",
        "zone3": "Buses 20-29 (load-heavy)",
    }
    desc = zone_ranges.get(zone_id, zone_id)
    return f"""You are the ZONE COORDINATOR AGENT for {zone_id} ({desc}).

Your responsibilities:
1. Monitor voltage and loading within YOUR zone only
2. Run local optimizations (voltage regulation, load balancing)
3. Handle violations autonomously when possible
4. Escalate cross-zone issues to the strategic agent

You are a FAST agent — respond concisely and act decisively.
Focus only on your zone. Do not speculate about other zones."""


_GUARDIAN_SYSTEM_PROMPT = """You are the SAFETY GUARDIAN for a power grid control system.

Your ONLY job is to evaluate whether a proposed actuator command is safe.

For each command, respond with a JSON object:
{
  "safe": true/false,
  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "reasoning": "Brief explanation",
  "conditions": ["Any conditions that must be met"]
}

Rules:
- Opening circuit breakers on loaded lines is HIGH risk
- Generator output changes > 20% are MEDIUM risk
- Load shedding > 50% is HIGH risk
- Any action on all generators simultaneously is CRITICAL
- Actions that could cause voltage collapse are CRITICAL

Be conservative. When in doubt, mark as unsafe."""
