"""Centralized configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings, loaded from .env or environment."""

    # --- LLM (shared) ---
    llm_api_key: str = "ollama"
    llm_base_url: str = "http://ubuntu:11434"

    # --- Multi-Agent Model Assignments ---
    # Strategic agent: the "big brain" for cross-zone reasoning
    strategic_model: str = "qwen3:4b"
    # Per-zone coordinator agents: each zone gets a dedicated model instance
    zone1_model: str = "zone1:latest"
    zone2_model: str = "zone2:latest"
    zone3_model: str = "zone3:latest"
    # Safety guardian: validates actuator commands
    guardian_model: str = "llama-guard3:latest"

    # Backwards compat alias
    llm_model: str = "qwen3:4b"

    def get_zone_model(self, zone_id: str) -> str:
        """Return the model name for a specific zone."""
        zone_map = {
            "zone1": self.zone1_model,
            "zone2": self.zone2_model,
            "zone3": self.zone3_model,
        }
        return zone_map.get(zone_id, self.llm_model)

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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the global settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
