# app/constants.py
import json
from pathlib import Path

# Définition des chemins relatifs
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

def load_json_data(filename: str, default: dict) -> dict:
    """Charge un fichier JSON depuis app/data/ ou retourne le défaut."""
    file_path = DATA_DIR / filename
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

# Chargement des données dynamiques
HARDWARE_DATA = load_json_data("hardware.json", {})
DEFAULT_GRID_INTENSITY = load_json_data("regions.json", {})

# --- Constants ---
DEFAULT_PUE = 1.2           # Cloud efficient (STD)
DEFAULT_LIFESPAN = 4.0      # Durée de vie serveur (ans) (STD)
HOURS_PER_YEAR = 8760