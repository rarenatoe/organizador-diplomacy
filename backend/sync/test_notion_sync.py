"""
test_notion_sync.py — Unit tests for notion_sync.py.

Covers:
  - Name normalization
  - Filtering to snapshot players
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.sync.client import COUNTRY_PROPS, NotionPage, NotionProperty, extract_number
from backend.sync.core import (
    FIELD_DEFAULTS,
    NotionPlayerDict,
    build_notion_players_lookup,
    find_notion_player,
)
from backend.sync.matching import PlayerNameData, detect_similar_names, normalize_name, similarity

if TYPE_CHECKING:
    from typing import Any

# ── Name normalization ────────────────────────────────────────────────────────


class TestNormalizeName:
    def test_lowercases(self):
        assert normalize_name("John Doe") == "john doe"

    def test_strips_whitespace(self):
        assert normalize_name("  John Doe  ") == "john doe"

    def test_collapses_multiple_spaces(self):
        assert normalize_name("John   Doe") == "john doe"
        assert normalize_name("  John   \t  Doe  \n  ") == "john doe"

    def test_empty_string(self):
        assert normalize_name("") == ""

    def test_single_word(self):
        assert normalize_name("John") == "john"


# ── Similarity calculation ────────────────────────────────────────────────────


class TestSimilarity:
    def test_identical_strings(self):
        assert similarity("John Doe", "John Doe") == 1.0

    def test_case_insensitive(self):
        assert similarity("John Doe", "john doe") == 1.0

    def test_similar_names(self):
        # "Ren Alegre" vs "Renato Alegre" - first name is prefix (0.8)
        # score = (0.8 + 1.0) / 2 = 0.9
        sim = similarity("Ren Alegre", "Renato Alegre")
        assert sim == 0.9

    def test_different_names(self):
        sim = similarity("John Doe", "Jane Smith")
        assert sim < 0.75

    def test_jean_carlos_similarity(self):
        # "Jean Carlos" (2 words) vs "Jean Carlos R." (3 words)
        # Exact match for 2 words, difference is 1 word -> Boosted to 0.8
        sim = similarity("Jean Carlos", "Jean Carlos R.")
        assert sim == 0.8

    def test_word_count_difference_prefix_match(self):
        # "Jean" vs "Jean Carlos R." -> difference is 2 words, no boost
        # 1 match / 3 total words = 0.33
        sim = similarity("Jean", "Jean Carlos R.")
        assert 0.3 < sim < 0.4

    def test_same_first_name_different_last_name(self):
        # "John Smith" vs "John Doe" - mismatch in second word
        # "John" matches "John" (1.0), "Smith" vs "Doe" (low similarity)
        # score = (1.0 + low) / 2
        sim = similarity("John Smith", "John Doe")
        assert sim < 0.75

    def test_abbreviated_first_name_matches(self):
        # "P. Knight" vs "Paul Knight" - abbreviated first name matches (0.8)
        # score = (0.8 + 1.0) / 2 = 0.9
        sim = similarity("P. Knight", "Paul Knight")
        assert sim == 0.9

    def test_abbreviated_last_name_matches(self):
        # "Miguel P." vs "Miguel Paucar" - abbreviated last name matches (0.8)
        # score = (1.0 + 0.8) / 2 = 0.9
        sim = similarity("Miguel P.", "Miguel Paucar")
        assert sim == 0.9

    def test_both_abbreviated_match(self):
        # "T. Lopez" vs "Tomas L" - both abbreviated, both match (0.8)
        # score = (0.8 + 0.8) / 2 = 0.8
        sim = similarity("T. Lopez", "Tomas L")
        assert sim == 0.8

    def test_lori_sanchez_vs_lori_sal(self):
        # "Lori Sanchez" vs "Lori Sal." - "sal" is NOT prefix of "sanchez" (san vs sal)
        # Score = (1.0 + ratio("sanchez", "sal")) / 2
        # ratio("sanchez", "sal") = 2 * 2 / (7 + 3) = 0.4
        # score = (1.0 + 0.4) / 2 = 0.7
        sim = similarity("Lori Sanchez", "Lori Sal.")
        assert sim < 0.75

    def test_chachi_vs_charlie(self):
        # "Chachi Faker" vs "Charlie Faker" - "chachi" vs "charlie"
        # ratio("chachi", "charlie") is ~0.615
        # score = (0.615 + 1.0) / 2 = 0.807
        sim = similarity("Chachi Faker", "Charlie Faker")
        assert sim > 0.8

    def test_reversed_names(self):
        # "Renato Alegre" vs "Alegre Renato"
        # Order-independent matching (Token-Set)
        sim = similarity("Renato Alegre", "Alegre Renato")
        assert sim == 1.0

    def test_middle_name_initial(self):
        # "Renato Alegre" vs "Renato J. Alegre"
        # 2 matches out of 3 total words. "J." doesn't match anything.
        # Score = (1.0 + 1.0 + 0.0) / 3 = 0.66
        # Wait, if "J." is a prefix of nothing, it's 0.
        # matched_count = 2.0. len(long_words) = 3.
        # 2/3 = 0.66. But if we consider J. as a typo?
        # Actually, "Renato" matches "Renato", "Alegre" matches "Alegre".
        # matched_count = 2.0.
        # len(long_words) = 3.
        # score = 2.0 / 3.0 = 0.66.
        # This shouldn't be high enough by itself, but if we boost?
        # Difference is 1 word, and all words of short_words match perfectly.
        # Boost to 0.8!
        sim = similarity("Renato Alegre", "Renato J. Alegre")
        assert sim == 0.8

    def test_typo_in_long_name(self):
        # "Renato Alegre" vs "Renato Alegrre"
        # "Renato" (1.0) + "Alegre" vs "Alegrre" (ratio 0.92)
        # Score = (1.0 + 0.92) / 2 = 0.96
        sim = similarity("Renato Alegre", "Renato Alegrre")
        assert sim > 0.9

    def test_complex_typo_and_abbreviation(self):
        # "M. Paucar" vs "Miguel Pauca"
        # "M." vs "Miguel" (0.8 prefix)
        # "Paucar" vs "Pauca" (0.8 prefix)
        # Score = (0.8 + 0.8) / 2 = 0.8
        sim = similarity("M. Paucar", "Miguel Pauca")
        assert sim == 0.8

    def test_renato_vs_denisse_r_false_positive(self):
        # "Renato" vs "Denisse R." - "Renato" starts with "R", so it matched before.
        # But "Renato" is a first name, "R" is a surname initial.
        # Score = (0.7 [prefix match length 1] + 0.3 [typo]) / 2 = 0.5
        # Boost only if matched_count == len(short_words).
        # "renato" vs "r" is 0.7, "renato" vs "denisse" is 0.3.
        # Best match is 0.7. matched_count = 0.7. len(short_words) = 1.
        # 0.7 != 1.0, so NO boost. Final score = 0.7 / 2 = 0.35.
        sim = similarity("Renato", "Denisse R.")
        assert sim < 0.75

    def test_empty_strings(self):
        assert similarity("", "") == 1.0

    def test_one_empty(self):
        assert similarity("John", "") == 0.0


# ── Similar name detection ────────────────────────────────────────────────────


def _create_test_notion_player_names(
    name: str, alias: list[str] | None = None, notion_id: str = "test_id"
) -> PlayerNameData:
    """Helper to create a minimal NotionPlayerDict for testing."""
    return {"name": name, "alias": alias or [], "notion_id": notion_id}


class TestDetectSimilarNames:
    def test_no_similar_names(self):
        notion_players = {
            "john doe": _create_test_notion_player_names("John Doe"),
            "jane smith": _create_test_notion_player_names("Jane Smith"),
        }
        snapshot_names = ["John Doe", "Jane Smith"]
        result = detect_similar_names(notion_players, snapshot_names)
        assert result == []

    def test_detects_similar_pair(self):
        notion_players = {"john doe": _create_test_notion_player_names("John Doe")}
        snapshot_names = ["John D."]
        result = detect_similar_names(notion_players, snapshot_names)
        assert len(result) == 1
        assert result[0]["notion_name"] == "John Doe"
        assert result[0]["snapshot"] == "John D."
        assert result[0]["similarity"] >= 0.75

    def test_skips_exact_matches(self):
        notion_players = {"john doe": _create_test_notion_player_names("John Doe")}
        snapshot_names = ["John Doe"]
        result = detect_similar_names(notion_players, snapshot_names)
        assert result == []

    def test_skips_case_insensitive_exact_matches(self):
        notion_players = {"john doe": _create_test_notion_player_names("John Doe")}
        snapshot_names = ["john doe"]
        result = detect_similar_names(notion_players, snapshot_names)
        assert result == []

    def test_respects_threshold(self):
        notion_players = {"john doe": _create_test_notion_player_names("John Doe")}
        snapshot_names = ["Jane Smith"]
        # Default threshold is 0.75, these names are very different
        result = detect_similar_names(notion_players, snapshot_names, threshold=0.75)
        assert result == []

    def test_custom_threshold(self):
        notion_players = {"john doe": _create_test_notion_player_names("John Doe")}
        snapshot_names = ["John D."]
        # "John Doe" vs "John D." matches (D is prefix of Doe), so it should be found
        # score = (1.0 + 0.8) / 2 = 0.9
        result = detect_similar_names(notion_players, snapshot_names, threshold=0.85)
        assert len(result) == 1

    def test_multiple_matches(self):
        # Note: "John Doe" vs "John Doe Jr" won't match because word counts differ
        # Let's use names with same word count
        notion_players = {
            "john doe": _create_test_notion_player_names("John Doe"),
            "jane smith": _create_test_notion_player_names("Jane Smith"),
        }
        snapshot_names = ["John D.", "Jane S."]
        result = detect_similar_names(notion_players, snapshot_names)
        assert len(result) == 2

    def test_sorted_by_similarity(self):
        notion_players = {
            "john doe": _create_test_notion_player_names("John Doe"),
            "jane smith": _create_test_notion_player_names("Jane Smith"),
        }
        snapshot_names = ["John D.", "Jane S."]
        result = detect_similar_names(notion_players, snapshot_names)
        # Should be sorted by similarity descending (both are 1.0)
        assert result[0]["similarity"] >= result[1]["similarity"]

    def test_empty_lists(self):
        result = detect_similar_names({}, [])
        assert result == []

    def test_empty_notion(self):
        result = detect_similar_names({}, ["John Doe"])
        assert result == []

    def test_empty_snapshot(self):
        result = detect_similar_names(
            {"john doe": _create_test_notion_player_names("John Doe")}, []
        )
        assert result == []

    def test_detects_alias_similarity(self):
        notion_players = {
            "renato alegre": _create_test_notion_player_names("Renato Alegre", alias=["ren"])
        }
        snapshot_names = ["re"]  # Prefix of "ren"
        result = detect_similar_names(notion_players, snapshot_names, threshold=0.5)
        assert len(result) == 1
        assert result[0]["notion_name"] == "Renato Alegre"
        assert result[0]["snapshot"] == "re"
        assert result[0]["similarity"] == 0.8

    def test_alias_exact_match_skips_similarity(self):
        notion_players = {
            "renato alegre": _create_test_notion_player_names("Renato Alegre", alias=["ren"])
        }
        snapshot_names = ["ren"]  # Exact match with alias
        result = detect_similar_names(notion_players, snapshot_names)
        assert len(result) == 1
        assert result[0]["match_method"] == "alias_exact"
        assert result[0].get("matched_alias") == "ren"
        assert result[0]["notion_name"] == "Renato Alegre"

    def test_handles_list_input(self):
        # The function should handle both dict and list inputs for notion_players
        notion_players = [_create_test_notion_player_names("John Doe")]
        snapshot_names = ["John D."]
        result = detect_similar_names(notion_players, snapshot_names)
        assert len(result) == 1
        assert result[0]["notion_name"] == "John Doe"

    def test_detects_1_to_many_conflict(self):
        # Snapshot has "Renato", Notion has "Renato Alegre" and "Renato Garcia"
        # Both should match
        notion_players = [
            _create_test_notion_player_names("Renato Alegre"),
            _create_test_notion_player_names("Renato Garcia"),
        ]
        snapshot_names = ["Renato"]
        result = detect_similar_names(notion_players, snapshot_names)
        assert len(result) == 2
        notion_names = {r["notion_name"] for r in result}
        assert "Renato Alegre" in notion_names
        assert "Renato Garcia" in notion_names

    def test_detects_many_to_1_conflict(self):
        # Notion has "Renato", Snapshot has "Renato Alegre" and "Renato Garcia"
        # Both should match
        notion_players = [_create_test_notion_player_names("Renato")]
        snapshot_names = ["Renato Alegre", "Renato Garcia"]
        result = detect_similar_names(notion_players, snapshot_names)
        assert len(result) == 2
        snapshot_names_result = {r["snapshot"] for r in result}
        assert "Renato Alegre" in snapshot_names_result
        assert "Renato Garcia" in snapshot_names_result


# ── find_notion_player tests ─────────────────────────────────────────────────────


def test_find_notion_player():
    """Test find_notion_player function for exact matches, alias matching, and normalization."""
    # Construct mock notion players dictionary
    mock_notion_players: dict[str, NotionPlayerDict] = {
        "danivonklaus": {
            "nombre": "DaniVonKlaus",
            "alias": ["daniel eiler", "dani"],
            "notion_id": "test_id",
            "is_new": True,
            "juegos_este_ano": 0,
            "c_england": 0,
            "c_france": 0,
            "c_germany": 0,
            "c_italy": 0,
            "c_austria": 0,
            "c_russia": 0,
            "c_turkey": 0,
        }
    }

    # Test exact match
    result = find_notion_player("DaniVonKlaus", mock_notion_players)
    assert result is not None
    assert result["nombre"] == "DaniVonKlaus"
    assert result["alias"] == ["daniel eiler", "dani"]

    # Test alias match
    result = find_notion_player("Daniel Eiler", mock_notion_players)
    assert result is not None
    assert result["nombre"] == "DaniVonKlaus"
    assert result["alias"] == ["daniel eiler", "dani"]

    # Test alias match with different alias
    result = find_notion_player("Dani", mock_notion_players)
    assert result is not None
    assert result["nombre"] == "DaniVonKlaus"
    assert result["alias"] == ["daniel eiler", "dani"]

    # Test case/whitespace insensitivity for alias
    result = find_notion_player("  DANIEL   EILER  ", mock_notion_players)
    assert result is not None
    assert result["nombre"] == "DaniVonKlaus"
    assert result["alias"] == ["daniel eiler", "dani"]

    # Test case/whitespace insensitivity for exact name
    result = find_notion_player("  DANIVONKLAUS  ", mock_notion_players)
    assert result is not None
    assert result["nombre"] == "DaniVonKlaus"

    # Test no match
    result = find_notion_player("Unknown Player", mock_notion_players)
    assert result is None

    # Test empty dictionary
    empty_players: dict[str, NotionPlayerDict] = {}
    result = find_notion_player("DaniVonKlaus", empty_players)
    assert result is None


# ── Sync behavior tests ──────────────────────────────────────────────────────


class TestSyncBehavior:
    """Tests for the sync behavior to ensure players are preserved, merged, and filtered correctly."""

    def _simulate_sync_logic(
        self,
        existentes: dict[str, Any],
        notion_players: dict[str, Any],
        merges: dict[str, Any] | None = None,
        *,
        is_first_sync: bool = False,
    ) -> list[dict[str, Any]]:
        """Helper to simulate the exact row-building logic from notion_sync.py"""

        if merges is None:
            merges = {}

        filas: list[dict[str, Any]] = []
        if not is_first_sync:
            merged_notion_normalized = {normalize_name(v["to"]) for v in merges.values()}

            for nombre, existente in existentes.items():
                # 1. Merged players
                if nombre in merges:
                    merge_info: dict[str, Any] = merges[nombre]
                    notion_name: str = merge_info["to"]
                    action: str = merge_info.get("action", "merge_local")
                    notion_norm: str = normalize_name(notion_name)
                    if notion_norm in notion_players:
                        nd: dict[str, Any] = notion_players[notion_norm]
                        assert nd is not None
                        filas.append(
                            {
                                "Nombre": nd["nombre"] if action == "merge_notion" else nombre,
                                "is_new": nd["is_new"],
                                "Juegos_Este_Ano": nd["juegos_este_ano"],
                                "has_priority": int(
                                    existente.get("has_priority", FIELD_DEFAULTS["has_priority"])
                                ),
                                "partidas_deseadas": int(
                                    existente.get(
                                        "partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"]
                                    )
                                ),
                                "partidas_gm": int(
                                    existente.get("partidas_gm", FIELD_DEFAULTS["partidas_gm"])
                                ),
                                **{c: nd.get(c, 0) for c in COUNTRY_PROPS},
                            }
                        )
                        continue

                # 2. Notion players (exact match or alias)
                notion_data: NotionPlayerDict | None = find_notion_player(nombre, notion_players)
                if notion_data:
                    assert notion_data is not None
                    if normalize_name(notion_data["nombre"]) not in merged_notion_normalized:
                        filas.append(
                            {
                                "Nombre": nombre,  # Keep local name
                                "is_new": notion_data["is_new"],
                                "Juegos_Este_Ano": notion_data["juegos_este_ano"],
                                "has_priority": int(
                                    existente.get("has_priority", FIELD_DEFAULTS["has_priority"])
                                ),
                                "partidas_deseadas": int(
                                    existente.get(
                                        "partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"]
                                    )
                                ),
                                "partidas_gm": int(
                                    existente.get("partidas_gm", FIELD_DEFAULTS["partidas_gm"])
                                ),
                                **{c: notion_data.get(c, 0) for c in COUNTRY_PROPS},
                            }
                        )
                # 3. Not in Notion (Preserved locally)
                elif nombre not in merges:
                    filas.append(
                        {
                            "Nombre": nombre,
                            "is_new": existente.get("is_new", True),
                            "Juegos_Este_Ano": int(existente.get("juegos_este_ano", 0)),
                            "has_priority": int(
                                existente.get("has_priority", FIELD_DEFAULTS["has_priority"])
                            ),
                            "partidas_deseadas": int(
                                existente.get(
                                    "partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"]
                                )
                            ),
                            "partidas_gm": int(
                                existente.get("partidas_gm", FIELD_DEFAULTS["partidas_gm"])
                            ),
                            **{c: existente.get(c, 0) for c in COUNTRY_PROPS},
                        }
                    )
        else:
            # First ever sync
            for _, nd in notion_players.items():
                assert isinstance(nd, dict)
                filas.append(
                    {
                        "Nombre": nd["nombre"],
                        "is_new": nd["is_new"],
                        "Juegos_Este_Ano": nd["juegos_este_ano"],
                        "has_priority": FIELD_DEFAULTS["has_priority"],
                        "partidas_deseadas": FIELD_DEFAULTS["partidas_deseadas"],
                        "partidas_gm": FIELD_DEFAULTS["partidas_gm"],
                        **{c: nd.get(c, 0) for c in COUNTRY_PROPS},
                    }
                )
        return filas

    def test_players_not_in_notion_are_preserved(self):
        """Regression test: Local players not in Notion must not be deleted."""
        existentes = {
            "Andy": {
                "nombre": "Andy",
                "is_new": False,
                "juegos_este_ano": 2,
                "has_priority": False,
                "partidas_deseadas": 2,
                "partidas_gm": 1,
                "c_england": 1,
            },
            "Charlie": {
                "nombre": "Charlie",
                "is_new": False,
                "juegos_este_ano": 0,
                "has_priority": False,
                "partidas_deseadas": 2,
                "partidas_gm": 0,
            },
        }
        notion_players = {
            "andy": {
                "nombre": "Andy",
                "is_new": False,
                "juegos_este_ano": 1,
                "c_england": 2,
            },
        }

        filas = self._simulate_sync_logic(existentes, notion_players)

        assert len(filas) == 2
        nombres = [f["Nombre"] for f in filas]
        assert "Andy" in nombres
        assert "Charlie" in nombres

        andy_row = next(f for f in filas if f["Nombre"] == "Andy")
        assert andy_row["Juegos_Este_Ano"] == 1  # Updated from Notion
        assert andy_row["c_england"] == 2  # Updated from Notion

        charlie_row = next(f for f in filas if f["Nombre"] == "Charlie")
        assert charlie_row["Juegos_Este_Ano"] == 0  # Preserved from local

    def test_country_stats_extraction(self):
        """Test that country stats are correctly extracted and updated."""

        # Mock property with number
        prop_num: NotionProperty = {"type": "number", "number": 5}
        assert extract_number(prop_num) == 5

        # Mock property with formula
        prop_formula: NotionProperty = {
            "type": "formula",
            "formula": {"type": "number", "number": 3},
        }
        assert extract_number(prop_formula) == 3

        # Mock empty or invalid
        prop_empty: NotionProperty = {}
        assert extract_number(prop_empty) == 0

    def test_new_notion_players_are_ignored(self):
        """Regression test: New players in Notion must NOT be added to an existing snapshot."""
        existentes = {
            "Kur": {"nombre": "Kur", "is_new": False, "juegos_este_ano": 1},
        }
        notion_players = {
            "kur": {"nombre": "Kur", "is_new": False, "juegos_este_ano": 2},
            "nuevo_jugador": {
                "nombre": "Nuevo Jugador",
                "is_new": True,
                "juegos_este_ano": 0,
            },
        }

        filas = self._simulate_sync_logic(existentes, notion_players)

        assert len(filas) == 1
        assert filas[0]["Nombre"] == "Kur"
        assert filas[0]["Juegos_Este_Ano"] == 2  # Updated

    def test_player_merged_adopt_notion_name(self):
        """Test that merging a player and choosing to adopt Notion name works."""
        existentes = {
            "Kur": {
                "nombre": "Kur",
                "is_new": False,
                "juegos_este_ano": 1,
                "has_priority": True,
                "partidas_deseadas": 3,
            },
        }
        notion_players = {
            "kurt": {"nombre": "Kurt", "is_new": False, "juegos_este_ano": 5},
        }
        merges = {"Kur": {"to": "Kurt", "action": "merge_notion"}}

        filas = self._simulate_sync_logic(existentes, notion_players, merges)

        assert len(filas) == 1
        assert filas[0]["Nombre"] == "Kurt"  # Adopted new name
        assert filas[0]["Juegos_Este_Ano"] == 5  # Updated from Notion

    def test_player_merged_keep_local_name(self):
        """Test that merging a player and choosing to keep local name works."""
        existentes = {
            "Kur": {
                "nombre": "Kur",
                "is_new": False,
                "juegos_este_ano": 1,
                "has_priority": True,
                "partidas_deseadas": 3,
            },
        }
        notion_players = {
            "kurt": {"nombre": "Kurt", "is_new": False, "juegos_este_ano": 5},
        }
        merges = {"Kur": {"to": "Kurt", "action": "merge_local"}}

        filas = self._simulate_sync_logic(existentes, notion_players, merges)

        assert len(filas) == 1
        assert filas[0]["Nombre"] == "Kur"  # Kept local name
        assert filas[0]["Juegos_Este_Ano"] == 5  # Updated from Notion

    def test_player_merge_skipped(self):
        """Test that skipping a merge preserves the local player and ignores the new Notion player."""
        existentes = {
            "Kur": {"nombre": "Kur", "is_new": False, "juegos_este_ano": 1},
        }
        notion_players = {
            "kurt": {"nombre": "Kurt", "is_new": False, "juegos_este_ano": 5},
        }
        merges: dict[str, Any] = {}  # User skipped

        filas = self._simulate_sync_logic(existentes, notion_players, merges)

        assert len(filas) == 1
        assert filas[0]["Nombre"] == "Kur"  # Local preserved
        assert filas[0]["Juegos_Este_Ano"] == 1  # Local stats preserved (Kurt was ignored)

    def test_player_matched_via_alias_regression(self):
        """Regression: Match via alias must keep local name even without explicit merge."""
        existentes = {"Jean": {"nombre": "Jean", "is_new": True}}
        notion_players = {
            "jean carlos": {
                "nombre": "Jean Carlos",
                "is_new": False,
                "juegos_este_ano": 5,
                "alias": ["jean"],
            }
        }
        filas = self._simulate_sync_logic(existentes, notion_players)
        assert filas[0]["Nombre"] == "Jean"
        assert not filas[0]["is_new"]

    def test_golden_rule_explicit_merge_notion(self):
        """Regression: Explicit merge 'merge_notion' must change name to Notion main name."""
        existentes = {"Jean": {"nombre": "Jean", "is_new": True}}
        notion_players = {
            "jean carlos": {"nombre": "Jean Carlos", "is_new": False, "juegos_este_ano": 5}
        }
        merges = {"Jean": {"to": "Jean Carlos", "action": "merge_notion"}}
        filas = self._simulate_sync_logic(existentes, notion_players, merges)
        assert filas[0]["Nombre"] == "Jean Carlos"

    def test_golden_rule_explicit_merge_local(self):
        """Regression: Explicit merge 'merge_local' must keep name as local name."""
        existentes = {"Jean": {"nombre": "Jean", "is_new": True}}
        notion_players = {
            "jean carlos": {"nombre": "Jean Carlos", "is_new": False, "juegos_este_ano": 5}
        }
        merges = {"Jean": {"to": "Jean Carlos", "action": "merge_local"}}
        filas = self._simulate_sync_logic(existentes, notion_players, merges)
        assert filas[0]["Nombre"] == "Jean"


# Alias casing preservation tests


def test_build_notion_players_lookup_preserves_alias_casing() -> None:
    mock_pages: list[NotionPage] = [
        {
            "id": "test-id-123",
            "properties": {
                "Nombre": {"type": "title", "title": [{"plain_text": "Juan"}]},
                "Alias": {
                    "type": "rich_text",
                    "rich_text": [{"plain_text": "CamelCase Alias, UPPERCASE"}],
                },
                "Participaciones": {"type": "relation", "relation": []},
            },
        }
    ]

    result = build_notion_players_lookup(mock_pages, {})

    player = result["juan"]
    assert "CamelCase Alias" in player["alias"]
    assert "UPPERCASE" in player["alias"]
    # Ensure it did NOT aggressively lowercase
    assert "camelcase alias" not in player["alias"]
