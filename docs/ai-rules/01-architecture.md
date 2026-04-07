---
id: architecture
title: Pillar 1 - Stack & Architecture
priority: 10
---

## Core Architecture

**Rule:** Backend serves as pure data and algorithms using Python 3.13, uv, FastAPI, and SQLAlchemy.
**Anti-Pattern:** Using Flask or mixing presentation logic in backend code.

**Rule:** Frontend handles presentation and translation using Svelte 5, TypeScript, and Vite.
**Anti-Pattern:** Placing business logic or data processing in frontend components.

**Rule:** Maintain 400-line soft limit per file by extracting sub-domains into separate files.
**Anti-Pattern:** Creating monolithic files with multiple responsibilities unless highly cohesive and indivisible.

## Language Boundaries

**Rule:** Use English exclusively for internal code including Python/TS variables, types, function names, database schemas, and endpoints.
**Anti-Pattern:** Using Spanish for variable names like `let listaEspera = []` instead of `let waitingList = []`.

**Rule:** Use Spanish exclusively for UI text including HTML labels, user messages, button text, and error messages.
**Anti-Pattern:** Translating user-facing text like "Partida 1" or "Copiar jugadores" to English.

**Rule:** Never translate API-coupled data properties that map between frontend UI and database schema.
**Anti-Pattern:** Translating properties like `mesa.jugadores`, `juegos_este_ano`, or `pais_reason` which causes ripple effects.

## Directory Layout

**Rule:** Organize backend with `backend/api/routers/` for FastAPI endpoints, `backend/db/` for models and connection management, `backend/crud/` for modular data access, `backend/organizador/` for algorithms, and `backend/sync/` for Notion integration.
**Anti-Pattern:** Mixing concerns across directories or creating god files.

**Rule:** Place all frontend code in `frontend/src/` with Svelte components, `$state` runes, API utilities, and types.
**Anti-Pattern:** Scattering frontend code outside the designated src directory.

## Component Architecture

**Rule:** Prefer semantic boolean props like `destructive={true}` over specialized component variants like `variant="ghost-danger"`.
**Anti-Pattern:** Creating proliferating component variants that complicate the design system.

**Rule:** Feature components should bubble up destructive actions to central orchestrators via callback props.
**Anti-Pattern:** Performing API side-effects inside deeply nested UI components.

## Core Workflows & Business Logic

### Player Ingestion Flow

**Rule:** Users enter players via inline Autocomplete or bulk CSV import.
**Anti-Pattern:** Bypassing the similarity check for unrecognized names.

**Rule:** Unrecognized names MUST be intercepted via Notion similarity check and paused at the `SyncResolutionModal`.
**Anti-Pattern:** Allowing unrecognized names to proceed without similarity validation.

### History Lookup Flow

**Rule:** Must use strict 4-tier traversal: `TimelineEdge` -> `SnapshotPlayer` -> `SnapshotHistory` JSON logs -> `NotionCache`.
**Anti-Pattern:** Skipping traversal tiers or accessing data out of sequence.

### Manual Save Philosophy

**Rule:** Implement "Dumb Save" where frontend is the absolute source of truth for manual edits.
**Anti-Pattern:** Backend attempting to merge historical weights or applying smart corrections.

**Rule:** Backend strictly overwrites existing state without attempting to merge historical weights.
**Anti-Pattern:** Backend implementing complex merge logic for manual edits.

### Draft Algorithm Pipeline

**Rule:** Execute sequential phases: Calculate Tickets -> Distribute to Tables -> Assign Countries -> Deduplicate Waitlist.
**Anti-Pattern:** Skipping pipeline phases or executing them out of order.
