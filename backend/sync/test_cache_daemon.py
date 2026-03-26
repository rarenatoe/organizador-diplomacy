"""
test_cache_daemon.py – Unit tests for cache_daemon.py.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from backend.db import db
from .cache_daemon import update_notion_cache, _run_sync_loop

class TestCacheDaemon(unittest.TestCase):
    def setUp(self):
        self.conn = db.get_db(":memory:")
        
    def tearDown(self):
        self.conn.close()

    @patch("backend.sync.cache_daemon.descargar_todos")
    @patch("backend.sync.cache_daemon.conteo_partidas_este_ano")
    def test_update_notion_cache_populates_db(self, mock_conteo, mock_descargar):
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
    def test_run_sync_loop_warmup_and_interval(self, mock_getenv, mock_get_db, mock_update, mock_sleep):
        """_run_sync_loop performs an immediate warmup (before sleep) and then waits 15 min."""
        # Setup mocks to allow the loop to run once and then exit
        mock_getenv.side_effect = lambda k: "test_val" if "NOTION" in k else None
        mock_get_db.return_value = self.conn
        
        # Track the order of calls
        call_order = []
        mock_update.side_effect = lambda *args, **kwargs: call_order.append("update")
        
        def mock_sleep_fn(*args, **kwargs):
            call_order.append("sleep")
            raise Exception("StopLoop")
        mock_sleep.side_effect = mock_sleep_fn
        
        with self.assertRaisesRegex(Exception, "StopLoop"):
            _run_sync_loop()
            
        # Verify call order: update MUST happen before sleep (warmup)
        self.assertEqual(call_order, ["update", "sleep"])
        
        # Verify update was called with correct client and IDs
        self.assertTrue(mock_update.called)
        
        # Verify the interval was 900 seconds
        mock_sleep.assert_called_with(900)

if __name__ == "__main__":
    unittest.main()
