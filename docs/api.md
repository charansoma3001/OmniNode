# API Reference

This section documents the public Python APIs, REST endpoints, and WebSocket interfaces exposed by the OmniNode backend.

---

## REST Endpoints

All REST endpoints are served by the FastAPI MCP Registry at `http://localhost:8000`.

### `POST /register`
Register a new MCP server (sensor, actuator, or coordinator) with the registry.

**Request Body:**
```json
{
  "server_id": "sensor_voltage_zone1_abc123",
  "name": "Voltage Sensor (zone1)",
  "type": "sensor",
  "tools": [
    {
      "name": "read_sensor",
      "description": "Read a voltage sensor value",
      "inputSchema": { "type": "object", "properties": { "sensor_id": { "type": "string" } } }
    }
  ]
}
```

**Response:** `200 OK`

### `GET /tools`
Discover all registered MCP tools across all servers. Used by the Strategic Agent during startup.

**Response:**
```json
{
  "tools": [
    {
      "name": "voltage_sensor_zone1_read_sensor",
      "description": "Read a voltage sensor value",
      "server_id": "sensor_voltage_zone1_abc123",
      "inputSchema": { "..." }
    }
  ]
}
```

### `GET /servers`
List all registered MCP servers and their metadata.

### `POST /scenarios/{scenario_name}`
Trigger a pre-defined fault injection scenario on the power grid simulation.

**Available scenarios:** `peak_load`, `cyber_attack`, `generator_trip`, `cascade_failure`

---

## WebSocket Endpoints

All WebSocket endpoints are defined in `src/api/websocket.py` and use the `EventBus` for message delivery.

### `/ws/grid_state`
Streams real-time grid topology updates to the frontend.

**Direction:** Server → Client

**EventBus topic:** `grid_state`

**Payload:**
```json
{
  "timestamp": "2026-02-22T03:00:00.000Z",
  "nodes": [
    { "id": "bus_0", "position": { "x": 100, "y": 50 }, "data": { "label": "Bus 0", "voltage_pu": 1.02, "zone": "zone1", "status": "normal" } }
  ],
  "edges": [
    { "id": "line_0_1", "source": "bus_0", "target": "bus_1", "data": { "loading_percent": 45.3 } }
  ],
  "zone_health": { "zone1": "healthy", "zone2": "warning", "zone3": "critical" },
  "violations": [
    { "type": "voltage_low", "bus": 21, "value": 0.93, "limit": 0.95 }
  ]
}
```

### `/ws/agent_logs`
Streams Strategic Agent reasoning steps, tool calls, and tool results.

**Direction:** Server → Client

**EventBus topic:** `agent_log`

**Payload:**
```json
{
  "timestamp": "2026-02-22T03:01:00.000Z",
  "level": "tool_call",
  "message": "CALLING: generator_actuator_system_control(device_id=gen_0, action=ramp, delta_mw=5)"
}
```

**Log levels:**

| Level | Meaning |
|---|---|
| `info` | General reasoning or status updates |
| `warning` | Escalation notifications |
| `tool_call` | An MCP tool is being invoked |
| `decision` | A tool call has completed with a result |

### `/ws/guardian_events`
Streams Safety Guardian intercept results (approvals and blocks).

**Direction:** Server → Client

**EventBus topic:** `guardian_event`

**Payload:**
```json
{
  "timestamp": "2026-02-22T03:01:05.000Z",
  "command": { "action": "reduce", "device_id": "load_29", "parameters": { "reduction_kw": 10 } },
  "safe": true,
  "risk_level": "LOW",
  "reasoning": "Action evaluated as safe.",
  "conditions": []
}
```

### `/ws/commands`
Bidirectional WebSocket for receiving commands from the War Room UI.

**Direction:** Client → Server

**Payload (Natural Language Query):**
```json
{
  "action": "nl_query",
  "payload": "Why is Zone 3 showing critical warnings?"
}
```

**Payload (Scenario Trigger):**
```json
{
  "action": "trigger_scenario",
  "payload": "cyber_attack"
}
```

**Behaviour:**

- In **Real Mode** (`DEMO_MODE=0`): NL queries are routed to `StrategicAgent.query()`. Scenario triggers call `run_scenario()` on the live simulation, then immediately broadcast the updated grid state.
- In **Demo Mode** (`DEMO_MODE=1`): Commands are acknowledged via `agent_log` and trigger pre-scripted mock event sequences (see `src/api/mock_stream.py`).

---

## Python API — Core Classes

### EventBus

::: src.api.event_bus

### Strategic Agent

::: src.strategic.agent

### Safety Guardian

::: src.strategic.guardian

### LLM Client

::: src.common.llm_client

### Power Grid Simulation

::: src.simulation.power_grid

### Monitoring Loop

::: src.strategic.monitor

---

## Python API — Coordination Layer

### Zone Coordinator

::: src.coordination.zone_coordinator

### Zone Audit Logger

::: src.coordination.audit

---

## Python API — Physical Layer

### Base Sensor

::: src.physical.base_sensor

### Base Actuator

::: src.physical.base_actuator

---

## Python API — Domain Adapters

### Base Adapter

::: src.domains.base_adapter

### Power Grid Adapter

::: src.domains.power_grid
