"""
test_viewer.py — Tests for viewer.py (Flask backend).

This file imports tests from split files for better organization.
Tests are split by API endpoint functionality:
- test_viewer_chain.py: /api/chain
- test_viewer_snapshot.py: /api/snapshot, /api/snapshots, DELETE /api/snapshot, /api/snapshot/save, /api/notion/fetch
- test_viewer_run.py: /api/run
- test_viewer_player.py: /api/player/rename, /api/snapshot/<id>/add-player
"""
from __future__ import annotations

# Import all tests from split files so pytest can discover them
from .test_viewer_chain import TestApiChain
from .test_viewer_snapshot import (
    TestApiSnapshot,
    TestApiSnapshots,
    TestApiDeleteSnapshot,
    TestApiCreateSnapshot,
    TestApiSnapshotSave,
    TestApiNotionFetch,
)
from .test_viewer_run import TestApiRun
from .test_viewer_player import TestApiPlayerRename, TestApiAddPlayer
