---
applyTo: "backend/**/*.py"
---

## Python code conventions
- Type hints on **all** function signatures. `Path` everywhere (no raw strings).
- No `input()` — non-interactive. `print()` → stdout; `print(..., file=sys.stderr)` → errors.
- Code section separators: `# ── Title ────────────────────────────────────────────`

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
- `create_manual_snapshot(conn, source_snapshot_id, edits)` → int  ← new 'manual' snapshot with player subset/field overrides
- `delete_snapshot_cascade(conn, snapshot_id)` → list[int]  ← removes snapshot + downstream events/snapshots

Key helpers in `db_game.py`:
- `create_game_event(conn, input_snapshot_id, output_snapshot_id, intentos, copypaste_text)` → int
- `create_mesa(conn, game_event_id, numero, gm_player_id)` → int
- `add_mesa_player(conn, mesa_id, player_id, orden)` → None
- `add_waiting_player(conn, game_event_id, player_id, orden, cupos_faltantes)` → None
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
| `GET /api/snapshots` | GET | `{"snapshots": [{id, created_at, source}, …]}` |
| `POST /api/snapshot/<int:id>/edit` | POST | `{"snapshot_id": new_id}` — creates new `manual` snapshot (200/400/404) |
| `POST /api/run/<script>` | POST | `{returncode, stdout, stderr}` |

`/api/run/organizar` body: `{"snapshot": <int_id>}` (omit to use latest).
`/api/snapshot/<id>/edit` body: `{"players": [{nombre, prioridad, partidas_deseadas, partidas_gm}, …]}` — only listed players are included; omitting a player removes them from the next jornada.

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
