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
- **Fortifying the Database Boundary:** Raw SQL results from `db/views.py` MUST be immediately mapped into strict Pydantic models at the data access layer. NEVER pass raw `Row` objects or dicts with unsanitized DB values (e.g., SQLite ISO date strings) beyond the `crud/` layer. Sanitize and coerce types (dates, enums) before Pydantic validation.

## 2. API & Logic Boundaries

- **Repository Pattern:** Group CRUD operations by domain (`backend/crud/`). NEVER cram operations into single files or mix domains.
- **Strict API Purity:** Backend MUST NEVER send formatted UI strings (e.g., `"Antiguo (15 juegos)"`). APIs MUST send strictly typed primitive data.
- **Synchronized CQRS:** When altering a schema or write payload, you MUST simultaneously update aggregate SQL views and their TS interfaces.
- **Two-Step Generation:** Enforce `/api/game/draft` (in-memory) followed by `/api/game/save` (persistence). NEVER write draft data directly to DB.
- **Eradication of Type Cancer:** NEVER use `dict[str, Any]` across architectural boundaries. Every API endpoint MUST return a strictly defined Pydantic response model. Internal functions that pass data between layers MUST use typed `TypedDict` or Pydantic models, not bare dicts.
- **Absolute Trimming:** API response Pydantic models MUST contain ONLY the exact fields the frontend UI consumes. NEVER expose additional fields just because they were queried from the database. Each response model is a deliberate contract, not a DB row mirror.
- **Named Types for Unions (RootModel):** When frontend components need to reference a complex union type used across multiple fields (e.g., `str | int | bool | None`), NEVER define them inline repeatedly in Pydantic models. Inline unions cause the OpenAPI generator to emit anonymous types that can trigger ESLint's `no-duplicate-type-constituents` when extracted or combined in TypeScript. ALWAYS define an explicit `RootModel` (e.g., `class FieldValue(RootModel[str | int | bool | None]): pass`) so the frontend SDK generates and exports a clean, strongly-typed named alias.

## 3. Performance & SQLAlchemy "Fat Trimming"

- **Explicit Selection:** Fetch ONLY required columns (`select(NotionCache.notion_id, NotionCache.name)`). NEVER fetch entire models (`select(NotionCache)`) for read-only algorithms.
- **The Cartesian Trap:** When optimizing queries, NEVER remove `.join()` clauses if they restrict relational mapping. Missing joins cause cross-join fan-outs.
- **Type-Safe Mapping:** Explicitly map SQLAlchemy `Row` objects into typed dicts (`{"name": row.name}`). Avoid `**row.mappings()` to guarantee Pyright compile-time safety.

## 4. Python Typing & ISP

- **Minimal TypedDicts (ISP):** Pure functions MUST declare a minimal `TypedDict` representing exactly what they need, rather than demanding massive DB models.
- **Covariant Hints:** Use `collections.abc.Mapping` and `Sequence` in type hints so functions accept both slim and ORM-derived dicts.
- **Hashing Keys:** ALWAYS hash by primitive attributes (`.name`). NEVER pass Pydantic models as dict/Counter keys.
- **Front-to-Back Honesty:** Do NOT overuse `Optional` / `| None` types in API response models. ALWAYS force default values to empty primitives (`""` instead of `None`, `[]` instead of `None`) unless `null` is a semantically meaningful value the frontend must distinguish from empty. Nullable fields MUST be documented with an explicit reason.

## 5. Coding Standards & Logging

- **Logging:** ALWAYS use `from backend.core.logger import logger` with appropriate levels. Use `exc_info=True` for exceptions. NEVER use `print()` or `pprint()`.
- **Real-World String Normalization:** Human-entered strings (like names) are messy. ALWAYS normalize strings used in comparisons or fuzzy matching algorithms. This MUST include: converting to lowercase, stripping surrounding whitespace, collapsing internal multiple spaces, and aggressively removing accents/diacritics (e.g., using `unicodedata.normalize("NFKD", ...).encode("ascii", "ignore")`). NEVER rely on raw strict equality or basic `.lower()` for human names.
