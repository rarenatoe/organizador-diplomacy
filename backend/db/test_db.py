"""
Tests de unidad para db.py, db_game.py y db_views.py

Cubre los helpers de la capa de persistencia SQLite (in-memory):
  get_or_create_player, create_snapshot, add_snapshot_player,
  get_snapshot_players, get_latest_snapshot_id,
  snapshots_have_same_roster, create_sync_event,
  create_manual_snapshot, delete_snapshot_cascade,
  create_game_event, create_mesa, add_mesa_player (db_game),
  build_chain_data (db_views)
"""
import unittest

from . import db, db_game, db_views

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
        row = self.conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["source_snapshot_id"], snap1)
        self.assertEqual(row["output_snapshot_id"], snap2)
        self.assertEqual(row["type"], "sync")

    def test_sync_event_null_source(self):
        """First-ever sync has no source snapshot (leido=null)."""
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        eid = db.create_sync_event(self.conn, None, snap1)
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
        self.assertIsNone(row["source_snapshot_id"])

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

    # ── delete_snapshot_cascade ─────────────────────────────────────────────

    def test_delete_standalone_snapshot(self):
        """Deleting a snapshot with no events removes it and its players."""
        snap_id = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap_id, pid, "Antiguo", 0, 0, 1, 0)
        self.conn.commit()
        deleted = db.delete_snapshot_cascade(self.conn, snap_id)
        self.conn.commit()
        self.assertIn(snap_id, deleted)
        self.assertIsNone(db.get_latest_snapshot_id(self.conn))
        self.assertEqual(db.get_snapshot_players(self.conn, snap_id), [])

    def test_delete_cascades_producing_sync_event(self):
        """Deleting the output snapshot of a sync_event also removes the event."""
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "notion_sync")
        eid = db.create_sync_event(self.conn, snap1, snap2)
        self.conn.commit()
        db.delete_snapshot_cascade(self.conn, snap2)
        self.conn.commit()
        self.assertIsNone(self.conn.execute(
            "SELECT id FROM events WHERE id=?", (eid,)
        ).fetchone())
        self.assertIsNone(self.conn.execute(
            "SELECT id FROM snapshots WHERE id=?", (snap2,)
        ).fetchone())
        # Source snapshot must survive
        self.assertIsNotNone(self.conn.execute(
            "SELECT id FROM snapshots WHERE id=?", (snap1,)
        ).fetchone())

    def test_delete_cascades_downstream_chain(self):
        """Deleting snap2 also removes snap3 that was synced from snap2."""
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "notion_sync")
        snap3 = db.create_snapshot(self.conn, "notion_sync")
        db.create_sync_event(self.conn, snap1, snap2)
        db.create_sync_event(self.conn, snap2, snap3)
        self.conn.commit()
        deleted = db.delete_snapshot_cascade(self.conn, snap2)
        self.conn.commit()
        self.assertIn(snap2, deleted)
        self.assertIn(snap3, deleted)
        self.assertNotIn(snap1, deleted)
        self.assertIsNotNone(self.conn.execute(
            "SELECT id FROM snapshots WHERE id=?", (snap1,)
        ).fetchone())
        self.assertIsNone(self.conn.execute(
            "SELECT id FROM snapshots WHERE id=?", (snap3,)
        ).fetchone())

    def test_delete_cascades_game_event_and_mesas(self):
        """Deleting the output snapshot of a game_event also removes its mesas."""
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "organizar")
        pid = db.get_or_create_player(self.conn, "Alice")
        ge_id = db_game.create_game_event(self.conn, snap1, snap2, 1, "copypaste")
        mesa_id = db_game.create_mesa(self.conn, ge_id, 1, None)
        db_game.add_mesa_player(self.conn, mesa_id, pid, 1)
        self.conn.commit()
        db.delete_snapshot_cascade(self.conn, snap2)
        self.conn.commit()
        self.assertIsNone(self.conn.execute(
            "SELECT id FROM events WHERE id=?", (ge_id,)
        ).fetchone())
        self.assertIsNone(self.conn.execute(
            "SELECT id FROM mesas WHERE id=?", (mesa_id,)
        ).fetchone())

    # ── create_manual_snapshot ───────────────────────────────────────────

    def test_manual_snapshot_keeps_only_listed_players(self):
        """Players not in edits list are excluded from the new snapshot."""
        snap = db.create_snapshot(self.conn, "notion_sync")
        for name in ("Alice", "Bob", "Carol"):
            pid = db.get_or_create_player(self.conn, name)
            db.add_snapshot_player(self.conn, snap, pid, "Antiguo", 1, 0, 2, 0)
        self.conn.commit()
        edits = [
            {"nombre": "Alice", "prioridad": 1, "partidas_deseadas": 2, "partidas_gm": 0},
            {"nombre": "Bob",   "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 1},
        ]
        new_id = db.create_manual_snapshot(self.conn, snap, edits)
        self.conn.commit()
        players = {p["nombre"]: p for p in db.get_snapshot_players(self.conn, new_id)}
        self.assertIn("Alice", players)
        self.assertIn("Bob", players)
        self.assertNotIn("Carol", players)

    def test_manual_snapshot_applies_field_edits(self):
        """prioridad, partidas_deseadas and partidas_gm are updated in the new snapshot."""
        snap = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap, pid, "Antiguo", 3, 0, 1, 0)
        self.conn.commit()
        edits = [{"nombre": "Alice", "prioridad": 1, "partidas_deseadas": 3, "partidas_gm": 1}]
        new_id = db.create_manual_snapshot(self.conn, snap, edits)
        self.conn.commit()
        players = {p["nombre"]: p for p in db.get_snapshot_players(self.conn, new_id)}
        alice = players["Alice"]
        self.assertEqual(alice["prioridad"], 1)
        self.assertEqual(alice["partidas_deseadas"], 3)
        self.assertEqual(alice["partidas_gm"], 1)
        # Immutable fields must be preserved from source
        self.assertEqual(alice["experiencia"], "Antiguo")
        self.assertEqual(alice["juegos_este_ano"], 3)

    def test_manual_snapshot_source_is_manual(self):
        """The new snapshot's source must be 'manual'."""
        snap = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap, pid, "Antiguo", 0, 0, 1, 0)
        self.conn.commit()
        edits = [{"nombre": "Alice", "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 0}]
        new_id = db.create_manual_snapshot(self.conn, snap, edits)
        self.conn.commit()
        row = self.conn.execute(
            "SELECT source FROM snapshots WHERE id=?", (new_id,)
        ).fetchone()
        self.assertEqual(row["source"], "manual")

    def test_manual_snapshot_ignores_unknown_players(self):
        """Edits for players not in the source are silently skipped."""
        snap = db.create_snapshot(self.conn, "notion_sync")
        pid = db.get_or_create_player(self.conn, "Alice")
        db.add_snapshot_player(self.conn, snap, pid, "Antiguo", 0, 0, 1, 0)
        self.conn.commit()
        edits = [
            {"nombre": "Alice",  "prioridad": 0, "partidas_deseadas": 1, "partidas_gm": 0},
            {"nombre": "Ghost",  "prioridad": 1, "partidas_deseadas": 2, "partidas_gm": 0},
        ]
        new_id = db.create_manual_snapshot(self.conn, snap, edits)
        self.conn.commit()
        players = {p["nombre"] for p in db.get_snapshot_players(self.conn, new_id)}
        self.assertIn("Alice", players)
        self.assertNotIn("Ghost", players)

    # ── rename_player ─────────────────────────────────────────────────────

    def test_rename_player_simple(self):
        """Renaming a player when new_name doesn't exist works."""
        pid = db.get_or_create_player(self.conn, "Alice")
        self.conn.commit()
        result = db.rename_player(self.conn, "Alice", "Alicia")
        self.conn.commit()
        self.assertTrue(result)
        # Verify name was changed
        row = self.conn.execute("SELECT nombre FROM players WHERE id=?", (pid,)).fetchone()
        self.assertEqual(row["nombre"], "Alicia")

    def test_rename_player_old_name_not_exists(self):
        """Renaming a player that doesn't exist returns False."""
        result = db.rename_player(self.conn, "NonExistent", "NewName")
        self.assertFalse(result)

    def test_rename_player_new_name_in_same_snapshot_fails(self):
        """Renaming fails if new_name is already in the same snapshot."""
        snap = db.create_snapshot(self.conn, "notion_sync")
        pid1 = db.get_or_create_player(self.conn, "Alice")
        pid2 = db.get_or_create_player(self.conn, "Bob")
        db.add_snapshot_player(self.conn, snap, pid1, "Antiguo", 0, 0, 1, 0)
        db.add_snapshot_player(self.conn, snap, pid2, "Antiguo", 0, 0, 1, 0)
        self.conn.commit()
        # Try to rename Alice to Bob (which is already in the same snapshot)
        result = db.rename_player(self.conn, "Alice", "Bob")
        self.conn.commit()
        self.assertFalse(result)
        # Verify Alice's name didn't change
        row = self.conn.execute("SELECT nombre FROM players WHERE id=?", (pid1,)).fetchone()
        self.assertEqual(row["nombre"], "Alice")

    def test_rename_player_new_name_in_different_snapshot_succeeds(self):
        """Renaming succeeds if new_name exists but not in the same snapshot."""
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "notion_sync")
        pid1 = db.get_or_create_player(self.conn, "Alice")
        pid2 = db.get_or_create_player(self.conn, "Bob")
        # Alice in snap1, Bob in snap2
        db.add_snapshot_player(self.conn, snap1, pid1, "Antiguo", 0, 0, 1, 0)
        db.add_snapshot_player(self.conn, snap2, pid2, "Antiguo", 0, 0, 1, 0)
        self.conn.commit()
        # Rename Alice to Bob (Bob exists but not in snap1)
        result = db.rename_player(self.conn, "Alice", "Bob")
        self.conn.commit()
        self.assertTrue(result)
        # Verify snap1 now has Bob (linked to pid2)
        players = db.get_snapshot_players(self.conn, snap1)
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["nombre"], "Bob")
        # Verify Alice's player record was deleted (orphaned)
        alice_row = self.conn.execute("SELECT id FROM players WHERE id=?", (pid1,)).fetchone()
        self.assertIsNone(alice_row)

    def test_rename_player_links_snapshot_players(self):
        """When new_name exists, snapshot_players are linked to the existing player."""
        snap = db.create_snapshot(self.conn, "notion_sync")
        pid1 = db.get_or_create_player(self.conn, "Alice")
        pid2 = db.get_or_create_player(self.conn, "Bob")
        # Only Alice in snap
        db.add_snapshot_player(self.conn, snap, pid1, "Antiguo", 5, 1, 2, 1)
        self.conn.commit()
        # Rename Alice to Bob (Bob exists but not in snap)
        result = db.rename_player(self.conn, "Alice", "Bob")
        self.conn.commit()
        self.assertTrue(result)
        # Verify snap now has Bob with pid2
        players = db.get_snapshot_players(self.conn, snap)
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["nombre"], "Bob")
        # Verify the snapshot_player is linked to pid2
        sp_row = self.conn.execute(
            "SELECT player_id FROM snapshot_players WHERE snapshot_id=?", (snap,)
        ).fetchone()
        self.assertEqual(sp_row["player_id"], pid2)
        # Verify Alice's data was preserved
        self.assertEqual(players[0]["experiencia"], "Antiguo")
        self.assertEqual(players[0]["juegos_este_ano"], 5)

    def test_rename_player_with_gm_role_succeeds(self):
        """Renaming a player who is a game GM transfers the GM record to new player."""
        from backend.db import db_game
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "organizar")
        pid1 = db.get_or_create_player(self.conn, "Alice")
        pid2 = db.get_or_create_player(self.conn, "Bob")
        db.add_snapshot_player(self.conn, snap1, pid1, "Antiguo", 0, 0, 1, 0)
        event_id = db_game.create_game_event(self.conn, snap1, snap2, 1, "")
        mesa_id = db_game.create_mesa(self.conn, event_id, 1, pid1)  # Alice is GM
        self.conn.commit()

        result = db.rename_player(self.conn, "Alice", "Bob")
        self.conn.commit()

        self.assertTrue(result)
        # GM reference moved to Bob (pid2)
        gm_row = self.conn.execute(
            "SELECT gm_player_id FROM mesas WHERE id = ?", (mesa_id,)
        ).fetchone()
        self.assertEqual(gm_row["gm_player_id"], pid2)
        # Alice's player record was deleted (fully orphaned)
        alice_row = self.conn.execute(
            "SELECT id FROM players WHERE id = ?", (pid1,)
        ).fetchone()
        self.assertIsNone(alice_row)

    def test_rename_player_with_mesa_player_record_succeeds(self):
        """Renaming a player who appeared in a game table transfers the mesa record."""
        from backend.db import db_game
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "organizar")
        pid1 = db.get_or_create_player(self.conn, "Alice")
        pid2 = db.get_or_create_player(self.conn, "Bob")
        db.add_snapshot_player(self.conn, snap1, pid1, "Antiguo", 0, 0, 1, 0)
        event_id = db_game.create_game_event(self.conn, snap1, snap2, 1, "")
        mesa_id = db_game.create_mesa(self.conn, event_id, 1, None)
        db_game.add_mesa_player(self.conn, mesa_id, pid1, 1)  # Alice played in this mesa
        self.conn.commit()

        result = db.rename_player(self.conn, "Alice", "Bob")
        self.conn.commit()

        self.assertTrue(result)
        # Mesa player record now points to Bob (pid2)
        mp_row = self.conn.execute(
            "SELECT player_id FROM mesa_players WHERE mesa_id = ?", (mesa_id,)
        ).fetchone()
        self.assertEqual(mp_row["player_id"], pid2)
        # Alice's player record was deleted
        alice_row = self.conn.execute(
            "SELECT id FROM players WHERE id = ?", (pid1,)
        ).fetchone()
        self.assertIsNone(alice_row)

    def test_rename_player_with_waiting_list_record_succeeds(self):
        """Renaming a player on the waiting list transfers the waiting list record."""
        from backend.db import db_game
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "organizar")
        pid1 = db.get_or_create_player(self.conn, "Alice")
        pid2 = db.get_or_create_player(self.conn, "Bob")
        db.add_snapshot_player(self.conn, snap1, pid1, "Antiguo", 0, 0, 1, 0)
        event_id = db_game.create_game_event(self.conn, snap1, snap2, 1, "")
        db_game.add_waiting_player(self.conn, event_id, pid1, 1, 1)  # Alice on waiting list
        self.conn.commit()

        result = db.rename_player(self.conn, "Alice", "Bob")
        self.conn.commit()

        self.assertTrue(result)
        # Waiting list record now points to Bob (pid2)
        wl_row = self.conn.execute(
            "SELECT player_id FROM waiting_list WHERE event_id = ?", (event_id,)
        ).fetchone()
        self.assertEqual(wl_row["player_id"], pid2)
        # Alice's player record was deleted
        alice_row = self.conn.execute(
            "SELECT id FROM players WHERE id = ?", (pid1,)
        ).fetchone()
        self.assertIsNone(alice_row)

    def test_rename_player_not_orphaned_when_still_in_game(self):
        """If old player is still referenced in games after rename, they are NOT deleted."""
        from backend.db import db_game
        # Alice is in snap1 AND in a game mesa; Bob is in snap2 only.
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "notion_sync")
        snap3 = db.create_snapshot(self.conn, "organizar")
        pid1 = db.get_or_create_player(self.conn, "Alice")
        pid2 = db.get_or_create_player(self.conn, "Bob")
        # Alice in snap1 only, Bob in snap2 only
        db.add_snapshot_player(self.conn, snap1, pid1, "Antiguo", 0, 0, 1, 0)
        db.add_snapshot_player(self.conn, snap2, pid2, "Antiguo", 0, 0, 1, 0)
        # Alice also appears as GM in a game event (from snap1 → snap3)
        event_id = db_game.create_game_event(self.conn, snap1, snap3, 1, "")
        mesa_id = db_game.create_mesa(self.conn, event_id, 1, pid1)
        self.conn.commit()

        # Rename Alice → Bob; Bob is in snap2, Alice is in snap1 (different snaps → allowed)
        result = db.rename_player(self.conn, "Alice", "Bob")
        self.conn.commit()

        self.assertTrue(result)
        # After rename, snap1's player is now Bob
        players = db.get_snapshot_players(self.conn, snap1)
        self.assertEqual(players[0]["nombre"], "Bob")
        # The mesa GM is now Bob (pid2)
        gm_row = self.conn.execute(
            "SELECT gm_player_id FROM mesas WHERE id = ?", (mesa_id,)
        ).fetchone()
        self.assertEqual(gm_row["gm_player_id"], pid2)


    # ── Schema validation tests (seat belt for future issues) ─────────────


    def test_foreign_key_constraints_point_to_events(self):
        """
        Verify that mesas and waiting_list tables have correct
        foreign key constraints pointing to events(id).
        """
        # Check mesas table foreign keys
        mesas_fks = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='mesas'"
        ).fetchone()
        mesas_sql = mesas_fks[0] if mesas_fks else ""
        self.assertIn("REFERENCES events(id)", mesas_sql,
            "mesas table must have foreign key pointing to events(id)")

        # Check waiting_list table foreign keys
        wl_fks = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='waiting_list'"
        ).fetchone()
        wl_sql = wl_fks[0] if wl_fks else ""
        self.assertIn("REFERENCES events(id)", wl_sql,
            "waiting_list table must have foreign key pointing to events(id)")

    def test_unified_events_table_exists(self):
        """
        Verify that the unified events table exists with correct schema.
        """
        events_table = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='events'"
        ).fetchone()
        self.assertIsNotNone(events_table, "events table must exist")
        events_sql = events_table[0]
        self.assertIn("type", events_sql, "events table must have type column")
        self.assertIn("'sync'", events_sql, "events table must allow 'sync' type")
        self.assertIn("'game'", events_sql, "events table must allow 'game' type")
        self.assertIn("'edit'", events_sql, "events table must allow 'edit' type")
        self.assertIn("source_snapshot_id", events_sql, "events table must have source_snapshot_id")
        self.assertIn("output_snapshot_id", events_sql, "events table must have output_snapshot_id")
        self.assertIn("ON DELETE CASCADE", events_sql, "events table must have ON DELETE CASCADE")

    def test_game_details_table_exists(self):
        """
        Verify that game_details table exists with correct schema.
        """
        gd_table = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='game_details'"
        ).fetchone()
        self.assertIsNotNone(gd_table, "game_details table must exist")
        gd_sql = gd_table[0]
        self.assertIn("event_id", gd_sql, "game_details must have event_id column")
        self.assertIn("intentos", gd_sql, "game_details must have intentos column")
        self.assertIn("copypaste_text", gd_sql, "game_details must have copypaste_text column")
        self.assertIn("REFERENCES events(id)", gd_sql,
            "game_details must have foreign key pointing to events(id)")

    def test_game_event_creates_both_event_and_details(self):
        """
        Seat belt: Verify that creating a game event creates both
        an entry in events table AND game_details table.
        This ensures the unified schema works correctly.
        """
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "organizar")
        ge_id = db_game.create_game_event(self.conn, snap1, snap2, 5, "test copypaste")
        self.conn.commit()

        # Check events table
        event_row = self.conn.execute(
            "SELECT * FROM events WHERE id=?", (ge_id,)
        ).fetchone()
        self.assertIsNotNone(event_row, "Event must exist in events table")
        self.assertEqual(event_row["type"], "game")
        self.assertEqual(event_row["source_snapshot_id"], snap1)
        self.assertEqual(event_row["output_snapshot_id"], snap2)

        # Check game_details table
        details_row = self.conn.execute(
            "SELECT * FROM game_details WHERE event_id=?", (ge_id,)
        ).fetchone()
        self.assertIsNotNone(details_row, "Game details must exist in game_details table")
        self.assertEqual(details_row["intentos"], 5)
        self.assertEqual(details_row["copypaste_text"], "test copypaste")

    def test_mesa_insertion_with_valid_event_id(self):
        """
        Seat belt: Verify that inserting a mesa with a valid event_id works.
        This ensures the foreign key constraint is correctly configured.
        """
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "organizar")
        ge_id = db_game.create_game_event(self.conn, snap1, snap2, 1, "test")
        self.conn.commit()

        # This should NOT raise a FOREIGN KEY constraint error
        try:
            mesa_id = db_game.create_mesa(self.conn, ge_id, 1, None)
            self.conn.commit()
            self.assertIsNotNone(mesa_id, "Mesa should be created successfully")
        except Exception as e:
            self.fail(f"Mesa creation should not raise exception: {e}")

    def test_waiting_list_insertion_with_valid_event_id(self):
        """
        Seat belt: Verify that inserting into waiting_list with a valid event_id works.
        This ensures the foreign key constraint is correctly configured.
        """
        snap1 = db.create_snapshot(self.conn, "notion_sync")
        snap2 = db.create_snapshot(self.conn, "organizar")
        pid = db.get_or_create_player(self.conn, "Alice")
        ge_id = db_game.create_game_event(self.conn, snap1, snap2, 1, "test")
        self.conn.commit()

        # This should NOT raise a FOREIGN KEY constraint error
        try:
            db_game.add_waiting_player(self.conn, ge_id, pid, 1, 2)
            self.conn.commit()
        except Exception as e:
            self.fail(f"Waiting list insertion should not raise exception: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
