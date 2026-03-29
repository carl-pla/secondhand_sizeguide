from pathlib import Path
import json

BASE_DIR    = Path(__file__).parent.parent
SECRETS_DIR = BASE_DIR / "dashboard" / "secrets" 
RESULTS = BASE_DIR / "dashboard" / "secrets" / "results"
SECRETS_DIR.mkdir(exist_ok=True)

CONFIG_FILE       = SECRETS_DIR / "config.json"
ERGEBNISSE_FILE   = RESULTS / "vinted_ergebnisse.json"
EMPFEHLUNGEN_FILE = RESULTS / "vinted_empfehlungen.json"

# ─────────────────────────────────────────────
#  LOOKUP-TABELLEN
# ─────────────────────────────────────────────
VINTED_GROESSEN = {
    "XS / 34": "205", "S / 36": "206", "M / 38": "207",
    "L / 40": "208", "XL / 42": "209", "XXL / 44": "210",
}
OLLAMA_MODELLE = ["llama3", "mistral", "gemma3", "phi4", "llama3.2", "mistral-nemo"]
STIL_OPTIONEN  = ["Vintage", "Retro", "Y2K", "Streetwear", "Minimalistisch", "Sportlich", "Boho", "Grunge"]
ZUSTAND_OPTIONEN = ["Neu mit Etikett", "Neu ohne Etikett", "Sehr gut", "Gut", "Befriedigend"]

# ─────────────────────────────────────────────
#  DEFAULT-CONFIG
# ─────────────────────────────────────────────
DEFAULT_CONFIG = {
    "groesse": "M / 38",
    "stile": ["Vintage", "Retro"],
    "max_preis": 50,
    "min_zustand": "Gut",
    "suchbegriffe": ["vintage", "retro 90s", "y2k"],
    "eigene_masse": {"brust": 88, "taille": 70, "huefte": 96, "schulter": 38,
                     "laenge_oberteil": 60, "innennaht": 78},
    "ollama_url": "http://localhost:11435/api/generate",
    "ollama_modell": "llama3",
    "max_artikel_pro_suche": 5,
    "max_suchen": 2,
    "pause_zwischen_artikeln": [4, 7],
    "pause_zwischen_suchen": [6, 10],
}

# ─────────────────────────────────────────────
#  LADEN & SPEICHERN
# ─────────────────────────────────────────────

# config_defaults.py — am Ende hinzufügen
def lade_config(config_path: Path | str = CONFIG_FILE) -> dict:
    p = Path(config_path)
    result = DEFAULT_CONFIG.copy() # Starte immer mit den Defaults
    
    # Prüfen: Existiert die Datei UND ist sie nicht leer (Größe > 0)?
    if p.exists():
        with open(p, "r") as f:
            gespeichert = json.load(f)
            result.update(gespeichert)  # ← überschreibe nur was vorhanden ist
    return result
        

def speichere_config(config: dict, config_path: Path | str = CONFIG_FILE):
    with open(config_path, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"✅ Datei geschrieben: {config_path} mit {config.get('max_preis')}€")
