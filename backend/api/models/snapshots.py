"""Pydantic models for snapshots API responses."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, RootModel, field_validator

from backend.db.models import SnapshotSource


class SnapshotSaveEventType(StrEnum):
    MANUAL = "manual"
    SYNC = "sync"


class RenameChange(BaseModel):
    old_name: str
    new_name: str


class FieldValue(RootModel[str | int | bool | list[str] | None]):
    pass


class FieldChange(BaseModel):
    old: FieldValue
    new: FieldValue


class ModifiedPlayer(BaseModel):
    nombre: str
    changes: dict[str, FieldChange]


class DeepDiffResult(BaseModel):
    added: list[str]
    removed: list[str]
    renamed: list[RenameChange]
    modified: list[ModifiedPlayer]


class PlayerData(BaseModel):
    """Player data within a snapshot."""

    nombre: str
    notion_id: str | None
    notion_name: str | None
    is_new: bool
    juegos_este_ano: int
    has_priority: bool
    partidas_deseadas: int
    partidas_gm: int
    # Algorithm weight fields (read-only from NotionCache)
    c_england: int
    c_france: int
    c_germany: int
    c_italy: int
    c_austria: int
    c_russia: int
    c_turkey: int
    alias: str | None


class HistoryState(BaseModel):
    players: list[PlayerData]


class HistoryEntry(BaseModel):
    """History entry for snapshot changes."""

    id: int
    created_at: datetime
    action_type: str
    changes: DeepDiffResult


class SnapshotDetailResponse(BaseModel):
    """Response model for GET /api/snapshot/{id} endpoint."""

    id: int
    created_at: datetime
    source: SnapshotSource
    players: list[PlayerData]
    history: list[HistoryEntry]


class SnapshotSaveResponse(BaseModel):
    """Response model for snapshot save operations."""

    snapshot_id: int
    status: str | None = None  # "no_changes" when applicable


class NotionPlayerData(BaseModel):
    """Player data from Notion cache."""

    notion_id: str
    nombre: str
    is_new: bool
    juegos_este_ano: int
    c_england: int
    c_france: int
    c_germany: int
    c_italy: int
    c_austria: int
    c_russia: int
    c_turkey: int
    alias: list[str] | None = None


class SimilarName(BaseModel):
    """Similar name detection result."""

    notion_id: str
    notion_name: str
    snapshot: str
    similarity: float
    match_method: str
    matched_alias: str | None = None
    existing_local_name: str | None = None


class NotionFetchResponse(BaseModel):
    """Response model for POST /api/snapshot/notion/fetch endpoint."""

    players: list[NotionPlayerData]
    similar_names: list[SimilarName]
    last_updated: datetime | None

    @field_validator("last_updated", mode="before")
    @classmethod
    def convert_datetime_to_str(_cls, v: datetime | str | None) -> str | None:
        if isinstance(v, datetime):
            return v.isoformat()
        return v


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    deleted: int


HistoryState.model_rebuild()
DeepDiffResult.model_rebuild()
HistoryEntry.model_rebuild()
SnapshotDetailResponse.model_rebuild()
