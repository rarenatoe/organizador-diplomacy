"""Pydantic models for the Players API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool


class PlayerAutocompleteItem(BaseModel):
    display: str
    nombre: str
    notion_id: str | None = None
    notion_name: str | None = None
    is_local: bool
    is_alias: bool


class PlayerAutocompleteResponse(BaseModel):
    players: list[PlayerAutocompleteItem]


SourceType = Literal["history", "notion", "default"]


class PlayerHistoryItem(BaseModel):
    source: SourceType
    is_new: bool
    juegos_este_ano: int
    has_priority: bool
    partidas_deseadas: int
    partidas_gm: int
    notion_id: str | None = None
    notion_name: str | None = None


class PlayerHistoryResponse(BaseModel):
    player: PlayerHistoryItem


class PlayerSimilarityItem(BaseModel):
    notion_id: str
    notion_name: str
    snapshot: str
    similarity: float
    match_method: str
    matched_alias: str | None = None
    existing_local_name: str | None = None


class PlayerSimilarityResponse(BaseModel):
    similarities: list[PlayerSimilarityItem]


class RenameRequest(BaseModel):
    old_name: str
    new_name: str


class LookupRequest(BaseModel):
    name: str
    notion_id: str | None = None
    snapshot_id: int | None = None


class CheckSimilarityRequest(BaseModel):
    names: list[str]
