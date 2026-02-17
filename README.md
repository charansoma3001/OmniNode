# MCP-Based Multi-Agent System for Power Grid & Beyond

A three-layer hierarchical multi-agent system using the **Model Context Protocol (MCP)** to monitor and control simulated power grid infrastructure via natural language.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  STRATEGIC LAYER  — LLM Agent (Claude) as MCP Client    │
└─────────────────────────────────────────────────────────┘
                      ↕ MCP Protocol
┌─────────────────────────────────────────────────────────┐
│  COORDINATION LAYER — Zone/Substation MCP Servers        │
└─────────────────────────────────────────────────────────┘
                   ↕ MCP over MQTT
┌─────────────────────────────────────────────────────────┐
│  PHYSICAL LAYER — Sensor & Actuator MCP Servers          │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Copy environment config
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# 3. Start infrastructure (MQTT, InfluxDB, Grafana)
docker compose up -d

# 4. Start the MCP registry
mcp-registry

# 5. Run the simulation + all MCP servers
python scripts/start_all.py

# 6. Launch the natural language CLI
mcp-cli
```

## Project Structure

```
src/
├── common/          # Shared config, MQTT/InfluxDB clients
├── registry/        # MCP Registry (tool discovery)
├── physical/        # Sensor & Actuator MCP servers
├── coordination/    # Zone coordinator MCP servers
├── strategic/       # LLM agent, monitoring, memory
├── simulation/      # Pandapower digital twin
└── domains/         # Domain adapters (power grid, robotics, satellite)
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| LLM Agent | Claude (Anthropic SDK) |
| MCP SDK | `mcp` Python package |
| MQTT Broker | EMQX 5.8 |
| Time-Series DB | InfluxDB 2.7 |
| Power Simulation | Pandapower |
| Dashboard | Plotly Dash |
| Orchestration | Docker Compose |
