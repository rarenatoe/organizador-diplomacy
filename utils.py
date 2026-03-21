"""utils.py – Utilidades compartidas entre organizador.py y notion_sync.py."""
from pathlib import Path

# Directorio raíz del proyecto (donde viven los CSVs numerados).
DIRECTORIO: Path = Path(__file__).parent


def ultimo_csv(directorio: Path = DIRECTORIO) -> Path | None:
    """Retorna el jugadores_NNNN.csv con el número más alto, o None si no existe ninguno."""
    archivos = sorted(directorio.glob("jugadores_[0-9][0-9][0-9][0-9].csv"))
    return archivos[-1] if archivos else None


def siguiente_csv(directorio: Path = DIRECTORIO) -> Path:
    """Retorna la ruta del próximo jugadores_NNNN.csv (sin crearlo)."""
    ultimo = ultimo_csv(directorio)
    if ultimo is None:
        return directorio / "jugadores_0001.csv"
    num = int(ultimo.stem.split("_")[1])
    return directorio / f"jugadores_{num + 1:04d}.csv"
