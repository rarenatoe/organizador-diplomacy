---
id: architecture
title: Pillar 1 - Stack & Architecture
priority: 10
---
## Core Architecture
- **Backend:** Pure Data & Algorithms. Python 3.13, uv, FastAPI, and SQLAlchemy. (No Flask).
- **Frontend:** Presentation & Translation. Svelte 5, TypeScript, Vite.
- **File Size:** 400-line soft limit per file. Extract sub-domains into new files unless they are highly cohesive indivisible units.

## The Spanglish Boundary
- **INTERNAL CODE:** Python/TS variables, types, function names, database schemas, and endpoints MUST be in English.
- **UI:** HTML text, labels, user-facing error messages, and test queries MUST be in Spanish.
- **Translation Layer:** Translations between internal code and UI must go through `frontend/src/i18n.ts`.

## Directory Layout
- `backend/api/routers/`: FastAPI endpoints.
- `backend/db/`: Modular database operations (connection, crud, models, views).
- `backend/organizador/`: Core algorithms and pure data modeling.
- `backend/sync/`: Notion integration and caching daemon.
- `frontend/src/`: Svelte components, `$state` runes, API utilities, and types.
