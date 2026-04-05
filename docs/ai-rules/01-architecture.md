---
id: architecture
title: Pillar 1 - Stack & Architecture
priority: 10
---

## Core Architecture

- **Backend:** Pure Data & Algorithms. Python 3.13, uv, FastAPI, and SQLAlchemy. (No Flask).
- **Frontend:** Presentation & Translation. Svelte 5, TypeScript, Vite.
- **File Size:** 400-line soft limit per file. Extract sub-domains into new files unless they are highly cohesive indivisible units.

## The Spanglish Boundary (CRITICAL)

**INTERNAL CODE** (English ONLY):

- Python/TS variables, types, function names, database schemas, endpoints
- Component names, CSS classes, DOM variables
- Example: `let listaEspera = []` → `let waitingList = []`, `class="jugadores-excluidos"` → `class="excluded-players"`

**UI TEXT** (Spanish ONLY):

- HTML labels, user messages, button text, error messages
- Example: "Partida 1", "⚠️ Sin GM", "Copiar jugadores"

**CRITICAL EXCEPTION**: NEVER translate API-coupled data properties:

- `mesa.jugadores`, `juegos_este_ano`, `pais_reason`
- These map to frontend UI and database schema - translating causes massive ripple effects

## Directory Layout

- `backend/api/routers/`: FastAPI endpoints.
- `backend/db/`: Modular database operations (connection, crud, models, views).
- `backend/organizador/`: Core algorithms and pure data modeling.
- `backend/sync/`: Notion integration and caching daemon.
- `frontend/src/`: Svelte components, `$state` runes, API utilities, and types.
