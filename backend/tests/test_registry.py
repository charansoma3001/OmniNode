"""Tests for the MCP Registry service."""

import pytest
from fastapi.testclient import TestClient

from src.common.models import MCPServerRegistration, ToolDescriptor, SafetyLevel
from src.registry.server import app
from src.registry.store import RegistryStore


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_registration() -> dict:
    return MCPServerRegistration(
        server_id="test_sensor_001",
        name="Test Voltage Sensor",
        layer="physical",
        domain="power_grid",
        zone="zone1",
        transport="stdio",
        tools=[
            ToolDescriptor(
                name="read_sensor",
                description="Read voltage",
                safety_level=SafetyLevel.READ_ONLY,
            ),
        ],
    ).model_dump(mode="json")


class TestRegistry:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_register_server(self, client, sample_registration):
        resp = client.post("/register", json=sample_registration)
        assert resp.status_code == 200
        data = resp.json()
        assert data["server_id"] == "test_sensor_001"
        assert data["status"] == "active"

    def test_list_servers(self, client, sample_registration):
        client.post("/register", json=sample_registration)
        resp = client.get("/servers")
        assert resp.status_code == 200
        servers = resp.json()
        assert len(servers) >= 1

    def test_list_tools(self, client, sample_registration):
        client.post("/register", json=sample_registration)
        resp = client.get("/tools")
        assert resp.status_code == 200
        tools = resp.json()
        assert any(t["name"] == "read_sensor" for t in tools)

    def test_unregister(self, client, sample_registration):
        client.post("/register", json=sample_registration)
        resp = client.delete("/unregister/test_sensor_001")
        assert resp.status_code == 200

        resp = client.get("/servers/test_sensor_001")
        assert resp.status_code == 404

    def test_heartbeat(self, client, sample_registration):
        client.post("/register", json=sample_registration)
        resp = client.post("/heartbeat/test_sensor_001")
        assert resp.status_code == 200

    def test_filter_by_layer(self, client, sample_registration):
        client.post("/register", json=sample_registration)
        resp = client.get("/servers?layer=physical")
        assert resp.status_code == 200
        assert all(s["layer"] == "physical" for s in resp.json())

    def test_filter_by_zone(self, client, sample_registration):
        client.post("/register", json=sample_registration)
        resp = client.get("/servers?zone=zone1")
        assert resp.status_code == 200
        assert all(s["zone"] == "zone1" for s in resp.json())
