"""SQLAlchemy database schemas for the Diplomacy organizer."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from sqlalchemy import JSON, ForeignKey, String, TypeDecorator, func
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect

    # We import these ONLY for Pyright autocomplete to avoid circular imports!


class PydanticJSON(TypeDecorator[BaseModel | dict[str, Any]]):
    """Seamlessly converts Pydantic models to JSON dictionaries on database write."""

    impl = JSON
    cache_ok = True

    def process_bind_param(
        self,
        value: BaseModel | dict[str, Any] | None,
        dialect: Dialect,
    ) -> dict[str, Any] | list[Any] | None:
        del dialect
        if value is None:
            return None
        if isinstance(value, BaseModel):
            return value.model_dump(by_alias=True)
        return value

    def process_result_value(
        self,
        value: dict[str, Any] | None,
        dialect: Dialect,
    ) -> dict[str, Any] | None:
        del dialect
        return value


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class GraphNode(Base, kw_only=True):
    """Universal IDs for all entities (snapshots and events)."""

    __tablename__ = "graph_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    entity_type: Mapped[str] = mapped_column()

    # Relationships
    snapshot: Mapped[Snapshot | None] = relationship(uselist=False, init=False)
    timeline_edge: Mapped[TimelineEdge | None] = relationship(uselist=False, init=False)


class Player(Base, kw_only=True):
    """Unique player records."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(collation="NOCASE"), unique=True)
    notion_id: Mapped[str | None] = mapped_column(default=None)

    # Relationships
    snapshot_links: Mapped[list[SnapshotPlayer]] = relationship(init=False)
    table_player_links: Mapped[list[TablePlayer]] = relationship(init=False)
    tables_as_gm: Mapped[list[GameTable]] = relationship(back_populates="gm_player", init=False)
    waiting_list_entries: Mapped[list[WaitingList]] = relationship(
        back_populates="player", init=False
    )


class SnapshotSource(StrEnum):
    MANUAL = "manual"
    MANUAL_EDIT = "manual_edit"
    NOTION_SYNC = "notion_sync"
    ORGANIZAR = "organizar"


class Snapshot(Base, kw_only=True):
    """Point-in-time roster snapshots."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(ForeignKey("graph_nodes.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    source: Mapped[SnapshotSource] = mapped_column()

    # Relationships
    history_logs: Mapped[list[SnapshotHistory]] = relationship(
        init=False, cascade="all, delete-orphan"
    )


class SnapshotPlayer(Base, kw_only=True):
    """Many-to-many link between snapshots and players with game data."""

    __tablename__ = "snapshot_players"

    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    is_new: Mapped[bool] = mapped_column(default=False)
    games_this_year: Mapped[int] = mapped_column(default=0)
    has_priority: Mapped[bool] = mapped_column(default=False)
    desired_games: Mapped[int] = mapped_column(default=1)
    gm_games: Mapped[int] = mapped_column(default=0)


class TimelineEdge(Base, kw_only=True):
    """Timeline edges: games (jornadas) or manual 'what if' branches."""

    __tablename__ = "timeline_edges"

    id: Mapped[int] = mapped_column(ForeignKey("graph_nodes.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    edge_type: Mapped[str] = mapped_column()  # 'game' or 'branch'
    source_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("snapshots.id"), default=None)
    output_snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))

    # Relationships
    game_detail: Mapped[GameDetail | None] = relationship(init=False)
    game_tables: Mapped[list[GameTable]] = relationship(back_populates="timeline_edge", init=False)
    waiting_list: Mapped[list[WaitingList]] = relationship(
        back_populates="timeline_edge", init=False
    )


class GameDetail(Base, kw_only=True):
    """Additional details for game timeline edges."""

    __tablename__ = "game_details"

    timeline_edge_id: Mapped[int] = mapped_column(ForeignKey("timeline_edges.id"), primary_key=True)
    attempts: Mapped[int] = mapped_column(default=0)


class GameTable(Base, kw_only=True):
    """Game tables for a timeline edge."""

    __tablename__ = "game_tables"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    timeline_edge_id: Mapped[int] = mapped_column(ForeignKey("timeline_edges.id"), init=True)
    table_number: Mapped[int] = mapped_column()
    gm_player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), default=None)

    # Relationships
    timeline_edge: Mapped[TimelineEdge] = relationship(back_populates="game_tables", init=False)
    gm_player: Mapped[Player | None] = relationship(back_populates="tables_as_gm", init=False)
    table_players: Mapped[list[TablePlayer]] = relationship(init=False)


class TablePlayer(Base, kw_only=True):
    """Players assigned to a specific game table."""

    __tablename__ = "table_players"

    table_id: Mapped[int] = mapped_column(ForeignKey("game_tables.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    seat_order: Mapped[int] = mapped_column()
    country: Mapped[str] = mapped_column()
    country_reason: Mapped[str | None] = mapped_column(default=None)

    # Relationships
    game_table: Mapped[GameTable] = relationship(
        back_populates="table_players", overlaps="table_players", init=False
    )
    player: Mapped[Player] = relationship(
        back_populates="table_player_links", overlaps="table_player_links", init=False
    )


class WaitingList(Base, kw_only=True):
    """Players waiting for a spot in a timeline edge."""

    __tablename__ = "waiting_list"

    timeline_edge_id: Mapped[int] = mapped_column(ForeignKey("timeline_edges.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    list_order: Mapped[int] = mapped_column()
    missing_spots: Mapped[int] = mapped_column()

    # Relationships
    timeline_edge: Mapped[TimelineEdge] = relationship(back_populates="waiting_list", init=False)
    player: Mapped[Player] = relationship(back_populates="waiting_list_entries", init=False)


class NotionCache(Base, kw_only=True):
    """Cached player data from Notion."""

    __tablename__ = "notion_cache"

    notion_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    is_new: Mapped[bool] = mapped_column(default=False)
    games_this_year: Mapped[int] = mapped_column(default=0)
    c_england: Mapped[int] = mapped_column(default=0)
    c_france: Mapped[int] = mapped_column(default=0)
    c_germany: Mapped[int] = mapped_column(default=0)
    c_italy: Mapped[int] = mapped_column(default=0)
    c_austria: Mapped[int] = mapped_column(default=0)
    c_russia: Mapped[int] = mapped_column(default=0)
    c_turkey: Mapped[int] = mapped_column(default=0)
    alias: Mapped[list[str]] = mapped_column(JSON, default_factory=list)
    last_updated: Mapped[datetime] = mapped_column()


class SnapshotHistory(Base, kw_only=True):
    """Audit log for snapshot mutations."""

    __tablename__ = "snapshot_history"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    action_type: Mapped[SnapshotSource] = mapped_column(String)
    changes: Mapped[dict[str, Any]] = mapped_column(JSON)
    previous_state: Mapped[dict[str, Any]] = mapped_column(JSON)
