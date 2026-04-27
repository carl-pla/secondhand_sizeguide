from pathlib import Path
import json
import os 
import streamlit as st

# 1. Versuche die URL aus den Streamlit Secrets zu laden (Cloud-Modus)
# 2. Falls nicht da, schaue in Umgebungsvariablen
# 3. Falls beides leer, nutze localhost (Lokal-Modus)
try:
    MONGO_URL = st.secrets.get("MONGO_URL") or os.getenv("MONGO_URL") or "mongodb://localhost:27017"
except:
    # Falls Streamlit nicht im Kontext läuft (z.B. Scripts, Tests)
    MONGO_URL = os.getenv("MONGO_URL") or "mongodb://localhost:27017"

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
    "XS / 34": "206", "S / 36": "207", "M / 38": "208",
    "L / 40": "209", "XL / 42": "210", "XXL / 44": "211",
}
VINTED_KATEGORIEN = {
    "Herren Alles": "2050", "Herren Anzüge & Blazer": "32","Herren Jacken & Mäntel": "1206", "Herren Hosen": "34", "Herren Jeans": "257", "Herren Shorts": "80", "Herren Nachtwäsche": "2910", "Herren Socken & Unterwäsche": "85",
    "Herren Badebekleidung": "84", "Herren Sportartikel": "30", "Herren Tops & T-Shirts": "76", "Herren Pullover & Sweater": "79", 
    "Herren Stiefel": "1233", "Herren Elegante Schuhe": "1238", "Herren Sneaker": "1242", "Herren Loafer & Bootsschuhe": "2656", "Herren Sportschuhe": "1452",
    "Herren Kopftücher": "2960", "Herren Halstücher" : "2958", "Herren Krawatten": "2956", "Herren Einstechtücher": "2957", "Herren Gürtel": "96", "Herren Handschuhe": "91", "Herren Taschen": "94", "Herren Schmuck": "95", "Herren Uhren": "97",
    "Damen Alles": "4", "Damen Pullover & Strickpullover": "13", "Damen Kleider": "10", "Damen Skorts": "5491", "Damen Jeans": "183", "Damen Shorts": "15", "Damen Bademode": "28", "Damen Jacken & Mäntel": "1037", "Damen Anzüge & Blaze": "8", "Damen Röcke": "11", "Damen Tops & T-Shirts": "12", "Damen Hosen & Leggings": "9", "Damen Unterwäsche & Nachtwäsche": "29",
    "Damen Sportschuhe": "2630", "Damen Ballerinas": "2955", "Damen Stiefel": "1049", "Damen Absatzschuhe": "543", "Damen Hausschuhe, Pantoffeln & Slipper": "215", "Damen Sneaker": "2632", "Damen Bootsschuhe & Loafer": "2954", "Damen Schnürschuhe": "2951", "Damen Sandalen": "2949",
    "Damen Taschen": "19", "Damen Halstücher": "2932", "Damen Tücher & Schals": "89", "Damen Kopftücher": "2931", "Damen Hüte und Mützen": "88", "Damen Handschuhe": "90", "Damen Schmuck": "21", "Damen Uhren": "22", "Damen Haarschmuck": "1123", "Damen Gürtel": "20"
}
HABILLEUR_GROESSEN = {
    "XS": "xs", "S": "s", "M": "m", "L": "l", "XL": "xl"
}
HABILLEUR_KATEGORIEN = {
    "Anzug": "costume", "Jacket": "veste", "Mantel": "manteau"
}

# Standard-Maße für Habilleur Anzüge (Jacke + Hose, Größe M Beispiel)
HABILLEUR_MASSE_BEISPIEL = {
    # Jackenmaße
    "schulterbreite": 46,           # Schulterbreite (Naht zu Naht)
    "aermellange": 68,              # Ärmellänge (65 + 3 Erweiterung)
    "jackenlaenge": 75,             # Jackenlänge
    "achselbreite": 55,             # Achselbreite
    "jacke_taillenweite": 52,       # Taillenweite Jacke
    # Hosenmaße
    "hose_taillenweite": 50,        # Taillenweite Hose (45 + 5)
    "gabelhoehe": 30,               # Gabelhöhe
    "beinoeffnung": 26,             # Beinöffnung
    "hosenlaenge": 110,             # Hosenlänge (103 + 7)
    # Mantelmaße
    "mantel_schulterbreite": 48,    # Mantel Schulterbreite
    "mantel_gesamtlaenge": 80,      # Mantel Gesamtlänge
    "mantel_aermellange": 62,       # Mantel Ärmellänge
    "mantel_achselbreite": 57,       # Mantel Achselbreite
    "mantel_taillenweite": 54,       # Mantel Taillenweite
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
    "quelle": "vinted",  # oder "habilleur"
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
