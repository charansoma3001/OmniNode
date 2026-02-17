"""In-memory + JSON-file persistent store for the MCP Registry."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.common.models import MCPServerRegistration, ServerStatus

logger = logging.getLogger(__name__)

STALE_THRESHOLD = timedelta(seconds=60)
PERSIST_FILE = Path("data/registry_store.json")


class RegistryStore:
    """Thread-safe registry store backed by an in-memory dict with optional JSON persistence."""

    def __init__(self, persist: bool = True) -> None:
        self._servers: dict[str, MCPServerRegistration] = {}
        self._lock = asyncio.Lock()
        self._persist = persist

        if persist:
            PERSIST_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._load()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def register(self, registration: MCPServerRegistration) -> MCPServerRegistration:
        async with self._lock:
            registration.registered_at = datetime.utcnow()
            registration.last_heartbeat = datetime.utcnow()
            registration.status = ServerStatus.ACTIVE
            self._servers[registration.server_id] = registration
            self._save()
            logger.info("Registered MCP server: %s (%s)", registration.name, registration.server_id)
            return registration

    async def unregister(self, server_id: str) -> bool:
        async with self._lock:
            if server_id in self._servers:
                del self._servers[server_id]
                self._save()
                logger.info("Unregistered MCP server: %s", server_id)
                return True
            return False

    async def heartbeat(self, server_id: str) -> bool:
        async with self._lock:
            if server_id in self._servers:
                self._servers[server_id].last_heartbeat = datetime.utcnow()
                self._servers[server_id].status = ServerStatus.ACTIVE
                self._save()
                return True
            return False

    async def get_server(self, server_id: str) -> MCPServerRegistration | None:
        async with self._lock:
            return self._servers.get(server_id)

    async def list_servers(
        self,
        layer: str | None = None,
        domain: str | None = None,
        zone: str | None = None,
        status: ServerStatus | None = None,
    ) -> list[MCPServerRegistration]:
        async with self._lock:
            results = list(self._servers.values())
        if layer:
            results = [s for s in results if s.layer == layer]
        if domain:
            results = [s for s in results if s.domain == domain]
        if zone:
            results = [s for s in results if s.zone == zone]
        if status:
            results = [s for s in results if s.status == status]
        return results

    async def list_all_tools(self, domain: str | None = None) -> list[dict]:
        """Return a flat list of all tools across all active servers."""
        servers = await self.list_servers(status=ServerStatus.ACTIVE, domain=domain)
        tools = []
        for server in servers:
            for tool in server.tools:
                tools.append({
                    "server_id": server.server_id,
                    "server_name": server.name,
                    "layer": server.layer,
                    "zone": server.zone,
                    **tool.model_dump(),
                })
        return tools

    async def cleanup_stale(self) -> int:
        """Mark servers as stale if they haven't sent a heartbeat recently."""
        now = datetime.utcnow()
        count = 0
        async with self._lock:
            for server in self._servers.values():
                if (
                    server.status == ServerStatus.ACTIVE
                    and (now - server.last_heartbeat) > STALE_THRESHOLD
                ):
                    server.status = ServerStatus.STALE
                    count += 1
                    logger.warning("Server %s marked stale", server.server_id)
            if count:
                self._save()
        return count

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        if not self._persist:
            return
        data = {sid: s.model_dump(mode="json") for sid, s in self._servers.items()}
        PERSIST_FILE.write_text(json.dumps(data, indent=2, default=str))

    def _load(self) -> None:
        if not PERSIST_FILE.exists():
            return
        try:
            data = json.loads(PERSIST_FILE.read_text())
            for sid, sdata in data.items():
                self._servers[sid] = MCPServerRegistration(**sdata)
            logger.info("Loaded %d servers from persistent store", len(self._servers))
        except Exception as e:
            logger.warning("Failed to load registry store: %s", e)
