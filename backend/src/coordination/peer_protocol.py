"""Inter-zone coordination protocol."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from src.common.mqtt_client import MQTTClient, build_topic

logger = logging.getLogger(__name__)


class PeerProtocol:
    """MQTT-based inter-zone coordination protocol.

    Zones publish their state and negotiate boundary conditions
    (tie-line power flows) with neighboring zones.
    """

    def __init__(self, zone_id: str, mqtt: MQTTClient):
        self.zone_id = zone_id
        self.mqtt = mqtt
        self._peer_states: dict[str, dict] = {}
        self._pending_negotiations: dict[str, asyncio.Future] = {}

    async def start(self) -> None:
        """Subscribe to coordination topics."""
        await self.mqtt.subscribe(
            build_topic("coordination", "#"),
            self._on_coordination_message,
        )
        logger.info("Peer protocol started for %s", self.zone_id)

    async def publish_state(self, state: dict) -> None:
        """Broadcast zone state to peers."""
        await self.mqtt.publish(
            build_topic("coordination", self.zone_id, "state"),
            {
                "zone_id": self.zone_id,
                "timestamp": datetime.utcnow().isoformat(),
                "state": state,
            },
        )

    async def request_coordination(self, peer_zone: str, request: dict) -> dict:
        """Send a coordination request to a peer zone."""
        request_id = f"{self.zone_id}_{peer_zone}_{datetime.utcnow().timestamp()}"
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending_negotiations[request_id] = future

        await self.mqtt.publish(
            build_topic("coordination", peer_zone, "request"),
            {
                "request_id": request_id,
                "from_zone": self.zone_id,
                "to_zone": peer_zone,
                "request": request,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        try:
            result = await asyncio.wait_for(future, timeout=10.0)
            return result
        except asyncio.TimeoutError:
            return {"error": "Coordination request timed out", "peer": peer_zone}
        finally:
            self._pending_negotiations.pop(request_id, None)

    async def _on_coordination_message(self, topic: str, payload: dict) -> None:
        """Handle incoming coordination messages."""
        parts = topic.split("/")
        if len(parts) < 4:
            return

        target_zone = parts[2]
        msg_type = parts[3]

        if msg_type == "state" and target_zone != self.zone_id:
            self._peer_states[target_zone] = payload.get("state", {})
        elif msg_type == "response":
            request_id = payload.get("request_id")
            if request_id in self._pending_negotiations:
                self._pending_negotiations[request_id].set_result(payload)

    def get_peer_states(self) -> dict[str, dict]:
        """Return cached states of peer zones."""
        return dict(self._peer_states)
