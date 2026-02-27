"""Shared Pydantic models used across layers."""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Registry models
# ---------------------------------------------------------------------------

class SafetyLevel(str, enum.Enum):
    """Safety classification for MCP tools."""
    READ_ONLY = "read_only"          # Sensors – no side effects
    LOW_RISK = "low_risk"            # Non-critical actuations
    MEDIUM_RISK = "medium_risk"      # Significant state changes
    HIGH_RISK = "high_risk"          # Safety-critical actuations
    EMERGENCY = "emergency"          # Emergency procedures


class ServerStatus(str, enum.Enum):
    ACTIVE = "active"
    STALE = "stale"
    OFFLINE = "offline"


class ToolDescriptor(BaseModel):
    """Metadata for a single MCP tool."""
    name: str
    description: str
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    safety_level: SafetyLevel = SafetyLevel.READ_ONLY


class MCPServerRegistration(BaseModel):
    """Registration payload for an MCP server."""
    server_id: str
    name: str
    layer: str  # "physical", "coordination", "strategic"
    domain: str = "power_grid"
    zone: str | None = None
    transport: str = "stdio"  # "stdio" | "sse" | "mqtt"
    endpoint: str = ""
    tools: list[ToolDescriptor] = Field(default_factory=list)
    status: ServerStatus = ServerStatus.ACTIVE
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Sensor / Actuator models
# ---------------------------------------------------------------------------

class SensorReading(BaseModel):
    """A single sensor measurement."""
    sensor_id: str
    sensor_type: str
    zone: str
    value: float
    unit: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    quality: str = "good"  # "good" | "suspect" | "bad"


class ActuatorCommand(BaseModel):
    """A command sent to an actuator."""
    device_id: str
    device_type: str
    zone: str
    action: str
    parameters: dict = Field(default_factory=dict)
    validated: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ActuatorResponse(BaseModel):
    """Response from an actuator after command execution."""
    device_id: str
    action: str
    success: bool
    message: str = ""
    previous_state: dict = Field(default_factory=dict)
    new_state: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ViolationEvent(BaseModel):
    """A constraint violation detected by the monitoring system."""
    violation_id: str
    violation_type: str  # "voltage", "thermal", "frequency", "stability"
    zone: str
    severity: str  # "warning", "alarm", "critical"
    affected_components: list[str] = Field(default_factory=list)
    current_value: float
    limit_value: float
    unit: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentDecision(BaseModel):
    """Record of a decision made by the strategic agent."""
    decision_id: str
    trigger: str  # What caused this decision
    reasoning: str
    actions_taken: list[ActuatorCommand] = Field(default_factory=list)
    outcome: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
