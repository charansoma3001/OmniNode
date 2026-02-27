"""InfluxDB client wrapper for time-series sensor data."""

from __future__ import annotations

import logging
from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from src.common.config import get_settings
from src.common.models import SensorReading

logger = logging.getLogger(__name__)


class InfluxClient:
    """Wrapper for writing and querying sensor data in InfluxDB."""

    def __init__(self) -> None:
        settings = get_settings()
        self._url = settings.influxdb_url
        self._token = settings.influxdb_token
        self._org = settings.influxdb_org
        self._bucket = settings.influxdb_bucket
        self._client: InfluxDBClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        self._client = InfluxDBClient(
            url=self._url,
            token=self._token,
            org=self._org,
        )
        logger.info("Connected to InfluxDB at %s", self._url)

    def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info("InfluxDB connection closed")

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def write_reading(self, reading: SensorReading) -> None:
        """Write a single sensor reading."""
        if not self._client:
            logger.warning("InfluxDB not connected — skipping write")
            return

        point = (
            Point("sensor_reading")
            .tag("zone", reading.zone)
            .tag("sensor_id", reading.sensor_id)
            .tag("sensor_type", reading.sensor_type)
            .tag("quality", reading.quality)
            .field("value", reading.value)
            .time(reading.timestamp, WritePrecision.MS)
        )
        write_api = self._client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=self._bucket, record=point)

    def write_readings_batch(self, readings: list[SensorReading]) -> None:
        """Write a batch of sensor readings."""
        if not self._client:
            logger.warning("InfluxDB not connected — skipping batch write")
            return

        points = []
        for r in readings:
            points.append(
                Point("sensor_reading")
                .tag("zone", r.zone)
                .tag("sensor_id", r.sensor_id)
                .tag("sensor_type", r.sensor_type)
                .tag("quality", r.quality)
                .field("value", r.value)
                .time(r.timestamp, WritePrecision.MS)
            )
        write_api = self._client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=self._bucket, record=points)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query_history(
        self,
        sensor_id: str,
        start: str = "-1h",
        stop: str = "now()",
        aggregation: str | None = None,
        window: str = "1m",
    ) -> list[dict]:
        """Query historical sensor data.

        Args:
            sensor_id: Sensor to query
            start: Flux time expression (e.g. "-1h", "-7d")
            stop: Flux time expression
            aggregation: "mean", "max", "min", "last", or None for raw
            window: Aggregation window (e.g. "1m", "5m", "1h")
        """
        if not self._client:
            return []

        flux = f'''
        from(bucket: "{self._bucket}")
          |> range(start: {start}, stop: {stop})
          |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
        '''
        if aggregation:
            flux += f'''
          |> aggregateWindow(every: {window}, fn: {aggregation}, createEmpty: false)
            '''
        flux += '  |> yield(name: "result")'

        query_api = self._client.query_api()
        tables = query_api.query(flux)

        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "time": record.get_time().isoformat(),
                    "value": record.get_value(),
                    "sensor_id": record.values.get("sensor_id", sensor_id),
                })
        return results

    def get_latest(self, sensor_id: str) -> dict | None:
        """Get the most recent reading for a sensor."""
        if not self._client:
            return None

        flux = f'''
        from(bucket: "{self._bucket}")
          |> range(start: -5m)
          |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
          |> last()
        '''
        query_api = self._client.query_api()
        tables = query_api.query(flux)

        for table in tables:
            for record in table.records:
                return {
                    "time": record.get_time().isoformat(),
                    "value": record.get_value(),
                    "sensor_id": sensor_id,
                }
        return None
