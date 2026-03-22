"""utils.py – Shared path constants."""
from pathlib import Path

# Directory that contains data/diplomacy.db and (during migration) legacy files.
DIRECTORIO: Path = Path(__file__).parent / "data"
