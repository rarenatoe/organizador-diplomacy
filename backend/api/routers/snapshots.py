"""Snapshots router for /api/snapshot/* endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select, update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.snapshots import (
    DeleteResponse,
    HistoryState,
    NotionFetchResponse,
    NotionPlayerData,
    RenameChange,
    SimilarName,
    SnapshotDetailResponse,
    SnapshotSaveEventType,
    SnapshotSaveResponse,
)
from backend.crud.players import get_or_create_player
from backend.crud.snapshots import (
    add_player_to_snapshot,
    delete_snapshot_cascade,
    generate_deep_diff,
    get_snapshot_players,
    log_snapshot_history,
)
from backend.db.connection import get_session
from backend.db.models import (
    NotionCache,
    Player,
    Snapshot,
    SnapshotSource,
)
from backend.db.views import get_snapshot_detail
from backend.sync.matching import detect_similar_names, normalize_name


async def _insert_snapshot_players(
    session: AsyncSession,
    snapshot_id: int,
    players: list[PlayerCreate],
) -> None:
    """Insert a list of PlayerCreate into a snapshot (DRY helper)."""
    for player in players:
        if not player.nombre:
            continue
        player_id = await get_or_create_player(session, player.nombre, player.notion_id)
        await add_player_to_snapshot(
            session,
            snapshot_id,
            player_id,
            player.juegos_este_ano,
            player.partidas_deseadas,
            player.partidas_gm,
            has_priority=player.has_priority,
            is_new=player.is_new,
        )


router = APIRouter(prefix="/api/snapshot")


class PlayerCreate(BaseModel):
    nombre: str
    notion_id: str | None = None
    notion_name: str | None = None
    is_new: bool = True
    juegos_este_ano: int = 0
    has_priority: bool = False
    partidas_deseadas: int = 1
    partidas_gm: int = 0


class SnapshotCreateRequest(BaseModel):
    source: SnapshotSource = SnapshotSource.MANUAL
    parent_id: int | None = None
    players: list[PlayerCreate]


class SnapshotSaveRequest(BaseModel):
    parent_id: int | None = None
    event_type: SnapshotSaveEventType = SnapshotSaveEventType.MANUAL
    players: list[PlayerCreate]
    renames: list[RenameChange] = []


class NotionFetchRequest(BaseModel):
    snapshot_names: list[str] = []


@router.get("/{snapshot_id}")
async def api_snapshot(
    snapshot_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SnapshotDetailResponse:
    """Returns snapshot metadata + player list for the detail panel."""
    detail = await get_snapshot_detail(session, snapshot_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="not found")
    await session.commit()
    return detail


@router.delete("/{snapshot_id}")
async def api_delete_snapshot(
    snapshot_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> DeleteResponse:
    """Deletes a snapshot and all its dependent snapshots/events."""
    from backend.crud.chain import squash_linear_branch
    from backend.db.models import TimelineEdge

    try:
        # Check if snapshot exists
        result = await session.execute(select(Snapshot).where(Snapshot.id == snapshot_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="not found")

        # Collect parent snapshot IDs before deletion
        result = await session.execute(
            select(TimelineEdge.source_snapshot_id).where(
                TimelineEdge.output_snapshot_id == snapshot_id
            )
        )
        parent_ids: list[int] = [row for row in result.scalars().all() if row is not None]

        # Delete the snapshot and all its edges
        deleted = await delete_snapshot_cascade(session, snapshot_id)

        # Flush to ensure deletions are visible to the database session
        await session.flush()

        # Squash linear branches for each parent
        for parent_id in parent_ids:
            await squash_linear_branch(session, parent_id)

        await session.commit()
        return DeleteResponse(deleted=deleted)
    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/save")
async def api_snapshot_save(
    request: SnapshotSaveRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SnapshotSaveResponse:
    """
    Unified endpoint to save a new snapshot from a player list.
    Returns: {"snapshot_id": <new_id>}
    """
    from backend.crud.chain import create_branch_edge
    from backend.crud.snapshots import create_snapshot

    try:
        parent_id = request.parent_id
        event_type = request.event_type

        # Determine action type early using enum
        action_type = (
            SnapshotSource.NOTION_SYNC if event_type == "sync" else SnapshotSource.MANUAL_EDIT
        )

        # Initialize variables to appease Pylance
        previous_players = None
        diff = None

        # Validate parent exists if provided
        if parent_id is not None:
            result = await session.execute(select(Snapshot).where(Snapshot.id == parent_id))
            parent_row: Snapshot | None = result.scalar_one_or_none()
            if not parent_row:
                raise HTTPException(status_code=404, detail="parent snapshot not found")

            # Fetch old roster and calculate diff before checking children
            previous_players = await get_snapshot_players(session, parent_id)

            # Strip algorithm weight fields from previous_players to prevent phantom diffs
            # These fields come from NotionCache but aren't part of the roster
            roster_fields = {
                "nombre",
                "is_new",
                "juegos_este_ano",
                "has_priority",
                "partidas_deseadas",
                "partidas_gm",
            }
            previous_players_roster_only = [
                p.model_dump(include=roster_fields) for p in previous_players
            ]

            # Calculate diff before making changes
            new_players_dicts = [
                {
                    "nombre": p.nombre,
                    "is_new": p.is_new,
                    "juegos_este_ano": p.juegos_este_ano,
                    "has_priority": p.has_priority,
                    "partidas_deseadas": p.partidas_deseadas,
                    "partidas_gm": p.partidas_gm,
                }
                for p in request.players
            ]
            diff = generate_deep_diff(
                previous_players_roster_only, new_players_dicts, request.renames
            )

            # Apply renames before checking for no changes
            for r in request.renames:
                target_exists = await session.execute(
                    select(Player).where(Player.name == r.new_name)
                )
                if not target_exists.scalar_one_or_none():
                    await session.execute(
                        update(Player).where(Player.name == r.old_name).values(name=r.new_name)
                    )

            # No changes check - skip database writes entirely
            if not diff.added and not diff.removed and not diff.renamed and not diff.modified:
                return SnapshotSaveResponse(snapshot_id=parent_id, status="no_changes")

            # Check if parent is a leaf node (has no children)
            from backend.db.models import TimelineEdge

            result = await session.execute(
                select(TimelineEdge).where(TimelineEdge.source_snapshot_id == parent_id).limit(1)
            )
            has_children: bool = result.scalar_one_or_none() is not None

            # If parent is a leaf node, update in-place
            if not has_children:
                # Update snapshot source using enum
                parent_row.source = action_type

                # Clear old roster
                from backend.db.models import SnapshotPlayer

                await session.execute(
                    delete(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == parent_id)
                )

                # Insert new players using DRY helper
                await _insert_snapshot_players(session, parent_id, request.players)

                # Log the history using enum value
                await log_snapshot_history(
                    session,
                    snapshot_id=parent_id,
                    action_type=action_type,
                    changes=diff,
                    previous_state=HistoryState(players=previous_players),
                )

                await session.commit()
                return SnapshotSaveResponse(snapshot_id=parent_id)

            # If parent is an internal node (has children), apply STRICT GUARD
            if event_type == "sync" and parent_row.source == "notion_sync":
                raise HTTPException(
                    status_code=400,
                    detail="El snapshot base ya fue generado por notion_sync y aún no se ha jugado una partida.",
                )

        # Create snapshot with appropriate source (for internal nodes or no parent)
        source = SnapshotSource.NOTION_SYNC if event_type == "sync" else SnapshotSource.MANUAL
        snap_id = await create_snapshot(session, source)

        # Add players using DRY helper
        await _insert_snapshot_players(session, snap_id, request.players)

        # Create event linking parent to new snapshot if parent provided
        if parent_id is not None and diff is not None and previous_players is not None:
            await create_branch_edge(session, parent_id, snap_id)

            # Log the diff upon branch creation
            await log_snapshot_history(
                session,
                snapshot_id=snap_id,
                action_type=action_type,
                changes=diff,
                previous_state=HistoryState(players=previous_players),
            )

        await session.commit()
        return SnapshotSaveResponse(snapshot_id=snap_id)
    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Notion-related endpoints (also under /api/snapshot namespace for compatibility)


@router.post("/notion/fetch")
async def api_notion_fetch(
    request: NotionFetchRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> NotionFetchResponse:
    """
    Fetches raw player data from the local notion_cache table.
    Returns: {"players": [...], "similar_names": [...], "last_updated": "..."}
    """

    try:
        result = await session.execute(select(NotionCache).order_by(NotionCache.name))
        rows = result.scalars().all()

        if not rows:
            return NotionFetchResponse(players=[], similar_names=[], last_updated=None)

        players: list[NotionPlayerData] = []
        last_updated = rows[0].last_updated if rows else None

        for r in rows:
            players.append(
                NotionPlayerData(
                    notion_id=r.notion_id,
                    nombre=r.name,
                    is_new=r.is_new,
                    juegos_este_ano=r.games_this_year,
                    c_england=r.c_england or 0,
                    c_france=r.c_france or 0,
                    c_germany=r.c_germany or 0,
                    c_italy=r.c_italy or 0,
                    c_austria=r.c_austria or 0,
                    c_russia=r.c_russia or 0,
                    c_turkey=r.c_turkey or 0,
                    alias=r.alias,
                )
            )

        similar_names = []
        if request.snapshot_names:
            # Create dict with normalized names as keys and player data as values
            players_dict = {}
            for p in players:
                norm_name = normalize_name(p.nombre)
                players_dict[norm_name] = {
                    "notion_id": p.notion_id,
                    "name": p.nombre,
                    "alias": p.alias,
                }
            similar_names_raw = detect_similar_names(players_dict, request.snapshot_names)  # type: ignore
            similar_names = [SimilarName(**match) for match in similar_names_raw]

        await session.commit()
        return NotionFetchResponse(
            players=players,
            similar_names=similar_names,
            last_updated=last_updated,
        )
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
