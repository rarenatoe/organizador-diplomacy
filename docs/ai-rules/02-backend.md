---
id: backend
title: Pillar 2 - Backend & Database Philosophy
priority: 20
---

## Database Philosophy

- **Disposable Local SQLite:** The database is local and disposable (`sqlite (stdlib)` via `aiosqlite`).
- **No Migrations:** DO NOT use Alembic migrations. The DB schema is defined in code and re-created as needed.
- **Strict Typing:** Use explicit type annotations for all function signatures. Use Pydantic models for request/response validation and TypedDicts where appropriate.

## CRUD Architecture (Repository Pattern)

- **Modular Data Access:** Never cram DB operations into a single file. Use a functional Repository Pattern grouped by domain inside `backend/crud/` (e.g., `games.py`, `players.py`, `snapshots.py`, `chain.py`).
- **Domain Separation:** Each CRUD module handles a specific domain (players, games, snapshots, timeline edges) with clear separation of concerns.
- **No God Files:** Strictly forbid the recreation of monolithic "God files" for database operations. Each module should be focused and maintainable.
- **Consistent Patterns:** All CRUD functions follow the same async patterns with proper session handling and type annotations.

## Backend Coding Standards

- **Logging Only:** NEVER use `print()` or `pprint()` for any purpose. All logging must use `from backend.core.logger import logger` with appropriate levels (`logger.info()`, `logger.warning()`, `logger.error(..., exc_info=True)` for exceptions).

## Schema & Data Integrity

- **Global IDs:** Use a centralized `graph_nodes` table for universal IDs and cascading deletes across all entities.
- **Snapshots & Events:** Data flows through immutable snapshots connected by events (`timeline_edges`). Snapshots require an explicit source ID.

## Business Logic Patterns

- **Shielding Strategy:** The country assignment algorithm (`organizador/core.py`) prevents player repetition by conditionally assigning countries to act as "shields" for other players.
- **Draft Mode:** A two-step API is strictly enforced. The `/api/game/draft` endpoint computes game tables in memory _without_ writing to the database, allowing manual review. Only `/api/game/save` persists the draft.
- **Notion Sync:** Notion data is cached locally. Background caching is orchestrated via `backend/sync/cache_daemon.py`.
