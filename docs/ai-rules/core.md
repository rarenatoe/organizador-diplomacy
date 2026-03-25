---
id: core
title: Project-Wide AI Instructions
scope: project
priority: 100
outputs:
  copilot: .github/copilot-instructions.md
  cline: .clinerules
  trae: .trae/rules/core.md
toolNotes:
  copilot: Base instructions read before scoped files.
  cline: Main entrypoint for Cline-compatible agents.
  trae: Project-wide rules, always applied.
---

# Copilot Instructions — Organizador Diplomacy

## Stack
Python 3.13 · uv · Flask 3 · pytest · notion-client · python-dotenv · SQLite (stdlib)
TypeScript 5 (strict) · bun · ESLint 9 (typescript-eslint v8 `strictTypeChecked`) · Vitest 4 · @testing-library/dom

> Scoped instructions: `python.md` (applyTo `backend/**/*.py`) and
> `typescript.md` (applyTo `frontend/src/**`) contain language-specific detail.

## Directory layout
```
.
├── backend/            Python source, tests, DB, Flask server
├── frontend/           TypeScript source, UI bundles, templates
└── [config files]      pyproject.toml, package.json, tsconfig.json, etc.
```

## File map

### Backend (`backend/`)
| File | Role |
|---|---|
| `organizador.py` | Algorithm: `_calcular_partidas()`, `organizar_partidas()` |
| `models.py` | Domain types: `Jugador`, `Mesa`, `ResultadoPartidas` |
| `formatter.py` | Text generation: `_formatear_*`, `_construir_proyeccion` |
| `db.py` | SQLite schema + CRUD helpers |
| `db_game.py` | Game-event persistence |
| `db_views.py` | Read-only queries for viewer |
| `viewer.py` | Flask REST API |
| `notion_sync.py` | Notion → DB sync |
| `test_*.py` | Tests (co-located) |

### Frontend (`frontend/`)
| Path | Role |
|---|---|
| `src/types.ts` | Shared TypeScript interfaces |
| `src/stores.svelte.ts` | Global state (`$state` runes) |
| `src/api.ts` | API utility module |
| `src/App.svelte` | Main layout shell |
| `src/components/*.svelte` | UI components |
| `static/style.css` | All CSS |
| `static/app.js` | Build artifact (gitignored) |

**One file, one format. No CSVs, no .txt reports.**

## Workflow
1. Run `uv run python -m pytest -q`.
2. Run `bun run build && bun run lint && bun run typecheck`. Check Svelte Problems in VS Code.
3. Refactor files >400 LOC.
4. Update/add tests for changes.
5. Update instructions if architecture/data model changed.
6. Commit: `feat:` · `fix:` · `refactor:` · `test:`.

## Principles
- **Governance**: Rules in `docs/ai-rules/`, generated via `scripts/generate-ai-instructions.ts`. No direct edits to `.trae/rules/*.md`.
- **Database**: Centralized `graph_nodes` table for global IDs and cascading deletes.
- **Testing**: Tests required for new behavior and modifications.
- **Integrity**: Snapshots require explicit source snapshot ID. UI uses store getters directly in templates.
- **Reactivity**: Svelte 5 `$state`, `$derived`, `$effect`. No local copies of store state.
- **Loading**: Use `-1` for unknown state; `0` when loaded.
- **Errors**: Check for null/undefined backend responses. UI toast for errors.
- **UI**: `title` attributes on disabled buttons for feedback.

## File Size
400-line soft limit. Extract sub-domains into new files. Exception: highly cohesive indivisible units.

## Testing
- Vitest + `@testing-library/dom` for DOM tests.
- Mock dependencies with `vi.mock()`.
- Export testable functions.
- Test files: `frontend/src/*.test.ts`.

## CSS
- Flex layout for panels, rows, containers.
- `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` for truncation.
- Scoped `<style>` in `.svelte` files.
- `static/style.css` for variables, resets, utility classes.
- Scroll pattern: `.panel-body` (flex column, hidden) + `.panel-scroll` (flex 1, auto scroll).

## Ripple Effect
- **Player change**: Update `organizador.py`, `models.py`, `formatter.py`, `notion_sync.py`, `db.py`, `db_game.py`, `viewer.py`, tests.
- **Flask route**: Update `test_viewer.py` (200, 400, 404).
- **Algorithm**: Update `db_views.py`, `test_viewer.py`, `test_db.py`.
- **Schema**: Update `db.py`, `test_db.py`, `test_viewer.py`.
- **UI**: Update `src/*.ts`, `static/style.css`, `types.ts`.

Tests live at root alongside source — flat layout is intentional for this project size.
