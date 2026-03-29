<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->
<!-- Source of truth: docs/ai-rules/*.md -->
# Copilot Instructions — Organizador Diplomacy

## Stack

Python 3.13 · uv · Flask 3 · pytest · notion-client · python-dotenv · SQLite (stdlib)
TypeScript 5 (strict) · bun · ESLint 9 (typescript-eslint v8 `strictTypeChecked`) · Vitest 4 · @testing-library/dom
Lefthook for smart pre-commit execution on changed files.

> Scoped instructions: `python.instructions.md` (applyTo `backend/**/*.py`) and
> `typescript.instructions.md` (applyTo `frontend/src/**`) contain language-specific detail.

## Directory layout

```
.
├── backend/            Python source, tests, DB, Flask server
│   ├── db/              Modular database operations
│   │   ├── connection.py      # Database connection and schema
│   │   ├── players.py         # Player CRUD operations
│   │   ├── snapshots.py       # Snapshot management
│   │   └── events.py         # Event operations
│   ├── organizador/      Core algorithm and models
│   │   ├── core.py           # Country assignment algorithm
│   │   └── models.py         # Domain types
│   ├── sync/              Notion integration
│   │   ├── api.py            # Notion API utilities
│   │   ├── similarity.py     # Name similarity detection
│   │   └── notion_sync.py   # Main orchestrator
│   └── viewer.py           # Flask REST API
├── frontend/           TypeScript source, UI bundles, templates
│   ├── src/
│   │   ├── types.ts          # Shared TypeScript interfaces
│   │   ├── stores.svelte.ts   # Global state ($state runes)
│   │   ├── api.ts            # API utility module
│   │   ├── App.svelte         # Main layout shell
│   │   └── components/*.svelte # UI components
│   └── [config files]      pyproject.toml, package.json, tsconfig.json, etc.
```

## File map

### Backend (`backend/`)

| File                  | Role                                                                                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `connection.py`       | Database connection and schema management                                                                                                                           |
| `players.py`          | Player CRUD operations (get_or_create_player, rename_player, add_player_to_snapshot, get_snapshot_players)                                                          |
| `snapshots.py`        | Snapshot management (create_snapshot, add_snapshot_player, get_latest_snapshot_id, snapshots_have_same_roster, create_manual_snapshot, create_root_manual_snapshot) |
| `events.py`           | Event operations (create_event, create_sync_event, create_game_event, delete_snapshot_cascade)                                                                      |
| `core.py`             | Algorithm: `_calcular_partidas()`, `organizar_partidas()`, `assign_countries_to_mesa()`                                                                             |
| `models.py`           | Domain types: `Jugador`, `Mesa`, `ResultadoPartidas`                                                                                                                |
| `formatter.py`        | Text generation: `_formatear_*`, `_construir_proyeccion`                                                                                                            |
| `db_game.py`          | Game-event persistence (legacy, now in events.py)                                                                                                                   |
| `db_views.py`         | Read-only queries for viewer                                                                                                                                        |
| `viewer.py`           | Flask REST API                                                                                                                                                      |
| `sync/api.py`         | Notion API utilities (download data, count games, extract numbers, get names, experience)                                                                           |
| `sync/similarity.py`  | Name similarity detection (\_normalize_name, \_words_match, \_similarity, \_detect_similar_names)                                                                   |
| `sync/notion_sync.py` | Main orchestrator (main function)                                                                                                                                   |
| `test_*.py`           | Tests (co-located with source files)                                                                                                                                |

### Frontend (`frontend/`)

| Path                      | Role                         |
| ------------------------- | ---------------------------- |
| `src/types.ts`            | Shared TypeScript interfaces |
| `src/stores.svelte.ts`    | Global state ($state runes)  |
| `src/api.ts`              | API utility module           |
| `src/App.svelte`          | Main layout shell            |
| `src/components/*.svelte` | UI components                |
| `static/style.css`        | All CSS                      |
| `static/app.js`           | Build artifact (gitignored)  |

**One file, one format. No CSVs, no .txt reports.**

## Workflow

1. Run `uv run python -m pytest -q`.
2. Run `bun run build && bun run lint && bun run typecheck`. Check Svelte Problems in VS Code.
3. Refactor files >400 LOC.
4. Update/add tests for changes.
5. Update instructions if architecture/data model changed.
6. Commit: `feat:` · `fix:` · `refactor:` · `test:`.

## Principles

- **Governance**: Rules in `docs/ai-rules/`, generated via `scripts/generate-ai-instructions.ts`. No direct edits to generated files.
- **Database**: Centralized `graph_nodes` table for global IDs and cascading deletes.
- **Testing**: Tests required for new behavior and modifications.
- **Integrity**: Snapshots require explicit source snapshot ID. UI uses store getters directly in templates.
- **Reactivity**: Svelte 5 `$state`, `$derived`, `$effect`. No local copies of store state.
- **Loading**: Use `-1` for unknown state; `0` when loaded.
- **Errors**: Check for null/undefined backend responses. UI toast for errors.
- **UI**: `title` attributes on disabled buttons for feedback.

## File Size

400-line soft limit. Extract sub-domains into new files. Exception: highly cohesive indivisible units.
