---
id: architecture
title: Pillar 1 - Domain, Boundaries & Architecture
priority: 10
---

## 1. Domain & Workflows

- **Core Entities:** `Snapshots` (rosters), `Games` (7-player tables + GMs), `Waitlists` (unseated).
- **History Lookup:** MUST use strict 4-tier traversal: `TimelineEdge` -> `SnapshotPlayer` -> `SnapshotHistory JSON` -> `NotionCache`. NEVER skip tiers.
- **Manual Save:** Frontend is the absolute source of truth. Backend strictly overwrites state. NEVER merge weights or apply smart corrections on manual saves.
- **Draft Pipeline & Reconciliation:** Calculate Tickets -> Distribute to Tables -> Assign Countries -> Mathematically Reconcile Waitlist. Treat complex algorithm outputs as "rough drafts". Both backend and frontend MUST use identical, deterministic mathematical reconciliation (e.g., `desired_games - seated_games = missing_slots`) to resolve final state instead of naive array patching.
- **Symmetric Optimistic UI:** When the frontend needs to react instantly to user mutations (like swapping players), it MUST execute the exact same deterministic math as the backend to rebuild the state. NEVER replicate complex backend algorithms in the UI; reduce the logic to shared mathematical truths.

## 2. Global Architecture & Language Boundaries

- **Backend Stack:** Python 3.13, uv, FastAPI, SQLAlchemy. NEVER use Flask or mix presentation logic.
- **Frontend Stack:** Svelte 5, TypeScript, Vite. NEVER place business logic in UI components.
- **Bilingual Codebase:** - **Internal Code:** English ONLY (variables, types, schemas, endpoints).
  - **UI Text:** Spanish ONLY (HTML labels, buttons, errors). NEVER translate user-facing text.
  - **API Payloads:** NEVER translate API-coupled data properties.

## 3. Domain-Driven Design (DDD)

- **Layer Separation:** - `organizador/`: Pure domain logic (Python dataclasses/TypedDicts). NO FastAPI/Pydantic imports.
  - `api/models/`: Pydantic DTOs. MUST expose `@classmethod def from_domain(cls, obj) -> "Self"` factories.
  - `api/routers/`: HTTP routing only. Validate input -> Call CRUD/Domain -> Call DTO factory.
- **Data Flow:** Downward only (Router → CRUD/Domain → DTO). Domain layer MUST NEVER reference DTOs.
- **Separation of Concerns:** Backend delivers structured primitives (e.g., `list[str]`). Frontend handles presentation/formatting (e.g., joining strings).

## 4. Algorithm & Degradation Principles

- **Graceful Degradation:** Favour partial matches (e.g., abbreviated names) over strict failures. Cap excessive user limits (e.g., too many GMs) instead of blocking the UI.
- **Relative Thresholds:** Use dynamic baselines (e.g., table minimums) for algorithms, NEVER hardcoded absolute limits.
- **Greedy Optimization:** Prefer Greedy Intervention loops over linear passes for complex assignments. Score assignments by simultaneous constraint resolutions.
