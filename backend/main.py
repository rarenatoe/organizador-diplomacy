"""Main FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routers.chain import router as chain_router
from backend.api.routers.games import router as games_router
from backend.api.routers.players import router as players_router
from backend.api.routers.snapshots import router as snapshots_router
from backend.api.routers.sync import router as sync_router
from backend.config import FRONTEND_DIR
from backend.db.connection import init_db
from backend.sync.cache_daemon import daemon_loop


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    FastAPI lifespan context manager.
    Initializes database and starts background daemon.
    """
    # Startup
    await init_db()

    # Start the Notion cache daemon in the background
    daemon_task = asyncio.create_task(daemon_loop())

    yield

    # Shutdown
    daemon_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await daemon_task


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Organizador Diplomacy",
    lifespan=lifespan,
)

# Include all routers
app.include_router(chain_router)
app.include_router(snapshots_router)
app.include_router(games_router)
app.include_router(players_router)
app.include_router(sync_router)

# Mount static files
static_dir = Path(FRONTEND_DIR) / "static"
if static_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(static_dir)),
        name="static",
    )


# Catch-all route for SPA
@app.get("/{full_path:path}")
async def catch_all(_full_path: str):
    """Serve the Svelte SPA for any route."""
    index_html = Path(FRONTEND_DIR) / "templates" / "index.html"
    # Fallback to static/index.html if templates doesn't exist
    if not index_html.exists():
        index_html = static_dir / "index.html"

    if index_html.exists():
        return FileResponse(str(index_html))

    return {"message": "Organizador Diplomacy API is running"}
