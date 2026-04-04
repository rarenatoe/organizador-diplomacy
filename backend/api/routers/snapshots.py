"""Snapshots router for /api/snapshot/* endpoints."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from notion_client import Client
from pydantic import BaseModel
from sqlalchemy import delete, select, update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.connection import get_session
from backend.db.crud import (
    add_player_to_snapshot,
    create_root_manual_snapshot,
    delete_snapshot_cascade,
    generate_deep_diff,
    get_or_create_player,
    get_snapshot_players,
    log_snapshot_history,
)
from backend.db.models import (
    HistoryActionType,
    NotionCache,
    Player,
    RenameDict,
    Snapshot,
    SnapshotPlayer,
)
from backend.db.views import get_snapshot_detail
from backend.sync.cache_daemon import update_notion_cache
from backend.sync.notion_sync import (
    detect_similar_names,
    normalize_name,
)


async def _insert_snapshot_players(
    session: AsyncSession,
    snapshot_id: int,
    players: list[PlayerCreate],
) -> None:
    """Insert a list of PlayerCreate into a snapshot (DRY helper)."""
    for player in players:
        if not player.nombre:
            continue
        player_id = await get_or_create_player(session, player.nombre)
        await add_player_to_snapshot(
            session,
            snapshot_id,
            player_id,
            player.experiencia,
            player.juegos_este_ano,
            player.prioridad,
            player.partidas_deseadas,
            player.partidas_gm,
        )



router = APIRouter(prefix="/api/snapshot")


class PlayerCreate(BaseModel):
    nombre: str
    experiencia: str = "Nuevo"
    juegos_este_ano: int = 0
    prioridad: int = 0
    partidas_deseadas: int = 1
    partidas_gm: int = 0


class SnapshotCreateRequest(BaseModel):
    source: str = "manual"
    parent_id: int | None = None
    players: list[PlayerCreate]


class SnapshotSaveRequest(BaseModel):
    parent_id: int | None = None
    event_type: str = "manual"
    players: list[PlayerCreate]
    renames: list[RenameDict] = []


class NotionFetchRequest(BaseModel):
    snapshot_names: list[str] = []


class AddPlayerRequest(BaseModel):
    nombre: str
    experiencia: str = "Nuevo"
    juegos_este_ano: int = 0
    prioridad: int = 0
    partidas_deseadas: int = 1
    partidas_gm: int = 0


@router.get("")
async def api_snapshot_list(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Returns a list of all snapshots with player counts."""
    from sqlalchemy import func

    result = await session.execute(
        select(Snapshot, func.count(SnapshotPlayer.player_id).label("player_count"))
        .outerjoin(SnapshotPlayer, Snapshot.id == SnapshotPlayer.snapshot_id)
        .group_by(Snapshot.id)
        .order_by(Snapshot.id)
    )
    snapshots: list[dict[str, Any]] = []
    for snap, count in result.all():
        snapshots.append(
            {
                "id": snap.id,
                "created_at": snap.created_at.isoformat() if snap.created_at else None,
                "source": snap.source,
                "player_count": count,
            }
        )
    return {"snapshots": snapshots}


@router.post("")
async def api_create_snapshot_root(
    request: SnapshotCreateRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, int]:
    """
    Creates a new snapshot. If parent_id is provided, links to parent via event.
    Returns: {"snapshot_id": <new_id>}
    """
    from backend.db.crud import create_branch_edge, create_snapshot, get_or_create_player

    try:
        # If parent_id provided, check if parent exists
        parent_id = request.parent_id
        if parent_id is not None:
            result = await session.execute(select(Snapshot).where(Snapshot.id == parent_id))
            parent_row = result.scalar_one_or_none()
            if not parent_row:
                raise HTTPException(status_code=404, detail="parent snapshot not found")

        # Create new snapshot
        snap_id = await create_snapshot(session, request.source)

        # Add players
        for player in request.players:
            if not player.nombre:
                continue
            player_id = await get_or_create_player(session, player.nombre)
            await add_player_to_snapshot(
                session,
                snap_id,
                player_id,
                player.experiencia,
                player.juegos_este_ano,
                player.prioridad,
                player.partidas_deseadas,
                player.partidas_gm,
            )

        # Create event linking to parent if provided
        if parent_id is not None:
            await create_branch_edge(session, parent_id, snap_id)

        await session.commit()
        return {"snapshot_id": snap_id}
    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{snapshot_id}")
async def api_snapshot(
    snapshot_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
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
) -> dict[str, Any]:
    """Deletes a snapshot and all its dependent snapshots/events."""
    from backend.db.crud import squash_linear_branch
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
        return {"deleted": deleted}
    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/new")
async def api_create_snapshot(
    request: SnapshotCreateRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, int]:
    """
    Creates a new root 'manual' snapshot (no source snapshot).
    Returns: {"snapshot_id": <new_id>}
    """
    try:
        players_data = [
            {
                "nombre": p.nombre,
                "experiencia": p.experiencia,
                "juegos_este_ano": p.juegos_este_ano,
                "prioridad": p.prioridad,
                "partidas_deseadas": p.partidas_deseadas,
                "partidas_gm": p.partidas_gm,
            }
            for p in request.players
        ]
        new_id = await create_root_manual_snapshot(session, players_data)
        await session.commit()
        return {"snapshot_id": new_id}
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{snapshot_id}/save")
async def api_snapshot_save_by_id(
    snapshot_id: int,
    request: SnapshotCreateRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, int]:
    """
    Save/update a snapshot's players and metadata by ID.
    Returns: {"snapshot_id": <id>}
    """

    try:
        # Check if snapshot exists
        result = await session.execute(select(Snapshot).where(Snapshot.id == snapshot_id))
        snap = result.scalar_one_or_none()
        if not snap:
            raise HTTPException(status_code=404, detail="snapshot not found")

        # Update source
        snap.source = request.source

        # Clear old roster
        await session.execute(
            delete(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snapshot_id)
        )

        # Add new players
        for player in request.players:
            if not player.nombre:
                continue
            player_id = await get_or_create_player(session, player.nombre)
            await add_player_to_snapshot(
                session,
                snapshot_id,
                player_id,
                player.experiencia,
                player.juegos_este_ano,
                player.prioridad,
                player.partidas_deseadas,
                player.partidas_gm,
            )

        await session.commit()
        return {"snapshot_id": snapshot_id}
    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/save")
async def api_snapshot_save(
    request: SnapshotSaveRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, int | str]:
    """
    Unified endpoint to save a new snapshot from a player list.
    Returns: {"snapshot_id": <new_id>}
    """
    from backend.db.crud import (
        add_player_to_snapshot,
        create_branch_edge,
        create_snapshot,
        get_or_create_player,
    )

    try:
        parent_id = request.parent_id
        event_type = request.event_type

        if event_type not in ("manual", "sync"):
            raise HTTPException(status_code=400, detail="event_type must be 'manual' or 'sync'")

        # Determine action type early using enum
        action_type = (
            HistoryActionType.NOTION_SYNC if event_type == "sync" else HistoryActionType.MANUAL_EDIT
        )

        # Validate parent exists if provided
        if parent_id is not None:
            result = await session.execute(select(Snapshot).where(Snapshot.id == parent_id))
            parent_row: Snapshot | None = result.scalar_one_or_none()
            if not parent_row:
                raise HTTPException(status_code=404, detail="parent snapshot not found")

            # Check if parent is a leaf node (has no children)
            from backend.db.models import TimelineEdge

            result = await session.execute(
                select(TimelineEdge).where(TimelineEdge.source_snapshot_id == parent_id).limit(1)
            )
            has_children: bool = result.scalar_one_or_none() is not None

            # If parent is a leaf node, update in-place
            if not has_children:
                # Update snapshot source using enum
                parent_row.source = action_type.value

                # Fetch old roster before clearing
                previous_players = await get_snapshot_players(session, parent_id)

                # Strip algorithm weight fields from previous_players to prevent phantom diffs
                # These fields come from NotionCache but aren't part of the roster
                roster_fields = {"nombre", "experiencia", "juegos_este_ano", "prioridad", "partidas_deseadas", "partidas_gm"}
                previous_players_roster_only = [
                    {k: v for k, v in p.items() if k in roster_fields}
                    for p in previous_players
                ]

                # Calculate diff before making changes
                new_players_dicts = [
                    {
                        "nombre": p.nombre,
                        "experiencia": p.experiencia,
                        "juegos_este_ano": p.juegos_este_ano,
                        "prioridad": p.prioridad,
                        "partidas_deseadas": p.partidas_deseadas,
                        "partidas_gm": p.partidas_gm,
                    }
                    for p in request.players
                ]
                diff = generate_deep_diff(previous_players_roster_only, new_players_dicts, request.renames)

                for r in request.renames:
                    target_exists = await session.execute(select(Player).where(Player.name == r["to"]))
                    if not target_exists.scalar_one_or_none():
                        await session.execute(
                            update(Player).where(Player.name == r["from"]).values(name=r["to"])
                        )

                # No changes check - skip database writes entirely
                if (
                    not diff["added"]
                    and not diff["removed"]
                    and not diff["renamed"]
                    and not diff["modified"]
                ):
                    return {"snapshot_id": parent_id, "status": "no_changes"}

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
                    action_type=action_type.value,
                    changes=diff,
                    previous_state={"players": previous_players},
                )

                await session.commit()
                return {"snapshot_id": parent_id}

            # If parent is an internal node (has children), apply STRICT GUARD
            if event_type == "sync" and parent_row.source == "notion_sync":
                raise HTTPException(
                    status_code=400,
                    detail="El snapshot base ya fue generado por notion_sync y aún no se ha jugado una partida.",
                )

        # Create snapshot with appropriate source (for internal nodes or no parent)
        source = "notion_sync" if event_type == "sync" else "manual"
        snap_id = await create_snapshot(session, source)

        # Add players with defaults for missing fields
        for player in request.players:
            if not player.nombre:
                continue
            player_id = await get_or_create_player(session, player.nombre)
            await add_player_to_snapshot(
                session,
                snap_id,
                player_id,
                player.experiencia,
                player.juegos_este_ano,
                player.prioridad,
                player.partidas_deseadas,
                player.partidas_gm,
            )

        # Create event linking parent to new snapshot if parent provided
        if parent_id is not None:
            await create_branch_edge(session, parent_id, snap_id)

        await session.commit()
        return {"snapshot_id": snap_id}
    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{snapshot_id}/add-player")
async def api_add_player(
    snapshot_id: int,
    request: AddPlayerRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, int]:
    """Add a player to a snapshot."""
    try:
        # Check if snapshot exists
        result = await session.execute(select(Snapshot).where(Snapshot.id == snapshot_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="snapshot not found")

        if not request.nombre:
            raise HTTPException(status_code=400, detail="nombre is required")

        player_id = await get_or_create_player(session, request.nombre)

        # Check if player already exists in this snapshot
        existing = await session.execute(
            select(SnapshotPlayer).where(
                SnapshotPlayer.snapshot_id == snapshot_id, SnapshotPlayer.player_id == player_id
            )
        )
        if existing.scalar_one_or_none():
            # Player already exists in snapshot, just return their ID
            await session.commit()
            return {"player_id": player_id}

        await add_player_to_snapshot(
            session,
            snapshot_id,
            player_id,
            request.experiencia,
            request.juegos_este_ano,
            request.prioridad,
            request.partidas_deseadas,
            request.partidas_gm,
        )
        await session.commit()
        return {"player_id": player_id}
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
) -> dict[str, Any]:
    """
    Fetches raw player data from the local notion_cache table.
    Returns: {"players": [...], "similar_names": [...], "last_updated": "..."}
    """

    try:
        result = await session.execute(select(NotionCache).order_by(NotionCache.name))
        rows = result.scalars().all()

        if not rows:
            return {"players": [], "similar_names": [], "last_updated": None}

        players: list[dict[str, Any]] = []
        last_updated = rows[0].last_updated if rows else None

        for r in rows:
            players.append(
                {
                    "nombre": r.name,
                    "experiencia": r.experience,
                    "juegos_este_ano": r.games_this_year,
                    "c_england": r.c_england,
                    "c_france": r.c_france,
                    "c_germany": r.c_germany,
                    "c_italy": r.c_italy,
                    "c_austria": r.c_austria,
                    "c_russia": r.c_russia,
                    "c_turkey": r.c_turkey,
                }
            )

        similar_names = []
        if request.snapshot_names:
            # Create dict with normalized names as keys and player data as values
            players_dict = {}
            for p in players:
                norm_name = normalize_name(p["nombre"])
                players_dict[norm_name] = p
            similar_names = detect_similar_names(players_dict, request.snapshot_names)  # type: ignore

        await session.commit()
        return {
            "players": players,
            "similar_names": similar_names,
            "last_updated": last_updated,
        }
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/notion/force_refresh")
async def api_notion_force_refresh(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """
    Manually triggers a Notion cache update synchronously.
    Returns: {"success": true, "message": "..."}
    """
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")
    part_db_id = os.getenv("NOTION_PARTICIPACIONES_DB_ID")

    if not token or not db_id or not part_db_id:
        raise HTTPException(status_code=500, detail="Notion credentials not configured")
    if token.startswith("secret_XXX"):
        raise HTTPException(status_code=500, detail="Notion token is a placeholder value")

    client = Client(auth=token)
    try:
        await update_notion_cache(session, client, db_id, part_db_id)
        await session.commit()
        return {"success": True, "message": "Cache updated successfully"}
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
