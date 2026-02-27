"""Base class for Actuator MCP Servers.

Each actuator type extends this to expose standardized MCP tools:
- control, adjust_setpoint, validate_action, emergency_shutdown, get_status
"""

from __future__ import annotations

import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.common.config import get_settings
from src.common.models import (
    MCPServerRegistration,
    ActuatorCommand,
    ActuatorResponse,
    SafetyLevel,
    ToolDescriptor,
)
from src.simulation.power_grid import PowerGridSimulation

logger = logging.getLogger(__name__)


class BaseActuatorServer(ABC):
    """Abstract MCP server for a category of actuators.

    Subclasses implement `_execute_action()`, `_get_device_ids()`, `_get_status()`.
    All actuations are validated against the simulation before execution.
    """

    def __init__(
        self,
        device_type: str,
        grid: PowerGridSimulation,
        zone: str = "system",
    ):
        self.device_type = device_type
        self.grid = grid
        self.zone = zone
        self.server_id = f"actuator_{device_type}_{zone}_{uuid.uuid4().hex[:8]}"
        self.name = f"{device_type.replace('_', ' ').title()} Actuator ({zone})"

        # MCP Server
        self.mcp = Server(self.name)
        self._register_tools()

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def _execute_action(self, device_id: str, action: str, parameters: dict) -> ActuatorResponse:
        """Execute a control action on a device."""
        ...

    @abstractmethod
    def _get_device_ids(self) -> list[str]:
        """Return list of all device IDs managed by this server."""
        ...

    @abstractmethod
    def _get_device_status(self, device_id: str) -> dict:
        """Return current status of a device."""
        ...

    @abstractmethod
    def _validate_in_sandbox(self, device_id: str, action: str, parameters: dict) -> dict:
        """Validate an action using the simulation sandbox."""
        ...

    # ------------------------------------------------------------------
    # MCP Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        # Build action enum from subclass if available
        valid_actions = getattr(self, "_valid_actions", None)
        action_enum = valid_actions or []
        action_description = (
            f"Action to perform. Valid values: {', '.join(action_enum)}"
            if action_enum
            else "Action to perform"
        )
        action_schema: dict = {"type": "string", "description": action_description}
        if action_enum:
            action_schema["enum"] = action_enum

        @self.mcp.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="control",
                    description=(
                        f"Execute a control action on a {self.device_type}. "
                        + (f"Valid actions: {', '.join(action_enum)}." if action_enum else "")
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string", "description": "Device identifier"},
                            "action": action_schema,
                            "parameters": {"type": "object", "description": "Action parameters"},
                            "validate": {"type": "boolean", "description": "Run sandbox validation first", "default": True},
                        },
                        "required": ["device_id", "action"],
                    },
                ),
                Tool(
                    name="validate_action",
                    description=f"Validate a {self.device_type} action in sandbox without executing",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string"},
                            "action": {"type": "string"},
                            "parameters": {"type": "object"},
                        },
                        "required": ["device_id", "action"],
                    },
                ),
                Tool(
                    name="get_status",
                    description=f"Get current status of a {self.device_type}",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string"}
                        },
                        "required": ["device_id"],
                    },
                ),
                Tool(
                    name="list_devices",
                    description=f"List all available {self.device_type} devices",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="emergency_shutdown",
                    description=f"Emergency shutdown for {self.device_type} in a zone",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "zone_id": {"type": "string", "description": "Zone to shut down"}
                        },
                        "required": ["zone_id"],
                    },
                ),
            ]

        @self.mcp.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            try:
                if name == "control":
                    result = self._handle_control(arguments)
                elif name == "validate_action":
                    result = self._handle_validate(arguments)
                elif name == "get_status":
                    result = self._get_device_status(arguments["device_id"])
                elif name == "list_devices":
                    result = {"devices": self._get_device_ids(), "type": self.device_type, "zone": self.zone}
                elif name == "emergency_shutdown":
                    result = self._handle_emergency(arguments["zone_id"])
                else:
                    result = {"error": f"Unknown tool: {name}"}
                return [TextContent(type="text", text=json.dumps(result, default=str))]
            except Exception as e:
                logger.error("Error in %s.%s: %s", self.device_type, name, e)
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def _handle_control(self, args: dict) -> dict:
        raw_device = args.get("device_id", "")
        device_id = str(raw_device.get("id", raw_device) if isinstance(raw_device, dict) else raw_device)
        
        raw_action = args.get("action", "")
        if not raw_action:
            for k, v in args.items():
                if isinstance(v, str) and v.lower() in {"open", "close", "activate", "deactivate", "scale", "shed", "restore", "charge", "discharge", "set_output", "ramp", "emergency_stop"}:
                    raw_action = v
                    break
        action = str(raw_action.get("operation", raw_action.get("action", raw_action)) if isinstance(raw_action, dict) else raw_action)
        
        parameters = args.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}
            
        validate = args.get("validate", True)

        # Safety: validate first
        if validate:
            validation = self._validate_in_sandbox(device_id, action, parameters)
            if not validation.get("safe", False):
                return {
                    "executed": False,
                    "reason": "Validation failed — action would cause violations",
                    "validation": validation,
                }

        # Execute
        response = self._execute_action(device_id, action, parameters)
        return response.model_dump(mode="json")

    def _handle_validate(self, args: dict) -> dict:
        raw_device = args.get("device_id", "")
        device_id = str(raw_device.get("id", raw_device) if isinstance(raw_device, dict) else raw_device)
        
        raw_action = args.get("action", "")
        if not raw_action:
            for k, v in args.items():
                if isinstance(v, str) and v.lower() in {"open", "close", "activate", "deactivate", "scale", "shed", "restore", "charge", "discharge", "set_output", "ramp", "emergency_stop"}:
                    raw_action = v
                    break
        action = str(raw_action.get("operation", raw_action.get("action", raw_action)) if isinstance(raw_action, dict) else raw_action)
        
        parameters = args.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}

        return self._validate_in_sandbox(device_id, action, parameters)

    def _handle_emergency(self, zone_id: str) -> dict:
        """Default emergency: disable all devices in zone."""
        devices = self._get_device_ids()
        results = []
        for did in devices:
            try:
                resp = self._execute_action(did, "emergency_stop", {})
                results.append(resp.model_dump(mode="json"))
            except Exception as e:
                results.append({"device_id": did, "error": str(e)})
        return {"zone": zone_id, "emergency": True, "results": results}

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def get_registration(self) -> MCPServerRegistration:
        tools = [
            ToolDescriptor(name="control", description=f"Control {self.device_type}", safety_level=SafetyLevel.MEDIUM_RISK),
            ToolDescriptor(name="validate_action", description=f"Validate {self.device_type} action", safety_level=SafetyLevel.READ_ONLY),
            ToolDescriptor(name="get_status", description=f"Get {self.device_type} status", safety_level=SafetyLevel.READ_ONLY),
            ToolDescriptor(name="list_devices", description=f"List {self.device_type} devices", safety_level=SafetyLevel.READ_ONLY),
            ToolDescriptor(name="emergency_shutdown", description="Emergency zone shutdown", safety_level=SafetyLevel.EMERGENCY),
        ]
        return MCPServerRegistration(
            server_id=self.server_id,
            name=self.name,
            layer="physical",
            domain="power_grid",
            zone=self.zone,
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
