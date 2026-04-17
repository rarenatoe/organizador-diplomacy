"""SQLAlchemy database schemas for the Diplomacy organizer."""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003
from enum import StrEnum
from typing import Any, NotRequired, TypedDict

from sqlalchemy import JSON, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship

# ── TypedDict types for diffing logic ─────────────────────────────────────────

# Using alternative TypedDict syntax to handle reserved keyword 'from'
RenameDict = TypedDict("RenameDict", {"from": str, "to": str})


class FieldChange(TypedDict):
    """A change to a single field with old and new values."""

    old: Any
    new: Any


class ModifiedPlayer(TypedDict):
    """A player with modified fields."""

    nombre: str
    changes: dict[str, FieldChange]


class DeepDiffResult(TypedDict):
    """Result of a deep diff operation on player lists."""

    added: list[str]
    removed: list[str]
    renamed: list[RenameDict]
    modified: list[ModifiedPlayer]


class PlayerStateDict(TypedDict):
    """TypedDict for player state in JSON history logs."""

    # Basic fields (always present)
    nombre: str
    notion_id: NotRequired[str | None]
    notion_name: NotRequired[str | None]
    is_new: bool
    juegos_este_ano: int
    has_priority: bool
    partidas_deseadas: int
    partidas_gm: int

    # Country fields (optional, may not be present in history logs)
    c_england: NotRequired[int]
    c_france: NotRequired[int]
    c_germany: NotRequired[int]
    c_italy: NotRequired[int]
    c_austria: NotRequired[int]
    c_russia: NotRequired[int]
    c_turkey: NotRequired[int]


class HistoryStateDict(TypedDict, total=False):
    """TypedDict for history state JSON structure."""

    players: list[PlayerStateDict]


class HistoryActionType(StrEnum):
    """Types of history actions for snapshot mutations."""

    MANUAL_EDIT = "manual_edit"
    NOTION_SYNC = "notion_sync"
    CREATION = "creation"


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


class Snapshot(Base, kw_only=True):
    """Point-in-time roster snapshots."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(ForeignKey("graph_nodes.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    source: Mapped[str] = mapped_column()

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
    action_type: Mapped[str] = mapped_column()  # e.g., 'notion_sync', 'manual_edit'
    changes: Mapped[DeepDiffResult] = mapped_column(JSON)  # Structured changes object
    previous_state: Mapped[HistoryStateDict] = mapped_column(
        JSON
    )  # Raw dict of the roster before the change
