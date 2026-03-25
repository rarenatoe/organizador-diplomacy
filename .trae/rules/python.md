<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->
<!-- Source of truth: docs/ai-rules/*.md -->
---
description: Python Scoped Instructions
globs: backend/**/*.py
---

## Python code conventions
- Type hints on **all** function signatures. `Path` everywhere (no raw strings).
- No `input()` — non-interactive. `print()` → stdout; `print(..., file=sys.stderr)` → errors.
- Code section separators: `# ── Title ────────────────────────────────────────────`

## Data model — SQLite schema (`db.py`)

```sql
graph_nodes (id PRIMARY KEY, entity_type CHECK IN ('snapshot', 'event'))
players (id, nombre UNIQUE)
snapshots (id FK references graph_nodes, created_at, source CHECK IN ('notion_sync','organizar','manual'))
snapshot_players (snapshot_id FK, player_id FK, experiencia, juegos_este_ano, prioridad, partidas_deseadas, partidas_gm, PK(snapshot_id, player_id))
events (id FK references graph_nodes, created_at, type CHECK IN ('sync', 'game', 'edit'), source_snapshot_id FK, output_snapshot_id FK)
game_details (event_id FK references events, intentos, copypaste_text)
mesas (id, game_event_id FK, numero, gm_player_id FK nullable)
mesa_players (mesa_id FK, player_id FK, orden, PK(mesa_id, player_id))
waiting_list (id, game_event_id FK, player_id FK, orden, cupos_faltantes)
```

**Graph Node Hierarchy Pattern**: All snapshots and events are descendants of the `graph_nodes` table. This allows for:
1.  **Global Unique IDs**: Snapshots and events never share an ID, simplifying UI routing and store logic.
2.  **Recursive Cascade**: Deleting a record from `graph_nodes` triggers `ON DELETE CASCADE` across all dependent tables (e.g., `snapshot_players`, `game_details`, `mesas`).
3.  **Atomic Deletes**: `delete_snapshot_cascade` identifies the subtree of nodes and deletes them from `graph_nodes` in a single transaction.

Key helpers:
- `db.py`: `get_db()`, `get_or_create_player()`, `create_snapshot()`, `add_snapshot_player()`, `get_snapshot_players()`, `get_latest_snapshot_id()`, `snapshots_have_same_roster()`, `create_sync_event()`, `create_game_event()`, `create_output_snapshot()`, `create_manual_snapshot()`, `delete_snapshot_cascade()`
- `db_game.py`: `create_game_event()`, `create_mesa()`, `add_mesa_player()`, `add_waiting_player()`, `create_output_snapshot()`
- `db_views.py`: `build_chain_data()` → DFS tree, `get_snapshot_detail()`, `get_game_event_detail()`

## Chain lineage (`build_chain_data` in `db_views.py`)
Returns `{"roots": [...]}` — a **tree**, not a flat list.
Each snapshot node: `{type:"snapshot", id, created_at, source, player_count, is_latest, branches: [{edge, output}, ...]}`
Each game edge: `{type:"game", id, created_at, from_id, to_id, intentos, mesa_count, espera_count}`
Each sync edge: `{type:"sync", id, created_at, from_id, to_id}`

- Root snapshots = snapshots not produced by any edge.
- `from_to[from_id]` = edges sorted by `created_at` (chronological).
- Walk: each snapshot owns its branches; each branch is `{edge, output: snapshot_node|null}`.
- Safety net: snapshots unreachable from roots are appended as additional roots.
- **Never use a flat `nodes` list** — that caused the bug where report_B from csv_0001 rendered as a child of csv_0002.

## Notion Sync behavior (important UX distinction)
`notion_sync.py` is a **fresh pull from Notion** — it always reads `Nombre`, `Experiencia`, `Juegos_Este_Ano` from Notion.
- **Strict Roster Rule:** It only updates players already present in the selected snapshot. It does **NOT** import new players from Notion. Local players not found in Notion are preserved.
- **Merge Name Support:** Accepts a `--merges` JSON argument to map local names to Notion names (e.g., "Kur" -> "Kurt"). Merged players adopt the Notion name and update their stats while preserving local configs.
- Preserves `prioridad`, `partidas_deseadas`, `partidas_gm` from the **selected snapshot** (or latest if none is selected).

## Flask API (`viewer.py`)
| Route | Method | Response |
|---|---|---|
| `GET /api/chain` | GET | `{"roots": [...]}` tree |
| `GET /api/snapshot/<int:id>` | GET | snapshot detail (200/404) |
| `DELETE /api/snapshot/<int:id>` | DELETE | `{"deleted": [id, ...]}` (200/404) |
| `GET /api/game/<int:id>` | GET | game event detail (200/404) |
| `GET /api/snapshots` | GET | `{"snapshots": [{id, created_at, source}, ...]}` |
| `POST /api/snapshot/<int:id>/edit` | POST | `{"snapshot_id": new_id}` — creates new `manual` snapshot (200/400/404) |
| `POST /api/run/<script>` | POST | `{returncode, stdout, stderr}` |

`/api/run/organizar` body: `{"snapshot": <int_id>}` — **Required: snapshot ID must be explicitly provided**.
`/api/snapshot/<id>/edit` body: `{"players": [{nombre, prioridad, partidas_deseadas, partidas_gm}, ...]}` — only listed players are included; omitting a player removes them from the next jornada.

## No defaults rule
Backend functions must never internally resolve 'latest' snapshots for state-changing operations. The caller is always responsible for providing an explicit snapshot ID.

## Snapshot requirement rules
- **organizar**: Always requires `snapshot_id`. Returns 400 if missing with message: "Snapshot selection required. Please click a snapshot node in the chain before syncing or organizing."
- **notion_sync**: Requires `snapshot_id` when database has existing data. Allows missing `snapshot_id` only for first-time sync (empty database). Returns 400 if missing with same message as organizar.
- **sync/detect**: Always requires `snapshot_id`. Returns 400 if missing.
- **sync/confirm**: Always requires `snapshot_id`. Returns 400 if missing.
- **First-time sync exception**: When database is empty (no snapshots), `notion_sync` without `--snapshot` is allowed to create the initial snapshot.

## Error message format
Use consistent error messages across all endpoints:
- Missing snapshot: "Snapshot selection required. Please click a snapshot node in the chain before syncing or organizing."
- Invalid snapshot type: "snapshot must be an integer"
- Snapshot not found: "not found" (404)

## Testing rules (Python)
Every new behavior → test in the corresponding file.
- New function → happy path + edge case (empty/zero) + invalid input.
- New Flask route → 200 success + 400 invalid input + 404 missing resource.
- New business rule → test name/docstring names the rule explicitly.
- Bug fix → regression test that would have caught it **before** the fix.

| Module | Test location |
|---|---|
| `organizador/organizador.py` · `organizador/models.py` (basic) | `organizador/test_organizador.py` |
| `organizador/organizador.py` (priority, GM, liga) | `organizador/test_algoritmo.py` |
| `db/db.py` · `db/db_game.py` · `db/db_views.py` | `db/test_db.py` → `TestDb` class |
| `viewer/viewer.py` | `viewer/test_viewer.py` (in-memory DB via `db.get_db(":memory:")`) |
| `sync/notion_sync.py` | manual/integration only (requires Notion API key) |
