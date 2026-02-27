"""Satellite domain adapter — prototype stub."""

from __future__ import annotations

from typing import Any

from src.domains.base_adapter import DomainAdapter


class SatelliteAdapter(DomainAdapter):
    """Prototype domain adapter for a satellite constellation.

    Provides sensor/actuator type definitions but no simulation backend yet.
    """

    @property
    def domain_name(self) -> str:
        return "satellite"

    def get_sensor_types(self) -> list[dict]:
        return [
            {"type": "telemetry", "unit": "various", "per": "satellite"},
            {"type": "attitude_sensor", "unit": "degrees", "per": "satellite"},
            {"type": "gps", "unit": "lat/lon/alt", "per": "satellite"},
            {"type": "comm_link", "unit": "dBm", "per": "ground_station"},
            {"type": "solar_panel", "unit": "W", "per": "satellite"},
            {"type": "thermal", "unit": "°C", "per": "subsystem"},
        ]

    def get_actuator_types(self) -> list[dict]:
        return [
            {"type": "thruster", "controls": "delta-v maneuvers"},
            {"type": "reaction_wheel", "controls": "attitude adjustments"},
            {"type": "antenna", "controls": "pointing direction"},
            {"type": "payload", "controls": "instrument operations"},
        ]

    def create_sensors(self, simulation: Any) -> list[Any]:
        # Stub — requires orbital propagation simulation
        return []

    def create_actuators(self, simulation: Any) -> list[Any]:
        return []

    def create_coordinators(self, simulation: Any) -> list[Any]:
        return []

    def get_constraints(self) -> dict:
        return {
            "max_delta_v_ms": 100,
            "min_fuel_pct": 5,
            "min_battery_pct": 10,
            "max_subsystem_temp_c": 60,
            "min_comm_snr_db": 10,
        }

    def get_safety_rules(self) -> list[str]:
        return [
            "Collision avoidance takes priority over all operations",
            "Thruster burns require ground station confirmation",
            "Minimum fuel reserve must be maintained",
            "Solar panel orientation must be checked before maneuvers",
        ]
