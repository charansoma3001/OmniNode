"""FastAPI WebSocket endpoints for the War Room frontend."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.event_bus import event_bus
from src.strategic.agent import StrategicAgent
from src.simulation.power_grid import PowerGridSimulation

logger = logging.getLogger(__name__)

router = APIRouter()

active_agent: StrategicAgent | None = None
active_grid: PowerGridSimulation | None = None

@router.websocket("/ws/grid_state")
async def websocket_grid_state(websocket: WebSocket) -> None:
    """Stream real-time grid state updates to the UI."""
    await websocket.accept()
    logger.info("WebSocket connected: /ws/grid_state")
    try:
        async for message in event_bus.subscribe("grid_state"):
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(message)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: /ws/grid_state")
    except Exception as e:
        logger.error(f"WebSocket error in /ws/grid_state: {e}")

@router.websocket("/ws/agent_logs")
async def websocket_agent_logs(websocket: WebSocket) -> None:
    """Stream strategic agent reasoning and tool calls."""
    await websocket.accept()
    logger.info("WebSocket connected: /ws/agent_logs")
    try:
        async for message in event_bus.subscribe("agent_log"):
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(message)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: /ws/agent_logs")
    except Exception as e:
        logger.error(f"WebSocket error in /ws/agent_logs: {e}")

@router.websocket("/ws/guardian_events")
async def websocket_guardian_events(websocket: WebSocket) -> None:
    """Stream safety guardian intercepts and rule evaluations."""
    await websocket.accept()
    logger.info("WebSocket connected: /ws/guardian_events")
    try:
        async for message in event_bus.subscribe("guardian_event"):
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(message)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: /ws/guardian_events")
    except Exception as e:
        logger.error(f"WebSocket error in /ws/guardian_events: {e}")

@router.websocket("/ws/commands")
async def websocket_commands(websocket: WebSocket) -> None:
    """Bidirectional WebSocket for receiving commands from the UI."""
    await websocket.accept()
    logger.info("WebSocket connected: /ws/commands")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                command = json.loads(data)
                # In a full implementation, we would route this to the StrategicAgent
                # or scenario executor. For now, we just acknowledge receipt.
                action = command.get("action")
                payload = command.get("payload")
                
                logger.info(f"Received UI command: {action} -> {payload}")
                
                if os.environ.get("DEMO_MODE", "1") == "0" and active_agent and active_grid:
                    # REAL MODE
                    if action == "nl_query":
                        logger.info(f"Routing natural language query to agent: {payload}")
                        # Running in background to not block WS receive loop
                        asyncio.create_task(active_agent.query(payload))
                        
                    elif action == "trigger_scenario":
                        from src.simulation.scenarios import run_scenario
                        logger.info(f"Triggering real scenario: {payload}")
                        run_scenario(payload, active_grid, persist=True)
                        asyncio.create_task(event_bus.publish("grid_state", active_grid.get_state()))
                        asyncio.create_task(event_bus.publish("agent_log", {
                            "level": "warning",
                            "message": f"CRITICAL: System administrator triggered scenario '{payload}'"
                        }))
                else:
                    # MOCK MODE
                    await event_bus.publish("agent_log", {
                        "level": "info",
                        "message": f"Received command from UI: {action} {payload}"
                    })
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from UI: {data}")
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: /ws/commands")
    except Exception as e:
        logger.error(f"WebSocket error in /ws/commands: {e}")
