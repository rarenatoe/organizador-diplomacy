"""
test_notion_sync.py — Unit tests for notion_sync.py.

Covers:
  - Name similarity detection
  - Name normalization
  - Filtering to snapshot players
"""
from __future__ import annotations

import pytest

from .notion_sync import (
    _normalize_name,
    _similarity,
    _detect_similar_names,
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

    def test_same_first_name_different_last_name(self):
        # "John Smith" vs "John Doe" - different last names
        sim = _similarity("John Smith", "John Doe")
        assert sim == 0.0  # Last names don't match

    def test_word_count_difference(self):
        # "John Doe" vs "John" - different word counts
        sim = _similarity("John Doe", "John")
        assert sim == 0.0  # Different word counts

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
        notion_names = ["John Doe", "Jane Smith"]
        snapshot_names = ["John Doe", "Jane Smith"]
        result = _detect_similar_names(notion_names, snapshot_names)
        assert result == []

    def test_detects_similar_pair(self):
        notion_names = ["John Doe"]
        snapshot_names = ["John D."]
        result = _detect_similar_names(notion_names, snapshot_names)
        assert len(result) == 1
        assert result[0]["notion"] == "John Doe"
        assert result[0]["snapshot"] == "John D."
        assert result[0]["similarity"] >= 0.75

    def test_skips_exact_matches(self):
        notion_names = ["John Doe"]
        snapshot_names = ["John Doe"]
        result = _detect_similar_names(notion_names, snapshot_names)
        assert result == []

    def test_skips_case_insensitive_exact_matches(self):
        notion_names = ["John Doe"]
        snapshot_names = ["john doe"]
        result = _detect_similar_names(notion_names, snapshot_names)
        assert result == []

    def test_respects_threshold(self):
        notion_names = ["John Doe"]
        snapshot_names = ["Jane Smith"]
        # Default threshold is 0.75, these names are very different
        result = _detect_similar_names(notion_names, snapshot_names, threshold=0.75)
        assert result == []

    def test_custom_threshold(self):
        notion_names = ["John Doe"]
        snapshot_names = ["John D."]
        # "John Doe" vs "John D." matches (D is prefix of Doe), so it should be found
        result = _detect_similar_names(notion_names, snapshot_names, threshold=0.99)
        assert len(result) == 1
        assert result[0]["similarity"] == 1.0

    def test_multiple_matches(self):
        # Note: "John Doe" vs "John Doe Jr" won't match because word counts differ
        # Let's use names with same word count
        notion_names = ["John Doe", "Jane Smith"]
        snapshot_names = ["John D.", "Jane S."]
        result = _detect_similar_names(notion_names, snapshot_names)
        assert len(result) == 2

    def test_sorted_by_similarity(self):
        notion_names = ["John Doe", "Jane Smith"]
        snapshot_names = ["John D.", "Jane S."]
        result = _detect_similar_names(notion_names, snapshot_names)
        # Should be sorted by similarity descending (both are 1.0)
        assert result[0]["similarity"] >= result[1]["similarity"]

    def test_empty_lists(self):
        result = _detect_similar_names([], [])
        assert result == []

    def test_empty_notion(self):
        result = _detect_similar_names([], ["John Doe"])
        assert result == []

    def test_empty_snapshot(self):
        result = _detect_similar_names(["John Doe"], [])
        assert result == []