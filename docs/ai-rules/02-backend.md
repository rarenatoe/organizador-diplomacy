---
id: backend
title: Pillar 2 - Backend & Database Philosophy
priority: 20
---

## 1. Database & Schema (`aiosqlite`)

- **Schema Management:** Define strictly in code. BANNED: Persistent external DBs, Alembic migrations.
- **Identity & Graphs:** Use `graph_nodes` for universal IDs. Anchor identity to immutable `notion_id`, not user-editable names. Flow data through immutable snapshots via `timeline_edges`.
- **Deep Cascades:** Use recursive cascade functions for tree/graph deletions. NEVER use shallow loops.
- **Data Sanitization:** Map raw SQL `Row` results into Pydantic models at the `crud/` layer. Sanitize/coerce types before validation.
- **Collections:** Use SQLAlchemy `JSON`. DTOs/DB models MUST default to `[]`. BANNED: `""` or `None` for lists.

## 2. API & Logic Boundaries

- **Repository Pattern:** Group CRUD operations by domain (`backend/crud/`). NEVER cram operations into single files or mix domains.
- **Strict API Purity:** Backend MUST NEVER send formatted UI strings (e.g., `"Antiguo (15 juegos)"`). APIs MUST send strictly typed primitive data.
- **Synchronized CQRS:** When altering a schema or write payload, you MUST simultaneously update aggregate SQL views and their TS interfaces.
- **Two-Step Generation:** Enforce `/api/game/draft` (in-memory) followed by `/api/game/save` (persistence). NEVER write draft data directly to DB.
- **Strict SDK Optionality:** If the frontend strictly requires a field, DO NOT assign a default value in the Pydantic response model. Default values in Pydantic implicitly mark fields as optional (`?`) in the generated TypeScript.
- **Strict Primitives:** Eliminate `None`/`null` for calculable numeric or boolean states. Use strict types (e.g., `int` defaulting to `0` behind the scenes) to eradicate defensive `?? 0` fallback checks in the frontend UI.
- **Eradication of Type Cancer:** NEVER use `dict[str, Any]` across architectural boundaries, **with ONE strict exception:** passing serialized Pydantic writes (`model_dump(mode="json")`) from Routers into CRUD functions. Everywhere else, use typed `TypedDict` or Pydantic models.
- **Absolute Trimming:** API response Pydantic models MUST contain ONLY the exact fields the frontend UI consumes. NEVER expose additional fields just because they were queried from the database. Each response model is a deliberate contract, not a DB row mirror.
- **Named Types for Unions (RootModel):** When frontend components need to reference a complex union type used across multiple fields (e.g., `str | int | bool | None`), NEVER define them inline repeatedly in Pydantic models. Inline unions cause the OpenAPI generator to emit anonymous types that can trigger ESLint's `no-duplicate-type-constituents` when extracted or combined in TypeScript. ALWAYS define an explicit `RootModel` (e.g., `class FieldValue(RootModel[str | int | bool | None]): pass`) so the frontend SDK generates and exports a clean, strongly-typed named alias.

## 3. Performance & Python ISP

- **Query Optimization:** Fetch ONLY required columns. NEVER remove restricting `.join()` clauses (causes Cartesian fan-outs). Use `.in_()` subqueries for bulk deletions to prevent N+1.
- **Interface Segregation:** Pure functions declare minimal `TypedDict`s instead of demanding massive ORM models. Use covariant hints (`Mapping`, `Sequence`).
- **String Normalization:** Aggressively normalize human strings (lowercase, strip, collapse spaces, remove accents) for comparisons.
- **Logging:** Use `backend.core.logger`. BANNED: `print()`, `pprint()`.
