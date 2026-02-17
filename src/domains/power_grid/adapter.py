"""Power grid domain adapter — full implementation."""

from __future__ import annotations

from typing import Any

from src.domains.base_adapter import DomainAdapter
from src.simulation.power_grid import PowerGridSimulation
from src.physical.sensors.voltage import VoltageSensorServer
from src.physical.sensors.current import CurrentSensorServer
from src.physical.sensors.temperature import TemperatureSensorServer
from src.physical.sensors.frequency import FrequencySensorServer
from src.physical.sensors.power_quality import PowerQualitySensorServer
from src.physical.actuators.circuit_breaker import CircuitBreakerServer
from src.physical.actuators.generator import GeneratorServer
from src.physical.actuators.load_controller import LoadControllerServer
from src.physical.actuators.voltage_regulator import VoltageRegulatorServer
from src.physical.actuators.energy_storage import EnergyStorageServer
from src.coordination.zone_coordinator import ZoneCoordinator


class PowerGridAdapter(DomainAdapter):
    """Full domain adapter for the IEEE 30-bus power grid."""

    @property
    def domain_name(self) -> str:
        return "power_grid"

    def get_sensor_types(self) -> list[dict]:
        return [
            {"type": "voltage", "unit": "p.u.", "per": "bus"},
            {"type": "current", "unit": "kA", "per": "line"},
            {"type": "temperature", "unit": "°C", "per": "transformer"},
            {"type": "frequency", "unit": "Hz", "per": "system"},
            {"type": "power_quality", "unit": "%", "per": "zone"},
        ]

    def get_actuator_types(self) -> list[dict]:
        return [
            {"type": "circuit_breaker", "controls": "line switching"},
            {"type": "generator", "controls": "active/reactive power dispatch"},
            {"type": "load_controller", "controls": "demand response"},
            {"type": "voltage_regulator", "controls": "shunt capacitor banks"},
            {"type": "energy_storage", "controls": "battery charge/discharge"},
        ]

    def create_sensors(self, simulation: PowerGridSimulation) -> list[Any]:
        zones = simulation.get_zone_buses()
        sensors = []
        for zone in zones:
            sensors.append(VoltageSensorServer(simulation, zone=zone))
            sensors.append(CurrentSensorServer(simulation, zone=zone))
            sensors.append(PowerQualitySensorServer(simulation, zone=zone))
        # System-wide sensors
        sensors.append(TemperatureSensorServer(simulation))
        sensors.append(FrequencySensorServer(simulation))
        return sensors

    def create_actuators(self, simulation: PowerGridSimulation) -> list[Any]:
        return [
            CircuitBreakerServer(simulation),
            GeneratorServer(simulation),
            LoadControllerServer(simulation),
            VoltageRegulatorServer(simulation),
            EnergyStorageServer(simulation),
        ]

    def create_coordinators(self, simulation: PowerGridSimulation) -> list[Any]:
        zone_buses = simulation.get_zone_buses()
        zone_lines = simulation.get_zone_lines()
        coordinators = []
        for zone_id, buses in zone_buses.items():
            lines = zone_lines.get(zone_id, [])
            coordinators.append(ZoneCoordinator(zone_id, simulation, buses, lines))
        return coordinators

    def get_constraints(self) -> dict:
        return {
            "voltage_min_pu": 0.95,
            "voltage_max_pu": 1.05,
            "line_loading_max_pct": 100.0,
            "frequency_min_hz": 59.5,
            "frequency_max_hz": 60.5,
            "transformer_alarm_temp_c": 85.0,
            "transformer_trip_temp_c": 105.0,
        }

    def get_safety_rules(self) -> list[str]:
        return [
            "Always validate actuations in sandbox before execution",
            "Emergency islanding requires human confirmation",
            "Generator output must stay within min/max limits",
            "Load shedding above 20% requires human approval",
            "All switching operations must check for islanding risk",
        ]
