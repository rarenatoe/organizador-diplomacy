"""Unit tests for generate_deep_diff function - no database required.

These tests are synchronous and don't require a database session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.crud.snapshots import generate_deep_diff

if TYPE_CHECKING:
    from backend.db.models import RenameDict


class TestGenerateDeepDiff:
    """Unit tests for generate_deep_diff function."""

    def test_renames_prevent_added_removed(self) -> None:
        """Renames should prevent players from appearing in added/removed lists."""
        old_players = [{"nombre": "OldName", "is_new": True, "juegos_este_ano": 0}]
        new_players = [{"nombre": "NewName", "is_new": True, "juegos_este_ano": 0}]
        renames: list[RenameDict] = [{"from": "OldName", "to": "NewName"}]

        result = generate_deep_diff(old_players, new_players, renames)

        # Renamed player should NOT appear in added or removed
        added_items = result.get("added", [])
        removed_items = result.get("removed", [])
        assert "NewName" not in added_items, "Renamed player should not be in added"
        assert "OldName" not in removed_items, "Renamed player should not be in removed"
        # But should appear in renamed list
        assert result["renamed"] == renames

    def test_added_players_only_in_new_list(self) -> None:
        """Players only in new list should be marked as added."""
        old_players = [{"nombre": "Alice", "is_new": True, "juegos_este_ano": 0}]
        new_players = [
            {"nombre": "Alice", "is_new": True, "juegos_este_ano": 0},
            {"nombre": "Bob", "is_new": False, "juegos_este_ano": 5},
        ]

        result = generate_deep_diff(old_players, new_players, [])

        assert result["added"] == ["Bob"]
        assert result["removed"] == []

    def test_removed_players_only_in_old_list(self) -> None:
        """Players only in old list should be marked as removed."""
        old_players = [
            {"nombre": "Alice", "is_new": True, "juegos_este_ano": 0},
            {"nombre": "Charlie", "is_new": False, "juegos_este_ano": 10},
        ]
        new_players = [{"nombre": "Alice", "is_new": True, "juegos_este_ano": 0}]

        result = generate_deep_diff(old_players, new_players, [])

        assert result["added"] == []
        assert result["removed"] == ["Charlie"]

    def test_modified_field_changes(self) -> None:
        """Changes to fields should be detected and reported with old/new values."""
        old_players = [{"nombre": "Pablo", "is_new": True, "juegos_este_ano": 2}]
        new_players = [{"nombre": "Pablo", "is_new": True, "juegos_este_ano": 3}]

        result = generate_deep_diff(old_players, new_players, [])

        assert result["added"] == []
        assert result["removed"] == []
        modified_list = result.get("modified", [])
        assert len(modified_list) == 1

        mod = modified_list[0]
        assert mod["nombre"] == "Pablo"
        assert "juegos_este_ano" in mod["changes"]
        assert mod["changes"]["juegos_este_ano"] == {"old": 2, "new": 3}

    def test_multiple_field_changes(self) -> None:
        """Multiple field changes should all be reported."""
        old_players = [
            {"nombre": "Pablo", "is_new": True, "juegos_este_ano": 2, "has_priority": False}
        ]
        new_players = [
            {
                "nombre": "Pablo",
                "is_new": False,
                "juegos_este_ano": 3,
                "has_priority": True,
            }
        ]

        result = generate_deep_diff(old_players, new_players, [])

        modified_list = result.get("modified", [])
        assert len(modified_list) == 1
        mod = modified_list[0]
        assert mod["nombre"] == "Pablo"
        assert len(mod["changes"]) == 3
        assert mod["changes"]["is_new"] == {"old": True, "new": False}
        assert mod["changes"]["juegos_este_ano"] == {"old": 2, "new": 3}
        assert mod["changes"]["has_priority"] == {"old": False, "new": True}

    def test_no_changes_empty_result(self) -> None:
        """Identical player lists should produce empty changes."""
        players = [
            {"nombre": "Alice", "is_new": True, "juegos_este_ano": 0},
            {"nombre": "Bob", "is_new": False, "juegos_este_ano": 5},
        ]

        result = generate_deep_diff(players, players, [])

        assert result["added"] == []
        assert result["removed"] == []
        assert result["modified"] == []
        assert result["renamed"] == []

    def test_nombre_field_ignored_in_changes(self) -> None:
        """The 'nombre' field should be ignored when detecting modifications."""
        old_players = [{"nombre": "Pablo", "is_new": True}]
        # Same player data, name should not trigger modification
        new_players = [{"nombre": "Pablo", "is_new": True}]

        result = generate_deep_diff(old_players, new_players, [])

        # No modifications since only nombre was compared (and skipped)
        assert result["modified"] == []

    def test_complex_scenario_all_categories(self) -> None:
        """Test a complex scenario with added, removed, renamed, and modified players."""
        old_players = [
            {"nombre": "Alice", "is_new": True, "juegos_este_ano": 0},
            {"nombre": "Bob", "is_new": False, "juegos_este_ano": 5},
            {"nombre": "OldCharlie", "is_new": True, "juegos_este_ano": 1},
        ]
        new_players = [
            {"nombre": "Alice", "is_new": True, "juegos_este_ano": 1},  # Modified
            {"nombre": "Bob", "is_new": False, "juegos_este_ano": 5},  # Unchanged
            {"nombre": "NewCharlie", "is_new": True, "juegos_este_ano": 1},  # Renamed
            {"nombre": "David", "is_new": False, "juegos_este_ano": 10},  # Added
        ]
        renames: list[RenameDict] = [{"from": "OldCharlie", "to": "NewCharlie"}]

        result = generate_deep_diff(old_players, new_players, renames)

        # Check added
        assert result["added"] == ["David"]

        # Check removed - no one was removed (Bob is unchanged, Charlie was renamed)
        assert result["removed"] == []

        # Check renamed
        assert result["renamed"] == renames

        # Check modified - Alice had juegos_este_ano change from 0 to 1
        modified_list = result.get("modified", [])
        assert len(modified_list) == 1
        assert modified_list[0]["nombre"] == "Alice"
        assert modified_list[0]["changes"]["juegos_este_ano"] == {"old": 0, "new": 1}
