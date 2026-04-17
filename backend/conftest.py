"""
conftest.py — Pytest configuration and shared async fixtures.

This file is automatically loaded by pytest and provides async fixtures
to all test files in the backend directory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.connection import get_session
from backend.db.models import Base
from backend.main import app

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Creates an in-memory SQLite database with all tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Async HTTP client with db_session injected via dependency override."""

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def add_snapshot(
    db_session: AsyncSession, source: str = "notion_sync", players: int = 5
) -> int:
    """Creates a snapshot with `players` dummy players and returns the snapshot id."""
    from backend.crud.players import get_or_create_player
    from backend.crud.snapshots import (
        add_player_to_snapshot,
        create_snapshot,
    )

    snap_id = await create_snapshot(db_session, source)
    for i in range(players):
        pid = await get_or_create_player(db_session, f"Jugador_{snap_id}_{i}")
        await add_player_to_snapshot(
            db_session, snap_id, pid, i, 1, 0, has_priority=False, is_new=False
        )
    await db_session.commit()
    return snap_id
