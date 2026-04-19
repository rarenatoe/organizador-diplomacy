"""Sync router for /api/run/* and /api/notion/* endpoints."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.sync.notion_sync import (
    run_notion_sync_background,
)

router = APIRouter()


class SyncResponse(BaseModel):
    success: bool
    message: str


class RunNotionSyncRequest(BaseModel):
    snapshot: int | None = None
    force: bool = False
    merges: dict[str, dict[str, str]] | None = None


@router.post("/api/run/notion_sync")
async def api_run_notion_sync(
    request: RunNotionSyncRequest,
    background_tasks: BackgroundTasks,
) -> SyncResponse:
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
            merges=request.merges,
        )
        return SyncResponse(
            success=True,
            message="Notion sync started in background",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
