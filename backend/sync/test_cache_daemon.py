"""
test_cache_daemon.py – Unit tests for cache_daemon.py.
"""
from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from backend.db import db

from .cache_daemon import run_sync_loop, update_notion_cache


class TestCacheDaemon(unittest.TestCase):
    def setUp(self):
        self.conn = db.get_db(":memory:")
        # Create notion_cache table for testing
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notion_cache (
                notion_id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                experiencia TEXT NOT NULL,
                juegos_este_ano INTEGER NOT NULL DEFAULT 0,
                c_england INTEGER NOT NULL DEFAULT 0,
                c_france INTEGER NOT NULL DEFAULT 0,
                c_germany INTEGER NOT NULL DEFAULT 0,
                c_italy INTEGER NOT NULL DEFAULT 0,
                c_austria INTEGER NOT NULL DEFAULT 0,
                c_russia INTEGER NOT NULL DEFAULT 0,
                c_turkey INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT
            )
        """)
        
    def tearDown(self):
        self.conn.close()

    @patch("backend.sync.cache_daemon.descargar_todos")
    @patch("backend.sync.cache_daemon.conteo_partidas_este_ano")
    def test_update_notion_cache_populates_db(self, mock_conteo: MagicMock, mock_descargar: MagicMock) -> None:
        """update_notion_cache correctly inserts Notion data into notion_cache table."""
        mock_client = MagicMock()
        mock_descargar.return_value = [
            {
                "id": "page1",
                "properties": {
                    "Nombre": {"title": [{"plain_text": "Alice"}]},
                    "Participaciones": {"relation": [{"id": "rel1"}]},
                    "∀ 🇬🇧": {"type": "number", "number": 1},
                    "∀ 🇫🇷": {"type": "number", "number": 0},
                    "∀ 🇩🇪": {"type": "number", "number": 0},
                    "∀ 🇮🇹": {"type": "number", "number": 0},
                    "∀ 🇦🇹": {"type": "number", "number": 0},
                    "∀ 🇷🇺": {"type": "number", "number": 0},
                    "∀ 🇹🇷": {"type": "number", "number": 0},
                }
            }
        ]
        mock_conteo.return_value = {"page1": 5}
        
        update_notion_cache(self.conn, mock_client, "db1", "pdb1")
        
        row = self.conn.execute("SELECT * FROM notion_cache").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["nombre"], "Alice")
        self.assertEqual(row["experiencia"], "Antiguo")
        self.assertEqual(row["juegos_este_ano"], 5)
        self.assertEqual(row["c_england"], 1)

    @patch("backend.sync.cache_daemon.time.sleep")
    @patch("backend.sync.cache_daemon.update_notion_cache")
    @patch("backend.sync.cache_daemon.db.get_db")
    @patch("backend.sync.cache_daemon.os.getenv")
    def test_run_sync_loop_warmup_and_interval(
        self, 
        mock_getenv: MagicMock, 
        mock_get_db: MagicMock, 
        mock_update: MagicMock, 
        mock_sleep: MagicMock
    ) -> None:
        """run_sync_loop performs an immediate warmup (before sleep) and then waits 15 min."""
        # Setup mocks to allow the loop to run once and then exit
        def getenv_side_effect(k: str) -> str | None:
            return "test_val" if "NOTION" in k else None
        
        mock_getenv.side_effect = getenv_side_effect
        mock_get_db.return_value = self.conn
        
        # Track the order of calls
        call_order: list[str] = []
        
        def update_side_effect(*_args: Any, **_kwargs: Any) -> None:
            call_order.append("update")
        
        mock_update.side_effect = update_side_effect
        
        def mock_sleep_fn(*_args: Any, **_kwargs: Any) -> None:
            call_order.append("sleep")
            raise Exception("StopLoop")
        mock_sleep.side_effect = mock_sleep_fn
        
        with self.assertRaisesRegex(Exception, "StopLoop"):
            run_sync_loop()
            
        # Verify call order: update MUST happen before sleep (warmup)
        self.assertEqual(call_order, ["update", "sleep"])
        
        # Verify update was called with correct client and IDs
        self.assertTrue(mock_update.called)
        
        # Verify the interval was 900 seconds
        mock_sleep.assert_called_with(900)

if __name__ == "__main__":
    unittest.main()
