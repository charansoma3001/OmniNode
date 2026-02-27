"""Simple asynchronous Event Bus for publishing real-time events to WebSockets."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class EventBus:
    """Singleton event bus for pub/sub communication."""
    
    _instance: EventBus | None = None
    
    def __new__(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._channels = defaultdict(list)
            cls._instance._lock = asyncio.Lock()
        return cls._instance
        
    def __init__(self) -> None:
        # Prevent re-initialization since __init__ is called on every instantiation
        pass

    async def publish(self, channel: str, message: dict | str) -> None:
        """Publish a message to all subscribers of a channel."""
        if isinstance(message, dict) and "timestamp" not in message:
            from datetime import datetime
            message["timestamp"] = datetime.now().isoformat()
            
        async with self._instance._lock:
            queues = self._instance._channels[channel][:] # Copy the list of queues
        
        if not queues:
            return
            
        for queue in queues:
            try:
                # Use put_nowait to avoid blocking the publisher
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue for channel '{channel}' is full. Dropping message.")

    async def subscribe(self, channel: str) -> AsyncGenerator[dict | str, None]:
        """Subscribe to a channel and yield messages as they arrive."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        
        async with self._instance._lock:
            self._instance._channels[channel].append(queue)
            
        try:
            while True:
                message = await queue.get()
                yield message
                queue.task_done()
        except asyncio.CancelledError:
            pass
        finally:
            async with self._instance._lock:
                if queue in self._instance._channels[channel]:
                    self._instance._channels[channel].remove(queue)
            
event_bus = EventBus()
