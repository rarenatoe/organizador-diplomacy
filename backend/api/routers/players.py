"""Players router for /api/player/* endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession

from backend.db.connection import get_session
from backend.db.crud import rename_player
from backend.db.models import Player

router = APIRouter(prefix="/api/player")


class RenameRequest(BaseModel):
    old_name: str
    new_name: str


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
        result = await session.execute(select(Player).where(Player.nombre == request.old_name))
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
