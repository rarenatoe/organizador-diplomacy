"""Games router for /api/game/* endpoints."""

from __future__ import annotations

import subprocess
from collections import Counter
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession

from backend.config import PROJECT_ROOT
from backend.db.connection import get_session
from backend.db.crud import get_snapshot_players
from backend.db.models import Event
from backend.db.views import get_game_event_detail
from backend.organizador.core import calcular_partidas
from backend.organizador.models import Jugador, ResultadoPartidas
from backend.organizador.persistence_async import save_game_draft_async, update_game_draft_async

router = APIRouter(prefix="/api/game")


class GameDraftRequest(BaseModel):
    snapshot_id: int


class GameSaveRequest(BaseModel):
    snapshot_id: int
    draft: dict[str, Any]
    editing_game_id: int | None = None


class RunScriptRequest(BaseModel):
    snapshot: int | None = None


@router.get("/{game_event_id}")
async def api_game(
    game_event_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Returns full game event detail for the detail panel."""
    detail = await get_game_event_detail(session, game_event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="not found")
    await session.commit()
    return detail


@router.post("/draft")
async def api_game_draft(
    request: GameDraftRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """
    Generates a draft of game tables without saving to the database.
    Returns: ResultadoPartidas as dict
    """
    try:
        if not request.snapshot_id:
            raise HTTPException(status_code=400, detail="snapshot_id is required")

        rows: list[dict[str, Any]] = await get_snapshot_players(session, request.snapshot_id)
        jugadores: list[Jugador] = [
            Jugador(
                nombre=r["nombre"],
                experiencia=r["experiencia"],
                juegos_ano=r["juegos_este_ano"],
                prioridad=str(bool(r["prioridad"])),
                partidas_deseadas=r["partidas_deseadas"],
                partidas_gm=r["partidas_gm"],
                c_england=r["c_england"],
                c_france=r["c_france"],
                c_germany=r["c_germany"],
                c_italy=r["c_italy"],
                c_austria=r["c_austria"],
                c_russia=r["c_russia"],
                c_turkey=r["c_turkey"],
            )
            for r in rows
        ]

        # Check for duplicates
        duplicates = [n for n, c in Counter(j.nombre for j in jugadores).items() if c > 1]
        if duplicates:
            raise HTTPException(
                status_code=400,
                detail=f"Nombres duplicados en el snapshot: {', '.join(duplicates)}",
            )

        resultado: ResultadoPartidas | None = calcular_partidas(jugadores)
        if resultado is None:
            raise HTTPException(
                status_code=400, detail="No hay suficientes jugadores para armar una partida."
            )

        await session.commit()
        return resultado.model_dump()
    except HTTPException:
        raise
    except AttributeError as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Attribute error: {str(exc)}") from exc
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/save")
async def api_game_save(
    request: GameSaveRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, int]:
    """
    Saves a confirmed game draft to the database.
    Supports both creating new games and updating existing games in-place.
    Returns: {"game_id": int}
    """
    try:
        if not request.snapshot_id or not request.draft:
            raise HTTPException(status_code=400, detail="snapshot_id and draft are required")

        if request.editing_game_id is not None:
            # In-place editing: check if game is a leaf node
            stmt = select(Event).where(
                Event.id == request.editing_game_id,
                Event.type == "game",
            )
            result = await session.execute(stmt)
            game_row: Event | None = result.scalar_one_or_none()

            if not game_row:
                raise HTTPException(status_code=404, detail="Game not found")

            output_snapshot_id: int = game_row.output_snapshot_id

            # Check if it's a leaf node (no events source from it)
            stmt2 = select(Event).where(Event.source_snapshot_id == output_snapshot_id).limit(1)
            result2 = await session.execute(stmt2)
            is_leaf: bool = result2.scalar_one_or_none() is None

            if is_leaf:
                # Update existing game in place
                game_id = await update_game_draft_async(
                    session,
                    request.editing_game_id,
                    request.snapshot_id,
                    output_snapshot_id,
                    request.draft,
                )
                await session.commit()
                return {"game_id": game_id}

        # Create new game (fallback or normal flow)
        game_id = await save_game_draft_async(session, request.snapshot_id, request.draft)
        await session.commit()
        return {"game_id": game_id}
    except HTTPException:
        raise
    except AttributeError as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Attribute error in save: {str(exc)}") from exc
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Note: /api/snapshots endpoint moved to snapshots.py for consistency
# This keeps all snapshot listing under the snapshot router


@router.post("/run/{script}")
async def api_run(
    script: str,
    request: RunScriptRequest,
) -> dict[str, Any]:
    """Runs a background script (e.g., notion_sync)."""
    if script not in ("notion_sync",):
        raise HTTPException(status_code=400, detail="unknown script")

    cwd = PROJECT_ROOT
    snapshot_id = request.snapshot

    SCRIPT_MODULES = {"notion_sync": "backend.sync.notion_sync"}
    cmd = ["uv", "run", "python", "-m", SCRIPT_MODULES[script]]
    if snapshot_id is not None:
        cmd += ["--snapshot", str(snapshot_id)]

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=90,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
