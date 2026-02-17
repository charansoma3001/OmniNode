"""FastAPI-based MCP Registry service for tool/server discovery."""

from __future__ import annotations

import asyncio
import logging

import uvicorn
from fastapi import FastAPI, HTTPException

from src.common.models import MCPServerRegistration, ServerStatus
from src.registry.store import RegistryStore

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP Registry",
    description="Central registry for MCP server and tool discovery",
    version="0.1.0",
)

store = RegistryStore()


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

async def _stale_cleanup_loop() -> None:
    """Periodic task to mark stale servers."""
    while True:
        count = await store.cleanup_stale()
        if count:
            logger.info("Cleaned up %d stale servers", count)
        await asyncio.sleep(30)


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(_stale_cleanup_loop())
    logger.info("MCP Registry started")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    servers = await store.list_servers()
    active = sum(1 for s in servers if s.status == ServerStatus.ACTIVE)
    return {"status": "ok", "total_servers": len(servers), "active_servers": active}


@app.post("/register", response_model=MCPServerRegistration)
async def register_server(registration: MCPServerRegistration) -> MCPServerRegistration:
    """Register a new MCP server (or update existing)."""
    return await store.register(registration)


@app.delete("/unregister/{server_id}")
async def unregister_server(server_id: str) -> dict:
    """Remove an MCP server from the registry."""
    removed = await store.unregister(server_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "removed", "server_id": server_id}


@app.post("/heartbeat/{server_id}")
async def heartbeat(server_id: str) -> dict:
    """Update heartbeat timestamp for a server."""
    found = await store.heartbeat(server_id)
    if not found:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "ok", "server_id": server_id}


@app.get("/servers", response_model=list[MCPServerRegistration])
async def list_servers(
    layer: str | None = None,
    domain: str | None = None,
    zone: str | None = None,
    status: ServerStatus | None = None,
) -> list[MCPServerRegistration]:
    """List registered MCP servers with optional filters."""
    return await store.list_servers(layer=layer, domain=domain, zone=zone, status=status)


@app.get("/servers/{server_id}", response_model=MCPServerRegistration)
async def get_server(server_id: str) -> MCPServerRegistration:
    """Get details for a specific MCP server."""
    server = await store.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@app.get("/tools")
async def list_tools(domain: str | None = None) -> list[dict]:
    """List all tools across all active MCP servers."""
    return await store.list_all_tools(domain=domain)


@app.get("/tools/{tool_name}")
async def get_tool(tool_name: str) -> list[dict]:
    """Find all servers providing a specific tool."""
    all_tools = await store.list_all_tools()
    matches = [t for t in all_tools if t["name"] == tool_name]
    if not matches:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return matches


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    from src.common.config import get_settings
    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.registry_port)


if __name__ == "__main__":
    main()
