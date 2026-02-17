"""Realistic time-varying sensor data generation for the digital twin."""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timedelta

import numpy as np

from src.common.influx_client import InfluxClient
from src.common.models import SensorReading
from src.simulation.power_grid import PowerGridSimulation

logger = logging.getLogger(__name__)


class DataGenerator:
    """Generates realistic sensor data with noise, daily profiles, and random events."""

    def __init__(self, grid: PowerGridSimulation, influx: InfluxClient | None = None):
        self.grid = grid
        self.influx = influx
        self._time_offset: float = 0.0  # hours since midnight

    def generate_snapshot(self, timestamp: datetime | None = None) -> list[SensorReading]:
        """Generate a full set of sensor readings for the current grid state."""
        if timestamp is None:
            timestamp = datetime.utcnow()

        readings: list[SensorReading] = []
        zone_buses = self.grid.get_zone_buses()

        # --- Voltage sensors ---
        for zone, buses in zone_buses.items():
            for bus_id in buses:
                try:
                    vm = self.grid.get_bus_voltage(bus_id)
                    noise = random.gauss(0, 0.002)  # ±0.2% noise
                    readings.append(SensorReading(
                        sensor_id=f"voltage_bus_{bus_id}",
                        sensor_type="voltage",
                        zone=zone,
                        value=round(vm + noise, 4),
                        unit="p.u.",
                        timestamp=timestamp,
                    ))
                except (KeyError, IndexError):
                    continue

        # --- Line current sensors ---
        zone_lines = self.grid.get_zone_lines()
        for zone, lines in zone_lines.items():
            for line_id in lines:
                try:
                    i_ka = self.grid.get_line_current(line_id)
                    noise = random.gauss(0, i_ka * 0.01)  # ±1% noise
                    readings.append(SensorReading(
                        sensor_id=f"current_line_{line_id}",
                        sensor_type="current",
                        zone=zone,
                        value=round(abs(i_ka + noise), 4),
                        unit="kA",
                        timestamp=timestamp,
                    ))
                except (KeyError, IndexError):
                    continue

        # --- Transformer temperature sensors ---
        for trafo_id in self.grid.net.trafo.index:
            try:
                temp = self.grid.get_transformer_temperature(trafo_id)
                noise = random.gauss(0, 0.5)  # ±0.5°C
                bus = int(self.grid.net.trafo.hv_bus.at[trafo_id])
                zone = self._bus_to_zone(bus, zone_buses)
                readings.append(SensorReading(
                    sensor_id=f"temp_trafo_{trafo_id}",
                    sensor_type="temperature",
                    zone=zone,
                    value=round(temp + noise, 1),
                    unit="°C",
                    timestamp=timestamp,
                ))
            except (KeyError, IndexError):
                continue

        # --- Frequency sensor (system-wide) ---
        freq = self.grid.get_frequency()
        noise = random.gauss(0, 0.005)  # ±5 mHz
        readings.append(SensorReading(
            sensor_id="frequency_system",
            sensor_type="frequency",
            zone="system",
            value=round(freq + noise, 4),
            unit="Hz",
            timestamp=timestamp,
        ))

        # --- Power quality (THD) per zone ---
        for zone in zone_buses:
            thd = random.uniform(1.0, 5.0)  # % THD
            readings.append(SensorReading(
                sensor_id=f"thd_{zone}",
                sensor_type="power_quality",
                zone=zone,
                value=round(thd, 2),
                unit="%",
                timestamp=timestamp,
            ))

        return readings

    def apply_daily_profile(self, hour: float) -> None:
        """Apply a daily load profile to the grid.

        Typical residential/commercial pattern with morning and evening peaks.
        """
        # Normalized load factor (0.6 at night, 1.0 at peaks)
        load_factor = 0.7 + 0.3 * (
            0.5 * math.sin(math.pi * (hour - 6) / 12) +
            0.3 * math.sin(math.pi * (hour - 17) / 4)
        )
        load_factor = max(0.5, min(1.2, load_factor))

        for load_id in self.grid.net.load.index:
            # Scale load relative to nominal
            base_p = self.grid.net.load.p_mw.at[load_id]
            self.grid.net.load.p_mw.at[load_id] = base_p * load_factor

        self.grid.run_power_flow()

    def generate_historical_data(
        self,
        hours: int = 24,
        interval_minutes: int = 5,
    ) -> list[SensorReading]:
        """Generate historical data for seeding the time-series DB."""
        all_readings: list[SensorReading] = []
        now = datetime.utcnow()
        start = now - timedelta(hours=hours)

        steps = (hours * 60) // interval_minutes
        for step in range(steps):
            ts = start + timedelta(minutes=step * interval_minutes)
            hour = ts.hour + ts.minute / 60.0
            self.apply_daily_profile(hour)
            readings = self.generate_snapshot(timestamp=ts)
            all_readings.extend(readings)

        logger.info("Generated %d historical readings over %d hours", len(all_readings), hours)
        return all_readings

    def seed_influxdb(self, hours: int = 24) -> None:
        """Generate and write historical data to InfluxDB."""
        if not self.influx:
            logger.warning("No InfluxDB client — cannot seed data")
            return

        readings = self.generate_historical_data(hours=hours)
        batch_size = 500
        for i in range(0, len(readings), batch_size):
            batch = readings[i : i + batch_size]
            self.influx.write_readings_batch(batch)
        logger.info("Seeded InfluxDB with %d readings", len(readings))

    @staticmethod
    def _bus_to_zone(bus_id: int, zone_buses: dict[str, list[int]]) -> str:
        for zone, buses in zone_buses.items():
            if bus_id in buses:
                return zone
        return "unknown"
