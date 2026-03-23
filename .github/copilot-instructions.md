# Copilot Instructions — Organizador Diplomacy

## Stack
Python 3.13 · uv · Flask 3 · pytest · notion-client · python-dotenv · SQLite (stdlib)
TypeScript 5 (strict) · bun · ESLint 9 (typescript-eslint v8 `strictTypeChecked`) · Vitest 4 · @testing-library/dom

> Scoped instructions: `python.instructions.md` (applyTo `backend/**/*.py`) and
> `typescript.instructions.md` (applyTo `frontend/src/**`) contain language-specific detail.

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
| `organizador.py` | Algorithm entry-point: `_calcular_partidas()`, `organizar_partidas()` |
| `models.py` | Domain types: `Jugador`, `Mesa`, `ResultadoPartidas` |
| `formatter.py` | Pure text generation: `_formatear_*`, `_construir_proyeccion` |
| `utils.py` | Shared constants: `DIRECTORIO` |
| `db.py` | SQLite schema, connection, snapshot/player/sync CRUD helpers |
| `db_game.py` | Game-event persistence: `create_game_event`, `create_mesa`, `add_mesa_player`, `add_waiting_player`, `create_output_snapshot` |
| `db_views.py` | Read-only query helpers for viewer: `build_chain_data`, `get_snapshot_detail`, `get_game_event_detail` |
| `viewer.py` | Flask viewer: DB-backed REST API |
| `notion_sync.py` | Notion → DB sync (content-addressed, no CSV files) |
| `test_organizador.py` | Basic tests for `organizador.py` and `models.py` (correctness, balance, error, espera) |
| `test_algoritmo.py` | Advanced algorithm tests (prioridad, GM rules, liga, peso de participación) |
| `test_db.py` | Tests for `db.py`, `db_game.py` and `db_views.py` (`TestDb` class) |
| `test_viewer.py` | Tests for `viewer.py` (in-memory SQLite via `db.get_db(":memory:")`) |
| `test_notion_sync.py` | Tests for `notion_sync.py` (name similarity, normalization) |

### Frontend (`frontend/`)
| Path | Role |
|---|---|
| `src/types.ts` | All TypeScript interfaces shared across the UI (domain types) |
| `src/stores.svelte.ts` | Global Svelte 5 state using `$state` runes (selectedSnapshot, snapshotCount, chainData, activeNodeId) |
| `src/api.ts` | Centralized API utility module (fetchChain, fetchSnapshot, fetchGame, runScript, detectSync, confirmSync, etc.) |
| `src/main.ts` | Entry point: mounts App.svelte to DOM |
| `src/App.svelte` | Main layout shell: Header, ChainViewer, SidePanel, Toaster, modals |
| `src/components/Header.svelte` | Top bar with buttons (Refresh, Sync Notion, Organizar, Deselect) |
| `src/components/ChainViewer.svelte` | Chain tree display, loads and renders snapshot nodes |
| `src/components/SnapshotNode.svelte` | Recursive snapshot node with branches (uses self-import) |
| `src/components/GameNode.svelte` | Game edge card component |
| `src/components/SyncNode.svelte` | Sync edge card component |
| `src/components/SidePanel.svelte` | Detail panel container with slide animation |
| `src/components/SnapshotDetail.svelte` | Snapshot panel: player table, edit controls, CSV copy |
| `src/components/GameDetail.svelte` | Game panel: mesa cards, waiting list, share text |
| `src/components/SyncDetail.svelte` | Sync panel: metadata display |
| `src/components/Toaster.svelte` | Toast notification system (syncing, success, error states) |
| `src/components/SyncResolutionModal.svelte` | Sequential conflict resolution cards (Merge/Skip) |
| `src/components/TerminalModal.svelte` | Script output modal with spinner |
| `src/index.html` | Vite entry HTML template |
| `static/style.css` | All CSS for the viewer UI (unchanged) |
| `static/app.js` | Bundled output (Vite build). **Gitignored** — regenerate with `bun run build`. |
| `templates/index.html` | Production HTML (copied from static/index.html by build script) |

### Data
| File | Format | Git | Mutability |
|---|---|---|---|
| `diplomacy.db` | SQLite | ignored | runtime state — single source of truth |

**One file, one format. No CSVs, no .txt reports, no metadata.json.**

`static/app.js` is a build artifact and is gitignored. After cloning, run `bun install && bun run build` before starting the viewer.

## After every feature or fix
1. Run `uv run python -m pytest -q` — confirm all pass.
2. Run `bun run build && bun run lint` — TypeScript must compile and lint clean.
3. **Check file sizes**: `wc -l backend/*.py frontend/src/*.ts frontend/static/style.css | sort -rn` — refactor any file >400 LOC.
4. Add/update tests in the relevant test file.
5. Update the relevant instructions file if conventions, data model, or architecture changed.
6. Commit: `feat:` · `fix:` · `refactor:` · `test:` prefix.

## Principles
- Maintainability over expediency: design for extensibility and clarity.
- Tests required for every new behavior. Documentation must stay current.
- No inlined CSS/JS/magic strings — one format per file, centralized constants.
- Large refactors warrant their own commit; don't combine with feature work.
- Dead code: evaluate every file for unreachable branches, unused exports, redundant constants. Remove if safe — verify via full test suite before committing.

## File size guideline
**400-line soft limit per file.** When a file crosses this threshold:
1. Identify logical responsibility boundaries (not arbitrary line counts).
2. Extract the cohesive sub-domain into a new file with a single-responsibility name.
3. Python: add a new flat-layout file at root. TypeScript: add a new `src/*.ts` module (update file map and import graph in `typescript.instructions.md`).
4. Run all tests + build + lint before committing the split.

## Frontend testing conventions
- Use Vitest with `@testing-library/dom` for DOM testing
- Mock external dependencies with `vi.mock()` at the top of test files
- Export functions that need testing (e.g., `showRenameDialog`, `showAddPlayerDialog`)
- Wrap module-level DOM access in conditional checks for test environment compatibility
- Test files: `frontend/src/*.test.ts`

## CSS conventions
- Use flexbox for layout (e.g., `.player-name-cell` with `display: flex`)
- Use `flex: 1` for expandable content, `flex-shrink: 0` for fixed elements
- Use `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` for text truncation
- Use `margin-left: auto` to push elements to the right in flex containers
- Never inline CSS in HTML — always use `static/style.css`

## Ripple-effect checklist
**Player field change** → `organizador.py` · `models.py` · `formatter.py` · `notion_sync.py` · `db.py` (schema + helpers) · `db_game.py` (game helpers) · `viewer.py` (API) · `test_organizador.py` (`_j()` + `_pool()`) · `test_algoritmo.py` (`_j()` + `_pool()`) · `test_db.py` (`TestDb`) · `test_viewer.py` (`_add_snapshot()` helper)
**New Flask route** → `TestApi*` class in `test_viewer.py` with 200 + 400 + 404 coverage.
**Chain algorithm change** → update `db_views.py` · `TestApiChain` in `test_viewer.py` (use `roots` tree, not `nodes` flat list) · `TestDb` in `test_db.py` · "Chain lineage" section in `python.instructions.md`.
**DB schema change** → update `_SCHEMA` in `db.py` · all affected helpers · `test_db.py` `TestDb` · `test_viewer.py` fixtures · `python.instructions.md`.
**UI logic change** → edit relevant `src/*.ts` module + `bun run build`. **New domain type** → add to `src/types.ts`. **Style change** → edit `static/style.css`. Never re-inline into `index.html`.
**Frontend test** → add to `frontend/src/*.test.ts` · mock dependencies with `vi.mock()` · export tested functions.

Tests live at root alongside source — flat layout is intentional for this project size.


