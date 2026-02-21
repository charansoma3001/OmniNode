# MCP Power Grid Strategic Agent

A hierarchical, multi-agent system utilizing the **Model Context Protocol (MCP)** to monitor, optimize, and safely control a simulated electrical power grid (IEEE 30-bus) via Large Language Models (LLMs). 

This project demonstrates how multiple specialized LLM agents can collaborate to manage critical infrastructure autonomously while ensuring operational safety.

---

## 🏗 System Architecture

The system operates across three distinct layers, integrated seamlessly via MCP:

```
┌──────────────────────────────────────────────────────────────┐
│  STRATEGIC LAYER  — "The Big Brain" (System-wide Agent)      │
│  Resolves cross-zone issues, handles natural language UX     │
└───────────────────────┬──────────────────────────────────────┘
                        │ MCP Protocol (JSON-RPC)
┌───────────────────────┴──────────────────────────────────────┐
│  COORDINATION LAYER — Zone Coordinators (Substation Agents)  │
│  Autonomous local optimization and violation handling        │
└───────────────────────┬──────────────────────────────────────┘
                        │ MCP Protocol (JSON-RPC)
┌───────────────────────┴──────────────────────────────────────┐
│  PHYSICAL LAYER — Digital Twin (Pandapower)                  │
│  Sensor servers (Voltage, Current, Frequency)                │
│  Actuator servers (Circuit Breakers, Generators)             │
└──────────────────────────────────────────────────────────────┘
```

### The Component Roster
The system runs the following roster of interconnected servers and agents:
- **1× Strategic Agent**: A master LLM (e.g., `llama3.1`) that reasons over the entire grid state, processes human commands, and acts as the ultimate decider for high-risk operations.
- **3× Zone Coordinators**: Specialized LLMs (e.g., `granite4`, `qwen2.5`, `llama3.2`) assigned to geographic zones (Buses 0–9, 10–19, 20–29). They handle local load balancing and voltage regulation autonomously.
- **11× Sensor MCP Servers**: Continuous readers for Voltage, Current, Transformer Temperature, Power Quality (THD), and System Frequency.
- **5× Actuator MCP Servers**: Interfaces for Circuit Breakers, Generators, Load Controllers, Voltage Regulators (shunt capacitors), and Energy Storage.
- **1× Safety Guardian Agent**: *(Optional config)* Validates actuator commands before execution.
- **1× MCP Registry**: A lightweight discovery service (`FastAPI`) where all sensor, actuator, and coordinator tools are registered for discovery by the Strategic Agent.

---

## 🛠 Project Structure

```text
mcp-multi-agent/
├── pyproject.toml             # Python dependencies (uv)
├── .env                       # Environment configuration (LLMs, API keys)
├── scripts/
│   └── start_all.py           # Main orchestrator script to launch all servers
├── src/
│   ├── common/                # Shared settings, LLM client wrapper, data models
│   ├── registry/              # FastAPI MCP registry server (`mcp-registry`)
│   ├── simulation/            # IEEE 30-bus Pandapower digital twin & data generation
│   ├── physical/              # Physical Layer MCP Servers
│   │   ├── sensors/           # Voltage, current, temperature, frequency MCP servers
│   │   └── actuators/         # Breaker, generator, capacitor MCP servers
│   ├── coordination/          # Zone Coordinator MCP servers & optimization heuristics
│   ├── strategic/             # Strategic Agent, CLI, Memory, and Monitoring Loop
│   ├── dashboard/             # Plotly Dash real-time monitoring UI
│   └── domains/               # Domain adapters wrapping the simulation for MCP
└── tests/                     # Unit and integration tests
```

---

## 🚀 Setup & Installation

### Prerequisites
1. **Python 3.11+**
2. **`uv` Package Manager** (Recommended for fast dependency resolution)
3. **Ollama** running locally or a remote OpenAI-compatible endpoint.

### Installation

1. **Clone and Install Dependencies:**
   ```bash
   uv sync --all-extras
   ```

2. **Configure Environment:**
   Copy the `.env` template or create a new `.env` file in the root directory:
   ```ini
   # /mcp-multi-agent/.env

   # Strategic agent: cross-zone reasoning
   STRATEGIC_MODEL=llama3.1:latest
   
   # Per-zone coordinator agents
   ZONE1_MODEL=granite4:latest
   ZONE2_MODEL=qwen2.5:latest
   ZONE3_MODEL=llama3.2:latest
   
   # LLM Connection
   LLM_API_KEY=ollama
   LLM_BASE_URL=http://localhost:11434
   LLM_CONTEXT_WINDOW=8192  # Increased for complex grid state reasoning
   ```
   *Note: Ensure the specified Ollama models are pulled (`ollama pull <model_name>`) before starting.*

---

## ▶️ Running the System

To run the full suite, you need to open multiple terminal instances. The project leverages `uv run` to ensure scripts execute within the correct virtual environment path.

**Terminal 1: Start the MCP Service Registry**
The registry acts as the phonebook for all tools.
```bash
uv run mcp-registry
```

**Terminal 2: Launch the Digital Twin & Agents**
This script initializes the IEEE 30-bus simulation, generates MCP server wrappers for all components, registers them, and starts the asynchronous monitoring loop.
```bash
uv run python scripts/start_all.py
```

**Terminal 3: Launch the Real-Time Dashboard**
View the grid state visually (Voltage bars, line loading, zone health).
```bash
uv run mcp-dashboard
# Access at http://localhost:8050
```

**Terminal 4: Launch the Natural Language Interactive CLI**
The primary interface to chat with the Strategic Agent and issue commands.
```bash
uv run mcp-cli
```

---

## 💻 Interacting with the System

Once the `mcp-cli` is running, you can issue both internal commands and natural language prompts:

### Built-in CLI Commands
- `status`: Prints a system-wide overview (Generation, Load, Losses, Frequency, Max Voltage/Loading).
- `zones`: Displays instantaneous health summaries for Zone 1, Zone 2, and Zone 3.
- `history`: Shows the last 5 decisions made by the Strategic Agent.
- `monitor start / stop`: Toggles the background monitoring loop.
- `rollback`: Reverts the grid state to the original baseline snapshot.
- `scenario <name>`: Injects a pre-defined fault or demand spike (e.g., `scenario peak_load`).
- `exit` or `quit`: Shut down the CLI.

### Natural Language Control
You can type instructions natively. The Strategic Agent translates these into MCP tool executions.

**Examples:**
- *"Why is Zone 3 showing a critical warning, and can you fix it?"*
- *"Open the circuit breaker on line 5 to simulate a fault and tell me what happens to the voltages."*
- *"Increase generation at bus 1 to 45 MW to handle the load."*
- *"Run a complete diagnostic of the system and resolve any existing voltage violations using the zone coordinators."*

---

## 🧠 How the AI Monitoring Loop Works

When you run `start_all.py`, an asynchronous `MonitoringLoop` begins. 
Here is what happens every interval (e.g., 30 seconds):

1. **Simulation Tick**: Loads fluctuate slightly via the `DataGenerator`, and `pandapower` runs a power flow analysis.
2. **Violation Detection**: The system checks voltages (0.95–1.05 p.u.), line loadings (< 100%), and frequency.
3. **Zone-First Delegation**: If violations exist, they are grouped by zone and dispatched to the respective **Zone Coordinator LLM** in parallel.
4. **Autonomous Correction**: Zone LLMs assess their domains and execute local tools (e.g., switching shunt capacitors or shifting load) to fix the grid.
5. **Strategic Escalation**: If multiple zones are failing, or a zone specifically requests help ("Escalate to strategic agent"), the violations are aggregated and fed into the **Strategic Agent**.
6. **Master Execution**: The Strategic Agent reads the context and executes cross-zone or high-risk tools to stabilize the grid.

---

## 🔧 Extensibility

Because the system is built strictly using the **Model Context Protocol**, adding new capabilities is incredibly straightforward:

1. **New Sensors/Actuators**: Create a new class extending `mcp.server.Server`. Add `@self.mcp.list_tools()` and `@self.mcp.call_tool()` decorators. Register it in the `PowerGridAdapter`.
2. **New Domains**: You can replace `src/simulation/power_grid.py` with an adapter for a robotics system or a satellite network. As long as they expose MCP servers, the Strategic Agent LLM can discover and operate them.
