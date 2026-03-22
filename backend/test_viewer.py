"""
test_viewer.py — Unit tests for viewer.py (Flask backend).

Covers:
  - API routes: /api/chain, /api/snapshot/<id>, /api/game/<id>, /api/snapshots
  - /api/run validation (unknown script, invalid snapshot value)
  - db.build_chain_data: tree {"roots": [...]} from DB
"""
from __future__ import annotations

import json

import pytest

from . import db, db_game, viewer
from .viewer import app


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_db() -> "db.sqlite3.Connection":
    """Returns an in-memory DB with the full schema."""
    return db.get_db(":memory:")


def _add_snapshot(conn, source: str = "notion_sync", players: int = 5) -> int:
    """Creates a snapshot with `players` dummy players and returns the snapshot id."""
    snap_id = db.create_snapshot(conn, source)
    for i in range(players):
        pid = db.get_or_create_player(conn, f"Jugador_{snap_id}_{i}")
        db.add_snapshot_player(conn, snap_id, pid, "Antiguo", i, 0, 1, 0)
    conn.commit()
    return snap_id


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mem_db():
    conn = _make_db()
    yield conn
    conn.close()


@pytest.fixture
def client(mem_db, monkeypatch):
    """Flask test client with db.get_db() patched to return the in-memory DB.

    A thin proxy that swallows close() lets routes follow their normal
    try/finally cleanup without destroying the shared in-memory connection.
    """
    class _NoClose:
        """Proxy for sqlite3.Connection that ignores close() calls."""
        def __init__(self, conn: "db.sqlite3.Connection") -> None:
            object.__setattr__(self, "_c", conn)
        def __getattr__(self, name: str):  # type: ignore[override]
            return getattr(object.__getattribute__(self, "_c"), name)
        def __setattr__(self, name: str, value: object) -> None:
            setattr(object.__getattribute__(self, "_c"), name, value)
        def close(self) -> None:
            pass  # keep the connection alive for the full test

    monkeypatch.setattr(db, "get_db", lambda path=None: _NoClose(mem_db))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, mem_db


# ── /api/chain ────────────────────────────────────────────────────────────────

class TestApiChain:
    def test_empty_db_returns_empty_roots(self, client):
        c, conn = client
        resp = c.get("/api/chain")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["roots"] == []

    def test_single_snapshot_is_root(self, client):
        c, conn = client
        _add_snapshot(conn, players=3)
        resp = c.get("/api/chain")
        data = json.loads(resp.data)
        assert len(data["roots"]) == 1
        root = data["roots"][0]
        assert root["type"] == "snapshot"
        assert root["player_count"] == 3
        assert root["branches"] == []

    def test_sync_branch_not_a_root(self, client):
        """Snapshot produced by a sync_event must be a branch, not a root."""
        c, conn = client
        snap1 = _add_snapshot(conn)
        snap2 = _add_snapshot(conn)
        db.create_sync_event(conn, snap1, snap2)
        conn.commit()
        resp = c.get("/api/chain")
        data = json.loads(resp.data)
        assert len(data["roots"]) == 1
        root = data["roots"][0]
        assert root["id"] == snap1
        assert len(root["branches"]) == 1
        branch = root["branches"][0]
        assert branch["edge"]["type"] == "sync"
        assert branch["output"]["id"] == snap2

    def test_latest_flag_on_highest_id(self, client):
        """is_latest is True only on the snapshot with the highest id."""
        c, conn = client
        snap1 = _add_snapshot(conn)
        snap2 = _add_snapshot(conn)
        db.create_sync_event(conn, snap1, snap2)
        conn.commit()
        resp = c.get("/api/chain")
        data = json.loads(resp.data)
        root = data["roots"][0]
        assert root["is_latest"] is False
        assert root["branches"][0]["output"]["is_latest"] is True

    def test_two_branches_from_same_snapshot(self, client):
        """
        Regression: two game_events reading from snap1 must produce two sibling
        branches of snap1, not a chain snap1→game_A→snap2→game_B→snap3.
        """
        c, conn = client
        snap1 = _add_snapshot(conn, players=14)
        snap2 = _add_snapshot(conn, source="organizar", players=14)
        snap3 = _add_snapshot(conn, source="organizar", players=14)

        db_game.create_game_event(conn, snap1, snap2, 1, "copypaste1")
        db_game.create_game_event(conn, snap1, snap3, 1, "copypaste2")
        conn.commit()

        resp = c.get("/api/chain")
        data = json.loads(resp.data)
        # snap1 is the only root; snap2 and snap3 are children
        assert len(data["roots"]) == 1
        root = data["roots"][0]
        assert root["id"] == snap1
        assert len(root["branches"]) == 2
        output_ids = {b["output"]["id"] for b in root["branches"]}
        assert output_ids == {snap2, snap3}


# ── /api/snapshot/<id> ────────────────────────────────────────────────────────

class TestApiSnapshot:
    def test_returns_snapshot_detail(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn, players=4)
        resp = c.get(f"/api/snapshot/{snap_id}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["id"] == snap_id
        assert len(data["players"]) == 4

    def test_unknown_id_returns_404(self, client):
        c, conn = client
        resp = c.get("/api/snapshot/9999")
        assert resp.status_code == 404


# ── /api/game/<id> ────────────────────────────────────────────────────────────

class TestApiGame:
    def test_returns_game_detail(self, client):
        c, conn = client
        snap_in = _add_snapshot(conn, players=7)
        snap_out = _add_snapshot(conn, source="organizar", players=7)
        ge_id = db_game.create_game_event(conn, snap_in, snap_out, 1, "copypaste text")
        conn.commit()
        resp = c.get(f"/api/game/{ge_id}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["id"] == ge_id
        assert data["copypaste"] == "copypaste text"

    def test_unknown_id_returns_404(self, client):
        c, conn = client
        resp = c.get("/api/game/9999")
        assert resp.status_code == 404


# ── /api/snapshots ────────────────────────────────────────────────────────────

class TestApiSnapshots:
    def test_lists_snapshots_in_order(self, client):
        c, conn = client
        snap1 = _add_snapshot(conn, source="notion_sync")
        snap2 = _add_snapshot(conn, source="organizar")
        resp = c.get("/api/snapshots")
        data = json.loads(resp.data)
        ids = [s["id"] for s in data["snapshots"]]
        assert ids == [snap1, snap2]

    def test_empty_when_no_snapshots(self, client):
        c, conn = client
        resp = c.get("/api/snapshots")
        data = json.loads(resp.data)
        assert data["snapshots"] == []


# ── /api/run ──────────────────────────────────────────────────────────────────

class TestApiRun:
    def test_unknown_script_returns_400(self, client):
        c, conn = client
        resp = c.post("/api/run/evil_script")
        assert resp.status_code == 400

    def test_invalid_snapshot_type_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/run/organizar",
            data=json.dumps({"snapshot": "not_an_int"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_valid_integer_snapshot_accepted(self, client, monkeypatch):
        import subprocess
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post(
            "/api/run/organizar",
            data=json.dumps({"snapshot": 1}),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_no_snapshot_key_accepted(self, client, monkeypatch):
        """Omitting snapshot uses latest — should not 400."""
        import subprocess
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post("/api/run/organizar", content_type="application/json")
        assert resp.status_code == 200

    def test_run_notion_sync_with_snapshot_passes_arg(self, client, monkeypatch):
        """Passing snapshot id to notion_sync forwards --snapshot to the subprocess."""
        import subprocess
        calls: list[list[str]] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: calls.append(a[0]) or type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post(
            "/api/run/notion_sync",
            data=json.dumps({"snapshot": 3}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert "--snapshot" in calls[0]
        assert "3" in calls[0]
        assert "backend.notion_sync" in calls[0]

    def test_run_organizar_invokes_correct_module(self, client, monkeypatch):
        """Organizar script maps to backend.organizador module (not a bare .py file)."""
        import subprocess
        calls: list[list[str]] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: calls.append(a[0]) or type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post("/api/run/organizar", content_type="application/json")
        assert resp.status_code == 200
        assert "backend.organizador" in calls[0]

    def test_run_uses_module_flag(self, client, monkeypatch):
        """Both scripts are invoked with 'python -m <module>' to avoid relative-import errors."""
        import subprocess
        calls: list[list[str]] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: calls.append(a[0]) or type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        for script in ("notion_sync", "organizar"):
            calls.clear()
            c.post(f"/api/run/{script}", content_type="application/json")
            assert "-m" in calls[0], f"{script}: expected '-m' flag in command"
            # Must NOT be a bare .py filename (that would trigger the relative-import error)
            assert not any(arg.endswith(".py") for arg in calls[0]), (
                f"{script}: command must not reference a .py file directly"
            )

    def test_run_cwd_is_project_root(self, client, monkeypatch):
        """subprocess.run must be called with cwd set to the project root (not backend/)."""
        import subprocess
        from pathlib import Path
        captured_kwargs: list[dict] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: captured_kwargs.append(kw) or type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        c.post("/api/run/notion_sync", content_type="application/json")
        assert captured_kwargs, "subprocess.run was not called"
        cwd = Path(captured_kwargs[0]["cwd"])
        # The cwd must be the project root, which contains pyproject.toml
        assert (cwd / "pyproject.toml").exists(), (
            f"cwd '{cwd}' is not the project root (pyproject.toml not found there)"
        )
        # Must NOT be the backend/ subdirectory
        assert cwd.name != "backend", "cwd must be project root, not backend/"

    def test_run_notion_sync_invalid_snapshot_type_returns_400(self, client):
        """notion_sync with a non-integer snapshot value returns 400."""
        c, conn = client
        resp = c.post(
            "/api/run/notion_sync",
            data=json.dumps({"snapshot": "bad"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_run_notion_sync_no_snapshot_accepted(self, client, monkeypatch):
        """Calling notion_sync without snapshot uses latest — should not 400."""
        import subprocess
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post("/api/run/notion_sync", content_type="application/json")
        assert resp.status_code == 200


# ── DELETE /api/snapshot/<id> ───────────────────────────────────────────────────

class TestApiDeleteSnapshot:
    def test_delete_existing_snapshot_returns_200(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn)
        conn.commit()
        resp = c.delete(f"/api/snapshot/{snap_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert snap_id in data["deleted"]

    def test_delete_nonexistent_snapshot_returns_404(self, client):
        c, conn = client
        resp = c.delete("/api/snapshot/9999")
        assert resp.status_code == 404

    def test_delete_removes_snapshot_from_chain(self, client):
        """After deletion the snapshot no longer appears in /api/chain."""
        c, conn = client
        snap_id = _add_snapshot(conn)
        conn.commit()
        c.delete(f"/api/snapshot/{snap_id}")
        chain = c.get("/api/chain").get_json()
        ids = [n["id"] for n in chain["roots"]]
        assert snap_id not in ids

    def test_delete_cascades_sync_event_via_api(self, client):
        """Deleting the output snapshot of a sync event returns both IDs deleted."""
        c, conn = client
        snap1 = _add_snapshot(conn)
        snap2 = _add_snapshot(conn)
        db.create_sync_event(conn, snap1, snap2)
        conn.commit()
        resp = c.delete(f"/api/snapshot/{snap2}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert snap2 in data["deleted"]
        # snap1 must NOT be in deleted list
        assert snap1 not in data["deleted"]


class TestApiEditSnapshot:
    def test_edit_creates_new_manual_snapshot(self, client):
        """POST /api/snapshot/<id>/edit returns 200 with new snapshot_id."""
        c, conn = client
        snap_id = _add_snapshot(conn, players=3)
        conn.commit()
        names = [p["nombre"] for p in db.get_snapshot_players(conn, snap_id)]
        players_list = [
            {"nombre": n, "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 0}
            for n in names
        ]
        resp = c.post(
            f"/api/snapshot/{snap_id}/edit",
            data=json.dumps({"players": players_list}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "snapshot_id" in data
        assert data["snapshot_id"] != snap_id

    def test_edit_nonexistent_snapshot_returns_404(self, client):
        c, conn = client
        resp = c.post(
            "/api/snapshot/9999/edit",
            data=json.dumps({"players": []}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_edit_invalid_players_type_returns_400(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn)
        conn.commit()
        resp = c.post(
            f"/api/snapshot/{snap_id}/edit",
            data=json.dumps({"players": "not_a_list"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_edit_new_snapshot_has_manual_source(self, client):
        """The snapshot created by the edit endpoint has source='manual'."""
        c, conn = client
        snap_id = _add_snapshot(conn, players=1)
        conn.commit()
        names = [p["nombre"] for p in db.get_snapshot_players(conn, snap_id)]
        resp = c.post(
            f"/api/snapshot/{snap_id}/edit",
            data=json.dumps({"players": [
                {"nombre": names[0], "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 0}
            ]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        new_id = resp.get_json()["snapshot_id"]
        detail = c.get(f"/api/snapshot/{new_id}").get_json()
        assert detail["source"] == "manual"


# ── /api/sync/detect ──────────────────────────────────────────────────────────

class TestApiSyncDetect:
    def test_detect_returns_valid_json(self, client, monkeypatch):
        """POST /api/sync/detect returns valid JSON with similar_names."""
        import subprocess
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {
                "returncode": 0,
                "stdout": json.dumps({
                    "notion_count": 5,
                    "snapshot_count": 5,
                    "similar_names": []
                }),
                "stderr": ""
            })(),
        )
        resp = c.post("/api/sync/detect", content_type="application/json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "similar_names" in data
        assert "notion_count" in data
        assert "snapshot_count" in data

    def test_detect_with_snapshot_passes_arg(self, client, monkeypatch):
        """Passing snapshot id to detect forwards --snapshot to the subprocess."""
        import subprocess
        calls: list[list[str]] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: calls.append(a[0]) or type("R", (), {
                "returncode": 0,
                "stdout": json.dumps({"notion_count": 0, "snapshot_count": 0, "similar_names": []}),
                "stderr": ""
            })(),
        )
        resp = c.post(
            "/api/sync/detect",
            data=json.dumps({"snapshot": 3}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert "--snapshot" in calls[0]
        assert "3" in calls[0]
        assert "--detect-only" in calls[0]

    def test_detect_invalid_snapshot_type_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/sync/detect",
            data=json.dumps({"snapshot": "bad"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_detect_failure_returns_500(self, client, monkeypatch):
        """If subprocess returns non-zero, detect returns 500."""
        import subprocess
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": "error"})(),
        )
        resp = c.post("/api/sync/detect", content_type="application/json")
        assert resp.status_code == 500


# ── /api/sync/confirm ─────────────────────────────────────────────────────────

class TestApiSyncConfirm:
    def test_confirm_returns_run_result(self, client, monkeypatch):
        """POST /api/sync/confirm returns RunResult with returncode."""
        import subprocess
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post("/api/sync/confirm", content_type="application/json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["returncode"] == 0

    def test_confirm_with_merges_passes_json(self, client, monkeypatch):
        """Passing merges forwards --merges JSON to the subprocess."""
        import subprocess
        calls: list[list[str]] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: calls.append(a[0]) or type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        merges = [{"from": "John D.", "to": "John Doe"}]
        resp = c.post(
            "/api/sync/confirm",
            data=json.dumps({"merges": merges}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert "--merges" in calls[0]
        # Find the merges JSON in the command
        merges_idx = calls[0].index("--merges")
        merges_json = calls[0][merges_idx + 1]
        parsed = json.loads(merges_json)
        assert parsed["merges"] == merges

    def test_confirm_with_snapshot_passes_arg(self, client, monkeypatch):
        """Passing snapshot id to confirm forwards --snapshot to the subprocess."""
        import subprocess
        calls: list[list[str]] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: calls.append(a[0]) or type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post(
            "/api/sync/confirm",
            data=json.dumps({"snapshot": 5}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert "--snapshot" in calls[0]
        assert "5" in calls[0]

    def test_confirm_invalid_snapshot_type_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/sync/confirm",
            data=json.dumps({"snapshot": "bad"}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ── /api/player/rename ────────────────────────────────────────────────────────

class TestApiPlayerRename:
    def test_rename_player_success(self, client):
        c, conn = client
        # Create a player
        pid = db.get_or_create_player(conn, "Turk")
        conn.commit()
        
        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "Turk", "new_name": "Kurt"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        
        # Verify the name was changed
        row = conn.execute("SELECT nombre FROM players WHERE id = ?", (pid,)).fetchone()
        assert row["nombre"] == "Kurt"

    def test_rename_player_not_found_returns_404(self, client):
        c, conn = client
        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "NonExistent", "new_name": "NewName"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_rename_player_new_name_exists_returns_404(self, client):
        c, conn = client
        # Create two players
        db.get_or_create_player(conn, "Player1")
        db.get_or_create_player(conn, "Player2")
        conn.commit()
        
        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "Player1", "new_name": "Player2"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_rename_player_same_name_returns_400(self, client):
        c, conn = client
        db.get_or_create_player(conn, "Player1")
        conn.commit()
        
        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "Player1", "new_name": "Player1"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_rename_player_missing_fields_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/player/rename",
            data=json.dumps({"old_name": "Player1"}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ── /api/snapshot/<id>/add-player ─────────────────────────────────────────────

class TestApiAddPlayer:
    def test_add_player_success(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn, players=1)
        conn.commit()
        
        resp = c.post(
            f"/api/snapshot/{snap_id}/add-player",
            data=json.dumps({
                "nombre": "NewPlayer",
                "experiencia": "Nuevo",
                "juegos_este_ano": 0,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "player_id" in data
        
        # Verify the player was added
        players = db.get_snapshot_players(conn, snap_id)
        nombres = [p["nombre"] for p in players]
        assert "NewPlayer" in nombres

    def test_add_player_nonexistent_snapshot_returns_404(self, client):
        c, conn = client
        resp = c.post(
            "/api/snapshot/9999/add-player",
            data=json.dumps({"nombre": "NewPlayer"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_add_player_missing_nombre_returns_400(self, client):
        c, conn = client
        snap_id = _add_snapshot(conn, players=1)
        conn.commit()
        
        resp = c.post(
            f"/api/snapshot/{snap_id}/add-player",
            data=json.dumps({"experiencia": "Nuevo"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
