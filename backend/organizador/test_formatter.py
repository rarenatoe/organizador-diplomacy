"""Tests for formatter.py functionality."""

from backend.organizador.formatter import format_copypaste_from_dict, translate_country
from backend.organizador.models import DraftPlayer, DraftResult, DraftTable


class TestCountryTranslation:
    """Test country name translation functionality."""
    
    def test_translate_country_valid_countries(self):
        """Test translation of valid country names."""
        assert translate_country("England") == "Inglaterra"
        assert translate_country("France") == "Francia"
        assert translate_country("Germany") == "Alemania"
        assert translate_country("Italy") == "Italia"
        assert translate_country("Austria") == "Austria"
        assert translate_country("Russia") == "Rusia"
        assert translate_country("Turkey") == "Turquía"
    
    def test_translate_country_invalid_country(self):
        """Test that invalid country names are returned as-is."""
        assert translate_country("InvalidCountry") == "InvalidCountry"
        assert translate_country("Spain") == "Spain"
    
    def test_translate_country_none_and_empty(self):
        """Test handling of None and empty strings."""
        assert translate_country("") == ""
        assert translate_country("") == ""
        assert translate_country("   ") == "   "


class TestCopypasteFormatting:
    """Test copypaste text formatting with country translations."""
    
    def test_format_copypaste_with_countries(self):
        """Test copypaste formatting includes translated country names."""
        result_dict = {
            "tables": [
                {
                    "table_number": 1,
                    "gm": {"name": "GameMaster1"},
                    "players": [
                        {"name": "Alice", "country": "England"},
                        {"name": "Bob", "country": "France"},
                        {"name": "Charlie", "country": ""},
                    ]
                }
            ],
            "waitlist_players": []
        }
        
        result = format_copypaste_from_dict(result_dict)
        
        # Check that country names are translated
        assert "Alice (Inglaterra)" in result
        assert "Bob (Francia)" in result
        assert "Charlie" in result  # No country
        assert "Partida 1  |  GM: GameMaster1" in result
    
    def test_format_copypaste_without_gm(self):
        """Test copypaste formatting without a GM."""
        result_dict = {
            "tables": [
                {
                    "table_number": 1,
                    "gm": None,
                    "players": [
                        {"name": "Alice", "country": "Germany"},
                    ]
                }
            ],
            "waitlist_players": []
        }
        
        result = format_copypaste_from_dict(result_dict)
        assert "Partida 1" in result
        assert "Alice (Alemania)" in result
        assert "GM:" not in result
    
    def test_format_copypaste_with_waiting_list(self):
        """Test copypaste formatting includes waiting list."""
        result_dict = {
            "tables": [],
            "waitlist_players": [
                {"name": "Player1"},
                {"name": "Player2"},
                {"name": "Player1"},  # Duplicate, should be deduped
            ]
        }
        
        result = format_copypaste_from_dict(result_dict)
        lines = result.split("\n")
        
        assert "Lista de espera:" in result
        assert "- Player1" in result
        assert "- Player2" in result
        # Check duplicates are removed
        player1_count = sum(1 for line in lines if "Player1" in line)
        assert player1_count == 1


class TestFormatterIntegration:
    """Test integration with ResultadoPartidas model."""
    
    def test_format_copypaste_with_country_reason_footnotes(self):
        """Test that country_reason appears as footnotes with asterisks."""
        result_dict = {
            "tables": [
                {
                    "table_number": 1,
                    "gm": {"name": "GameMaster1"},
                    "players": [
                        {"name": "Alice", "country": "England", "country_reason": "Test reason 1"},
                        {"name": "Bob", "country": "France", "country_reason": "Test reason 1"},  # Same reason
                        {"name": "Charlie", "country": "Germany", "country_reason": "Different reason"},
                        {"name": "Dave", "country": "Italy"},  # No reason
                    ]
                }
            ],
            "waitlist_players": []
        }
        
        result = format_copypaste_from_dict(result_dict)
        lines = result.split("\n")
        
        # Check footnote markers on player lines
        assert "Alice (Inglaterra*)" in result
        assert "Bob (Francia*)" in result  # Same asterisk as Alice
        assert "Charlie (Alemania**)" in result  # Double asterisk
        assert "Dave (Italia)" in result  # No asterisk
        
        # Check footnotes appear at the bottom
        assert "* Test reason 1" in result
        assert "** Different reason" in result
        
        # Verify footnote comes after player list for the mesa
        alice_line = next(i for i, line in enumerate(lines) if "Alice" in line)
        footnote_line = next(i for i, line in enumerate(lines) if "* Test reason 1" in line)
        assert footnote_line > alice_line, "Footnote should appear after player listing"

    def test_draft_result_with_translation(self):
        """Test that DraftResult.to_dict() works with translation."""
        # Create test data
        player1 = DraftPlayer(
            name="Alice",
            priority="alta",
            desired_games=1,
            gm_games=0,
            c_england=1,
            c_france=0,
            c_germany=0,
            c_italy=0,
            c_austria=0,
            c_russia=0,
            c_turkey=0,
            country="England",
            experience="Nuevo",
            games_this_year=1,
        )
        
        table = DraftTable(table_number=1, gm=None, players=[player1])
        result = DraftResult(
            tables=[table],
            waitlist_players=[],
            attempts_used=1,
            theoretical_minimum=0,
        )
        
        # Test that the model_dump() method works
        result_dict = result.model_dump()
        assert result_dict["tables"][0]["players"][0]["country"] == "England"
        
        # Test that formatting translates it
        formatted = format_copypaste_from_dict(result_dict)
        assert "Alice (Inglaterra)" in formatted
