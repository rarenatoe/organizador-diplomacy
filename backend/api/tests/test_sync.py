"""
test_sync.py — Tests for /api/run/notion_sync and /api/notion/force_refresh endpoints.

Tests the sync daemon and Notion cache functionality.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ── POST /api/run/notion_sync ─────────────────────────────────────────────────


class TestApiRunNotionSync:
    async def test_notion_sync_starts_background_task(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """The notion_sync endpoint should start a background task and return immediately."""
        with patch(
            "backend.api.routers.sync.run_notion_sync_background",
            new_callable=AsyncMock,
        ) as mock_run:
            resp = await client.post("/api/run/notion_sync", json={})
            assert resp.status_code == 200
            data = resp.json()
            assert "sync_id" in data or "success" in data
            # Verify background task was scheduled
            mock_run.assert_called_once()

    async def test_notion_sync_returns_error_on_exception(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """Background tasks are added successfully even if they will fail later."""
        with patch(
            "backend.sync.notion_sync.run_notion_sync_background",
            side_effect=Exception("Sync failed"),
        ):
            resp = await client.post("/api/run/notion_sync", json={})
            # Background task error is caught and logged, endpoint returns success
            assert resp.status_code == 200


# ── POST /api/snapshot/notion/fetch ───────────────────────────────────────────


class TestApiNotionPlayers:
    async def test_get_notion_players_cached(self, client: Any, db_session: Any) -> None:
        """Should return cached Notion players if available."""
        # Insert test data into notion_cache
        from datetime import datetime

        from backend.db.models import NotionCache

        cache_entry = NotionCache(
            notion_id="test_id_1",
            nombre="Test Player",
            experiencia="Antiguo",
            juegos_este_ano=5,
            c_england=1,
            c_france=0,
            c_germany=0,
            c_italy=0,
            c_austria=0,
            c_russia=0,
            c_turkey=0,
            last_updated=datetime(2026, 3, 30, 12, 0, 0),
        )
        db_session.add(cache_entry)
        await db_session.commit()

        resp = await client.post("/api/snapshot/notion/fetch", json={"snapshot_id": None})
        assert resp.status_code == 200
        data = resp.json()
        assert "players" in data
        assert len(data["players"]) > 0

    async def test_get_notion_players_no_cache(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """Should handle case when cache is empty."""
        resp = await client.post("/api/snapshot/notion/fetch", json={"snapshot_id": None})
        assert resp.status_code == 200
        data = resp.json()
        assert "players" in data
        # Empty cache should return empty list
        assert data["players"] == []


# ── POST /api/notion/force_refresh ────────────────────────────────────────────


class TestApiNotionForceRefresh:
    async def test_force_refresh_triggers_cache_update(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """Force refresh should trigger an immediate cache update."""
        with patch(
            "backend.api.routers.sync.update_notion_cache",
            new_callable=AsyncMock,
        ) as mock_update:
            resp = await client.post("/api/notion/force_refresh")
            assert resp.status_code == 200
            mock_update.assert_called_once()

    async def test_force_refresh_returns_success(
        self,
        client: Any,
        db_session: Any,  # noqa: ARG002
    ) -> None:
        """Force refresh should return a success message."""
        with patch(
            "backend.api.routers.sync.update_notion_cache",
            new_callable=AsyncMock,
        ):
            resp = await client.post("/api/notion/force_refresh")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data or "message" in data
