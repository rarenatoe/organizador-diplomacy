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

## After every feature or fix
1. Run `uv run python -m pytest -q` — confirm all pass.
2. Run `bun run build && bun run lint && bun run typecheck` — TypeScript must compile, lint clean, and type-check clean. **Also check for Svelte errors/warnings in the VS Code Problems panel (svelte.svelte-vscode)** — fix any before committing.
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
- **Chain Integrity:** Every operation that creates a new snapshot (sync, organizar, edit) must have a source snapshot ID provided by the UI. Fallbacks to 'latest' are prohibited to prevent accidental branching. UI implementation detail: Always call store getters directly in Svelte templates (e.g., `{getGetter()}`) rather than copying store state into local component `$state` to avoid reactivity lag.
- **Svelte 5 Reactivity:** Use `$state` rune for reactive state objects. Use `$derived` runes in components to track store getter changes. Use `$effect` for side effects. Never copy store values into local `$state` variables in components—use `$derived` instead.
- **Loading States:** Use `-1` as sentinel value for "loading/unknown" state (e.g., `snapshotCount = -1`). This prevents buttons from flickering to "enabled" during initial load. Only transition to `0` when data is actually loaded.
- **Error Handling:** Always check for null/undefined responses from backend before accessing properties. Show user-friendly error messages via toast notifications. Add null checks in async functions to prevent TypeError crashes.
- **UI Feedback:** Add `title` attributes to disabled buttons explaining why they're disabled. This helps users understand the required action (e.g., "Selecciona un snapshot en la cadena para organizar").

## File size guideline
**400-line soft limit per file.** When a file crosses this threshold:
1. Identify logical responsibility boundaries (not arbitrary line counts).
2. Extract the cohesive sub-domain into a new file with a single-responsibility name.
3. Python: add a new flat-layout file at root. TypeScript: add a new `src/*.ts` module (update file map and import graph in `typescript.instructions.md`).
4. Run all tests + build + lint before committing the split.

**Exception:** A file may safely exceed this limit if it represents a single, indivisible logical unit (e.g., a highly cohesive Class, Svelte Component, or complex pure function) that would lose clarity or context if artificially split.

## Frontend testing conventions
- Use Vitest with `@testing-library/dom` for DOM testing
- Mock external dependencies with `vi.mock()` at the top of test files
- Export functions that need testing (e.g., `showRenameDialog`, `showAddPlayerDialog`)
- Wrap module-level DOM access in conditional checks for test environment compatibility
- Test files: `frontend/src/*.test.ts`

## CSS conventions
- **Favor flex layout** for all UI structure — use `display: flex` and `flex-direction: column` for panels, rows, and containers.
- Use `flex: 1` for expandable content, `flex-shrink: 0` for fixed elements
- Use `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` for text truncation
- Use `margin-left: auto` to push elements to the right in flex containers
- Use Svelte's native `<style>` blocks within `.svelte` files for component-specific styles to keep styling scoped and tied directly to the component.
- Reserve `static/style.css` strictly for global variables (`:root`), body resets, and widely shared utility classes (e.g., `.btn`).
- All CSS source files must be human-readable with properties written on multiple lines.
- **Panel scroll pattern**: For panels with scrollable content + fixed buttons at bottom:
  - `.panel-body` → `display: flex; flex-direction: column; overflow: hidden;`
  - `.panel-scroll` → `flex: 1; overflow-y: auto; min-height: 0;`
  - Wrap scrollable sections in `<div class="panel-scroll">`, keep buttons outside

## Ripple-effect checklist
**Player field change** → `organizador.py` · `models.py` · `formatter.py` · `notion_sync.py` · `db.py` (schema + helpers) · `db_game.py` (game helpers) · `viewer.py` (API) · `test_organizador.py` (`_j()` + `_pool()`) · `test_algoritmo.py` (`_j()` + `_pool()`) · `test_db.py` (`TestDb`) · `test_viewer.py` (`_add_snapshot()` helper)
**New Flask route** → `TestApi*` class in `test_viewer.py` with 200 + 400 + 404 coverage.
**Chain algorithm change** → update `db_views.py` · `TestApiChain` in `test_viewer.py` (use `roots` tree, not `nodes` flat list) · `TestDb` in `test_db.py` · "Chain lineage" section in `python.instructions.md`.
**DB schema change** → update `_SCHEMA` in `db.py` · all affected helpers · `test_db.py` `TestDb` · `test_viewer.py` fixtures · `python.instructions.md`.
**UI logic change** → edit relevant `src/*.ts` module + `bun run build`. **New domain type** → add to `src/types.ts`. **Style change** → edit `static/style.css`. Never re-inline into `index.html`.
**Frontend test** → add to `frontend/src/*.test.ts` · mock dependencies with `vi.mock()` · export tested functions.

Tests live at root alongside source — flat layout is intentional for this project size.


