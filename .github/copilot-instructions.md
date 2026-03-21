# Copilot Instructions — Organizador Diplomacy

## Project overview

Local Python tool for managing Diplomacy tournament rounds.
Stack: Python 3.13 · uv · Flask · pytest · notion-client · flat CSVs in `data/`.

## Testing rules

**Every new behavior must have a corresponding unit test.**

- New function → test its outputs for at least: happy path, edge case (empty/zero), and one invalid input.
- New Flask route → test: 200 success, 400 for invalid input, 404 for missing resources.
- New business rule (priority logic, weight calculation, CSV field change) → test the rule explicitly by name in the test docstring or test function name.
- Bug fix → add a regression test that would have caught the bug before the fix.

Test files:
| Module | Test file |
|---|---|
| `organizador.py` | `test_organizador.py` |
| `viewer.py` | `test_viewer.py` |
| `utils.py` | `test_organizador.py` (utils section) |
| `notion_sync.py` | manual / integration only (requires Notion API) |

Run tests with: `uv run python -m pytest -q`

## Code conventions

- Python type hints on all function signatures.
- `Path` objects (never raw strings) for all file paths.
- No `input()` calls anywhere — the tool is non-interactive.
- All user-facing output goes to `print()` on stdout; errors to `print(..., file=sys.stderr)`.
- Section separator comments use `# ── Title ─────...─` pattern.

## Data model

- `data/jugadores_NNNN.csv` — immutable numbered CSVs (tracked in git).
- `data/reporte_YYYY-MM-DD_HH-MM-SS.txt` — ignored by git, 4-section format.
- `data/.pending` — flag file; created by `notion_sync.py`, deleted by `organizador.py`.
- CSV columns: `Nombre, Experiencia, Juegos_Este_Ano, Prioridad, Partidas_Deseadas, Partidas_GM`.

## Adding features checklist

1. Write the test first (or alongside the implementation).
2. If changing a CSV column: update `organizador.py`, `notion_sync.py`, `viewer.py` (API + HTML table), and `test_organizador.py` fixture helpers.
3. If adding a new Flask route: add it to `TestApi*` classes in `test_viewer.py`.
4. After changes: run `uv run python -m pytest -q` and confirm all pass before committing.
5. Commit message format: `feat:`, `fix:`, `refactor:`, or `test:` prefix.
