"""
test_viewer_run.py — Tests for /api/run endpoint.

Tests script execution and validation.
The 'organizar' script was replaced by the two-step /api/game/draft + /api/game/save
flow. Only 'notion_sync' is still accepted by /api/run.
"""
from __future__ import annotations

import json

# Fixtures are provided by conftest.py


# ── /api/run ──────────────────────────────────────────────────────────────────

class TestApiRun:
    def test_unknown_script_returns_400(self, client):
        c, conn = client
        resp = c.post("/api/run/evil_script")
        assert resp.status_code == 400

    def test_organizar_script_no_longer_accepted(self, client):
        """organizar was replaced by /api/game/draft + /api/game/save; /api/run/organizar → 400."""
        c, conn = client
        resp = c.post(
            "/api/run/organizar",
            data=json.dumps({"snapshot": 1}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "unknown script" in data["error"]

    def test_invalid_snapshot_type_returns_400(self, client):
        c, conn = client
        resp = c.post(
            "/api/run/notion_sync",
            data=json.dumps({"snapshot": "not_an_int"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_run_notion_sync_with_snapshot_passes_arg(self, client, monkeypatch):
        """Passing snapshot id to notion_sync forwards --snapshot to the subprocess."""
        import subprocess
        calls: list[list[str]] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **_kw: calls.append(a[0]) or type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post(
            "/api/run/notion_sync",
            data=json.dumps({"snapshot": 3}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert "--snapshot" in calls[0]
        assert "3" in calls[0]
        assert "backend.sync.notion_sync" in calls[0]

    def test_run_uses_module_flag(self, client, monkeypatch):
        """Scripts are invoked with 'python -m <module>' to avoid relative-import errors."""
        import subprocess
        calls: list[list[str]] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **_kw: calls.append(a[0]) or type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        calls.clear()
        c.post(
            "/api/run/notion_sync",
            data=json.dumps({"snapshot": 1}),
            content_type="application/json",
        )
        assert "-m" in calls[0], "expected '-m' flag in notion_sync command"
        assert not any(arg.endswith(".py") for arg in calls[0]), (
            "command must not reference a .py file directly"
        )

    def test_run_cwd_is_project_root(self, client, monkeypatch):
        """subprocess.run must be called with cwd set to the project root (not backend/)."""
        import subprocess
        from pathlib import Path
        captured_kwargs: list[dict] = []
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *_a, **kw: captured_kwargs.append(kw) or type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        c.post(
            "/api/run/notion_sync",
            data=json.dumps({"snapshot": 1}),
            content_type="application/json",
        )
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

    def test_run_notion_sync_missing_snapshot_returns_200_when_empty(self, client, monkeypatch):
        """Calling notion_sync without snapshot returns 200 when DB is empty (first-time sync)."""
        import subprocess

        
        # Clear all snapshots to simulate first-time sync
        c, conn = client
        conn.execute("DELETE FROM snapshot_players")
        conn.execute("DELETE FROM snapshots")
        conn.commit()
        
        monkeypatch.setattr(
            subprocess, "run",
            lambda *_a, **_kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post("/api/run/notion_sync", content_type="application/json")
        assert resp.status_code == 200

    def test_run_notion_sync_first_time_no_snapshot_allowed(self, client, monkeypatch):
        """First-time sync (empty DB) is allowed without snapshot ID."""
        import subprocess

        
        # Clear all snapshots to simulate first-time sync
        c, conn = client
        conn.execute("DELETE FROM snapshot_players")
        conn.execute("DELETE FROM snapshots")
        conn.commit()
        
        monkeypatch.setattr(
            subprocess, "run",
            lambda *_a, **_kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post("/api/run/notion_sync", content_type="application/json")
        assert resp.status_code == 200
