"""Chain router for /api/chain endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession

from backend.db.connection import get_session
from backend.db.views import build_chain_data

router = APIRouter(prefix="/api")


@router.get("/chain")
async def api_chain(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Returns the full chain tree for the timeline view."""
    try:
        data = await build_chain_data(session)
        await session.commit()
        return data
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
