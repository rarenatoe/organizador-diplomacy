"""utils.py – Shared path constants."""
from pathlib import Path

# Directory that contains data/diplomacy.db and (during migration) legacy files.
# Go up one level from backend/ to find data/ at project root
DIRECTORIO: Path = Path(__file__).parent.parent / "data"
