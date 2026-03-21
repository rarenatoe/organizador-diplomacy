# Copilot Instructions — Organizador Diplomacy

## Stack
Python 3.13 · uv · Flask 3 · pytest · notion-client · python-dotenv · flat CSVs in `data/`

## File map
| File | Role |
|---|---|
| `organizador.py` | Algorithm: `Jugador`, `Mesa`, `ResultadoPartidas`, `_calcular_partidas()` |
| `utils.py` | Shared: `DIRECTORIO`, `ultimo_csv()`, `siguiente_csv()` |
| `viewer.py` | Flask viewer: report parsing, `_build_chain()`, REST API |
| `notion_sync.py` | Notion → CSV sync; writes CSVs + `.pending` flag |
| `templates/index.html` | Single-page UI — plain HTML/CSS/JS, no build step, no framework |
| `test_organizador.py` | Tests for `organizador.py` + `utils.py` (`TestUtils` class) |
| `test_viewer.py` | Tests for `viewer.py` |
| `data/` | `jugadores_NNNN.csv` (immutable, git-tracked) + `reporte_*.txt` (git-ignored) |

Tests live at root alongside source — flat layout is intentional for this project size.

## Data model
- **CSV** `data/jugadores_NNNN.csv` — immutable numbered snapshots; never edit in-place.
  Columns: `Nombre, Experiencia, Juegos_Este_Ano, Prioridad, Partidas_Deseadas, Partidas_GM`
- **Report** `data/reporte_YYYY-MM-DD_HH-MM-SS.txt` — 4 sections separated by `"═"*44`:
  `LISTO PARA COMPARTIR` · `DETALLE DEL EVENTO` · `PROYECCIÓN JUEGOS_ESTE_AÑO` · `REGISTRO`
  `REGISTRO` fields `Leído de` / `Escrito en` are the **canonical chain lineage edges**.
- **Pending flag** `data/.pending` — created by `notion_sync.py`, deleted by `organizador.py`.

## Chain lineage (`_build_chain` in viewer.py)
Returns `{"roots": [...], "pending": bool}` — a **tree**, not a flat list.
Each CSV node: `{type, filename, player_count, is_latest, pending, branches: [{report, output}, …]}`
Each report node: `{type, filename, generated, partidas, en_espera, intentos, leido, escrito}`

- Root CSVs = CSVs not produced by any report (notion_sync outputs or manual imports).
- `csv_to_reports[csv]` = reports sorted by filename (timestamp = chronological).
- Walk: each CSV owns its branches; each branch is `{report, output_csv_subtree}`.
- Safety net: CSVs unreachable from roots are appended as additional roots.
- **Never use a flat `nodes` list** — that caused the bug where report_B from csv_0001
  rendered as a child of csv_0002 instead of a sibling branch of report_A.

## UI conventions (`templates/index.html`)
- No framework, no build step. All logic in vanilla JS inside the file.
- **Click-to-select**: CSV node click → `setSelectedCsv(fn)` → `.csv-selected` green ring + button label "Organizar · NNNN".
- `runOrganizar()` reads `_selectedCsv` (`null` = latest CSV). `deselectCsv()` resets.

## Code conventions
- Type hints on **all** function signatures. `Path` everywhere (no raw strings).
- No `input()` — non-interactive. `print()` → stdout; `print(..., file=sys.stderr)` → errors.
- Code section separators: `# ── Title ────────────────────────────────────────────`
- Filename regexes: CSV `jugadores_\d{4}\.csv` · Report `reporte_.+\.txt`

## Testing rules
Every new behavior → test in the corresponding file.
- New function → happy path + edge case (empty/zero) + invalid input.
- New Flask route → 200 success + 400 invalid input + 404 missing resource.
- New business rule → test name/docstring names the rule explicitly.
- Bug fix → regression test that would have caught it **before** the fix.
- Run `uv run python -m pytest -q` — all must pass before committing.

| Module | Test location |
|---|---|
| `organizador.py` | `test_organizador.py` |
| `utils.py` | `test_organizador.py` → `TestUtils` |
| `viewer.py` | `test_viewer.py` |
| `notion_sync.py` | manual/integration only (requires Notion API key) |

## After every feature or fix
1. Run `uv run python -m pytest -q` — confirm all pass.
2. Add/update tests in the relevant test file.
3. Update **this file** if conventions, stack, data model, or architecture changed.
4. Commit: `feat:` · `fix:` · `refactor:` · `test:` prefix.

## Ripple-effect checklist
**CSV column change** → `organizador.py` · `notion_sync.py` · `viewer.py` (API + HTML table) · `test_organizador.py` (`_j()` + `_pool()` helpers) · `test_viewer.py` (`_make_csv()` helper)
**New Flask route** → `TestApi*` class in `test_viewer.py` with 200 + 400 + 404 coverage.
**Chain algorithm change** → update `TestApiChain` in `test_viewer.py` (use `roots` tree, not `nodes` flat list) + "Chain lineage" section above.

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
