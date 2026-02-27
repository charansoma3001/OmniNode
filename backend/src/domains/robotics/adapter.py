"""Robotics domain adapter — prototype stub."""

from __future__ import annotations

from typing import Any

from src.domains.base_adapter import DomainAdapter


class RoboticsAdapter(DomainAdapter):
    """Prototype domain adapter for a robotics assembly line.

    Provides sensor/actuator type definitions but no simulation backend yet.
    """

    @property
    def domain_name(self) -> str:
        return "robotics"

    def get_sensor_types(self) -> list[dict]:
        return [
            {"type": "position_encoder", "unit": "degrees", "per": "joint"},
            {"type": "force_sensor", "unit": "N", "per": "end_effector"},
            {"type": "proximity_sensor", "unit": "mm", "per": "workstation"},
            {"type": "vision_camera", "unit": "frame", "per": "inspection_point"},
            {"type": "temperature", "unit": "°C", "per": "motor"},
        ]

    def get_actuator_types(self) -> list[dict]:
        return [
            {"type": "robot_arm", "controls": "6-DOF joint positions"},
            {"type": "gripper", "controls": "grip/release operations"},
            {"type": "conveyor_belt", "controls": "speed and direction"},
            {"type": "tool_changer", "controls": "end-effector selection"},
        ]

    def create_sensors(self, simulation: Any) -> list[Any]:
        # Stub — requires Gazebo/ROS2 simulation
        return []

    def create_actuators(self, simulation: Any) -> list[Any]:
        return []

    def create_coordinators(self, simulation: Any) -> list[Any]:
        return []

    def get_constraints(self) -> dict:
        return {
            "max_joint_velocity_deg_s": 180,
            "max_payload_kg": 10,
            "min_clearance_mm": 50,
            "max_motor_temp_c": 80,
        }

    def get_safety_rules(self) -> list[str]:
        return [
            "Never exceed joint limits",
            "Emergency stop on collision detection",
            "Verify gripper force before lifting",
            "Human zone clearance before arm motion",
        ]
