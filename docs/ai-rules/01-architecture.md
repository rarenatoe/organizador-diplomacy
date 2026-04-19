---
id: architecture
title: Pillar 1 - Domain, Boundaries & Architecture
priority: 10
---

## 1. Domain Context (CRITICAL)

- **The Application:** Diplomacy Tournament Organizer.
- **Core Entities:** `Snapshots` (player rosters), `Games` (7-player tables + GMs), `Waitlists` (unseated players).
- **The Algorithm:** Prioritizes seating based on veteran status, games played this year, and historical country assignments to prevent repetition.

## 2. Global Architecture & Boundaries

- **Backend Stack:** Python 3.13, uv, FastAPI, SQLAlchemy. NEVER use Flask or mix presentation logic in backend.
- **Frontend Stack:** Svelte 5, TypeScript, Vite. NEVER place business logic or data processing in frontend components.
- **Language Boundaries:** - Internal Code: English ONLY (variables, types, DB schemas, endpoints). NEVER use Spanish (e.g., `listaEspera`).
  - UI Text: Spanish ONLY (HTML labels, buttons, error messages). NEVER translate user-facing text.
  - API Properties: NEVER translate API-coupled data properties (e.g., `mesa.jugadores`).

## 3. Directory Layout

- **Backend (`backend/`):** `api/routers/` (Endpoints), `db/` (Models), `crud/` (Data access), `organizador/` (Algorithms), `sync/` (Notion integration).
- **Frontend (`frontend/src/`):** ALL frontend code lives here. NEVER scatter outside.

## 4. Core Workflows

- **Player Ingestion:** Users enter players via Autocomplete or bulk CSV. Unrecognized names MUST be intercepted via Notion similarity check (`SyncResolutionModal`). NEVER bypass validations.
- **History Lookup:** MUST use strict 4-tier traversal: `TimelineEdge` -> `SnapshotPlayer` -> `SnapshotHistory JSON` -> `NotionCache`. NEVER skip tiers.
- **Manual Save (Dumb Save):** Frontend is absolute source of truth for manual edits. Backend strictly overwrites existing state. NEVER merge historical weights or apply smart corrections on manual saves.
- **Draft Pipeline:** Calculate Tickets -> Distribute to Tables -> Assign Countries -> Deduplicate Waitlist. NEVER skip phases or execute out of order.
