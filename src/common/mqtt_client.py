"""Async MQTT client wrapper with MCP topic conventions."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

import paho.mqtt.client as mqtt

from src.common.config import get_settings

logger = logging.getLogger(__name__)

# Topic convention:  mcp/{layer}/{zone}/{device_type}/{device_id}/{action}
TOPIC_PREFIX = "mcp"


def build_topic(*parts: str) -> str:
    """Build an MQTT topic from path segments."""
    return "/".join([TOPIC_PREFIX, *parts])


class MQTTClient:
    """Async-friendly wrapper around paho-mqtt for MCP message transport."""

    def __init__(self, client_id: str | None = None):
        settings = get_settings()
        self._host = settings.mqtt_broker_host
        self._port = settings.mqtt_broker_port
        self._client_id = client_id or settings.mqtt_client_id
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._client_id,
        )
        self._subscriptions: dict[str, list[Callable[[str, dict], Awaitable[None]]]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connected = asyncio.Event()

        # Wire up paho callbacks
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to the MQTT broker (non-blocking)."""
        self._loop = asyncio.get_running_loop()
        self._client.connect_async(self._host, self._port)
        self._client.loop_start()
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("MQTT connection timed out — continuing without broker")

    async def disconnect(self) -> None:
        """Gracefully disconnect."""
        self._client.loop_stop()
        self._client.disconnect()
        self._connected.clear()
        logger.info("MQTT disconnected")

    # ------------------------------------------------------------------
    # Pub / Sub
    # ------------------------------------------------------------------

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """Publish a JSON payload to an MQTT topic."""
        data = json.dumps(payload, default=str)
        self._client.publish(topic, data, qos=qos, retain=retain)
        logger.debug("Published to %s: %s", topic, data[:200])

    async def subscribe(
        self,
        topic: str,
        callback: Callable[[str, dict], Awaitable[None]],
        qos: int = 1,
    ) -> None:
        """Subscribe to an MQTT topic with an async callback."""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
            self._client.subscribe(topic, qos=qos)
        self._subscriptions[topic].append(callback)
        logger.info("Subscribed to %s", topic)

    # ------------------------------------------------------------------
    # Paho callbacks (run on paho's thread – schedule onto asyncio loop)
    # ------------------------------------------------------------------

    def _on_connect(self, client: Any, userdata: Any, flags: Any, rc: Any, properties: Any = None) -> None:
        logger.info("MQTT connected (rc=%s)", rc)
        if self._loop:
            self._loop.call_soon_threadsafe(self._connected.set)
        # Re-subscribe on reconnect
        for topic in self._subscriptions:
            client.subscribe(topic)

    def _on_message(self, client: Any, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Non-JSON message on %s", msg.topic)
            return

        callbacks = self._subscriptions.get(msg.topic, [])
        # Also check wildcard subscriptions
        for pattern, cbs in self._subscriptions.items():
            if mqtt.topic_matches_sub(pattern, msg.topic):
                callbacks = cbs
                break

        if self._loop:
            for cb in callbacks:
                asyncio.run_coroutine_threadsafe(cb(msg.topic, payload), self._loop)

    def _on_disconnect(self, client: Any, userdata: Any, rc: Any, properties: Any = None) -> None:
        logger.warning("MQTT disconnected (rc=%s)", rc)
        self._connected.clear()
