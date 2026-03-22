"""
config.py — Central configuration for path constants.

This module defines all path constants used throughout the backend.
If the project structure changes, only this file needs to be updated.
"""
from __future__ import annotations

from pathlib import Path

# ── Project root (contains pyproject.toml) ────────────────────────────────────

PROJECT_ROOT: Path = Path(__file__).parent.parent

# ── Backend directory ──────────────────────────────────────────────────────────

BACKEND_DIR: Path = PROJECT_ROOT / "backend"

# ── Frontend directory ─────────────────────────────────────────────────────────

FRONTEND_DIR: Path = PROJECT_ROOT / "frontend"

# ── Data directory ─────────────────────────────────────────────────────────────

DATA_DIR: Path = PROJECT_ROOT / "data"

# ── Database path ──────────────────────────────────────────────────────────────

DB_PATH: Path = DATA_DIR / "diplomacy.db"

# ── Flask configuration ────────────────────────────────────────────────────────

FLASK_TEMPLATE_DIR: Path = FRONTEND_DIR / "templates"
FLASK_STATIC_DIR: Path = FRONTEND_DIR / "static"