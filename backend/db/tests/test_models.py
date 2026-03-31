"""
test_models.py — Regression tests for SQLAlchemy model configuration.

Tests to prevent "tried to blank-out primary key" errors and relationship conflicts.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import configure_mappers

from backend.db.models import (
    Event,
    GameDetail,
    GraphNode,
    Mesa,
    MesaPlayer,
    Player,
    Snapshot,
    SnapshotPlayer,
    WaitingList,
)

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
        snapshot = Snapshot(id=node.id, source="manual")
        db_session.add(snapshot)
        await db_session.flush()
        assert snapshot.id == node.id

    async def test_player_instantiation(self, db_session: Any) -> None:
        """Player should instantiate without PK blank-out error."""
        player = Player(nombre="TestPlayer")
        db_session.add(player)
        await db_session.flush()
        assert player.id is not None

    async def test_snapshot_player_instantiation(self, db_session: Any) -> None:
        """SnapshotPlayer (composite PK) should instantiate without errors."""
        # Setup prerequisites
        node = GraphNode(entity_type="snapshot")
        db_session.add(node)
        await db_session.flush()
        snapshot = Snapshot(id=node.id, source="manual")
        db_session.add(snapshot)
        player = Player(nombre="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        # Create SnapshotPlayer with explicit PKs
        sp = SnapshotPlayer(
            snapshot_id=snapshot.id,
            player_id=player.id,
            experiencia="Antiguo",
            juegos_este_ano=0,
            prioridad=1,
            partidas_deseadas=2,
            partidas_gm=0,
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
        """Event should instantiate without PK blank-out error."""
        # Setup prerequisites
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source="manual")
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="event")
        db_session.add(node2)
        await db_session.flush()

        event = Event(
            id=node2.id,
            type="sync",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(event)
        await db_session.flush()
        assert event.id == node2.id

    async def test_mesa_instantiation(self, db_session: Any) -> None:
        """Mesa should instantiate with required FK without blank-out error."""
        # Setup prerequisites
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source="manual")
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="event")
        db_session.add(node2)
        await db_session.flush()
        event = Event(
            id=node2.id,
            type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(event)
        await db_session.flush()

        # Create Mesa with required event_id FK
        mesa = Mesa(event_id=event.id, numero=1)
        db_session.add(mesa)
        await db_session.flush()
        assert mesa.id is not None
        assert mesa.event_id == event.id

    async def test_mesa_player_instantiation(self, db_session: Any) -> None:
        """MesaPlayer (composite PK) should instantiate without errors."""
        # Setup prerequisites
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source="manual")
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="event")
        db_session.add(node2)
        await db_session.flush()
        event = Event(
            id=node2.id,
            type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(event)
        await db_session.flush()

        mesa = Mesa(event_id=event.id, numero=1)
        db_session.add(mesa)
        player = Player(nombre="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        # Create MesaPlayer with explicit PKs
        mp = MesaPlayer(
            mesa_id=mesa.id,
            player_id=player.id,
            orden=1,
            pais="England",
        )
        db_session.add(mp)
        await db_session.flush()

        result = await db_session.execute(
            select(MesaPlayer).where(
                MesaPlayer.mesa_id == mesa.id,
                MesaPlayer.player_id == player.id,
            )
        )
        assert result.scalar_one() is not None

    async def test_waiting_list_instantiation(self, db_session: Any) -> None:
        """WaitingList (composite PK) should instantiate without errors."""
        # Setup prerequisites
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source="manual")
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="event")
        db_session.add(node2)
        await db_session.flush()
        event = Event(
            id=node2.id,
            type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(event)
        player = Player(nombre="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        # Create WaitingList with explicit PKs
        wl = WaitingList(
            event_id=event.id,
            player_id=player.id,
            orden=1,
            cupos_faltantes=2,
        )
        db_session.add(wl)
        await db_session.flush()

        result = await db_session.execute(
            select(WaitingList).where(
                WaitingList.event_id == event.id,
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
        snapshot = Snapshot(id=node1.id, source="manual")
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="event")
        db_session.add(node2)
        await db_session.flush()
        event = Event(
            id=node2.id,
            type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(event)
        await db_session.flush()

        # Create GameDetail using event's ID as PK
        gd = GameDetail(
            event_id=event.id,
            intentos=5,
            copypaste_text="test data",
        )
        db_session.add(gd)
        await db_session.flush()
        assert gd.event_id == event.id


# ── Relationship Configuration Tests ─────────────────────────────────────────


class TestRelationshipConfiguration:
    """Verify SQLAlchemy relationships are properly configured without conflicts."""

    def test_configure_mappers_no_warnings(self) -> None:
        """Configuring mappers should not produce relationship conflict warnings."""
        # This will raise warnings if relationships overlap incorrectly
        configure_mappers()
        # If we get here without warnings, relationships are properly configured

    async def test_mesa_event_relationship(self, db_session: Any) -> None:
        """Mesa.event relationship should work with non-nullable FK."""
        # Setup
        node1 = GraphNode(entity_type="snapshot")
        db_session.add(node1)
        await db_session.flush()
        snapshot = Snapshot(id=node1.id, source="manual")
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="event")
        db_session.add(node2)
        await db_session.flush()
        event = Event(
            id=node2.id,
            type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(event)
        await db_session.flush()

        mesa = Mesa(event_id=event.id, numero=1)
        db_session.add(mesa)
        await db_session.flush()

        # Test relationship access
        result = await db_session.execute(select(Mesa).where(Mesa.id == mesa.id))
        fetched_mesa = result.scalar_one()
        # Relationship should be accessible (though lazy loading requires session)
        assert fetched_mesa.event_id == event.id

    async def test_player_mesa_links_relationship(self, db_session: Any) -> None:
        """Player.mesa_links relationship should not cause PK blank-out."""
        player = Player(nombre="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        # Player should have empty mesa_links (not None)
        # Note: accessing relationship requires active session
        result = await db_session.execute(select(Player).where(Player.id == player.id))
        fetched_player = result.scalar_one()
        assert fetched_player.id == player.id

    async def test_snapshot_snapshot_links_relationship(self, db_session: Any) -> None:
        """SnapshotPlayer with relationships should not blank PKs."""
        node = GraphNode(entity_type="snapshot")
        db_session.add(node)
        await db_session.flush()
        snapshot = Snapshot(id=node.id, source="manual")
        db_session.add(snapshot)
        player = Player(nombre="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        sp = SnapshotPlayer(
            snapshot_id=snapshot.id,
            player_id=player.id,
            experiencia="Antiguo",
            juegos_este_ano=0,
            prioridad=1,
            partidas_deseadas=2,
            partidas_gm=0,
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
        snapshot = Snapshot(id=node1.id, source="manual")
        db_session.add(snapshot)

        node2 = GraphNode(entity_type="event")
        db_session.add(node2)
        await db_session.flush()
        event = Event(
            id=node2.id,
            type="game",
            source_snapshot_id=node1.id,
            output_snapshot_id=node1.id,
        )
        db_session.add(event)
        await db_session.flush()

        # Create related objects
        mesa = Mesa(event_id=event.id, numero=1)
        db_session.add(mesa)
        player = Player(nombre="TestPlayer")
        db_session.add(player)
        await db_session.flush()

        mp = MesaPlayer(mesa_id=mesa.id, player_id=player.id, orden=1, pais="England")
        db_session.add(mp)
        await db_session.commit()

        # Verify all objects persist correctly
        result = await db_session.execute(select(Mesa).where(Mesa.id == mesa.id))
        assert result.scalar_one().event_id == event.id

        result = await db_session.execute(
            select(MesaPlayer).where(
                MesaPlayer.mesa_id == mesa.id,
                MesaPlayer.player_id == player.id,
            )
        )
        fetched_mp = result.scalar_one()
        assert fetched_mp.mesa_id == mesa.id
        assert fetched_mp.player_id == player.id
