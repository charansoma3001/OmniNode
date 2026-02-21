"""Plotly Dash real-time monitoring dashboard."""

from __future__ import annotations

import json
import logging

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output

from src.simulation.power_grid import PowerGridSimulation
from src.simulation.data_generator import DataGenerator

logger = logging.getLogger(__name__)

# Initialize simulation
grid = PowerGridSimulation()
data_gen = DataGenerator(grid)

# Dash app
app = dash.Dash(
    __name__,
    title="MCP Power Grid Dashboard",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.layout = html.Div(
    style={"fontFamily": "Inter, sans-serif", "backgroundColor": "#0f172a", "color": "#e2e8f0", "minHeight": "100vh", "padding": "20px"},
    children=[
        # Header
        html.Div(
            style={"textAlign": "center", "marginBottom": "30px"},
            children=[
                html.H1("⚡ MCP Power Grid Monitor", style={"color": "#38bdf8", "margin": "0"}),
                html.P("IEEE 30-Bus Digital Twin — Real-time Monitoring", style={"color": "#94a3b8"}),
            ],
        ),

        # KPI Cards
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))", "gap": "15px", "marginBottom": "30px"},
            id="kpi-cards",
        ),

        # Main grid
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"},
            children=[
                # Voltage heatmap
                html.Div(
                    style={"backgroundColor": "#1e293b", "borderRadius": "12px", "padding": "20px"},
                    children=[
                        html.H3("Bus Voltages (p.u.)", style={"color": "#38bdf8", "marginTop": "0"}),
                        dcc.Graph(id="voltage-chart"),
                    ],
                ),
                # Line loading
                html.Div(
                    style={"backgroundColor": "#1e293b", "borderRadius": "12px", "padding": "20px"},
                    children=[
                        html.H3("Line Loading (%)", style={"color": "#38bdf8", "marginTop": "0"}),
                        dcc.Graph(id="loading-chart"),
                    ],
                ),
            ],
        ),

        # Zone status + violations
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px", "marginTop": "20px"},
            children=[
                html.Div(
                    style={"backgroundColor": "#1e293b", "borderRadius": "12px", "padding": "20px"},
                    children=[
                        html.H3("Zone Health", style={"color": "#38bdf8", "marginTop": "0"}),
                        html.Div(id="zone-status"),
                    ],
                ),
                html.Div(
                    style={"backgroundColor": "#1e293b", "borderRadius": "12px", "padding": "20px"},
                    children=[
                        html.H3("Active Violations", style={"color": "#f87171", "marginTop": "0"}),
                        html.Div(id="violations-panel"),
                    ],
                ),
            ],
        ),

        # Auto-refresh
        dcc.Interval(id="interval", interval=5000, n_intervals=0),
    ],
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    [
        Output("kpi-cards", "children"),
        Output("voltage-chart", "figure"),
        Output("loading-chart", "figure"),
        Output("zone-status", "children"),
        Output("violations-panel", "children"),
    ],
    [Input("interval", "n_intervals")],
)
def update_dashboard(n):
    # Try to load external state first (from CLI scenarios)
    import os
    import time
    
    state_file = "grid_state.json"
    loaded = False
    if os.path.exists(state_file):
        try:
            import pandapower as pp
            # Load external state blindly to sync with CLI
            grid.net = pp.from_json(state_file, convert=True)
            grid.run_power_flow()
            loaded = True
        except Exception as e:
            logger.error("Failed to load grid state: %s", e)

    if not loaded:
        # Fallback to internal simulation
        grid.run_power_flow()

    # KPIs
    total_gen = grid.get_total_generation()
    total_load = grid.get_total_load()
    freq = grid.get_frequency()
    losses = grid.get_total_losses()
    voltages = grid.get_bus_voltages()
    loadings = grid.get_line_loadings()
    v_violations = sum(1 for v in voltages.values() if v < 0.95 or v > 1.05)
    t_violations = sum(1 for l in loadings.values() if l > 100)

    kpi_cards = [
        _kpi_card("Generation", f"{total_gen:.1f} MW", "#22c55e"),
        _kpi_card("Load", f"{total_load:.1f} MW", "#3b82f6"),
        _kpi_card("Frequency", f"{freq:.3f} Hz", "#f59e0b" if abs(freq - 60) > 0.2 else "#22c55e"),
        _kpi_card("Losses", f"{losses:.2f} MW", "#94a3b8"),
        _kpi_card("Violations", f"{v_violations + t_violations}", "#ef4444" if (v_violations + t_violations) > 0 else "#22c55e"),
    ]

    # Voltage chart
    bus_ids = sorted(voltages.keys())
    voltage_fig = {
        "data": [{
            "x": [f"Bus {b}" for b in bus_ids],
            "y": [voltages[b] for b in bus_ids],
            "type": "bar",
            "marker": {"color": ["#ef4444" if voltages[b] < 0.95 or voltages[b] > 1.05 else "#38bdf8" for b in bus_ids]},
        }],
        "layout": {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#94a3b8"},
            "margin": {"t": 10, "b": 30, "l": 40, "r": 10},
            "yaxis": {"range": [0.9, 1.1], "gridcolor": "#334155"},
            "xaxis": {"tickangle": -45},
            "shapes": [
                {"type": "line", "y0": 0.95, "y1": 0.95, "x0": -0.5, "x1": len(bus_ids) - 0.5, "line": {"dash": "dash", "color": "#f87171"}},
                {"type": "line", "y0": 1.05, "y1": 1.05, "x0": -0.5, "x1": len(bus_ids) - 0.5, "line": {"dash": "dash", "color": "#f87171"}},
            ],
        },
    }

    # Loading chart
    line_ids = sorted(loadings.keys())[:20]  # Top 20
    loading_fig = {
        "data": [{
            "x": [f"L{l}" for l in line_ids],
            "y": [loadings[l] for l in line_ids],
            "type": "bar",
            "marker": {"color": ["#ef4444" if loadings[l] > 100 else "#f59e0b" if loadings[l] > 80 else "#38bdf8" for l in line_ids]},
        }],
        "layout": {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#94a3b8"},
            "margin": {"t": 10, "b": 30, "l": 40, "r": 10},
            "yaxis": {"gridcolor": "#334155"},
            "shapes": [
                {"type": "line", "y0": 100, "y1": 100, "x0": -0.5, "x1": len(line_ids) - 0.5, "line": {"dash": "dash", "color": "#f87171"}},
            ],
        },
    }

    # Zone status
    zone_buses = grid.get_zone_buses()
    zone_elements = []
    for zone, buses in zone_buses.items():
        zone_voltages = [voltages.get(b, 1.0) for b in buses]
        min_v = min(zone_voltages)
        max_v = max(zone_voltages)
        zone_loads = grid.net.load[grid.net.load.bus.isin(buses)]
        total = float(zone_loads.p_mw.sum()) if len(zone_loads) > 0 else 0
        v_count = sum(1 for v in zone_voltages if v < 0.95 or v > 1.05)
        color = "#ef4444" if v_count > 2 else "#f59e0b" if v_count > 0 else "#22c55e"

        zone_elements.append(html.Div(
            style={"backgroundColor": "#0f172a", "borderRadius": "8px", "padding": "12px", "marginBottom": "8px", "borderLeft": f"4px solid {color}"},
            children=[
                html.Div(f"🏭 {zone.upper()}", style={"fontWeight": "bold", "color": color}),
                html.Div(f"V: {min_v:.3f}–{max_v:.3f} p.u. | Load: {total:.1f} MW | ⚠ {v_count}", style={"fontSize": "0.85em", "color": "#94a3b8"}),
            ],
        ))

    # Violations
    violation_elements = []
    for b, v in voltages.items():
        if v < 0.95:
            violation_elements.append(html.Div(f"🔴 Bus {b}: Low voltage {v:.4f} p.u.", style={"color": "#f87171", "padding": "4px 0"}))
        elif v > 1.05:
            violation_elements.append(html.Div(f"🔴 Bus {b}: High voltage {v:.4f} p.u.", style={"color": "#f87171", "padding": "4px 0"}))
    for l, ld in loadings.items():
        if ld > 100:
            violation_elements.append(html.Div(f"🔴 Line {l}: Overloaded {ld:.1f}%", style={"color": "#f87171", "padding": "4px 0"}))

    if not violation_elements:
        violation_elements = [html.Div("✅ No active violations", style={"color": "#22c55e"})]

    return kpi_cards, voltage_fig, loading_fig, zone_elements, violation_elements


def _kpi_card(title: str, value: str, color: str) -> html.Div:
    return html.Div(
        style={"backgroundColor": "#1e293b", "borderRadius": "12px", "padding": "20px", "textAlign": "center"},
        children=[
            html.Div(title, style={"color": "#94a3b8", "fontSize": "0.85em", "marginBottom": "5px"}),
            html.Div(value, style={"color": color, "fontSize": "1.8em", "fontWeight": "bold"}),
        ],
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    main()
