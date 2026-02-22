# Developer Guide

This guide covers how to set up, run, extend, and test the OmniNode multi-agent system. It includes the backend Python architecture, the War Room frontend, and the full development workflow.

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| **Python** | ≥ 3.11 | Backend runtime |
| **uv** | Latest | Fast Python package manager |
| **Node.js** | ≥ 18 | War Room frontend |
| **Ollama** | Latest | Local LLM hosting |
| **Docker** | Latest | MQTT broker & InfluxDB |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/charansoma3001/OmniNode && cd OmniNode

# 2. Install Python dependencies
uv sync --all-extras

# 3. Install frontend dependencies
cd dashboard && npm install && cd ..

# 4. Pull required LLM models
ollama pull qwen2.5:14b
ollama pull llama-guard3:latest

# 5. Start infrastructure (MQTT, InfluxDB)
docker-compose up -d

# 6. Launch the War Room (Real LLM mode)
python scripts/start_warroom.py --real

# 7. Launch the frontend dashboard (separate terminal)
cd dashboard && npm run dev
```

Access the War Room at `http://localhost:3000`.

---

## Project Structure

```text
OmniNode/
├── pyproject.toml                  # Python build config & dependencies (uv)
├── mkdocs.yml                      # Zensical documentation configuration
├── .env                            # Environment variables (LLM endpoints, models)
├── scripts/
│   ├── start_all.py                # Legacy CLI-only launcher
│   └── start_warroom.py            # War Room launcher (backend + WebSocket bridge)
├── src/
│   ├── api/                        # WebSocket bridge & Event Bus
│   │   ├── event_bus.py            # Singleton async Pub/Sub event bus
│   │   ├── websocket.py            # FastAPI WebSocket endpoints (/ws/*)
│   │   ├── mock_stream.py          # Pre-scripted demo events for DEMO_MODE
│   │   └── models.py               # Pydantic message models
│   ├── common/                     # Shared utilities
│   │   ├── config.py               # Pydantic Settings (env vars)
│   │   └── llm_client.py           # LLM wrapper (OpenAI-compatible, tool loops)
│   ├── registry/                   # MCP Registry (FastAPI)
│   │   ├── server.py               # Registry endpoints + startup orchestration
│   │   └── store.py                # In-memory server registry
│   ├── simulation/                 # IEEE 30-bus Digital Twin
│   │   ├── power_grid.py           # PowerGridSimulation (pandapower)
│   │   ├── scenarios.py            # Pre-defined fault/crisis injection scenarios
│   │   └── data_generator.py       # Load fluctuation & noise generation
│   ├── physical/                   # Physical Layer MCP Servers
│   │   ├── sensors/                # Voltage, Current, Temperature, Frequency servers
│   │   ├── actuators/              # Breaker, Generator, Load, VoltReg, Storage servers
│   │   ├── base_sensor.py          # Abstract sensor base class
│   │   └── base_actuator.py        # Abstract actuator base class
│   ├── coordination/               # Zone Coordinator PLCs
│   │   ├── zone_coordinator.py     # Deterministic IEC 60255 rule engine
│   │   ├── optimizer.py            # Zone optimization heuristics
│   │   └── audit.py                # SQLite audit logger
│   ├── strategic/                  # Strategic AI Layer
│   │   ├── agent.py                # StrategicAgent (LLM tool discovery & execution)
│   │   ├── guardian.py             # SafetyGuardian (command validation LLM)
│   │   ├── monitor.py              # Async MonitoringLoop
│   │   ├── memory.py               # ContextMemory for agent history
│   │   └── cli.py                  # Interactive CLI interface
│   └── domains/                    # Domain adapters (PowerGrid, Robotics, Satellite)
├── dashboard/                      # War Room Frontend (Next.js)
│   ├── src/
│   │   ├── app/                    # Next.js app router pages
│   │   ├── components/war-room/    # UI widgets
│   │   │   ├── TopologyMap.tsx     # React Flow IEEE 30-bus map
│   │   │   ├── BrainScanner.tsx    # Agent reasoning terminal
│   │   │   ├── GuardianPanel.tsx   # Safety intercept log
│   │   │   ├── CommandBar.tsx      # NL query & scenario trigger input
│   │   │   ├── KpiCards.tsx        # Generation, load, frequency, violations
│   │   │   └── DomainSwitcher.tsx  # Power Grid / Robotics / Satellite tabs
│   │   └── hooks/                  # WebSocket data hooks
│   │       ├── useGridState.ts     # /ws/grid_state consumer
│   │       ├── useAgentLogs.ts     # /ws/agent_logs consumer
│   │       └── useGuardianEvents.ts # /ws/guardian_events consumer
│   └── package.json
├── docs/                           # Zensical documentation (this site)
└── tests/                          # Unit & integration tests
```

---

## Backend Architecture

### The `LLMClient` (`src/common/llm_client.py`)

The `LLMClient` is a reusable wrapper around any OpenAI-compatible LLM API (Ollama, vLLM, etc.). Each agent tier gets its own instance with a dedicated model.

**Key methods:**

| Method | Description |
|---|---|
| `complete(prompt, temperature)` | Single-turn text completion (used by the Guardian). |
| `tool_loop(user_message, tools, tool_executor, tool_choice)` | Iterative agentic loop: sends the prompt with tool schemas, executes any returned tool calls via `tool_executor`, and feeds results back until the LLM returns a final text response. |

**Factory functions:**

| Function | Model | Role |
|---|---|---|
| `create_strategic_llm()` | `STRATEGIC_MODEL` | Cross-zone reasoning |
| `create_guardian_llm()` | `GUARDIAN_MODEL` | Command safety validation |

### The `StrategicAgent` (`src/strategic/agent.py`)

The `StrategicAgent` is the orchestrator. On startup, it:

1. Discovers all available MCP tools from the registry (`GET /tools`).
2. Maps each tool to its owning server object for direct in-process execution.
3. Accepts a `SafetyGuardian` instance for actuator command interception.

**Tool execution flow (`_call_server_tool`):**

- **Zone Coordinator tools:** Routed to the coordinator's internal methods (e.g., `get_zone_status`, `voltage_regulation`).
- **Sensor tools:** Routed to the sensor's read handlers (e.g., `read_sensor`, `read_sensors_batch`).
- **Actuator tools:** Routed through the `SafetyGuardian` first. If the Guardian approves, the actuator's `_handle_control()` is called. If blocked, an error is returned to the LLM so it can re-plan.

!!! warning "Async Execution Context"
    `_call_server_tool` is an `async def` method. This is intentional—since the Safety Guardian calls an external LLM, it must be awaited. Using `asyncio.run()` inside a running event loop (FastAPI/uvicorn) will crash with a `RuntimeError`.

### The `SafetyGuardian` (`src/strategic/guardian.py`)

**Response parsing:** The Guardian handles multiple LLM output formats:

1. **JSON:** `{"safe": true, "risk_level": "LOW", "reasoning": "..."}` → parsed directly.
2. **Plain text:** `safe` or `unsafe\n[category]` (typical of `llama-guard3`) → converted to JSON via a fallback text parser.
3. **Unparseable:** Falls back to `safe=False, risk_level=HIGH` with a "Manual review required" condition.

### Actuator Action Aliases

Actuators support **action aliases** to normalise the diverse action names that LLMs generate. For example:

| LLM Output | Normalised Action |
|---|---|
| `bank_toggle` | `activate` (Voltage Regulator) |
| `shed_load` | `shed` (Load Controller) |
| `shed` | `shed` (Load Controller) |

These are defined in `_ACTION_ALIASES` dictionaries within each actuator class (`voltage_regulator.py`, `load_controller.py`).

---

## Frontend Development

### Tech Stack

| Package | Purpose |
|---|---|
| **Next.js** (App Router) | React framework with SSR |
| **Tailwind CSS v4** | Utility-first styling |
| **shadcn/ui** | Accessible component library |
| **Framer Motion** | State-change animations |
| **React Flow** | Interactive topology graph |
| **react-use-websocket** | Auto-reconnecting WebSocket hooks |

### Running the Frontend

```bash
cd dashboard
npm install
npm run dev
# → http://localhost:3000
```

The frontend connects to the backend at `ws://localhost:8000/ws/*`. Ensure the backend is running before starting the dashboard.

### Custom WebSocket Hooks

All real-time data flows through three custom React hooks:

| Hook | WebSocket | State |
|---|---|---|
| `useGridState()` | `/ws/grid_state` | `{ gridState }` — nodes, edges, zone health, violations |
| `useAgentLogs()` | `/ws/agent_logs` | `{ logs }` — array of agent log messages (latest first) |
| `useGuardianEvents()` | `/ws/guardian_events` | `{ events }` — array of guardian intercept events (latest first) |

Each hook uses `react-use-websocket` with `shouldReconnect: () => true` for automatic reconnection.

---

## Extending the System

### Adding a New Sensor

1. Create a new class extending `BaseSensor` in `src/physical/sensors/`.
2. Implement the `_handle_read()` and `_get_sensor_ids()` methods.
3. Register it in the `PowerGridAdapter` or directly in `server.py`.

### Adding a New Actuator

1. Create a new class extending `BaseActuator` in `src/physical/actuators/`.
2. Implement `_handle_control()`, `_handle_validate()`, and `_get_device_ids()`.
3. Add `_ACTION_ALIASES` for any nonstandard action names your LLM might generate.
4. Register it in the server startup flow.

### Adding a New Domain

Replace `src/simulation/power_grid.py` with an adapter for your domain (robotics, satellite, etc.). As long as it exposes MCP sensor and actuator servers, the Strategic Agent will discover and operate them automatically.

---

## Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest --cov=src tests/

# Run a specific test
uv run pytest tests/test_zone_coordinator.py -v
```

---

## Building Documentation

The documentation site is built with Zensical (MkDocs-compatible):

```bash
# Build the site
uv run zensical build --clean

# Serve locally for development
uv run zensical serve

# The site is output to ./site/
```

Documentation is auto-deployed to GitHub Pages on push to `main` via `.github/workflows/docs.yml`.
