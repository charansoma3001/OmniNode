"""MQTT-to-MCP proxy for resource-constrained IoT devices."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.common.mqtt_client import MQTTClient, build_topic

logger = logging.getLogger(__name__)


class MQTTProxy:
    """Bridges raw MQTT device data into MCP tools.

    Subscribes to MQTT topics for IoT devices, caches latest values,
    and exposes them as MCP read tools.
    """

    def __init__(self, mqtt: MQTTClient, ttl_seconds: float = 30.0):
        self.mqtt = mqtt
        self.ttl = ttl_seconds
        self._cache: dict[str, dict] = {}  # device_id -> {value, timestamp}

        self.mcp = Server("MQTT IoT Proxy")
        self._register_tools()

    def _register_tools(self) -> None:
        @self.mcp.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="read_iot_device",
                    description="Read the latest cached value from an IoT device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string"}
                        },
                        "required": ["device_id"],
                    },
                ),
                Tool(
                    name="list_iot_devices",
                    description="List all IoT devices with cached data",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="send_iot_command",
                    description="Send a command to an IoT device via MQTT",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string"},
                            "command": {"type": "string"},
                            "parameters": {"type": "object"},
                        },
                        "required": ["device_id", "command"],
                    },
                ),
            ]

        @self.mcp.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            if name == "read_iot_device":
                result = self._read_cached(arguments["device_id"])
            elif name == "list_iot_devices":
                result = self._list_devices()
            elif name == "send_iot_command":
                result = await self._send_command(arguments)
            else:
                result = {"error": f"Unknown tool: {name}"}
            return [TextContent(type="text", text=json.dumps(result, default=str))]

    async def start(self) -> None:
        """Connect to MQTT and subscribe to device topics."""
        await self.mqtt.connect()
        await self.mqtt.subscribe(
            build_topic("iot", "#"),
            self._on_device_message,
        )
        logger.info("MQTT Proxy started, listening on mcp/iot/#")

    async def _on_device_message(self, topic: str, payload: dict) -> None:
        """Cache incoming device messages."""
        # Extract device_id from topic: mcp/iot/{device_id}/data
        parts = topic.split("/")
        if len(parts) >= 3:
            device_id = parts[2]
            self._cache[device_id] = {
                "data": payload,
                "timestamp": datetime.utcnow().isoformat(),
                "topic": topic,
            }

    def _read_cached(self, device_id: str) -> dict:
        entry = self._cache.get(device_id)
        if not entry:
            return {"error": f"No data for device: {device_id}"}

        # Check TTL
        ts = datetime.fromisoformat(entry["timestamp"])
        age = (datetime.utcnow() - ts).total_seconds()
        return {
            "device_id": device_id,
            "data": entry["data"],
            "timestamp": entry["timestamp"],
            "age_seconds": round(age, 1),
            "stale": age > self.ttl,
        }

    def _list_devices(self) -> dict:
        devices = []
        for did, entry in self._cache.items():
            ts = datetime.fromisoformat(entry["timestamp"])
            age = (datetime.utcnow() - ts).total_seconds()
            devices.append({
                "device_id": did,
                "last_seen": entry["timestamp"],
                "age_seconds": round(age, 1),
                "stale": age > self.ttl,
            })
        return {"devices": devices, "count": len(devices)}

    async def _send_command(self, args: dict) -> dict:
        device_id = args["device_id"]
        command = args["command"]
        parameters = args.get("parameters", {})
        topic = build_topic("iot", device_id, "command")
        await self.mqtt.publish(topic, {
            "command": command,
            "parameters": parameters,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return {"sent": True, "device_id": device_id, "command": command, "topic": topic}

    async def run(self) -> None:
        await self.start()
        async with stdio_server() as (read, write):
            await self.mcp.run(read, write, self.mcp.create_initialization_options())
