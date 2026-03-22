"""
test_viewer_run.py — Tests for /api/run endpoint.

Tests script execution and validation.
"""
from __future__ import annotations

import json

import pytest

# Fixtures are provided by conftest.py


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
        assert "backend.sync.notion_sync" in calls[0]

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
        assert "backend.organizador.organizador" in calls[0]

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