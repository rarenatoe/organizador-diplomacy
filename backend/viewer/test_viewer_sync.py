"""
test_viewer_sync.py — Tests for /api/sync endpoints.

Tests sync detection and confirmation.
"""
from __future__ import annotations

import json

import pytest

# Fixtures are provided by conftest.py


# ── /api/sync/detect ──────────────────────────────────────────────────────────

class TestApiSyncDetect:
    def test_detect_missing_snapshot_returns_400(self, client):
        """Omitting snapshot returns 400 — snapshot_id is required."""
        c, conn = client
        resp = c.post("/api/sync/detect", content_type="application/json")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "Snapshot selection required" in data["error"]

    def test_detect_returns_valid_json(self, client, monkeypatch):
        """POST /api/sync/detect with snapshot returns valid JSON with similar_names."""
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
        resp = c.post(
            "/api/sync/detect",
            data=json.dumps({"snapshot": 1}),
            content_type="application/json",
        )
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
        resp = c.post(
            "/api/sync/detect",
            data=json.dumps({"snapshot": 1}),
            content_type="application/json",
        )
        assert resp.status_code == 500


# ── /api/sync/confirm ─────────────────────────────────────────────────────────

class TestApiSyncConfirm:
    def test_confirm_missing_snapshot_returns_400(self, client):
        """Omitting snapshot returns 400 — snapshot_id is required."""
        c, conn = client
        resp = c.post("/api/sync/confirm", content_type="application/json")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "Snapshot selection required" in data["error"]

    def test_confirm_returns_run_result(self, client, monkeypatch):
        """POST /api/sync/confirm with snapshot returns RunResult with returncode."""
        import subprocess
        c, conn = client
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        )
        resp = c.post(
            "/api/sync/confirm",
            data=json.dumps({"snapshot": 1}),
            content_type="application/json",
        )
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
            data=json.dumps({"snapshot": 1, "merges": merges}),
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