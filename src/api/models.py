"""Pydantic models for WebSocket payloads."""

from __future__ import annotations

from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field

class GridStatePayload(BaseModel):
    """Payload for real-time grid state broadcast."""
    timestamp: str
    total_generation_mw: float
    total_load_mw: float
    total_losses_mw: float
    frequency_hz: float
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    zone_health: dict[str, str] = Field(default_factory=dict)
    violations: list[dict[str, Any]] = Field(default_factory=list)

class AgentLogPayload(BaseModel):
    """Payload for strategic agent reasoning steps."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    level: str = "info"  # info, warning, error, analyzing, tool_call, tool_result, decision
    message: str
    data: dict[str, Any] | None = None

class GuardianEventPayload(BaseModel):
    """Payload for safety guardian intercepts."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    command: dict[str, Any]
    safe: bool
    risk_level: str
    reasoning: str
    conditions: list[str] = Field(default_factory=list)
