"""Async database connection and session management."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.config import DB_PATH

# Ensure data directory exists
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# Async engine with aiosqlite driver
async_engine = create_async_engine(
    f"sqlite+aiosqlite:///{DB_PATH}",
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
    echo=False,
)


async def _enable_foreign_keys() -> None:
    """Enable foreign key pragmas for SQLite (required per-connection)."""
    async with async_engine.connect() as conn:
        await conn.exec_driver_sql("PRAGMA foreign_keys = ON")
        await conn.exec_driver_sql("PRAGMA journal_mode = WAL")


async def init_db() -> None:
    """Create all tables if they don't exist."""
    await _enable_foreign_keys()
    from backend.db.models import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Migration: add pais_reason column if it doesn't exist
        from sqlalchemy import text

        cursor = await conn.execute(text("PRAGMA table_info(mesa_players)"))
        columns = [row[1] for row in cursor.fetchall()]
        if "pais_reason" not in columns:
            await conn.execute(text("ALTER TABLE mesa_players ADD COLUMN pais_reason TEXT"))


async def get_session() -> AsyncGenerator[AsyncSession]:
    """
    Async generator that yields an AsyncSession.
    Usage:
        async with get_session() as session:
            result = await session.execute(...)
    """
    async with AsyncSession(async_engine) as session:
        try:
            yield session
        finally:
            await session.close()
