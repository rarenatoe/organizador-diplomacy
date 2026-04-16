---
id: backend
title: Pillar 2 - Backend & Database Philosophy
priority: 20
---

## 1. Database Philosophy

- **Database System:** Use disposable local SQLite with `sqlite (stdlib)` via `aiosqlite`. NEVER use persistent or external database services.
- **Schema Management:** Define DB schema in code, re-create as needed. NEVER use Alembic migrations or separate schema files.
- **Type Safety:** Use explicit type annotations for all functions and Pydantic models for validation. NEVER use untyped signatures.

## 2. CRUD Architecture (Repository Pattern)

- **Domain Organization:** Use functional Repository Pattern grouped by domain in `backend/crud/` with separate modules (games, players, snapshots, chain). NEVER cram DB operations into single files.
- **Domain Separation:** Each CRUD module handles specific domain with focused responsibilities. NEVER create modules handling unrelated domains.
- **Async Consistency:** Follow consistent async patterns with proper session handling and type annotations. NEVER mix sync/async patterns.

## 3. Backend Coding Standards

- **Logging:** Use `from backend.core.logger import logger` with appropriate levels. Use `exc_info=True` for exceptions. NEVER use `print()` or `pprint()`.

## 4. Schema & Data Integrity

- **Universal IDs:** Use centralized `graph_nodes` table for universal IDs and cascading deletes. NEVER implement separate ID systems.
- **Immutable Snapshots:** Flow data through immutable snapshots connected by `timeline_edges` with explicit source IDs. NEVER create mutable data structures.

## 5. Business Logic Patterns

- **Country Assignment:** Implement algorithm preventing player repetition with conditional country shields. NEVER allow unrestricted repetition.
- **Two-Step API:** Enforce `/api/game/draft` (in-memory) followed by `/api/game/save` (persistence). NEVER write draft data directly to database.
- **Notion Caching:** Cache Notion data locally via `backend/sync/cache_daemon.py`. NEVER make direct API calls during user interactions.

## 6. API Endpoint Rules

- **Snapshot Save:** `/api/snapshot/save` MUST blindly trust frontend payload. NEVER merge historical weights or apply corrections.
- **Player Lookup:** `/api/player/lookup` MUST use 4-tier fallback: Timeline -> Global Snapshot -> JSON Logs -> Notion Cache. NEVER skip tiers.
- **Game Generation:** Execute two-phase algorithm: distribution loop first, country assignment second. NEVER interleave phases.
- **Hashing Keys:** ALWAYS hash by primitive attributes (`.name`) when using `Counter()` or dict keys. NEVER pass Pydantic models as keys.

## 7. Query Mechanics & Synchronization

- **The Cartesian Product Trap:** When optimizing SQLAlchemy queries by removing unused models from a `select()` list, NEVER remove the `.join()` clause if it restricts the relational mapping. Missing joins cause cross-join fan-outs that crash the frontend.
- **Unified Sync Pipeline:** Disparate logic for background daemons and manual API syncs causes race conditions. ALWAYS unify into a singular pipeline: Extraction (`fetch_notion_data`) -> Transformation (`build_notion_players_lookup`) -> Loading (`notion_cache_to_db`).
- **Granular Conflict Resolution:** Bulk data ingestion MUST intercept similarities and pause. Let the user decide the resolution strategy (`link_rename`, `link_only`, `use_existing`, `merge`). Blindly merging data destroys user intent.
