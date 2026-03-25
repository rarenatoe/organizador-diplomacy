---
id: python
title: Python Scoped Instructions
scope: language
applyTo:
  - backend/**/*.py
priority: 80
outputs:
  copilot: .github/python.instructions.md
  trae: .trae/rules/python.md
toolNotes:
  copilot: Scoped instructions for Python changes.
  trae: Auto-attached for backend/**/*.py files.
---

## Python conventions
- Type hints on all function signatures. `Path` for file paths.
- Non-interactive: no `input()`. `print()` for stdout, `sys.stderr` for errors.
- Separators: `# ── Title ────────────────────────────────────────────`

## Data Model (SQLite)
`graph_nodes`: Global IDs, `ON DELETE CASCADE`.
`players`: `id`, `nombre` (unique).
`snapshots`: `id`, `created_at`, `source`.
`snapshot_players`: Join table with stats (`experiencia`, `prioridad`, etc.).
`events`: `id`, `created_at`, `type`, `source_snapshot_id`, `output_snapshot_id`.
`game_details`, `mesas`, `mesa_players`, `waiting_list`: Game state.

## Chain Lineage
`build_chain_data` returns a tree (`roots`).
- Snapshots own `branches` (edges to output snapshots).
- Sort edges by `created_at`.

## Notion Sync
- Fresh pull of `Nombre`, `Experiencia`, `Juegos_Este_Ano`.
- Strict Roster: only updates existing players. No new players added unless first sync.
- Merges: `--merges` JSON maps local names to Notion names.
- Preserves local stats (`prioridad`, `partidas_deseadas`, `partidas_gm`).

## API (viewer.py)
- `GET /api/chain`: Tree data.
- `GET /api/snapshot/<id>`: Detail.
- `POST /api/snapshot/<id>/edit`: New manual snapshot.
- `POST /api/run/<script>`: Run `organizar` or `notion_sync`.
- Required: explicit `snapshot_id` for state-changing operations. No 'latest' fallback.

## Testing
- Tests in corresponding files.
- Coverage: happy path, edge cases (0, empty), invalid input.
- Bug fixes: regression tests.

| Module | Test |
|---|---|
| `organizador/` | `test_organizador.py`, `test_algoritmo.py` |
| `db/` | `test_db.py` |
| `viewer/` | `test_viewer.py` |
| `sync/` | `test_notion_sync.py` |
