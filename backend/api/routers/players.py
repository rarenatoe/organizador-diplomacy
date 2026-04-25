"""Players router for /api/player/* endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import TypeAdapter
from sqlalchemy import select

from backend.api.models.players import (
    CheckSimilarityRequest,
    LookupRequest,
    PlayerAutocompleteItem,
    PlayerAutocompleteResponse,
    PlayerHistoryResponse,
    PlayerSimilarityItem,
    PlayerSimilarityResponse,
    RenameRequest,
    SuccessResponse,
)
from backend.crud.players import lookup_player_history, rename_player
from backend.db.connection import get_session
from backend.db.models import NotionCache, Player
from backend.sync.matching import PlayerNameData, detect_similar_names

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession

router = APIRouter(prefix="/api/player")


@router.post("/rename")
async def api_player_rename(
    request: RenameRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SuccessResponse:
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
        return SuccessResponse(success=True)
    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/all")
async def api_player_get_all(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> PlayerAutocompleteResponse:
    """Get all known players. Returns rich, unformatted objects to power UI autocomplete."""
    try:
        player_result = await session.execute(select(Player.name, Player.notion_id))
        local_players = player_result.fetchall()

        results: list[PlayerAutocompleteItem] = []
        local_notion_ids: set[str] = set()

        # 1. Local Players (No deduplication needed; SQLite UNIQUE constraint guarantees local name uniqueness)
        for player_name, notion_id in local_players:
            clean_name = player_name.strip() if player_name else ""
            if clean_name:
                results.append(
                    PlayerAutocompleteItem(
                        display=clean_name,
                        nombre=clean_name,
                        notion_id=notion_id,
                        notion_name=None,
                        is_local=True,
                        is_alias=False,
                    )
                )
                if notion_id:
                    local_notion_ids.add(notion_id)

        # 2. Notion Players & Aliases (Only if not handled locally)
        notion_result = await session.execute(select(NotionCache))
        notion_rows = notion_result.scalars().all()

        for notion_data in notion_rows:
            if notion_data.notion_id not in local_notion_ids:
                canonical_name = notion_data.name.strip() if notion_data.name else ""

                if canonical_name:
                    results.append(
                        PlayerAutocompleteItem(
                            display=canonical_name,
                            nombre=canonical_name,
                            notion_id=notion_data.notion_id,
                            notion_name=canonical_name,
                            is_local=False,
                            is_alias=False,
                        )
                    )

                # Deduplicate aliases ONLY within this specific person's profile
                if notion_data.alias:
                    seen_aliases_for_person = {canonical_name.lower()}
                    for alias in notion_data.alias:
                        clean_alias = alias.strip()
                        if clean_alias and clean_alias.lower() not in seen_aliases_for_person:
                            results.append(
                                PlayerAutocompleteItem(
                                    display=clean_alias,
                                    nombre=clean_alias,
                                    notion_id=notion_data.notion_id,
                                    notion_name=canonical_name,
                                    is_local=False,
                                    is_alias=True,
                                )
                            )
                            seen_aliases_for_person.add(clean_alias.lower())

        # Sort alphabetically by lowercased display name, but return the preserved case
        results.sort(key=lambda x: x.display.lower())
        return PlayerAutocompleteResponse(players=results)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/lookup")
async def api_player_lookup(
    request: LookupRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> PlayerHistoryResponse:
    """Targeted deep history lookup. Prioritizes notion_id if provided."""
    try:
        result = await lookup_player_history(
            session, request.name, request.notion_id, request.snapshot_id
        )
        return PlayerHistoryResponse(player=result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/check-similarity")
async def api_player_check_similarity(
    request: CheckSimilarityRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> PlayerSimilarityResponse:
    """Checks a list of names for typos against the NotionCache."""
    try:
        result = await session.execute(
            select(NotionCache.notion_id, NotionCache.name, NotionCache.alias)
        )

        notion_players_list: list[PlayerNameData] = [
            {
                "notion_id": row.notion_id,
                "name": row.name,
                "alias": row.alias,
            }
            for row in result.all()
        ]

        matches = detect_similar_names(notion_players_list, request.names)

        # Cross-reference matches with existing local players
        if matches:
            # Type-safe: 'notion_id' is guaranteed to exist by PlayerSimilarityDict
            notion_ids = [m["notion_id"] for m in matches]

            if notion_ids:
                existing_players = await session.execute(
                    select(Player.notion_id, Player.name).where(Player.notion_id.in_(notion_ids))
                )
                existing_map = {row[0]: row[1] for row in existing_players.fetchall()}
                for m in matches:
                    if m["notion_id"] in existing_map:
                        # Adding optional key natively permitted by NotRequired
                        m["existing_local_name"] = existing_map[m["notion_id"]]

        items = TypeAdapter(list[PlayerSimilarityItem]).validate_python(matches)
        return PlayerSimilarityResponse(similarities=items)

    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
