---
id: architecture
title: Pillar 1 - Stack & Architecture
priority: 10
---

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
