---
id: backend
title: Pillar 2 - Backend & Database Philosophy
priority: 20
---

## Database Philosophy

**Rule:** Use disposable local SQLite database with `sqlite (stdlib)` via `aiosqlite`.
**Anti-Pattern:** Using persistent database systems or external database services.

**Rule:** Define DB schema in code and re-create as needed without Alembic migrations.
**Anti-Pattern:** Using database migration tools or maintaining separate schema files.

**Rule:** Use explicit type annotations for all function signatures and Pydantic models for request/response validation.
**Anti-Pattern:** Using untyped function signatures or skipping validation models.

## CRUD Architecture (Repository Pattern)

**Rule:** Use functional Repository Pattern grouped by domain inside `backend/crud/` with separate modules for games, players, snapshots, and chain.
**Anti-Pattern:** Cramming DB operations into a single file or creating monolithic database modules.

**Rule:** Maintain clear domain separation where each CRUD module handles a specific domain with focused responsibilities.
**Anti-Pattern:** Creating modules that handle multiple unrelated domains or concerns.

**Rule:** Follow consistent async patterns with proper session handling and type annotations across all CRUD functions.
**Anti-Pattern:** Mixing sync/async patterns or inconsistent session management.

## Backend Coding Standards

**Rule:** Use `from backend.core.logger import logger` with appropriate levels for all logging (`logger.info()`, `logger.warning()`, `logger.error(..., exc_info=True)` for exceptions).
**Anti-Pattern:** Using `print()` or `pprint()` for any logging or debugging purposes.

## Schema & Data Integrity

**Rule:** Use centralized `graph_nodes` table for universal IDs and cascading deletes across all entities.
**Anti-Pattern:** Implementing separate ID systems or manual cascading logic.

**Rule:** Flow data through immutable snapshots connected by events (`timeline_edges`) with explicit source IDs.
**Anti-Pattern:** Creating mutable data structures or snapshots without proper source tracking.

## Business Logic Patterns

**Rule:** Implement country assignment algorithm that prevents player repetition by conditionally assigning countries as shields.
**Anti-Pattern:** Allowing unrestricted player repetition or missing shield assignments.

**Rule:** Enforce two-step API with `/api/game/draft` computing tables in memory without database writes, followed by `/api/game/save` for persistence.
**Anti-Pattern:** Writing draft data directly to database or skipping the review step.

**Rule:** Cache Notion data locally with background orchestration via `backend/sync/cache_daemon.py`.
**Anti-Pattern:** Making direct API calls to Notion during user interactions.

## API Endpoint Rules

**Rule:** The `/api/snapshot/save` endpoint must blindly and strictly trust the frontend payload without historical overrides.
**Anti-Pattern:** Backend attempting to merge historical weights or apply smart corrections during save operations.

**Rule:** Lookups via `/api/player/lookup` must use deep 4-tier fallback: Timeline -> Global Snapshot -> JSON Logs -> Notion Cache.
**Anti-Pattern:** Skipping traversal tiers or accessing data out of sequence during lookups.

**Rule:** Treat the `priority` field as semantically boolean, using strictly `0` or `1` in logic and test setups.
**Anti-Pattern:** Using non-boolean values for priority fields or treating them as integers.

**Rule:** Execute game generation with two-phase algorithm: distribution loop to group players first, then assign countries second.
**Anti-Pattern:** Interleaving distribution and country assignment or skipping the grouping phase.

**Rule:** Always hash by primitive attributes (e.g., `.name`) when using `Counter()` or dict keys.
**Anti-Pattern:** Passing Pydantic models like `DraftPlayer` into `Counter()` or using them as dict keys.
