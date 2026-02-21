# Configuration Guide

The project leverages both environment variables and on-disk JSON data stores to share state seamlessly between the simulation, the MCP registry, and the various operational agents.

## Environment Variables (`.env`)

The system requires an environment file (`.env`) placed in the root directory. Copy the `.env.example` file to start.

| Variable | Description | Default |
|----------|-------------|---------|
| `STRATEGIC_MODEL` | The LLM model name used for the top-level Strategic Agent. | `llama3.1:latest` |

| `LLM_API_KEY` | Key for authentication (can be anything if local). | `ollama` |
| `LLM_BASE_URL` | Endpoint for the OpenAI-compatible completion API. | `http://localhost:11434` |
| `LLM_CONTEXT_WINDOW` | Maximum tokens allowed for the context window. | `8192` |

## State Management Files

### `grid_state.json`
This is the central "digital twin" storage file updated continuously by the `PowerGridAdapter`. 
It holds the latest snapshot of the physical simulation.

**Structure:**
```json
{
  "timestamp": "2023-10-24T12:00:00Z",
  "buses": [
    {
      "id": 0,
      "zone": "Zone 1",
      "voltage_pu": 1.02,
      "type": "slack"
    }
  ],
  "lines": [
    {
      "id": 0,
      "from_bus": 0,
      "to_bus": 1,
      "loading_percent": 45.3,
      "status": "closed"
    }
  ],
  "generators": [...],
  "loads": [...]
}
```

### `registry_store.json`
This file is managed exclusively by the `mcp-registry` (FastAPI). It holds a list of all currently active MCP servers (sensors, actuators, coordinators).

**Structure:**
```json
{
  "servers": {
    "voltage_sensor_zone1": {
      "type": "sensor",
      "url": "http://localhost:8001/mcp",
      "status": "online",
      "last_heartbeat": "2023-10-24T12:00:05Z"
    },
    ...
  }
}
```
Agents query this file (via the registry API) to perform dynamic tool discovery.
