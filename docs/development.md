# Developer Guide

This guide covers how to extend the MCP multi-agent framework by adding new domains, creating sensors/actuators, and testing the system.

## Extending `base_adapter.py`

If you are adding a new domain (e.g., Robotics), you must implement the `BaseAdapter` interface.

```python
from src.domains.base_adapter import BaseAdapter

class RoboticsAdapter(BaseAdapter):
    def initialize_simulation(self):
        # Setup kinematic chains, physics engine, etc.
        pass
        
    def step_simulation(self):
        # Advance the simulation by one tick
        pass
        
    def get_sensors(self):
        # Return a list of sensor tools
        pass
        
    def get_actuators(self):
        # Return a list of actuator tools
        pass
```

## Creating New Sensors or Actuators

All components that expose data or functionality must be wrapped as an MCP Server.

**1. Define the Server:**
Use the `mcp.server.Server` class.

**2. Expose the Data/Action:**
Use the `@server.mcp.list_tools()` and `@server.mcp.call_tool()` decorators.

```python
import mcp.server.Server

# Example Custom Sensor
sensor = mcp.server.Server("CustomVoltageSensor")

@sensor.mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(name="read_voltage", description="Reads voltage at bus 5")]

@sensor.mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "read_voltage":
        # fetch from grid_state.json or memory
        return [TextContent(type="text", text="1.05 p.u.")]
```

**3. Registration:**
Ensure the new server registers itself with the `mcp-registry` on startup so the Strategic Agent or Zone Coordinators can find it.

## Running the Test Suite

We use `pytest` for all unit and integration testing.

```bash
uv run pytest tests/
```

To run with coverage:
```bash
uv run pytest --cov=src tests/
```

Continuous Integration (CI) will enforce that these tests pass on every pull request to `main`.
