# Copilot Instructions — Organizador Diplomacy

## Stack
Python 3.13 · uv · Flask 3 · pytest · notion-client · python-dotenv · SQLite (stdlib)
TypeScript 5 (strict) · bun · ESLint 9 (typescript-eslint v8 `strictTypeChecked`)

## File map

### Python (flat layout — intentional for this project size)
| File | Role |
|---|---|
| `organizador.py` | Algorithm entry-point: `_calcular_partidas()`, `organizar_partidas()` |
| `models.py` | Domain types: `Jugador`, `Mesa`, `ResultadoPartidas` |
| `formatter.py` | Pure text generation: `_formatear_*`, `_construir_proyeccion` |
| `utils.py` | Shared constants: `DIRECTORIO` |
| `db.py` | SQLite schema, connection, all write/read CRUD helpers |
| `db_views.py` | Read-only query helpers for viewer: `build_chain_data`, `get_snapshot_detail`, `get_game_event_detail` |
| `viewer.py` | Flask viewer: DB-backed REST API |
| `notion_sync.py` | Notion → DB sync (content-addressed, no CSV files) |
| `migrate.py` | One-time migration from CSV/TXT/metadata.json → `diplomacy.db` |
| `test_organizador.py` | Tests for `organizador.py` and `models.py` |
| `test_db.py` | Tests for `db.py` and `db_views.py` (`TestDb` class) |
| `test_viewer.py` | Tests for `viewer.py` (in-memory SQLite via `db.get_db(":memory:")`) |

### TypeScript
| Path | Role |
|---|---|
| `src/types.ts` | All TypeScript interfaces shared across the UI (domain types) |
| `src/app.ts` | All UI logic — **edit this, not `static/app.js`** |
| `static/app.js` | Bundled output (bun build IIFE). **Gitignored** — regenerate with `bun run build`. |
| `static/style.css` | All CSS for the viewer UI |
| `templates/index.html` | ~57-line Jinja2 shell. No inline logic, no onclick attributes. |

### Config
| File | Role |
|---|---|
| `tsconfig.json` | `strict: true` + `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes` |
| `eslint.config.mjs` | `typescript-eslint` `strictTypeChecked` flat config |
| `package.json` | bun scripts: `build`, `typecheck`, `lint`, `lint:fix` |

### Data (`data/`)
| File | Format | Git | Mutability |
|---|---|---|---|
| `diplomacy.db` | SQLite | ignored | runtime state — single source of truth |

**One file, one format. No CSVs, no .txt reports, no metadata.json.**

### Why `src/` only contains TypeScript
`src/` is the source directory for the only compiled language in this project.
Python files are interpreted and run directly — no compilation step, no separate source/output distinction.
The flat Python layout is intentional and appropriate for the current project size (~10 source files).

**`static/app.js` is a build artifact and is gitignored.** After cloning, run `bun install && bun run build` before starting the viewer.
`bun build` bundles `src/app.ts` (entry point) and all its imports (e.g. `src/types.ts`) into a single IIFE at `static/app.js`.

## Data model — SQLite schema (`db.py`)

```sql
players (id, nombre UNIQUE)
snapshots (id, created_at, source CHECK IN ('notion_sync','organizar','manual'))
snapshot_players (snapshot_id FK, player_id FK,
                  experiencia, juegos_este_ano, prioridad,
                  partidas_deseadas, partidas_gm, PK(snapshot_id, player_id))
sync_events (id, created_at, source_snapshot FK nullable, output_snapshot FK)
game_events (id, created_at, input_snapshot_id FK, output_snapshot_id FK,
             intentos, copypaste_text)
mesas (id, game_event_id FK, numero, gm_player_id FK nullable)
mesa_players (mesa_id FK, player_id FK, orden, PK(mesa_id, player_id))
waiting_list (id, game_event_id FK, player_id FK, orden, cupos_faltantes)
```

Key helpers in `db.py`:
- `get_db(path)` — opens connection; pass `":memory:"` for tests
- `get_or_create_player(conn, nombre)` → int
- `create_snapshot(conn, source)` → int
- `add_snapshot_player(conn, snap_id, player_id, experiencia, juegos, prioridad, deseadas, gm)` → None
- `get_snapshot_players(conn, snapshot_id)` → list[dict]
- `get_latest_snapshot_id(conn)` → int | None
- `snapshots_have_same_roster(conn, snapshot_id, notion_rows)` → bool  ← content-addressed guard
- `create_sync_event(conn, source_snapshot_id, output_snapshot_id)` → int
- `create_game_event(conn, input_snapshot_id, output_snapshot_id, intentos, copypaste_text)` → int
- `create_output_snapshot(conn, input_snapshot_id, resultado)` → int  ← copies+updates player state

Key helpers in `db_views.py`:
- `build_chain_data(conn)` → dict  ← DFS tree for the chain UI
- `get_snapshot_detail(conn, snapshot_id)` → dict | None
- `get_game_event_detail(conn, game_event_id)` → dict | None

## Chain lineage (`build_chain_data` in `db_views.py`)
Returns `{"roots": [...]}` — a **tree**, not a flat list.
Each snapshot node: `{type:"snapshot", id, created_at, source, player_count, is_latest, branches: [{edge, output}, …]}`
Each game edge: `{type:"game", id, created_at, from_id, to_id, intentos, mesa_count, espera_count}`
Each sync edge: `{type:"sync", id, created_at, from_id, to_id}`

- Root snapshots = snapshots not produced by any edge.
- `from_to[from_id]` = edges sorted by `created_at` (chronological).
- Walk: each snapshot owns its branches; each branch is `{edge, output: snapshot_node|null}`.
- Safety net: snapshots unreachable from roots are appended as additional roots.
- **Never use a flat `nodes` list** — that caused the bug where report_B from csv_0001 rendered as a child of csv_0002.

## Notion Sync behavior (important UX distinction)
`notion_sync.py` is a **fresh pull from Notion** — it does NOT use the selected snapshot.
- Always reads Notion for `Nombre`, `Experiencia`, `Juegos_Este_Ano`.
- Preserves `prioridad`, `partidas_deseadas`, `partidas_gm` from the latest snapshot in the DB.
- Guard: `snapshots_have_same_roster(conn, latest_id, notion_rows)` — if identical data and not `--force`, skips creating a new snapshot.
- Creates `sync_event(source=latest_id, output=new_snap_id)`.
- The selected snapshot in the UI only affects `Organizar`, never `Sync Notion`.

## Flask API (`viewer.py`)
| Route | Method | Response |
|---|---|---|
| `GET /api/chain` | GET | `{"roots": [...]}` tree |
| `GET /api/snapshot/<int:id>` | GET | snapshot detail (200/404) |
| `GET /api/game/<int:id>` | GET | game event detail (200/404) |
| `GET /api/snapshots` | GET | `{"snapshots": [{id, created_at, source}, …]}` |
| `POST /api/run/<script>` | POST | `{returncode, stdout, stderr}` |

`/api/run/organizar` body: `{"snapshot": <int_id>}` (omit to use latest).

## UI conventions
- `index.html` is a ~57-line Jinja2 shell. **No logic here, no onclick attributes** — event listeners wired in `src/app.ts`.
- All CSS in `static/style.css`. All JS compiled from `src/app.ts` → `static/app.js`.
- **Click-to-select**: snapshot node click → `setSelectedSnapshot(id)` → `.csv-selected` green ring + button label "Organizar · #N".
- Game node click → `openGame(id)` → GET `/api/game/<id>`, shows detail panel.
- Sync node click → `openSyncPanel(id)` → searches chain data for the edge, shows metadata panel.
- `runOrganizar()` reads `_selectedSnapshot` (`null` = latest snapshot). `deselectSnapshot()` resets.
- `renderSnapshotTree()` renders the chain recursively — branches stacked vertically so no false arrow.

## TypeScript conventions
- All domain interfaces live in `src/types.ts` — export everything from there.
- All UI logic lives in `src/app.ts` — import types with `import type { … } from "./types"`.
- Run `bun run build` to bundle into `static/app.js` (IIFE, no `type="module"` needed). `bun run typecheck` for type-only check. `bun run lint` — ESLint strict.
- All DOM interactions use `!` non-null assertion (acceptable — developer controls the HTML).
- No `onclick` attributes in HTML — all event listeners in `src/app.ts`.
- No `String()`, no `!!bool` — use the typed value directly.

## Code conventions
- Type hints on **all** function signatures. `Path` everywhere (no raw strings).
- No `input()` — non-interactive. `print()` → stdout; `print(..., file=sys.stderr)` → errors.
- Code section separators: `# ── Title ────────────────────────────────────────────`

## Testing rules
Every new behavior → test in the corresponding file.
- New function → happy path + edge case (empty/zero) + invalid input.
- New Flask route → 200 success + 400 invalid input + 404 missing resource.
- New business rule → test name/docstring names the rule explicitly.
- Bug fix → regression test that would have caught it **before** the fix.
- Run `uv run python -m pytest -q` — all must pass before committing.

| Module | Test location |
|---|---|
| `organizador.py` · `models.py` | `test_organizador.py` |
| `db.py` · `db_views.py` | `test_db.py` → `TestDb` class |
| `viewer.py` | `test_viewer.py` (in-memory DB via `db.get_db(":memory:")`) |
| `notion_sync.py` | manual/integration only (requires Notion API key) |
| `migrate.py` | manual only (requires existing data files) |

## After every feature or fix
1. Run `uv run python -m pytest -q` — confirm all pass.
2. Run `bun run build && bun run lint` — TypeScript must compile and lint clean.
3. Add/update tests in the relevant test file.
4. Update **this file** if conventions, stack, data model, or architecture changed.
5. Commit: `feat:` · `fix:` · `refactor:` · `test:` prefix.

## Engineering philosophy
**Never choose the shortcut over the maintainable solution.**
- Do not skip tests to save time. Do not defer documentation updates.
- Do not inline CSS/JS into HTML. Do not inline magic strings into multiple files.
- If a proper fix requires a larger refactor, do the refactor in a dedicated commit — do not apply a hack and plan to "fix it later."
- When uncertain between two approaches, choose the one that makes future changes easier, not the one that makes this change faster.

## Planned migrations (not yet implemented — do not regress)
- **Framework (Vue/React)**: Revisit if `src/app.ts` or total `src/` size exceeds ~500 lines again after the current modules. The bundler (`bun build`) is already in place; adding a framework is the next step.

## File size guideline
**500-line soft limit per file.** When a file crosses this threshold:
1. Identify logical responsibility boundaries (not arbitrary line counts).
2. Extract the cohesive sub-domain into a new file with a single-responsibility name.
3. Python: add a new flat-layout file at root. TypeScript: add a new `src/*.ts` module (export types, import in `app.ts`).
4. Update the file map table and ripple-effect checklist in this file.
5. Run all tests + build + lint before committing the split.

Split decisions made so far:
- `db.py` → `db.py` (CRUD) + `db_views.py` (read-only chain/detail queries)
- `test_organizador.py` → `test_organizador.py` (algorithm/models) + `test_db.py` (persistence layer)
- `src/app.ts` → `src/types.ts` (domain interfaces) + `src/app.ts` (UI logic)

## Ripple-effect checklist
**Player field change** → `organizador.py` · `models.py` · `formatter.py` · `notion_sync.py` · `db.py` (schema + helpers) · `viewer.py` (API) · `test_organizador.py` (`_j()` + `_pool()`) · `test_db.py` (`TestDb`) · `test_viewer.py` (`_add_snapshot()` helper)
**New Flask route** → `TestApi*` class in `test_viewer.py` with 200 + 400 + 404 coverage.
**Chain algorithm change** → update `db_views.py` · `TestApiChain` in `test_viewer.py` (use `roots` tree, not `nodes` flat list) · `TestDb` in `test_db.py` + “Chain lineage” section above.
**DB schema change** → update `_SCHEMA` in `db.py` · all affected helpers · `test_db.py` `TestDb` · `test_viewer.py` fixtures · this section.
**UI logic change** → edit `src/app.ts` + `bun run build`. **New domain type** → add to `src/types.ts`. **Style change** → edit `static/style.css`. Never re-inline into `index.html`.

Tests live at root alongside source — flat layout is intentional for this project size.


