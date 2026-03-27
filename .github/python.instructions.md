<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->
<!-- Source of truth: docs/ai-rules/*.md -->
---
applyTo: "backend/**/*.py"
---

# Python Instructions — Organizador Diplomacy

## Stack
Python 3.13 · uv · Flask 3 · pytest · notion-client · python-dotenv · SQLite (stdlib)

> Scoped instructions: `python.md` (applyTo `backend/**/*.py`) contain language-specific detail.

## Directory Layout
```
backend/
├── db/              Modular database operations
│   ├── connection.py      # Database connection and schema
│   ├── players.py         # Player CRUD operations
│   ├── snapshots.py       # Snapshot management
│   └── events.py         # Event operations
├── organizador/      Core algorithm and models
│   ├── core.py           # Country assignment algorithm
│   └── models.py         # Domain types
├── sync/              Notion integration
│   ├── api.py            # Notion API utilities
│   ├── similarity.py     # Name similarity detection
│   └── notion_sync.py   # Main orchestrator
└── viewer.py           # Flask REST API
```

## File Map

### Backend (`backend/`)
| File | Role |
|---|---|
| `connection.py` | Database connection and schema management |
| `players.py` | Player CRUD operations (get_or_create_player, rename_player, add_player_to_snapshot, get_snapshot_players) |
| `snapshots.py` | Snapshot management (create_snapshot, add_snapshot_player, get_latest_snapshot_id, snapshots_have_same_roster, create_manual_snapshot, create_root_manual_snapshot) |
| `events.py` | Event operations (create_event, create_sync_event, create_game_event, delete_snapshot_cascade) |
| `core.py` | Algorithm: `_calcular_partidas()`, `organizar_partidas()`, `assign_countries_to_mesa()` |
| `models.py` | Domain types: `Jugador`, `Mesa`, `ResultadoPartidas` |
| `formatter.py` | Text generation: `_formatear_*`, `_construir_proyeccion` |
| `db_game.py` | Game-event persistence (legacy, now in events.py) |
| `db_views.py` | Read-only queries for viewer |
| `viewer.py` | Flask REST API |
| `sync/api.py` | Notion API utilities (descargar_todos, conteo_partidas_este_ano, extraer_numero, extraer_nombre, experiencia) |
| `sync/similarity.py` | Name similarity detection (_normalize_name, _words_match, _similarity, _detect_similar_names) |
| `sync/notion_sync.py` | Main orchestrator (main function) |
| `test_*.py` | Tests (co-located with source files) |

## Principles
- **Modular Database**: Use separate files in `backend/db/` for different concerns (connection, players, snapshots, events).
- **Import Structure**: Import from `backend.db.connection` for database operations, not directly from `backend.db`.
- **Type Safety**: Use explicit type annotations for all function signatures and return types.
- **Error Handling**: Raise specific exceptions for invalid states, use try/except blocks for database operations.
- **Testing**: Tests co-located with source files, use pytest fixtures for consistent test data.
- **API Design**: Flask routes should return JSON responses, use proper HTTP status codes.
- **Background Processing**: Use separate modules for background tasks (like Notion caching).

## Business Logic
- **Shielding Strategy**: Country assignment algorithm in `assign_countries_to_mesa()` prevents player repetition by only assigning countries when necessary.
- **Draft Mode**: Game drafts are created in memory without database writes, allowing manual review before persistence.
- **Background Caching**: `notion_cache.py` provides SQLite table and `cache_daemon.py` for periodic data synchronization.
- **Two-step Draft API**: `/api/game/draft` calculates results without writing to DB, `/api/game/save` persists the draft.

## Database Schema
- **Global IDs**: All entities use `graph_nodes` table for universal IDs with cascading deletes.
- **Player Management**: `players` table with unique `nombre` constraint, linked to `graph_nodes`.
- **Snapshots**: `snapshots` table with `source` field for tracking data provenance.
- **Game Events**: `events` table with type field for different operations (sync, game, edit).
- **Country Assignment**: `mesa_players` table includes `pais` column for country assignments.

## Testing
- Use pytest for all backend tests.
- Test files should be `test_*.py` and co-located with implementation files.
- Mock external dependencies (Notion API) using `unittest.mock`.
- Test database operations using in-memory SQLite (`:memory:`).
