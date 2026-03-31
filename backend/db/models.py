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
    snapshot: Mapped[Snapshot | None] = relationship(uselist=False, init=False)
    event: Mapped[Event | None] = relationship(uselist=False, init=False)


class Player(Base, kw_only=True):
    """Unique player records."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    nombre: Mapped[str] = mapped_column(unique=True)

    # Relationships
    snapshot_links: Mapped[list[SnapshotPlayer]] = relationship(init=False)
    mesa_links: Mapped[list[MesaPlayer]] = relationship(init=False)
    mesas_as_gm: Mapped[list[Mesa]] = relationship(back_populates="gm_player", init=False)
    waiting_list_entries: Mapped[list[WaitingList]] = relationship(
        back_populates="player", init=False
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
    game_detail: Mapped[GameDetail | None] = relationship(init=False)
    mesas: Mapped[list[Mesa]] = relationship(back_populates="event", init=False)
    waiting_list: Mapped[list[WaitingList]] = relationship(
        back_populates="event", init=False
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
    event: Mapped[Event] = relationship(back_populates="mesas", init=False)
    gm_player: Mapped[Player | None] = relationship(back_populates="mesas_as_gm", init=False)
    mesa_players: Mapped[list[MesaPlayer]] = relationship(init=False)


class MesaPlayer(Base, kw_only=True):
    """Players assigned to a specific mesa."""

    __tablename__ = "mesa_players"

    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesas.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    orden: Mapped[int] = mapped_column()
    pais: Mapped[str] = mapped_column()
    pais_reason: Mapped[str | None] = mapped_column(default=None)

    # Relationships
    mesa: Mapped[Mesa] = relationship(init=False)
    player: Mapped[Player] = relationship(init=False)


class WaitingList(Base, kw_only=True):
    """Players waiting for a spot in a game event."""

    __tablename__ = "waiting_list"

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    orden: Mapped[int] = mapped_column()
    cupos_faltantes: Mapped[int] = mapped_column()

    # Relationships
    event: Mapped[Event] = relationship(back_populates="waiting_list", init=False)
    player: Mapped[Player] = relationship(
        back_populates="waiting_list_entries", init=False
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
