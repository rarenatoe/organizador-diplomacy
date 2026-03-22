"""
Tests de unidad para db.py y db_views.py

Cubre los helpers de la capa de persistencia SQLite (in-memory):
  get_or_create_player, create_snapshot, add_snapshot_player,
  get_snapshot_players, get_latest_snapshot_id,
  snapshots_have_same_roster, create_sync_event,
  build_chain_data (db_views)
"""
import unittest

import db
import db_views


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_conn() -> "db.sqlite3.Connection":
    """Returns an in-memory DB with the full schema."""
    return db.get_db(":memory:")


class TestDb(unittest.TestCase):

    def setUp(self) -> None:
        self.conn = _make_conn()

    def tearDown(self) -> None:
        self.conn.close()

    # ── get_latest_snapshot_id ────────────────────────────────────────────────

    def test_latest_snapshot_none_when_empty(self):
        """Returns None when the DB has no snapshots."""
        self.assertIsNone(db.get_latest_snapshot_id(self.conn))

    def test_latest_snapshot_returns_highest_id(self):
        """Returns the id of the most recently created snapshot."""
        id1 = db.create_snapshot(self.conn, "notion_sync")
        id2 = db.create_snapshot(self.conn, "organizar")
        self.conn.commit()
        self.assertEqual(db.get_latest_snapshot_id(self.conn), id2)
        self.assertGreater(id2, id1)

    # ── get_or_create_player ──────────────────────────────────────────────────

    def test_player_created_once(self):
        """Calling get_or_create_player twice returns the same id."""
        pid1 = db.get_or_create_player(self.conn, "Alice")
        pid2 = db.get_or_create_player(self.conn, "Alice")
        self.conn.commit()
        self.assertEqual(pid1, pid2)

    def test_different_players_have_different_ids(self):
        pid1 = db.get_or_create_player(self.conn, "Alice")
        pid2 = db.get_or_create_player(self.conn, "Bob")
        self.conn.commit()
        self.assertNotEqual(pid1, pid2)

    # ── create_snapshot / add_snapshot_player / get_snapshot_players ─────────

    def test_snapshot_players_roundtrip(self):
        """Players inserted via add_snapshot_player are returned by get_snapshot_players."""
        snap_id = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap_id, pid, "Antiguo", 3, 0, 2, 0)
        self.conn.commit()
        players = db.get_snapshot_players(self.conn, snap_id)
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["nombre"], "Alice")
        self.assertEqual(players[0]["experiencia"], "Antiguo")
        self.assertEqual(players[0]["juegos_este_ano"], 3)
        self.assertEqual(players[0]["partidas_deseadas"], 2)

    def test_empty_snapshot_returns_empty_list(self):
        snap_id = db.create_snapshot(self.conn, "organizar")
        self.conn.commit()
        self.assertEqual(db.get_snapshot_players(self.conn, snap_id), [])

    def test_get_snapshot_players_unknown_id_returns_empty(self):
        self.assertEqual(db.get_snapshot_players(self.conn, 9999), [])

    # ── snapshots_have_same_roster ────────────────────────────────────────────

    def test_same_roster_returns_true(self):
        """snapshots_have_same_roster returns True when Notion data matches the snapshot."""
        snap_id = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap_id, pid, "Antiguo", 2, 0, 1, 0)
        self.conn.commit()
        notion_rows = [{"Nombre": "Alice", "Experiencia": "Antiguo", "Juegos_Este_Ano": 2}]
        self.assertTrue(db.snapshots_have_same_roster(self.conn, snap_id, notion_rows))

    def test_different_juegos_returns_false(self):
        snap_id = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap_id, pid, "Antiguo", 2, 0, 1, 0)
        self.conn.commit()
        notion_rows = [{"Nombre": "Alice", "Experiencia": "Antiguo", "Juegos_Este_Ano": 5}]
        self.assertFalse(db.snapshots_have_same_roster(self.conn, snap_id, notion_rows))

    def test_added_player_returns_false(self):
        snap_id = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap_id, pid, "Antiguo", 2, 0, 1, 0)
        self.conn.commit()
        notion_rows = [
            {"Nombre": "Alice", "Experiencia": "Antiguo", "Juegos_Este_Ano": 2},
            {"Nombre": "Bob",   "Experiencia": "Nuevo",   "Juegos_Este_Ano": 0},
        ]
        self.assertFalse(db.snapshots_have_same_roster(self.conn, snap_id, notion_rows))

    # ── create_sync_event ─────────────────────────────────────────────────────

    def test_sync_event_created(self):
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "notion_sync")
        eid = db.create_sync_event(self.conn, snap1, snap2)
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM sync_events WHERE id=?", (eid,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["source_snapshot"], snap1)
        self.assertEqual(row["output_snapshot"], snap2)

    def test_sync_event_null_source(self):
        """First-ever sync has no source snapshot (leido=null)."""
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        eid = db.create_sync_event(self.conn, None, snap1)
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM sync_events WHERE id=?", (eid,)).fetchone()
        self.assertIsNone(row["source_snapshot"])

    # ── build_chain_data (db_views) ───────────────────────────────────────────

    def test_build_chain_empty_db(self):
        """Empty DB returns roots=[]."""
        data = db_views.build_chain_data(self.conn)
        self.assertEqual(data["roots"], [])

    def test_build_chain_single_root(self):
        snap_id = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap_id, pid, "Antiguo", 0, 0, 1, 0)
        self.conn.commit()
        data = db_views.build_chain_data(self.conn)
        self.assertEqual(len(data["roots"]), 1)
        root = data["roots"][0]
        self.assertEqual(root["id"], snap_id)
        self.assertEqual(root["player_count"], 1)
        self.assertEqual(root["branches"], [])

    def test_build_chain_sync_produces_branch(self):
        """Snapshot produced by a sync_event must appear as a branch, not a root."""
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap1, pid, "Antiguo", 0, 0, 1, 0)
        db.add_snapshot_player(self.conn, snap2, pid, "Antiguo", 1, 0, 1, 0)
        db.create_sync_event(self.conn, snap1, snap2)
        self.conn.commit()
        data = db_views.build_chain_data(self.conn)
        # Only snap1 is a root; snap2 is the branch output
        self.assertEqual(len(data["roots"]), 1)
        root = data["roots"][0]
        self.assertEqual(root["id"], snap1)
        self.assertEqual(len(root["branches"]), 1)
        branch = root["branches"][0]
        self.assertEqual(branch["edge"]["type"], "sync")
        self.assertEqual(branch["output"]["id"], snap2)

    def test_build_chain_latest_flag(self):
        """is_latest is True only on the snapshot with the highest id."""
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "notion_sync")
        db.create_sync_event(self.conn, snap1, snap2)
        self.conn.commit()
        data = db_views.build_chain_data(self.conn)
        root = data["roots"][0]
        self.assertFalse(root["is_latest"])
        self.assertTrue(root["branches"][0]["output"]["is_latest"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
