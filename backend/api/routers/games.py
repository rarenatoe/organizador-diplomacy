"""Games router for /api/game/* endpoints."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession

from backend.api.models.games import (
    GameDetailResponse,
    GameDraftRequest,
    GameDraftResponse,
    GameSaveRequest,
)
from backend.crud.chain import squash_linear_branch
from backend.crud.games import save_game_draft, update_game_draft
from backend.crud.snapshots import delete_snapshot_cascade, get_snapshot_players
from backend.db.connection import get_session
from backend.db.models import TimelineEdge
from backend.db.views import get_game_event_detail
from backend.organizador.core import calculate_matches
from backend.organizador.models import DraftPlayer

router = APIRouter(prefix="/api/game")


@router.get("/{game_event_id}")
async def api_game(
    game_event_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GameDetailResponse:
    """Returns full game event detail for the detail panel."""
    detail = await get_game_event_detail(session, game_event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="not found")
    await session.commit()
    return detail


@router.delete("/{game_id}")
async def api_game_delete(
    game_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, bool]:
    """Delete a game and its output snapshot, with optional squash on parent."""
    # Query the TimelineEdge where id == game_id and edge_type == 'game'
    stmt = select(TimelineEdge).where(
        TimelineEdge.id == game_id,
        TimelineEdge.edge_type == "game",
    )
    result = await session.execute(stmt)
    edge = result.scalar_one_or_none()

    # If it doesn't exist, raise a 404 HTTPException
    if edge is None:
        raise HTTPException(status_code=404, detail="Game not found")

    # Extract the output_snapshot_id and source_snapshot_id from the edge
    output_snapshot_id = edge.output_snapshot_id
    source_snapshot_id = edge.source_snapshot_id

    # Call await delete_snapshot_cascade(session, edge.output_snapshot_id)
    await delete_snapshot_cascade(session, output_snapshot_id)

    # Call await session.flush()
    await session.flush()

    # If source_snapshot_id is not None, call await squash_linear_branch(session, edge.source_snapshot_id)
    if source_snapshot_id is not None:
        await squash_linear_branch(session, source_snapshot_id)

    # await session.commit() and return {"deleted": True}
    await session.commit()
    return {"deleted": True}


@router.post("/draft")
async def api_game_draft(
    request: GameDraftRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GameDraftResponse:
    """
    Generates a draft of game tables without saving to the database.
    Returns: DraftResult as dict
    """
    try:
        if not request.snapshot_id:
            raise HTTPException(status_code=400, detail="snapshot_id is required")

        rows = await get_snapshot_players(session, request.snapshot_id)
        jugadores: list[DraftPlayer] = [
            DraftPlayer(
                name=r.nombre,
                is_new=r.is_new,
                games_this_year=r.juegos_este_ano,
                has_priority=r.has_priority,
                desired_games=r.partidas_deseadas,
                gm_games=r.partidas_gm,
                c_england=r.c_england,
                c_france=r.c_france,
                c_germany=r.c_germany,
                c_italy=r.c_italy,
                c_austria=r.c_austria,
                c_russia=r.c_russia,
                c_turkey=r.c_turkey,
            )
            for r in rows
        ]

        # Check for duplicates
        duplicates = [n for n, c in Counter(j.name for j in jugadores).items() if c > 1]
        if duplicates:
            raise HTTPException(
                status_code=400,
                detail=f"Nombres duplicados en el snapshot: {', '.join(duplicates)}",
            )

        resultado = calculate_matches(jugadores)
        if resultado is None:
            raise HTTPException(
                status_code=400, detail="No hay suficientes jugadores para armar una partida."
            )

        await session.commit()

        return GameDraftResponse.from_domain(resultado)
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

        # Convert Pydantic model back to dict for CRUD functions
        draft_dict: dict[str, Any] = request.draft.model_dump(mode="json")

        if request.editing_game_id is not None:
            # In-place editing: check if game is a leaf node
            stmt = select(TimelineEdge).where(
                TimelineEdge.id == request.editing_game_id,
                TimelineEdge.edge_type == "game",
            )
            result = await session.execute(stmt)
            game_row: TimelineEdge | None = result.scalar_one_or_none()

            if not game_row:
                raise HTTPException(status_code=404, detail="Game not found")

            output_snapshot_id: int = game_row.output_snapshot_id

            # Check if it's a leaf node (no events source from it)
            stmt2 = (
                select(TimelineEdge)
                .where(TimelineEdge.source_snapshot_id == output_snapshot_id)
                .limit(1)
            )
            result2 = await session.execute(stmt2)
            is_leaf: bool = result2.scalar_one_or_none() is None

            if is_leaf:
                # Update existing game in place
                game_id = await update_game_draft(
                    session,
                    request.editing_game_id,
                    request.snapshot_id,
                    output_snapshot_id,
                    draft_dict,
                )
                await session.commit()
                return {"game_id": game_id}

        # Create new game (fallback or normal flow)
        game_id = await save_game_draft(session, request.snapshot_id, draft_dict)
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
