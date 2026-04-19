---
id: backend
title: Pillar 2 - Backend & Database Philosophy
priority: 20
---

## 1. Database & Schema

- **Database System:** Use disposable local SQLite (`aiosqlite`). NEVER use persistent external DBs or Alembic migrations. Define schema strictly in code.
- **Universal IDs:** Use centralized `graph_nodes` table for universal IDs and cascading deletes. NEVER implement separate ID systems.
- **Immutable Identity:** ALWAYS anchor to immutable external IDs (`notion_id`). NEVER rely on user-editable strings (`name`) for relational mapping.
- **Immutable Snapshots:** Flow data through immutable snapshots connected by `timeline_edges`. NEVER create mutable historical data structures.

## 2. API & Logic Boundaries

- **Repository Pattern:** Group CRUD operations by domain (`backend/crud/`). NEVER cram operations into single files or mix domains.
- **Strict API Purity:** Backend MUST NEVER send formatted UI strings (e.g., `"Antiguo (15 juegos)"`). APIs MUST send strictly typed primitive data.
- **Synchronized CQRS:** When altering a schema or write payload, you MUST simultaneously update aggregate SQL views and their TS interfaces.
- **Two-Step Generation:** Enforce `/api/game/draft` (in-memory) followed by `/api/game/save` (persistence). NEVER write draft data directly to DB.

## 3. Performance & SQLAlchemy "Fat Trimming"

- **Explicit Selection:** Fetch ONLY required columns (`select(NotionCache.notion_id, NotionCache.name)`). NEVER fetch entire models (`select(NotionCache)`) for read-only algorithms.
- **The Cartesian Trap:** When optimizing queries, NEVER remove `.join()` clauses if they restrict relational mapping. Missing joins cause cross-join fan-outs.
- **Type-Safe Mapping:** Explicitly map SQLAlchemy `Row` objects into typed dicts (`{"name": row.name}`). Avoid `**row.mappings()` to guarantee Pyright compile-time safety.

## 4. Python Typing & ISP

- **Minimal TypedDicts (ISP):** Pure functions MUST declare a minimal `TypedDict` representing exactly what they need, rather than demanding massive DB models.
- **Covariant Hints:** Use `collections.abc.Mapping` and `Sequence` in type hints so functions accept both slim and ORM-derived dicts.
- **Hashing Keys:** ALWAYS hash by primitive attributes (`.name`). NEVER pass Pydantic models as dict/Counter keys.

## 5. Coding Standards & Logging

- **Logging:** ALWAYS use `from backend.core.logger import logger` with appropriate levels. Use `exc_info=True` for exceptions. NEVER use `print()` or `pprint()`.
