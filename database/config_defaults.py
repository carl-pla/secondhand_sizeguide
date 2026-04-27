from pathlib import Path
import json
import os 
import streamlit as st

# 1. Versuche die URL aus den Streamlit Secrets zu laden (Cloud-Modus)
# 2. Falls nicht da, schaue in Umgebungsvariablen
# 3. Falls beides leer, nutze localhost (Lokal-Modus)
MONGO_URL = st.secrets.get("MONGO_URL") or os.getenv("MONGO_URL") or "mongodb://localhost:27017"

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
category_ids_ebay = {
    "Kleidung & Accessoires": "11450",  # allgemeine ID (übergeordnet)

    "Herren Alles": "260012",
    "Herren Anzüge & Blazer": "3001",
    "Herren Badebekleidung": "15690",
    "Herren Fitnessmode": "185099",
    "Herren Hosen": "57989",
    "Herren Jacken, Mäntel und Westen": "57988",
    "Herren Jeans": "11483",
    "Herren Nachtwäsche": "11510",
    "Herren Pullover & Strick": "11484",
    "Herren Shirts und Hemden": "185100",
    "Herren Shorts und Bermudas": "15689",
    "Herren Unterwäsche": "11507",
    "Herren Stiefel": "11498",
    "Herren Business-Schuhe": "53120",
    "Herren Sneaker": "15709",
    "Herren Halbschuhe": "24087",
    "Herren Hüte und Mützen": "52365",
    "Herren Schals & Tücher": "52382",
    "Herren Krawatten & Fliegen": "15662",
    "Herren Gürtel": "2993",
    "Herren Handschuhe und Fäustlinge": "2994",
    "Herren Taschen": "52357",
    "Herren Schmuck": "10290",
    "Herren Armbanduhren & Taschenuhren": "260325",

    "Damen Alles": "260010",
    "Damen Pullover & Strickpullover": "63866",
    "Damen Kleider": "63861",
    "Damen Jeans": "11554",
    "Damen Shorts & Bermudas": "11555",
    "Damen Bademode": "63867",
    "Damen Jacken, Mäntel und Westen": "63862",
    "Damen Anzüge & Anzugteile": "63865",
    "Damen Röcke": "63864",
    "Damen Blusen, Tops & Shirts": "53159",
    "Damen Hosen & Leggings": "169001",
    "Damen Unterwäsche & Nachtwäsche": "11514",
    "Damen Stiefel & Stiefeletten": "53557",
    "Damen Absatzschuhe": "55793",
    "Damen Hausschuhe": "11632",
    "Damen Sneaker": "95672",
    "Damen Halbschuhe & Ballerinas": "45333",
    "Damen Sandalen": "62107",
    "Damen Taschen": "169291",
    "Damen Schals & Tücher": "45238",
    "Damen Hüte und Mützen": "45230",
    "Damen Handschuhe & Fäustlinge": "105559",
    "Damen Modeschmuck": "10968",
    "Damen Armbanduhren & Taschenuhren": "260325",
    "Damen Kopfschmuck & Fascinators": "168998",
    "Damen Gürtel": "3003"
}

condition_ids_ebay = {
    "Neu mit Etikett": "1000",
    "Neu ohne Etikett": "1000|1500|1750",
    "Sehr gut": "1000|1500|1750|2000|2010|2020|2500|2750|2990|3000|4000",
    "Gut": "1000|1500|1750|2000|2010|2020|2030|2500|2750|2990|3000|3010|4000|5000",
    "Befriedigend": "1000|1500|1750|2000|2010|2020|2030|2500|2750|2990|3000|3010|4000|5000|6000"
}

VINTED_GROESSEN = {
    "XS / 34": "206", "S / 36": "207", "M / 38": "208",
    "L / 40": "209", "XL / 42": "210", "XXL / 44": "211",
}
VINTED_KATEGORIEN = {
    "Herren Alles": "2050", "Herren Anzüge & Blazer": "32","Herren Jacken & Mäntel": "1206", "Herren Hosen": "34", "Herren Jeans": "257", "Herren Shorts": "80", "Herren Nachtwäsche": "2910", "Herren Socken & Unterwäsche": "85",
    "Herren Badebekleidung": "84", "Herren Sportartikel": "30", "Herren Tops & T-Shirts": "76", "Herren Pullover & Sweater": "79", 
    "Herren Stiefel": "1233", "Herren Elegante Schuhe": "1238", "Herren Sneaker": "1242", "Herren Loafer & Bootsschuhe": "2656", "Herren Sportschuhe": "1452",
    "Herren Kopftücher": "2960", "Herren Halstücher" : "2958", "Herren Krawatten": "2956", "Herren Einstechtücher": "2957", "Herren Gürtel": "96", "Herren Hanschuhe": "91", "Herren Taschen": "94", "Herren Schmuck": "95", "Herren Uhren": "97",
    "Damen Alles": "4", "Damen Pullover & Strickpullover": "13", "Damen Kleider": "10", "Damen Skorts": "5491", "Damen Jeans": "183", "Damen Shorts": "15", "Damen Bademode": "28", "Damen Jacken & Mäntel": "1037", "Damen Anzüge & Blaze": "8", "Damen Röcke": "11", "Damen Tops & T-Shirts": "12", "Damen Hosen & Leggings": "9", "Damen Unterwäsche & Nachtwäsche": "29",
    "Damen Sportschuhe": "2630", "Damen Ballerinas": "2955", "Damen Stiefel": "1049", "Damen Absatzschuhe": "543", "Damen Hausschuhe, Pantoffeln & Slipper": "215", "Damen Sneaker": "2632", "Damen Bootsschuhe & Loafer": "2954", "Damen Schnürschuhe": "2951", "Damen Sandalen": "2949",
    "Damen Taschen": "19", "Damen Halstücher": "2932", "Damen Tücher & Schals": "89", "Damen Kopftücher": "2931", "Damen Hüte und Mützen": "88", "Damen Handschuhe": "90", "Damen Schmuck": "21", "Damen Uhren": "22", "Damen Haarschmuck": "1123", "Damen Gürtel": "20"
}
OLLAMA_MODELLE = ["llama3.2:3b", "llama3"]
STIL_OPTIONEN  = ["Menswear", "Vintage", "Retro", "Y2K", "Streetwear", "Minimalistisch", "Sportlich", "Boho", "Grunge"]
ZUSTAND_RANG = {
    "Neu mit Etikett": 5, "Neu ohne Etikett": 4,
    "Sehr gut": 3, "Gut": 2, "Befriedigend": 1,
}

ZUSTAND_OPTIONEN = list(ZUSTAND_RANG.keys())

# ─────────────────────────────────────────────
#  DEFAULT-CONFIG
# ─────────────────────────────────────────────
DEFAULT_CONFIG = {
    "user_email": "max@example.com",
    "groesse": "M / 38",
    "kategorie": "Herren Jacken & Mäntel",
    "stile": ["Vintage", "Retro"],
    "max_preis": 50,
    "min_zustand": "Gut",
    "eigene_masse": {"brust": 88, "taille": 70, "huefte": 96, "schulter": 38,
                     "laenge_oberteil": 60, "innennaht": 78},
    "ollama_url": "http://host.docker.internal:11434",
    "ollama_modell": "llama3.2:3b",
    "max_artikel_pro_suche": 3,
    "max_suchen": 1,
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
        with open(p, "r", encoding='utf-8') as f:
            gespeichert = json.load(f)
            result.update(gespeichert)  # ← überschreibe nur was vorhanden ist
    return result
        

def speichere_config(config: dict, config_path: Path | str = CONFIG_FILE):
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"✅ Datei geschrieben: {config_path} mit {config.get('max_preis')}€")
