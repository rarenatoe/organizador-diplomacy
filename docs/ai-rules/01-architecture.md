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
- **Graceful Degradation on Incomplete Data:** Algorithms resolving user identity or matching entries must account for incomplete data representation across systems (e.g., Notion vs Local DB). A partial representation (like an abbreviated middle/last name) that strongly matches a subset of a fully fleshed-out entry must be scored favorably, rather than heavily penalized for strict word-length mismatches.

## 5. Domain-Driven Design (DDD) & DTO Separation

- **Domain Model Purity:** Core business logic in `organizador/` (e.g., weight calculations, distribution algorithms) MUST NEVER import FastAPI, Pydantic, or any web framework. Domain models are plain Python dataclasses or TypedDicts only.
- **Strict Layer Boundaries:** `organizador/` owns Domain Models. `api/models/` owns DTOs (Pydantic). `api/routers/` owns HTTP concerns only. NEVER collapse these layers.
- **Factory Methods on DTOs:** Pydantic response models in `api/models/` MUST expose a `@classmethod def from_domain(cls, obj: DomainModel) -> "Self"` factory to translate Domain Models into API responses. NEVER perform this translation inside a router function.
- **Lean Routers:** FastAPI routers MUST only: validate input, call a CRUD or domain function, call the DTO factory, and return. NEVER embed business logic or data reshaping directly in router functions.
- **No Upward Coupling:** Domain layer (`organizador/`) MUST NEVER reference DTO models from `api/models/`. Data flows strictly downward: Router → CRUD/Domain → DTO factory → Response.
