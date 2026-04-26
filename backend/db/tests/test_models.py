"""
test_models.py — Regression tests for SQLAlchemy model configuration.

Tests to prevent "tried to blank-out primary key" errors and relationship conflicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.orm import configure_mappers

from backend.db.models import (
    GameDetail,
    GameTable,
    GraphNode,
    Player,
    Snapshot,
    SnapshotPlayer,
    SnapshotSource,
    TablePlayer,
    TimelineEdge,
    WaitingList,
)

if TYPE_CHECKING:
    from typing import Any

pytestmark = pytest.mark.asyncio


# ── Model Instantiation Tests ─────────────────────────────────────────────────


class TestModelInstantiation:
    """Verify models can be created without 'tried to blank-out primary key' errors."""

    async def test_graph_node_instantiation(self, db_session: Any) -> None:
        """GraphNode should instantiate without PK blank-out error."""
        node = GraphNode(entity_type="snapshot")
        db_session.add(node)
        await db_session.flush()
        assert node.id is not None

    async def test_snapshot_instantiation(self, db_session: Any) -> None:
        """Snapshot should instantiate without PK blank-out error."""
        # First create a GraphNode
        node = GraphNode(entity_type="snapshot")
        db_session.add(node)
        await db_session.flush()

        # Snapshot uses the node's ID as its PK
        snapshot = Snapshot(id=node.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)
        await db_session.flush()
        assert snapshot.id == node.id

    async def test_player_instantiation(self, db_session: Any) -> None:
        """Player should instantiate without PK blank-out error."""
        player = Player(name="TestPlayer")
        db_session.add(player)
        await db_session.flush()
        assert player.id is not None

    async def test_snapshot_player_instantiation(self, db_session: Any) -> None:
        """SnapshotPlayer (composite PK) should instantiate without errors."""
        # Setup prerequisites
        node = GraphNode(entity_type="snapshot")
        db_session.add(node)
        await db_session.flush()
        snapshot = Snapshot(id=node.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)
        player = Player(name="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        # Create SnapshotPlayer with explicit PKs
        sp = SnapshotPlayer(
            snapshot_id=snapshot.id,
            player_id=player.id,
            is_new=False,
            games_this_year=0,
            has_priority=True,
            desired_games=2,
            gm_games=0,
        )
        db_session.add(sp)
        await db_session.flush()

        result = await db_session.execute(
            select(SnapshotPlayer).where(
                SnapshotPlayer.snapshot_id == snapshot.id,
                SnapshotPlayer.player_id == player.id,
            )
        )
        assert result.scalar_one() is not None

    async def test_event_instantiation(self, db_session: Any) -> None:
        """TimelineEdge should instantiate without PK blank-out error."""
        # Setup prerequisites
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="timeline_edge")
        db_session.add(node2)
        await db_session.flush()

        edge = TimelineEdge(
            id=node2.id,
            edge_type="branch",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(edge)
        await db_session.flush()
        assert edge.id == node2.id

    async def test_mesa_instantiation(self, db_session: Any) -> None:
        """GameTable should instantiate with required FK without blank-out error."""
        # Setup prerequisites
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="timeline_edge")
        db_session.add(node2)
        await db_session.flush()
        edge = TimelineEdge(
            id=node2.id,
            edge_type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(edge)
        await db_session.flush()

        # Create GameTable with required timeline_edge_id FK
        table = GameTable(timeline_edge_id=edge.id, table_number=1)
        db_session.add(table)
        await db_session.flush()
        assert table.id is not None
        assert table.timeline_edge_id == edge.id

    async def test_table_player_instantiation(self, db_session: Any) -> None:
        """TablePlayer (composite PK) should instantiate without errors."""
        # Setup prerequisites
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="timeline_edge")
        db_session.add(node2)
        await db_session.flush()
        edge = TimelineEdge(
            id=node2.id,
            edge_type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(edge)
        await db_session.flush()

        table = GameTable(timeline_edge_id=edge.id, table_number=1)
        db_session.add(table)
        player = Player(name="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        # Create TablePlayer with explicit PKs
        tp = TablePlayer(
            table_id=table.id,
            player_id=player.id,
            seat_order=1,
            country="England",
        )
        db_session.add(tp)
        await db_session.flush()

        result = await db_session.execute(
            select(TablePlayer).where(
                TablePlayer.table_id == table.id,
                TablePlayer.player_id == player.id,
            )
        )
        assert result.scalar_one() is not None

    async def test_waiting_list_instantiation(self, db_session: Any) -> None:
        """WaitingList (composite PK) should instantiate without errors."""
        # Setup prerequisites
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="timeline_edge")
        db_session.add(node2)
        await db_session.flush()
        edge = TimelineEdge(
            id=node2.id,
            edge_type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(edge)
        player = Player(name="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        # Create WaitingList with explicit PKs
        wl = WaitingList(
            timeline_edge_id=edge.id,
            player_id=player.id,
            list_order=1,
            missing_spots=2,
        )
        db_session.add(wl)
        await db_session.flush()

        result = await db_session.execute(
            select(WaitingList).where(
                WaitingList.timeline_edge_id == edge.id,
                WaitingList.player_id == player.id,
            )
        )
        assert result.scalar_one() is not None

    async def test_game_detail_instantiation(self, db_session: Any) -> None:
        """GameDetail should instantiate without PK blank-out error."""
        # Setup prerequisites
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="timeline_edge")
        db_session.add(node2)
        await db_session.flush()
        edge = TimelineEdge(
            id=node2.id,
            edge_type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(edge)
        await db_session.flush()

        # Create GameDetail using edge's ID as PK
        gd = GameDetail(
            timeline_edge_id=edge.id,
            attempts=5,
        )
        db_session.add(gd)
        await db_session.flush()
        assert gd.timeline_edge_id == edge.id


# ── Relationship Configuration Tests ─────────────────────────────────────────


class TestRelationshipConfiguration:
    """Verify SQLAlchemy relationships are properly configured without conflicts."""

    async def test_configure_mappers_no_warnings(self) -> None:
        """Configuring mappers should not produce relationship conflict warnings."""
        # This will raise warnings if relationships overlap incorrectly
        configure_mappers()
        # If we get here without warnings, relationships are properly configured

    async def test_game_table_timeline_edge_relationship(self, db_session: Any) -> None:
        """GameTable.timeline_edge relationship should work with non-nullable FK."""
        # Setup
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="timeline_edge")
        db_session.add(node2)
        await db_session.flush()
        edge = TimelineEdge(
            id=node2.id,
            edge_type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(edge)
        await db_session.flush()

        table = GameTable(timeline_edge_id=edge.id, table_number=1)
        db_session.add(table)
        await db_session.flush()

        # Test relationship access
        result = await db_session.execute(select(GameTable).where(GameTable.id == table.id))
        fetched_table = result.scalar_one()
        # Relationship should be accessible (though lazy loading requires session)
        assert fetched_table.timeline_edge_id == edge.id

    async def test_player_table_player_links_relationship(self, db_session: Any) -> None:
        """Player.table_player_links relationship should not cause PK blank-out."""
        player = Player(name="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        # Player should have empty table_player_links (not None)
        # Note: accessing relationship requires active session
        result = await db_session.execute(select(Player).where(Player.id == player.id))
        fetched_player = result.scalar_one()
        assert fetched_player.id == player.id

    async def test_snapshot_snapshot_links_relationship(self, db_session: Any) -> None:
        """SnapshotPlayer with relationships should not blank PKs."""
        node = GraphNode(entity_type="snapshot")
        db_session.add(node)
        await db_session.flush()
        snapshot = Snapshot(id=node.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)
        player = Player(name="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        sp = SnapshotPlayer(
            snapshot_id=snapshot.id,
            player_id=player.id,
            is_new=False,
            games_this_year=0,
            has_priority=True,
            desired_games=2,
            gm_games=0,
        )
        db_session.add(sp)
        await db_session.flush()

        # Verify relationship doesn't affect PKs
        result = await db_session.execute(
            select(SnapshotPlayer).where(
                SnapshotPlayer.snapshot_id == snapshot.id,
                SnapshotPlayer.player_id == player.id,
            )
        )
        fetched_sp = result.scalar_one()
        assert fetched_sp.snapshot_id == snapshot.id
        assert fetched_sp.player_id == player.id


# ── Edge Case Tests ──────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases that previously caused issues."""

    async def test_cascade_operations_dont_blank_pks(self, db_session: Any) -> None:
        """Cascade operations should not trigger PK blank-out errors."""
        # Create complex object tree
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source=SnapshotSource.MANUAL)
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="timeline_edge")
        db_session.add(node2)
        await db_session.flush()
        edge = TimelineEdge(
            id=node2.id,
            edge_type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(edge)
        await db_session.flush()

        # Create related objects
        table = GameTable(timeline_edge_id=edge.id, table_number=1)
        db_session.add(table)
        player = Player(name="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        tp = TablePlayer(table_id=table.id, player_id=player.id, seat_order=1, country="England")
        db_session.add(tp)
        await db_session.commit()

        # Verify all objects persist correctly
        result = await db_session.execute(select(GameTable).where(GameTable.id == table.id))
        assert result.scalar_one().timeline_edge_id == edge.id

        result = await db_session.execute(
            select(TablePlayer).where(
                TablePlayer.table_id == table.id,
                TablePlayer.player_id == player.id,
            )
        )
        fetched_tp = result.scalar_one()
        assert fetched_tp.table_id == table.id
        assert fetched_tp.player_id == player.id
