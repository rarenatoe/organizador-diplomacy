"""Async database connection and session management."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from pathlib import Path

from sqlalchemy import text
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
    """Create all tables if they don't exist and run migrations."""
    await _enable_foreign_keys()
    from backend.core.logger import logger
    from backend.db.models import Base

    async with async_engine.begin() as conn:
        # Step 1: Schema alteration - add notion_id column if table already exists (Legacy Migration)
        logger.info("Checking for required schema migrations...")
        try:
            # Check if the players table exists first
            table_check = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='players'")
            )

            if table_check.scalar_one_or_none():
                # Check if notion_id column exists
                column_check = await conn.execute(text("PRAGMA table_info(players)"))
                columns = column_check.fetchall()
                column_names = [col[1] for col in columns]

                if "notion_id" not in column_names:
                    logger.info("Adding notion_id column to existing players table")
                    await conn.execute(text("ALTER TABLE players ADD COLUMN notion_id VARCHAR"))
                    await conn.execute(
                        text(
                            "CREATE UNIQUE INDEX IF NOT EXISTS idx_players_notion_id ON players(notion_id)"
                        )
                    )
                    logger.info("Successfully added notion_id column and unique index")
            else:
                logger.info("Fresh database detected, skipping schema migrations")

        except Exception as e:
            logger.error(f"Error in schema alteration: {e}", exc_info=True)

        # Create tables (will create fresh schema if DB is new)
        await conn.run_sync(Base.metadata.create_all)

        # Step 2: Auto-link existing players to Notion cache (run after table creation)
        logger.info("Checking for unlinked players...")
        try:
            # Ensure columns exist before querying (handles edge cases in SQLite)
            column_check = await conn.execute(text("PRAGMA table_info(players)"))
            if "notion_id" not in [col[1] for col in column_check.fetchall()]:
                await conn.execute(text("ALTER TABLE players ADD COLUMN notion_id VARCHAR"))
                await conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS idx_players_notion_id ON players(notion_id)"
                    )
                )

            notion_table_check = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='notion_cache'")
            )
            if notion_table_check.scalar_one_or_none():
                auto_link_query = text("""
                    UPDATE players 
                    SET notion_id = (
                        SELECT notion_id FROM notion_cache 
                        WHERE notion_cache.name = players.name
                    ) 
                    WHERE notion_id IS NULL 
                    AND EXISTS (
                        SELECT 1 FROM notion_cache 
                        WHERE notion_cache.name = players.name
                    )
                """)
                result = await conn.execute(auto_link_query)
                logger.info(f"Auto-linked {result.rowcount} players to Notion cache")

        except Exception as e:
            logger.error(f"Error in auto-linking: {e}", exc_info=True)

        # Migration: unify legacy 'sync' and 'edit' edges to 'branch'
        await conn.execute(
            text(
                "UPDATE timeline_edges SET edge_type = 'branch' WHERE edge_type IN ('sync', 'edit')"
            )
        )

        logger.info("Database initialization and migration completed")


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
