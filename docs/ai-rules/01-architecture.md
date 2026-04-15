---
id: architecture
title: Pillar 1 - Stack & Architecture
priority: 10
---

## 0. Domain Context (CRITICAL)

- **The Application:** This is a Diplomacy Tournament Organizer.
- **Core Entities:** - `Snapshots` (imported/synced player rosters).
  - `Games` (Generated tables consisting of exactly 7 players + optional Game Masters).
  - `Waitlists` (Players who did not get seated).
- **The Algorithm:** Prioritizes seating based on veteran status, games played this year, and historical country assignments to prevent repetition.

## 1. Core Architecture

- **Backend Stack:** Python 3.13, uv, FastAPI, SQLAlchemy. NEVER use Flask or mix presentation logic in backend.
- **Frontend Stack:** Svelte 5, TypeScript, Vite. NEVER place business logic or data processing in frontend components.
- **File Limits:** Maintain 400-line soft limit. Extract sub-domains when exceeded. NEVER create monolithic files.

## 2. Language Boundaries

- **Internal Code:** English ONLY for Python/TS variables, types, function names, database schemas, endpoints. NEVER use Spanish like `let listaEspera = []`.
- **UI Text:** Spanish ONLY for HTML labels, user messages, button text, error messages. NEVER translate user-facing text like "Partida 1".
- **API Properties:** NEVER translate API-coupled data properties (e.g., `mesa.jugadores`, `juegos_este_ano`). This causes ripple effects.

## 3. Directory Layout

- **Backend Organization:**
  - `backend/api/routers/` - FastAPI endpoints
  - `backend/db/` - Models and connection management
  - `backend/crud/` - Modular data access
  - `backend/organizador/` - Algorithms
  - `backend/sync/` - Notion integration
- **Frontend Organization:** ALL frontend code in `frontend/src/`. NEVER scatter outside src directory.

## 4. Component Architecture

- **Semantic Props:** Prefer boolean props like `destructive={true}` over specialized variants like `variant="ghost-danger"`. NEVER create proliferating variants.
- **Action Bubbling:** Feature components MUST bubble destructive actions to central orchestrators via callback props. NEVER perform API side-effects in nested UI components.

## 5. Core Workflows & Business Logic

### Player Ingestion Flow

- **Entry Methods:** Users enter players via inline Autocomplete or bulk CSV import. NEVER bypass similarity checks.
- **Similarity Validation:** Unrecognized names MUST be intercepted via Notion similarity check and paused at `SyncResolutionModal`. NEVER allow unrecognized names to proceed without validation.

### History Lookup Flow

- **Traversal Order:** MUST use strict 4-tier traversal: `TimelineEdge` -> `SnapshotPlayer` -> `SnapshotHistory` JSON logs -> `NotionCache`. NEVER skip tiers or access out of sequence.

### Manual Save Philosophy

- **Dumb Save Principle:** Frontend is absolute source of truth for manual edits. NEVER let backend merge historical weights or apply smart corrections.
- **Backend Overwrites:** Backend strictly overwrites existing state. NEVER implement complex merge logic for manual edits.

### Draft Algorithm Pipeline

- **Sequential Execution:** Calculate Tickets -> Distribute to Tables -> Assign Countries -> Deduplicate Waitlist. NEVER skip phases or execute out of order.

## 6. Data Modeling & API Boundaries

- **Immutable Identity (`notion_id` over `name`):** NEVER rely on user-editable strings for relational mapping or deduplication. ALWAYS anchor to an immutable external ID (`notion_id`).
- **Safe Legacy Migrations:** When introducing immutable IDs, write custom SQLAlchemy lifecycle hooks to auto-link existing records via heuristics BEFORE enforcing unique constraints.
- **Nested Objects over Flat Keys:** Group related data into nested objects (e.g., `country: { name, reason }`). Swapping an object reference automatically carries its related metadata, preventing orphaned data.
- **Strict API Purity:** The backend MUST NEVER send formatted UI strings (e.g., `etiqueta: "Antiguo (15 juegos)"`). APIs MUST send strictly typed, pure primitive data. The frontend is solely responsible for localization and UI formatting.
- **Synchronize Read & Write Models (CQRS):** When altering a database schema or write payload, you MUST simultaneously update the aggregate SQL views (e.g., `get_game_event_detail`) and their TypeScript interfaces.
- **Explicit Error Contracts:** The frontend API wrapper MUST explicitly handle framework-specific error shapes (like FastAPI's 422 `HTTPValidationError` array) and surface exact field-level rejections to the user.
