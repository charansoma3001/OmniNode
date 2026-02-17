"""Centralized configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings, loaded from .env or environment."""

    # --- Anthropic ---
    anthropic_api_key: str = ""
    agent_model: str = "claude-sonnet-4-20250514"

    # --- MQTT (EMQX) ---
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_client_id: str = "mcp-agent"

    # --- InfluxDB ---
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = "mcp-dev-token"
    influxdb_org: str = "mcp-org"
    influxdb_bucket: str = "power_grid"

    # --- MCP Registry ---
    registry_host: str = "localhost"
    registry_port: int = 8000

    @property
    def registry_url(self) -> str:
        return f"http://{self.registry_host}:{self.registry_port}"

    # --- Monitoring ---
    monitor_interval_seconds: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the global settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
