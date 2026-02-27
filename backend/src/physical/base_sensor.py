"""Base class for Sensor MCP Servers.

Each sensor type extends this to expose standardized MCP tools:
- read_sensor, read_sensors_batch, query_history, set_threshold, get_metadata
"""

from __future__ import annotations

import asyncio
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
    SensorReading,
    SafetyLevel,
    ToolDescriptor,
)
from src.simulation.power_grid import PowerGridSimulation

logger = logging.getLogger(__name__)


class BaseSensorServer(ABC):
    """Abstract MCP server for a category of sensors.

    Subclasses implement `_read_value()` and `_get_sensor_ids()`.
    """

    def __init__(
        self,
        sensor_type: str,
        unit: str,
        grid: PowerGridSimulation,
        zone: str = "system",
    ):
        self.sensor_type = sensor_type
        self.unit = unit
        self.grid = grid
        self.zone = zone
        self.server_id = f"sensor_{sensor_type}_{zone}_{uuid.uuid4().hex[:8]}"
        self.name = f"{sensor_type.title()} Sensor ({zone})"
        self._thresholds: dict[str, dict] = {}

        # MCP Server
        self.mcp = Server(self.name)
        self._register_tools()

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def _read_value(self, sensor_id: str) -> float:
        """Read current value for a specific sensor."""
        ...

    @abstractmethod
    def _get_sensor_ids(self) -> list[str]:
        """Return list of all sensor IDs managed by this server."""
        ...

    @abstractmethod
    def _get_sensor_metadata(self, sensor_id: str) -> dict:
        """Return metadata for a specific sensor."""
        ...

    # ------------------------------------------------------------------
    # MCP Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        @self.mcp.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="read_sensor",
                    description=f"Read current {self.sensor_type} sensor value",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sensor_id": {"type": "string", "description": "Sensor identifier"}
                        },
                        "required": ["sensor_id"],
                    },
                ),
                Tool(
                    name="read_sensors_batch",
                    description=f"Read multiple {self.sensor_type} sensors at once",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sensor_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of sensor IDs",
                            }
                        },
                        "required": ["sensor_ids"],
                    },
                ),
                Tool(
                    name="list_sensors",
                    description=f"List all available {self.sensor_type} sensors",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="set_threshold",
                    description=f"Set alert threshold for a {self.sensor_type} sensor",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sensor_id": {"type": "string"},
                            "min_value": {"type": "number", "description": "Minimum acceptable value"},
                            "max_value": {"type": "number", "description": "Maximum acceptable value"},
                        },
                        "required": ["sensor_id"],
                    },
                ),
                Tool(
                    name="get_metadata",
                    description=f"Get metadata for a {self.sensor_type} sensor",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sensor_id": {"type": "string"}
                        },
                        "required": ["sensor_id"],
                    },
                ),
            ]

        @self.mcp.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            import json
            try:
                if name == "read_sensor":
                    result = self._handle_read(arguments["sensor_id"])
                elif name == "read_sensors_batch":
                    result = self._handle_batch_read(arguments["sensor_ids"])
                elif name == "list_sensors":
                    result = {"sensors": self._get_sensor_ids(), "type": self.sensor_type, "zone": self.zone}
                elif name == "set_threshold":
                    result = self._handle_set_threshold(arguments)
                elif name == "get_metadata":
                    result = self._get_sensor_metadata(arguments["sensor_id"])
                else:
                    result = {"error": f"Unknown tool: {name}"}
                return [TextContent(type="text", text=json.dumps(result, default=str))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def _handle_read(self, sensor_id: str) -> dict:
        value = self._read_value(sensor_id)
        reading = SensorReading(
            sensor_id=sensor_id,
            sensor_type=self.sensor_type,
            zone=self.zone,
            value=value,
            unit=self.unit,
        )
        # Check thresholds
        alert = self._check_threshold(sensor_id, value)
        result = reading.model_dump(mode="json")
        if alert:
            result["alert"] = alert
        return result

    def _handle_batch_read(self, sensor_ids: list[str]) -> dict:
        readings = []
        for sid in sensor_ids:
            readings.append(self._handle_read(sid))
        return {"readings": readings, "count": len(readings)}

    def _handle_set_threshold(self, args: dict) -> dict:
        sensor_id = args["sensor_id"]
        self._thresholds[sensor_id] = {
            "min": args.get("min_value"),
            "max": args.get("max_value"),
        }
        return {"status": "threshold_set", "sensor_id": sensor_id, "threshold": self._thresholds[sensor_id]}

    def _check_threshold(self, sensor_id: str, value: float) -> dict | None:
        threshold = self._thresholds.get(sensor_id)
        if not threshold:
            return None
        if threshold.get("min") is not None and value < threshold["min"]:
            return {"type": "below_minimum", "value": value, "limit": threshold["min"]}
        if threshold.get("max") is not None and value > threshold["max"]:
            return {"type": "above_maximum", "value": value, "limit": threshold["max"]}
        return None

    # ------------------------------------------------------------------
    # Registry registration
    # ------------------------------------------------------------------

    def get_registration(self) -> MCPServerRegistration:
        """Build the registry registration payload."""
        tools = [
            ToolDescriptor(name="read_sensor", description=f"Read {self.sensor_type} value", safety_level=SafetyLevel.READ_ONLY),
            ToolDescriptor(name="read_sensors_batch", description=f"Batch read {self.sensor_type}", safety_level=SafetyLevel.READ_ONLY),
            ToolDescriptor(name="list_sensors", description=f"List {self.sensor_type} sensors", safety_level=SafetyLevel.READ_ONLY),
            ToolDescriptor(name="set_threshold", description=f"Set {self.sensor_type} alert threshold", safety_level=SafetyLevel.LOW_RISK),
            ToolDescriptor(name="get_metadata", description=f"Get {self.sensor_type} sensor metadata", safety_level=SafetyLevel.READ_ONLY),
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
        """Register this sensor server with the MCP registry."""
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
        """Start the MCP server via stdio transport."""
        await self.register_with_registry()
        async with stdio_server() as (read, write):
            await self.mcp.run(read, write, self.mcp.create_initialization_options())
