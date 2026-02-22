"""Safety Guardian — LLM-based safety validation for actuator commands.

Uses a dedicated safety model (e.g. llama-guard3) to evaluate whether
proposed grid actions are safe before execution.
"""

from __future__ import annotations

import json
import logging
import asyncio

from src.common.llm_client import LLMClient, create_guardian_llm
from src.api.event_bus import event_bus

logger = logging.getLogger(__name__)


class SafetyGuardian:
    """Validates actuator commands using a dedicated safety LLM.

    Sits between the strategic/coordinator agents and actuator execution.
    Every HIGH_RISK command must be approved by the guardian before execution.
    """

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or create_guardian_llm()
        self._validation_log: list[dict] = []
        logger.info("Safety Guardian initialized → model=%s", self.llm.model)

    async def validate_command(self, command: dict) -> dict:
        """Evaluate a proposed actuator command.

        Args:
            command: Dict with keys like:
                - action: "open_breaker", "set_generator_output", etc.
                - target: Component ID
                - parameters: Action parameters
                - context: Current grid state summary

        Returns:
            Dict with 'safe' (bool), 'risk_level', 'reasoning', 'conditions'.
        """
        # Sanitize command fields from common LLM hallucinations before processing or UI broadcast
        raw_action = command.get("action", "")
        # Fallback: if 'action' wasn't explicitly provided, search other keys like 'status', 'operation'
        if not raw_action:
            for k, v in command.items():
                if isinstance(v, str) and v.lower() in {"open", "close", "activate", "deactivate", "scale", "shed", "restore", "charge", "discharge", "set_output", "ramp", "emergency_stop"}:
                    raw_action = v
                    break
        command["action"] = str(raw_action.get("operation", raw_action.get("action", raw_action)) if isinstance(raw_action, dict) else raw_action)
        
        raw_target = command.get("device_id", command.get("target", "unknown"))
        command["device_id"] = str(raw_target.get("id", raw_target) if isinstance(raw_target, dict) else raw_target)
        command["target"] = command["device_id"]
        
        prompt = f"""Evaluate the safety of the following power grid command:

Action: {command.get('action', 'unknown')}
Target: {command.get('target', 'unknown')}
Parameters: {json.dumps(command.get('parameters', {}), default=str)}

Grid Context:
{command.get('context', 'No context provided')}

Respond ONLY with a JSON object (no markdown):
{{"safe": true/false, "risk_level": "LOW|MEDIUM|HIGH|CRITICAL", "reasoning": "...", "conditions": [...]}}"""

        try:
            raw = await self.llm.complete(prompt, temperature=0.1)
            # Try to parse JSON from the response
            # Strip any markdown code fences
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean
                clean = clean.rsplit("```", 1)[0] if "```" in clean else clean
                clean = clean.strip()

            lower_clean = clean.lower()
            if lower_clean == "safe" or lower_clean.startswith("safe\n"):
                result = {"safe": True, "risk_level": "LOW", "reasoning": "Action evaluated as safe.", "conditions": []}
            elif lower_clean.startswith("unsafe"):
                result = {"safe": False, "risk_level": "HIGH", "reasoning": f"Action blocked by safeguard model: {clean}", "conditions": []}
            else:
                result = json.loads(clean)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Guardian response not parseable: %s — raw: %s", e, raw[:200] if 'raw' in dir() else "N/A")
            result = {
                "safe": False,
                "risk_level": "HIGH",
                "reasoning": f"Guardian could not evaluate: {e}",
                "conditions": ["Manual review required"],
            }

        entry = {"command": command, "result": result}
        self._validation_log.append(entry)
        logger.info(
            "[Guardian] %s %s → safe=%s risk=%s",
            command.get("action"), command.get("target"),
            result.get("safe"), result.get("risk_level"),
        )
        
        # Publish event
        try:
            from datetime import datetime
            event_payload = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "command": command,
                "safe": result.get("safe", False),
                "risk_level": result.get("risk_level", "HIGH"),
                "reasoning": result.get("reasoning", ""),
                "conditions": result.get("conditions", [])
            }
            # Try to publish if there's a running event loop
            loop = asyncio.get_running_loop()
            loop.create_task(event_bus.publish("guardian_event", event_payload))
        except RuntimeError:
            # We might not be in an event loop (e.g., synchronous tests)
            pass
        except Exception as e:
            logger.error(f"Failed to publish guardian_event: {e}")

        return result

    def get_validation_log(self) -> list[dict]:
        return self._validation_log[-50:]
