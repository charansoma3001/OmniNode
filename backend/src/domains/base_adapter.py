"""Abstract base class for domain adapters.

Each domain (power grid, robotics, satellite) extends this to provide
domain-specific sensors, actuators, and coordinators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.simulation.power_grid import PowerGridSimulation


class DomainAdapter(ABC):
    """Abstract domain adapter providing a uniform interface for multi-domain support."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Return the domain identifier (e.g., 'power_grid', 'robotics')."""
        ...

    @abstractmethod
    def get_sensor_types(self) -> list[dict]:
        """Return list of sensor type definitions for this domain."""
        ...

    @abstractmethod
    def get_actuator_types(self) -> list[dict]:
        """Return list of actuator type definitions for this domain."""
        ...

    @abstractmethod
    def create_sensors(self, simulation: Any) -> list[Any]:
        """Instantiate all sensor MCP servers for this domain."""
        ...

    @abstractmethod
    def create_actuators(self, simulation: Any) -> list[Any]:
        """Instantiate all actuator MCP servers for this domain."""
        ...

    @abstractmethod
    def create_coordinators(self, simulation: Any) -> list[Any]:
        """Instantiate zone/area coordinator MCP servers."""
        ...

    def get_constraints(self) -> dict:
        """Return domain-specific constraints and limits."""
        return {}

    def get_safety_rules(self) -> list[str]:
        """Return domain-specific safety rules."""
        return []
