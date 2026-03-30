"""SQLAlchemy database schemas for the Diplomacy organizer."""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class GraphNode(Base, kw_only=True):
    """Universal IDs for all entities (snapshots and events)."""

    __tablename__ = "graph_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    entity_type: Mapped[str] = mapped_column()

    # Relationships
    snapshot: Mapped[Snapshot | None] = relationship(uselist=False, default=None)
    event: Mapped[Event | None] = relationship(uselist=False, default=None)


class Player(Base, kw_only=True):
    """Unique player records."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    nombre: Mapped[str] = mapped_column(unique=True)

    # Relationships
    snapshot_links: Mapped[list[SnapshotPlayer]] = relationship(default_factory=list)
    mesa_links: Mapped[list[MesaPlayer]] = relationship(viewonly=True, default_factory=list)
    mesas_as_gm: Mapped[list[Mesa]] = relationship(back_populates="gm_player", default_factory=list)
    waiting_list_entries: Mapped[list[WaitingList]] = relationship(
        back_populates="player", default_factory=list
    )


class Snapshot(Base, kw_only=True):
    """Point-in-time roster snapshots."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(ForeignKey("graph_nodes.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    source: Mapped[str] = mapped_column()


class SnapshotPlayer(Base, kw_only=True):
    """Many-to-many link between snapshots and players with game data."""

    __tablename__ = "snapshot_players"

    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    experiencia: Mapped[str] = mapped_column()
    juegos_este_ano: Mapped[int] = mapped_column(default=0)
    prioridad: Mapped[int] = mapped_column(default=0)
    partidas_deseadas: Mapped[int] = mapped_column(default=1)
    partidas_gm: Mapped[int] = mapped_column(default=0)


class Event(Base, kw_only=True):
    """Events: sync, game, or edit operations."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(ForeignKey("graph_nodes.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    type: Mapped[str] = mapped_column()
    source_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("snapshots.id"), default=None)
    output_snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))

    # Relationships
    game_detail: Mapped[GameDetail | None] = relationship(default=None)
    mesas: Mapped[list[Mesa]] = relationship(back_populates="event", default_factory=list)
    waiting_list: Mapped[list[WaitingList]] = relationship(
        back_populates="event", default_factory=list
    )


class GameDetail(Base, kw_only=True):
    """Additional details for game events."""

    __tablename__ = "game_details"

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), primary_key=True)
    intentos: Mapped[int] = mapped_column(default=0)
    copypaste_text: Mapped[str] = mapped_column()


class Mesa(Base, kw_only=True):
    """Game tables (mesas) for a game event."""

    __tablename__ = "mesas"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), init=True)
    numero: Mapped[int] = mapped_column()
    gm_player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), default=None)

    # Relationships
    event: Mapped[Event | None] = relationship(back_populates="mesas", init=False, default=None)
    gm_player: Mapped[Player | None] = relationship(back_populates="mesas_as_gm", default=None)
    mesa_players: Mapped[list[MesaPlayer]] = relationship(viewonly=True, default_factory=list)


class MesaPlayer(Base, kw_only=True):
    """Players assigned to a specific mesa."""

    __tablename__ = "mesa_players"

    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesas.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    orden: Mapped[int] = mapped_column()
    pais: Mapped[str] = mapped_column()

    # Relationships - viewonly to prevent PK synchronization issues
    mesa: Mapped[Mesa | None] = relationship(viewonly=True, default=None)
    player: Mapped[Player | None] = relationship(viewonly=True, default=None)


class WaitingList(Base, kw_only=True):
    """Players waiting for a spot in a game event."""

    __tablename__ = "waiting_list"

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    orden: Mapped[int] = mapped_column()
    cupos_faltantes: Mapped[int] = mapped_column()

    # Relationships
    event: Mapped[Event | None] = relationship(back_populates="waiting_list", default=None)
    player: Mapped[Player | None] = relationship(
        back_populates="waiting_list_entries", default=None
    )


class NotionCache(Base, kw_only=True):
    """Cached player data from Notion."""

    __tablename__ = "notion_cache"

    notion_id: Mapped[str] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column()
    experiencia: Mapped[str] = mapped_column()
    juegos_este_ano: Mapped[int] = mapped_column(default=0)
    c_england: Mapped[int] = mapped_column(default=0)
    c_france: Mapped[int] = mapped_column(default=0)
    c_germany: Mapped[int] = mapped_column(default=0)
    c_italy: Mapped[int] = mapped_column(default=0)
    c_austria: Mapped[int] = mapped_column(default=0)
    c_russia: Mapped[int] = mapped_column(default=0)
    c_turkey: Mapped[int] = mapped_column(default=0)
    last_updated: Mapped[datetime] = mapped_column()
