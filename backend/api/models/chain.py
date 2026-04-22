"""Chain router for /api/chain endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from backend.db.models import SnapshotSource

router = APIRouter(prefix="/api")

# ── Pydantic Models for OpenAPI Generation ───────────────────────────────────


class ChainEdge(BaseModel):
    id: int
    type: Literal["sync", "game", "edit", "branch"]
    created_at: datetime | str
    from_id: int
    to_id: int | None = None
    intentos: int | None = None
    mesa_count: int | None = None
    espera_count: int | None = None


class Branch(BaseModel):
    edge: ChainEdge
    output: SnapshotNode | None = None


class SnapshotNode(BaseModel):
    type: Literal["snapshot"]
    id: int
    created_at: datetime | str
    source: SnapshotSource
    player_count: int
    is_latest: bool
    branches: list[Branch]


class ChainResponse(BaseModel):
    roots: list[SnapshotNode]


# Resolve recursive forward references
Branch.model_rebuild()
SnapshotNode.model_rebuild()
ChainResponse.model_rebuild()
