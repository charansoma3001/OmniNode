# Core Concepts

The MCP Multi-Agent System is designed to seamlessly integrate Large Language Models (LLMs) with simulated physical systems. 

## The Domains

The architecture supports various physical domains by wrapping their simulation data into standard Model Context Protocol (MCP) servers.

- **Power Grid (IEEE 30-bus)**: The primary simulation provided. It models the generation, transmission, and load aspects of an electrical grid using `pandapower`. It provides sensor data (voltage, current, frequency) and actuator controls (breakers, generators).
- **Robotics (Future Extension)**: Control endpoints for individual servos, kinematics calculations, and LiDAR sensor simulation.
- **Satellite (Future Extension)**: Orbital parameters, communication bandwidth, and power management simulations.

## The Multi-Agent System

The system operates across three tiers:

### 1. The Strategic Agent (System-wide)
A powerful LLM (e.g., `llama3.1`) focused on global reasoning. It serves as "The Big Brain" which aggregates information from all zones and handles complex trade-offs or cascading failures that a single zone cannot resolve. It also serves as the user-facing natural language interface.

### 2. The Coordination Layer (Zone PLCs)
Deterministic, rule-based coordinators (Programmable Logic Controllers) assigned to geographic subsets (zones) of the system.
- They monitor local sensors continuously.
- They use hard-coded safety logic (e.g., IEC 60255 protection rules) to handle fast localized violations.
- They invoke local actuators (e.g., switching capacitors) to rectify issues deterministically without LLM latency.
- If an issue is unresolvable locally using their protection thresholds, they escalate the issue to the Strategic Agent.

### 3. The Physical Layer & Data Flow

- **Sensors:** Small MCP server endpoints that provide read-only data (e.g., reading a voltage from the `grid_state.json` store).
- **Actuators:** MCP server endpoints that take action, modifying either the `grid_state` or invoking the `PowerGridAdapter` to run a simulation step.
- **MCP Registry:** The communication spine. All sensors and actuators announce their presence (host, port, tool schemas) to the `mcp-registry`. Agents query the registry to discover what physical tools are available in their assigned zone.

**Data Flow Summary:**
`Simulation Step` -> `Sensor Servers Update State` -> `Monitoring Loop Detects Violation` -> `Assigns to Zone PLC` -> `PLC Evaluates Rules` -> `PLC Calls Actuator Tool` -> `Simulation Updates`.
