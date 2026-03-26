"""
test_notion_sync.py — Unit tests for notion_sync.py.

Covers:
  - Name similarity detection
  - Name normalization
  - Filtering to snapshot players
"""
from __future__ import annotations

from .notion_sync import (
    _detect_similar_names,
    _normalize_name,
    _similarity,
)

# ── Name normalization ────────────────────────────────────────────────────────

class TestNormalizeName:
    def test_lowercases(self):
        assert _normalize_name("John Doe") == "john doe"

    def test_strips_whitespace(self):
        assert _normalize_name("  John Doe  ") == "john doe"

    def test_collapses_multiple_spaces(self):
        assert _normalize_name("John   Doe") == "john doe"

    def test_empty_string(self):
        assert _normalize_name("") == ""

    def test_single_word(self):
        assert _normalize_name("John") == "john"


# ── Similarity calculation ────────────────────────────────────────────────────

class TestSimilarity:
    def test_identical_strings(self):
        assert _similarity("John Doe", "John Doe") == 1.0

    def test_case_insensitive(self):
        assert _similarity("John Doe", "john doe") == 1.0

    def test_similar_names(self):
        # "Ren Alegre" vs "Renato Alegre" - first name is prefix
        sim = _similarity("Ren Alegre", "Renato Alegre")
        assert sim == 1.0

    def test_different_names(self):
        sim = _similarity("John Doe", "Jane Smith")
        assert sim == 0.0

    def test_abbreviated_last_names_are_different(self):
        # "Gonzalo Ch." vs "Gonzalo L." - different people with abbreviated last names
        sim = _similarity("Gonzalo Ch.", "Gonzalo L.")
        assert sim == 0.0  # Last names don't match

    def test_jean_carlos_similarity(self):
        # "Jean Carlos" (2 words) vs "Jean Carlos R." (3 words)
        # Prefix matches perfectly, difference is 1 word -> Boosted to 0.8
        sim = _similarity("Jean Carlos", "Jean Carlos R.")
        assert sim == 0.8

    def test_word_count_difference_prefix_match(self):
        # "Jean" vs "Jean Carlos R." -> difference is 2 words, no boost
        # 1 match / 3 total words = 0.33
        sim = _similarity("Jean", "Jean Carlos R.")
        assert 0.3 < sim < 0.4

    def test_same_first_name_different_last_name(self):
        # "John Smith" vs "John Doe" - mismatch in second word
        sim = _similarity("John Smith", "John Doe")
        assert sim == 0.0

    def test_abbreviated_first_name_matches(self):
        # "P. Knight" vs "Paul Knight" - abbreviated first name matches
        sim = _similarity("P. Knight", "Paul Knight")
        assert sim == 1.0

    def test_abbreviated_last_name_matches(self):
        # "Miguel P." vs "Miguel Paucar" - abbreviated last name matches
        sim = _similarity("Miguel P.", "Miguel Paucar")
        assert sim == 1.0

    def test_both_abbreviated_match(self):
        # "T. Lopez" vs "Tomas L" - both abbreviated, both match
        sim = _similarity("T. Lopez", "Tomas L")
        assert sim == 1.0

    def test_lori_sanchez_vs_lori_sal(self):
        # "Lori Sanchez" vs "Lori Sal." - last names don't match
        sim = _similarity("Lori Sanchez", "Lori Sal.")
        assert sim == 0.0

    def test_chachi_vs_charlie(self):
        # "Chachi Faker" vs "Charlie Faker" - first names don't match
        sim = _similarity("Chachi Faker", "Charlie Faker")
        assert sim == 0.0

    def test_empty_strings(self):
        assert _similarity("", "") == 1.0

    def test_one_empty(self):
        assert _similarity("John", "") == 0.0


# ── Similar name detection ────────────────────────────────────────────────────

class TestDetectSimilarNames:
    def test_no_similar_names(self):
        notion_players = {
            "john doe": {"nombre": "John Doe"},
            "jane smith": {"nombre": "Jane Smith"}
        }
        snapshot_names = ["John Doe", "Jane Smith"]
        result = _detect_similar_names(notion_players, snapshot_names)
        assert result == []

    def test_detects_similar_pair(self):
        notion_players = {"john doe": {"nombre": "John Doe"}}
        snapshot_names = ["John D."]
        result = _detect_similar_names(notion_players, snapshot_names)
        assert len(result) == 1
        assert result[0]["notion"] == "John Doe"
        assert result[0]["snapshot"] == "John D."
        assert result[0]["similarity"] >= 0.75

    def test_skips_exact_matches(self):
        notion_players = {"john doe": {"nombre": "John Doe"}}
        snapshot_names = ["John Doe"]
        result = _detect_similar_names(notion_players, snapshot_names)
        assert result == []

    def test_skips_case_insensitive_exact_matches(self):
        notion_players = {"john doe": {"nombre": "John Doe"}}
        snapshot_names = ["john doe"]
        result = _detect_similar_names(notion_players, snapshot_names)
        assert result == []

    def test_respects_threshold(self):
        notion_players = {"john doe": {"nombre": "John Doe"}}
        snapshot_names = ["Jane Smith"]
        # Default threshold is 0.75, these names are very different
        result = _detect_similar_names(notion_players, snapshot_names, threshold=0.75)
        assert result == []

    def test_custom_threshold(self):
        notion_players = {"john doe": {"nombre": "John Doe"}}
        snapshot_names = ["John D."]
        # "John Doe" vs "John D." matches (D is prefix of Doe), so it should be found
        result = _detect_similar_names(notion_players, snapshot_names, threshold=0.99)
        assert len(result) == 1
        assert result[0]["similarity"] == 1.0

    def test_multiple_matches(self):
        # Note: "John Doe" vs "John Doe Jr" won't match because word counts differ
        # Let's use names with same word count
        notion_players = {
            "john doe": {"nombre": "John Doe"},
            "jane smith": {"nombre": "Jane Smith"}
        }
        snapshot_names = ["John D.", "Jane S."]
        result = _detect_similar_names(notion_players, snapshot_names)
        assert len(result) == 2

    def test_sorted_by_similarity(self):
        notion_players = {
            "john doe": {"nombre": "John Doe"},
            "jane smith": {"nombre": "Jane Smith"}
        }
        snapshot_names = ["John D.", "Jane S."]
        result = _detect_similar_names(notion_players, snapshot_names)
        # Should be sorted by similarity descending (both are 1.0)
        assert result[0]["similarity"] >= result[1]["similarity"]

    def test_empty_lists(self):
        result = _detect_similar_names({}, [])
        assert result == []

    def test_empty_notion(self):
        result = _detect_similar_names({}, ["John Doe"])
        assert result == []

    def test_empty_snapshot(self):
        result = _detect_similar_names({"john doe": {"nombre": "John Doe"}}, [])
        assert result == []

    def test_detects_alias_similarity(self):
         notion_players = {
             "renato alegre": {"nombre": "Renato Alegre", "alias": ["ren"]}
         }
         snapshot_names = ["re"] # Prefix of "ren"
         result = _detect_similar_names(notion_players, snapshot_names, threshold=0.5)
         assert len(result) == 1
         assert result[0]["notion"] == "Renato Alegre"
         assert result[0]["snapshot"] == "re"
         assert result[0]["similarity"] == 1.0

    def test_alias_exact_match_skips_similarity(self):
        notion_players = {
            "renato alegre": {"nombre": "Renato Alegre", "alias": ["ren"]}
        }
        snapshot_names = ["ren"] # Exact match with alias
        result = _detect_similar_names(notion_players, snapshot_names)
        assert result == [] # Should be skipped because it's an exact match with alias



# ── Sync behavior tests ──────────────────────────────────────────────────────

class TestSyncBehavior:
    """Tests for the sync behavior to ensure players are preserved, merged, and filtered correctly."""

    def _simulate_sync_logic(self, existentes, notion_players, merges=None, is_first_sync=False):
        """Helper to simulate the exact row-building logic from notion_sync.py"""
        from .notion_sync import FIELD_DEFAULTS, _find_notion_player, _normalize_name
        if merges is None:
            merges = {}
        
        filas = []
        if not is_first_sync:
            merged_notion_normalized = {_normalize_name(v["to"]) for v in merges.values()}
            
            for nombre, existente in existentes.items():
                # 1. Merged players
                if nombre in merges:
                    merge_info = merges[nombre]
                    notion_name = merge_info["to"]
                    action = merge_info.get("action", "merge_local")
                    notion_norm = _normalize_name(notion_name)
                    if notion_norm in notion_players:
                        notion_data = notion_players[notion_norm]
                        filas.append({
                            "Nombre":            notion_data["nombre"] if action == "merge_notion" else nombre,
                            "Experiencia":       notion_data["experiencia"],
                            "Juegos_Este_Ano":   notion_data["juegos"],
                            "prioridad":         int(existente.get("prioridad",         FIELD_DEFAULTS["prioridad"])),
                            "partidas_deseadas": int(existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])),
                            "partidas_gm":       int(existente.get("partidas_gm",       FIELD_DEFAULTS["partidas_gm"])),
                        })
                        continue
                
                # 2. Notion players (exact match or alias)
                notion_data = _find_notion_player(nombre, notion_players)
                if notion_data and _normalize_name(notion_data["nombre"]) not in merged_notion_normalized:
                    filas.append({
                        "Nombre":            nombre, # Keep local name
                        "Experiencia":       notion_data["experiencia"],
                        "Juegos_Este_Ano":   notion_data["juegos"],
                        "prioridad":         int(existente.get("prioridad",         FIELD_DEFAULTS["prioridad"])),
                        "partidas_deseadas": int(existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])),
                        "partidas_gm":       int(existente.get("partidas_gm",       FIELD_DEFAULTS["partidas_gm"])),
                    })
                # 3. Not in Notion (Preserved locally)
                elif nombre not in merges:
                    filas.append({
                        "Nombre":            nombre,
                        "Experiencia":       existente.get("experiencia", "Nuevo"),
                        "Juegos_Este_Ano":   int(existente.get("juegos_este_ano", 0)),
                        "prioridad":         int(existente.get("prioridad",         FIELD_DEFAULTS["prioridad"])),
                        "partidas_deseadas": int(existente.get("partidas_deseadas", FIELD_DEFAULTS["partidas_deseadas"])),
                        "partidas_gm":       int(existente.get("partidas_gm",       FIELD_DEFAULTS["partidas_gm"])),
                    })
        else:
            # First ever sync
            for _, notion_data in notion_players.items():
                filas.append({
                    "Nombre":            notion_data["nombre"],
                    "Experiencia":       notion_data["experiencia"],
                    "Juegos_Este_Ano":   notion_data["juegos"],
                    "prioridad":         FIELD_DEFAULTS["prioridad"],
                    "partidas_deseadas": FIELD_DEFAULTS["partidas_deseadas"],
                    "partidas_gm":       FIELD_DEFAULTS["partidas_gm"],
                })
        return filas

    def test_players_not_in_notion_are_preserved(self):
        """Regression test: Local players not in Notion must not be deleted."""
        existentes = {
            "Andy": {"nombre": "Andy", "experiencia": "Antiguo", "juegos_este_ano": 2, "prioridad": 0, "partidas_deseadas": 2, "partidas_gm": 1},
            "Charlie": {"nombre": "Charlie", "experiencia": "Antiguo", "juegos_este_ano": 0, "prioridad": 0, "partidas_deseadas": 2, "partidas_gm": 0},
        }
        notion_players = {
            "andy": {"nombre": "Andy", "experiencia": "Antiguo", "juegos": 1},
        }
        
        filas = self._simulate_sync_logic(existentes, notion_players)
        
        assert len(filas) == 2
        nombres = [f["Nombre"] for f in filas]
        assert "Andy" in nombres
        assert "Charlie" in nombres
        
        andy_row = next(f for f in filas if f["Nombre"] == "Andy")
        assert andy_row["Juegos_Este_Ano"] == 1 # Updated from Notion
        charlie_row = next(f for f in filas if f["Nombre"] == "Charlie")
        assert charlie_row["Juegos_Este_Ano"] == 0 # Preserved from local

    def test_new_notion_players_are_ignored(self):
        """Regression test: New players in Notion must NOT be added to an existing snapshot."""
        existentes = {
            "Kur": {"nombre": "Kur", "experiencia": "Antiguo", "juegos_este_ano": 1},
        }
        notion_players = {
            "kur": {"nombre": "Kur", "experiencia": "Antiguo", "juegos": 2},
            "nuevo_jugador": {"nombre": "Nuevo Jugador", "experiencia": "Nuevo", "juegos": 0},
        }
        
        filas = self._simulate_sync_logic(existentes, notion_players)
        
        assert len(filas) == 1
        assert filas[0]["Nombre"] == "Kur"
        assert filas[0]["Juegos_Este_Ano"] == 2 # Updated

    def test_player_merged_adopt_notion_name(self):
        """Test that merging a player and choosing to adopt Notion name works."""
        existentes = {
            "Kur": {"nombre": "Kur", "experiencia": "Antiguo", "juegos_este_ano": 1, "prioridad": 1, "partidas_deseadas": 3},
        }
        notion_players = {
            "kurt": {"nombre": "Kurt", "experiencia": "Antiguo", "juegos": 5},
        }
        merges = {"Kur": {"to": "Kurt", "action": "merge_notion"}}
        
        filas = self._simulate_sync_logic(existentes, notion_players, merges)
        
        assert len(filas) == 1
        assert filas[0]["Nombre"] == "Kurt" # Adopted new name
        assert filas[0]["Juegos_Este_Ano"] == 5 # Updated from Notion

    def test_player_merged_keep_local_name(self):
        """Test that merging a player and choosing to keep local name works."""
        existentes = {
            "Kur": {"nombre": "Kur", "experiencia": "Antiguo", "juegos_este_ano": 1, "prioridad": 1, "partidas_deseadas": 3},
        }
        notion_players = {
            "kurt": {"nombre": "Kurt", "experiencia": "Antiguo", "juegos": 5},
        }
        merges = {"Kur": {"to": "Kurt", "action": "merge_local"}}
        
        filas = self._simulate_sync_logic(existentes, notion_players, merges)
        
        assert len(filas) == 1
        assert filas[0]["Nombre"] == "Kur" # Kept local name
        assert filas[0]["Juegos_Este_Ano"] == 5 # Updated from Notion

    def test_player_merge_skipped(self):
        """Test that skipping a merge preserves the local player and ignores the new Notion player."""
        existentes = {
            "Kur": {"nombre": "Kur", "experiencia": "Antiguo", "juegos_este_ano": 1},
        }
        notion_players = {
            "kurt": {"nombre": "Kurt", "experiencia": "Antiguo", "juegos": 5},
        }
        merges = {} # User skipped
        
        filas = self._simulate_sync_logic(existentes, notion_players, merges)
        
        assert len(filas) == 1
        assert filas[0]["Nombre"] == "Kur" # Local preserved
        assert filas[0]["Juegos_Este_Ano"] == 1 # Local stats preserved (Kurt was ignored)

    def test_player_matched_via_alias_regression(self):
        """Regression: Match via alias must keep local name even without explicit merge."""
        existentes = {"Jean": {"nombre": "Jean", "experiencia": "Nuevo"}}
        notion_players = {
            "jean carlos": {"nombre": "Jean Carlos", "experiencia": "Antiguo", "juegos": 5, "alias": ["jean"]}
        }
        filas = self._simulate_sync_logic(existentes, notion_players)
        assert filas[0]["Nombre"] == "Jean"
        assert filas[0]["Experiencia"] == "Antiguo"

    def test_golden_rule_explicit_merge_notion(self):
        """Regression: Explicit merge 'merge_notion' must change name to Notion main name."""
        existentes = {"Jean": {"nombre": "Jean", "experiencia": "Nuevo"}}
        notion_players = {
            "jean carlos": {"nombre": "Jean Carlos", "experiencia": "Antiguo", "juegos": 5}
        }
        merges = {"Jean": {"to": "Jean Carlos", "action": "merge_notion"}}
        filas = self._simulate_sync_logic(existentes, notion_players, merges)
        assert filas[0]["Nombre"] == "Jean Carlos"

    def test_golden_rule_explicit_merge_local(self):
        """Regression: Explicit merge 'merge_local' must keep name as local name."""
        existentes = {"Jean": {"nombre": "Jean", "experiencia": "Nuevo"}}
        notion_players = {
            "jean carlos": {"nombre": "Jean Carlos", "experiencia": "Antiguo", "juegos": 5}
        }
        merges = {"Jean": {"to": "Jean Carlos", "action": "merge_local"}}
        filas = self._simulate_sync_logic(existentes, notion_players, merges)
        assert filas[0]["Nombre"] == "Jean"