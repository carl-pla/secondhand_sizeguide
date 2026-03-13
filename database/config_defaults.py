from pathlib import Path
import json

# ─────────────────────────────────────────────
#  PFADE
# ─────────────────────────────────────────────
SECRETS_DIR = Path("secrets")
SECRETS_DIR.mkdir(exist_ok=True)
CONFIG_FILE = SECRETS_DIR / "config.json"
ERGEBNISSE_FILE = SECRETS_DIR / "vinted_ergebnisse.json"
EMPFEHLUNGEN_FILE = SECRETS_DIR / "vinted_empfehlungen.json"

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
#  LADEN / SPEICHERN
# ─────────────────────────────────────────────
def lade_config(config_path: Path | str = CONFIG_FILE) -> dict:
    p = Path(config_path)
    if p.exists():
        with open(p, "r") as f:
            print(f"✓ Config geladen: {p}")
            return json.load(f)
    print("⚠️  Keine config.json gefunden – nutze Defaults")
    return DEFAULT_CONFIG.copy()

def speichere_config(config: dict, config_path: Path | str = CONFIG_FILE):
    with open(config_path, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"✓ Config gespeichert: {config_path}")
