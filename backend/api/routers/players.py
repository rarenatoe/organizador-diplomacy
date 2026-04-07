"""Players router for /api/player/* endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.sync.notion_sync import NotionPlayerDict, detect_similar_names

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession

from backend.crud.players import lookup_player_history, rename_player
from backend.db.connection import get_session
from backend.db.models import NotionCache, Player

router = APIRouter(prefix="/api/player")


class RenameRequest(BaseModel):
    old_name: str
    new_name: str


class LookupRequest(BaseModel):
    names: list[str]
    snapshot_id: int | None = None


class CheckSimilarityRequest(BaseModel):
    names: list[str]


@router.post("/rename")
async def api_player_rename(
    request: RenameRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """
    Rename a player in the players table.
    Returns: {"success": true} or error
    """
    try:
        if not request.old_name or not request.new_name:
            raise HTTPException(status_code=400, detail="old_name and new_name are required")

        if request.old_name == request.new_name:
            raise HTTPException(status_code=400, detail="old_name and new_name are the same")

        # Check if old player exists (404 if not)
        result = await session.execute(select(Player).where(Player.name == request.old_name))
        old_player = result.scalar_one_or_none()
        if not old_player:
            raise HTTPException(
                status_code=404,
                detail="Jugador no encontrado",
            )

        # Call rename_player - it handles merge logic internally
        success = await rename_player(session, request.old_name, request.new_name)

        if not success:
            raise HTTPException(
                status_code=409,
                detail="Conflicto al fusionar: los jugadores están en el mismo snapshot",
            )

        await session.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/all")
async def api_player_get_all(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """
    Get all known player names from database and Notion cache.
    Returns: {"names": [...]}
    """
    try:
        # Import NotionCache locally to avoid circular import issues
        from backend.db.models import NotionCache

        # Get all player names from Player table
        player_result = await session.execute(select(Player.name))
        player_names: list[str] = [row[0] for row in player_result.fetchall()]

        # Get all names and aliases from Notion cache
        notion_result = await session.execute(select(NotionCache.name, NotionCache.alias))
        notion_rows = notion_result.fetchall()

        # Extend with Notion cache names and aliases
        for row in notion_rows:
            player_names.append(row[0])  # name
            if row[1] and isinstance(row[1], list):
                player_names.extend(row[1])  # alias is JSON array

        # Remove whitespace and deduplicate
        all_names: set[str] = set()
        for name in player_names:
            clean_name = name.strip()
            if clean_name:
                all_names.add(clean_name)

        # Return sorted list
        sorted_names: list[str] = sorted(list(all_names))
        await session.commit()
        return {"names": sorted_names}
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/lookup")
async def api_player_lookup(
    request: LookupRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """
    Deep history lookup for player stats.
    Walks backward through timeline to find historical player data.
    """
    try:
        if not request.names:
            raise HTTPException(status_code=400, detail="names list cannot be empty")

        # Call the lookup function
        result = await lookup_player_history(session, request.names, request.snapshot_id)

        return {"players": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/check-similarity")
async def api_player_check_similarity(
    request: CheckSimilarityRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Checks a list of names for typos against the NotionCache."""
    try:
        result = await session.execute(select(NotionCache))
        rows = result.scalars().all()

        notion_players_list: list[NotionPlayerDict] = []
        for r in rows:
            notion_players_list.append(
                {
                    "notion_id": r.notion_id,
                    "nombre": r.name,
                    "experiencia": r.experience,
                    "juegos_este_ano": r.games_this_year,
                    "alias": r.alias or [],
                    "c_england": r.c_england,
                    "c_france": r.c_france,
                    "c_germany": r.c_germany,
                    "c_italy": r.c_italy,
                    "c_austria": r.c_austria,
                    "c_russia": r.c_russia,
                    "c_turkey": r.c_turkey,
                }
            )

        matches = detect_similar_names(notion_players_list, request.names)
        return {"similarities": matches}
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
