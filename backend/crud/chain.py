"""Chain/timeline edge related CRUD operations.

This module contains database operations for timeline edge and branch management,
extracted from the monolithic crud.py file for better organization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    GameDetail,
    GraphNode,
    Snapshot,
    SnapshotHistory,
    SnapshotPlayer,
    TimelineEdge,
)


async def create_timeline_edge(
    session: AsyncSession,
    edge_type: str,
    source_snapshot_id: int | None,
    output_snapshot_id: int,
) -> int:
    """Create a new timeline edge and return its ID."""
    # Create graph node
    node = GraphNode(entity_type="timeline_edge")
    session.add(node)
    await session.flush()
    node_id = node.id

    # Create timeline edge
    edge = TimelineEdge(
        id=node_id,
        edge_type=edge_type,
        source_snapshot_id=source_snapshot_id,
        output_snapshot_id=output_snapshot_id,
    )
    session.add(edge)
    await session.flush()
    return edge.id


async def create_branch_edge(
    session: AsyncSession, source_snapshot_id: int, output_snapshot_id: int
) -> int:
    """Create a branch edge."""
    return await create_timeline_edge(session, "branch", source_snapshot_id, output_snapshot_id)


async def squash_linear_branch(session: AsyncSession, snapshot_id: int) -> None:
    """
    Squashes linear branch chains into a single snapshot.
    If a snapshot has EXACTLY ONE outgoing edge, and that edge is NOT a game,
    this function absorbs the child snapshot into the parent.
    """
    # Query outgoing edges from this snapshot
    result = await session.execute(
        select(TimelineEdge).where(TimelineEdge.source_snapshot_id == snapshot_id)
    )
    outgoing_edges = result.scalars().all()

    # Only squash if exactly 1 outgoing edge and it's NOT a game
    if len(outgoing_edges) != 1:
        return

    edge = outgoing_edges[0]
    if edge.edge_type == "game":
        return

    child_id = edge.output_snapshot_id

    # Step 0: Inherit source and timestamp from child
    child_snap_result = await session.execute(select(Snapshot).where(Snapshot.id == child_id))
    child_snap = child_snap_result.scalar_one()
    await session.execute(
        update(Snapshot)
        .where(Snapshot.id == snapshot_id)
        .values(source=child_snap.source, created_at=child_snap.created_at)
    )

    # Step 1: Move child's outgoing edges to parent
    await session.execute(
        update(TimelineEdge)
        .where(TimelineEdge.source_snapshot_id == child_id)
        .values(source_snapshot_id=snapshot_id)
    )

    # Step 2: Move child's history to parent
    await session.execute(
        update(SnapshotHistory)
        .where(SnapshotHistory.snapshot_id == child_id)
        .values(snapshot_id=snapshot_id)
    )

    # Step 3: Delete parent's current roster
    await session.execute(delete(SnapshotPlayer).where(SnapshotPlayer.snapshot_id == snapshot_id))

    # Step 4: Move child's roster to parent
    await session.execute(
        update(SnapshotPlayer)
        .where(SnapshotPlayer.snapshot_id == child_id)
        .values(snapshot_id=snapshot_id)
    )

    # Step 5: Delete the branch edge
    await session.execute(delete(TimelineEdge).where(TimelineEdge.id == edge.id))
    await session.execute(delete(GraphNode).where(GraphNode.id == edge.id))

    # Step 6: Delete child snapshot and its graph node
    await session.execute(delete(Snapshot).where(Snapshot.id == child_id))
    await session.execute(delete(GraphNode).where(GraphNode.id == child_id))

    # Step 7: Recursively check if we need to squash again
    await squash_linear_branch(session, snapshot_id)


async def create_game_edge(
    session: AsyncSession,
    source_snapshot_id: int,
    output_snapshot_id: int,
    attempts: int,
) -> int:
    """Create a game edge with details."""
    edge_id = await create_timeline_edge(session, "game", source_snapshot_id, output_snapshot_id)

    detail = GameDetail(
        timeline_edge_id=edge_id,
        attempts=attempts,
    )
    session.add(detail)
    return edge_id
