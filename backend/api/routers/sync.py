"""Sync router for /api/run/* and /api/notion/* endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.db.connection import async_engine
from backend.sync.cache_daemon import update_notion_cache_async
from backend.sync.notion_sync import run_notion_sync_background

router = APIRouter()


class RunNotionSyncRequest(BaseModel):
    snapshot: int | None = None
    force: bool = False


@router.post("/api/run/notion_sync")
async def api_run_notion_sync(
    request: RunNotionSyncRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Enqueues notion_sync to run in the background.
    Returns immediately with success message.
    """
    try:
        # Enqueue the background task with its own session
        background_tasks.add_task(
            run_notion_sync_background,
            request.snapshot,
            force=request.force,
        )
        return {
            "success": True,
            "message": "Notion sync started in background",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/notion/force_refresh")
async def api_notion_force_refresh(
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Manually triggers a Notion cache update in the background.
    Returns immediately with success message.
    """
    try:
        background_tasks.add_task(_run_cache_refresh)
        return {
            "success": True,
            "message": "Cache refresh started in background",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _run_cache_refresh() -> None:
    """Helper to run cache refresh with a new session."""
    import os

    from dotenv import load_dotenv
    from notion_client import Client

    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not token or not db_id or not part_db_id or token.startswith("secret_XXX"):
        print("[Cache Refresh] Skipping: Missing Notion credentials")
        return

    client = Client(auth=token)

    from sqlalchemy.ext.asyncio.session import AsyncSession

    async with AsyncSession(async_engine) as session:
        try:
            await update_notion_cache_async(session, client, db_id, part_db_id)
            await session.commit()
            print("[Cache Refresh] Completed successfully")
        except Exception as e:
            await session.rollback()
            print(f"[Cache Refresh] Error: {e}")
        finally:
            await session.close()
