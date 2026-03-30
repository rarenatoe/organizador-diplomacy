"""Tests for formatter.py functionality."""

from backend.organizador.formatter import formatear_copypaste_from_dict, translate_country
from backend.organizador.models import Jugador, Mesa, ResultadoPartidas


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
    
    def test_formatear_copypaste_with_countries(self):
        """Test copypaste formatting includes translated country names."""
        resultado_dict = {
            "mesas": [
                {
                    "numero": 1,
                    "gm": {"nombre": "GameMaster1"},
                    "jugadores": [
                        {"nombre": "Alice", "pais": "England"},
                        {"nombre": "Bob", "pais": "France"},
                        {"nombre": "Charlie", "pais": ""},
                    ]
                }
            ],
            "tickets_sobrantes": []
        }
        
        result = formatear_copypaste_from_dict(resultado_dict)
        
        # Check that country names are translated
        assert "Alice (Inglaterra)" in result
        assert "Bob (Francia)" in result
        assert "Charlie" in result  # No country
        assert "Partida 1  |  GM: GameMaster1" in result
    
    def test_formatear_copypaste_without_gm(self):
        """Test copypaste formatting without a GM."""
        resultado_dict = {
            "mesas": [
                {
                    "numero": 1,
                    "gm": None,
                    "jugadores": [
                        {"nombre": "Alice", "pais": "Germany"},
                    ]
                }
            ],
            "tickets_sobrantes": []
        }
        
        result = formatear_copypaste_from_dict(resultado_dict)
        assert "Partida 1" in result
        assert "Alice (Alemania)" in result
        assert "GM:" not in result
    
    def test_formatear_copypaste_with_waiting_list(self):
        """Test copypaste formatting includes waiting list."""
        resultado_dict = {
            "mesas": [],
            "tickets_sobrantes": [
                {"nombre": "Player1"},
                {"nombre": "Player2"},
                {"nombre": "Player1"},  # Duplicate, should be deduped
            ]
        }
        
        result = formatear_copypaste_from_dict(resultado_dict)
        lines = result.split("\n")
        
        assert "Lista de espera:" in result
        assert "- Player1" in result
        assert "- Player2" in result
        # Check duplicates are removed
        player1_count = sum(1 for line in lines if "Player1" in line)
        assert player1_count == 1


class TestFormatterIntegration:
    """Test integration with ResultadoPartidas model."""
    
    def test_resultado_partidas_with_translation(self):
        """Test that ResultadoPartidas.to_dict() works with translation."""
        # Create test data
        jugador1 = Jugador(
            nombre="Alice",
            prioridad="alta",
            partidas_deseadas=1,
            partidas_gm=0,
            c_england=1,
            c_france=0,
            c_germany=0,
            c_italy=0,
            c_austria=0,
            c_russia=0,
            c_turkey=0,
            pais="England",
            experiencia="Nuevo",
            juegos_ano=1,
        )
        
        mesa = Mesa(numero=1, gm=None, jugadores=[jugador1])
        resultado = ResultadoPartidas(
            mesas=[mesa],
            tickets_sobrantes=[],
            intentos_usados=1,
            minimo_teorico=0,
        )
        
        # Test that the model_dump() method works
        resultado_dict = resultado.model_dump()
        assert resultado_dict["mesas"][0]["jugadores"][0]["pais"] == "England"
        
        # Test that formatting translates it
        formatted = formatear_copypaste_from_dict(resultado_dict)
        assert "Alice (Inglaterra)" in formatted
