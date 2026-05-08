"""
=== MATCHFIT – PYTEST SUITE ===
Abgedeckte Module:
  - ollama.py         → frage_ollama, analysiere_artikel
  - newsletter.py     → generiere_html, sende_email
  - scraping_sessions → speichere_in_mongo
  - users.py          → registriere_user, deaktiviere_user, lade_alle_user
  - main.py           → Validierungslogik (Pflichtfelder, Quellen)

Alle externen Abhängigkeiten (Ollama, MongoDB, SMTP) werden gemockt,
damit die Tests ohne laufende Dienste funktionieren.
"""

import json
import pytest 
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Füge das Wurzelverzeichnis des Projekts zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent))

"""WICHTIG FÜR .ENV VARIABLEN, VON DER KERNDATEI HIER, WERDEN DIE INFOS ALS MOCK AN ALLE VERTEILT!!!"""
@pytest.fixture(autouse=True)
def mock_env_vars(request):
    """Gaukelt dem System Umgebungsvariablen vor - nicht für test_main."""
    # Skip für test_main.py um pytest capture Probleme zu vermeiden
    if "test_main" in str(request.node.fspath):
        yield
        return
    
    with patch.dict(os.environ, {
        "MAIL_FROM": "test@example.com",
        "MAIL_PASSWORD": "dummy_password",
        "MONGO_URL": "mongodb://localhost:27017",
        "OLLAMA_HOST": "http://localhost:11434"
    }):
        yield


# ══════════════════════════════════════════════════════════════════
#  FIXTURES – Wiederverwendbare Testdaten
# ══════════════════════════════════════════════════════════════════

@pytest.fixture
def basis_config():
    """Minimale, gültige Konfiguration – Grundlage für alle Tests."""
    return {
        "groesse":                 "M / 38",
        "kategorie":               "Herren Jacken & Mäntel",
        "stile":                   ["Vintage", "Retro"],
        "max_preis":               50,
        "min_zustand":             "Gut",
        "eigene_masse":            {"brust": 88, "taille": 70, "huefte": 96,
                                    "schulter": 38, "laenge_oberteil": 60, "innennaht": 78},
        "ollama_url":              "http://localhost:11434/api/generate",
        "ollama_modell":           "llama3.2:3b",
        "max_artikel_pro_suche":   5,
        "max_suchen":              2,
        "pause_zwischen_artikeln": [2, 4],
        "pause_zwischen_suchen":   [3, 6],
        "user_email":              "test@example.com",
        "quelle":                  "vinted",
    }


@pytest.fixture
def basis_artikel():
    """Ein typischer gescrapter Artikel."""
    return {
        "url":          "https://www.vinted.de/items/123",
        "titel":        "Vintage Levi's Jacke 90er",
        "preis":        "35 €",
        "beschreibung": "Tolle Vintage-Jacke, Größe M, Brust 90cm, Taille 72cm. Kaum getragen.",
    }


@pytest.fixture
def ollama_antwort_gut():
    """Beispiel einer guten, validen Ollama-JSON-Antwort."""
    return json.dumps({
        "masse":        {"brust_cm": 90, "taille_cm": 72, "laenge_cm": 62},
        "zustand":      "Gut",
        "passt_groesse": True,
        "begruendung":  "Stil passt perfekt, Maße nahezu ideal.",
        "bewertung":    8,
        "empfohlen":    True,
    })


@pytest.fixture
def ollama_antwort_mit_praembel(ollama_antwort_gut):
    """Ollama antwortet manchmal mit Text vor dem JSON – realer Fehlerfall."""
    return f"Hier ist meine Analyse:\n\n{ollama_antwort_gut}\n\nIch hoffe das hilft!"


@pytest.fixture
def beispiel_empfehlungen():
    """Zwei fertig analysierte, empfohlene Artikel für Newsletter-Tests."""
    return [
        {
            "url":         "https://vinted.de/items/1",
            "titel":       "Vintage Levi's Jacke",
            "preis":       "35 €",
            "bewertung":   8,
            "empfohlen":   True,
            "begruendung": "Passt gut.",
        },
        {
            "url":         "https://vinted.de/items/2",
            "titel":       "Retro Wollmantel",
            "preis":       "45 €",
            "bewertung":   7,
            "empfohlen":   True,
            "begruendung": "Guter Zustand.",
        },
    ]


@pytest.fixture
def basis_artikel_ebay():
    """Ein typischer eBay-Artikel als rohe API-Antwort. Enthält nur relevante Felder."""
    return {
        "itemId": "v1|388630721336|0",
        "title": "Bermuda Gr. 48",
        "shortDescription": "Schöne Freizeithose. Nichtraucherhaushalt.",
        "price": {
            "value": "3.00",
            "currency": "EUR"
        },
        "condition": "Gebraucht - Gut",
        "conditionId": "3000",
        "localizedAspects": [
            {"type": "STRING", "name": "Abteilung",      "value": "Herren"},
            {"type": "STRING", "name": "Stil",            "value": "Chino"},
            {"type": "STRING", "name": "Größenkategorie", "value": "Normalgröße"},
            {"type": "STRING", "name": "Besonderheiten",  "value": "Taschen"},
            {"type": "STRING", "name": "Passform",        "value": "Regular"},
            {"type": "STRING", "name": "Anlass",          "value": "Freizeit"},
            {"type": "STRING", "name": "Material",        "value": "Baumwolle"},
            {"type": "STRING", "name": "Gewebeart",       "value": "Tweed"},
            {"type": "STRING", "name": "Größe",           "value": "48"},
            {"type": "STRING", "name": "Marke",           "value": "markenlos"},
            {"type": "STRING", "name": "Farbe",           "value": "Blau"},
            {"type": "STRING", "name": "Bundfalte",       "value": "Ohne Bundfalte"},
            {"type": "STRING", "name": "Thema",           "value": "Urlaub"},
            {"type": "STRING", "name": "Muster",          "value": "Ohne Muster"},
        ],
        "itemWebUrl": "https://www.ebay.de/itm/388630721336",
        "description": "<p dir=\"ltr\">Schöne Freizeithose.</p><br><p dir=\"ltr\">Nichtraucherhaushalt.</p>",
    }


# ══════════════════════════════════════════════════════════════════
#  HABILLEUR-FIXTURES – Testdaten für Habilleur Jean Tests
# ══════════════════════════════════════════════════════════════════

@pytest.fixture
def habilleur_config():
    """Habilleur Jean spezifische Konfiguration."""
    return {
        "groesse":                 "M",
        "kategorie":               "Jacket",
        "max_preis":               150,
        "max_artikel_pro_suche":   10,
        "min_zustand":             "Sehr gut",
        "habilleur_masse":         {
            "schulterbreite": 46,
            "aermellaenge": 68,
            "jackenlaenge": 75,
            "achselbreite": 55,
            "jacke_taillenweite": 52,
            "hose_taillenweite": 50,
            "gabelhoehe": 30,
            "beinoeffnung": 26,
            "hosenlaenge": 110,
        },
        "ollama_url":              "http://localhost:11434/api/generate",
        "ollama_modell":           "llama3.2:3b",
    }


@pytest.fixture
def habilleur_beschreibung_deutsch():
    """Vollständige Habilleur-Beschreibung mit Maßen auf Deutsch."""
    return """
    Habilleur Jean Anzug Größe M
    
    Maße der Jacke:
    Schulterbreite (gemessen über die Rückseite der Jacke, Naht zu Naht): 44 cm
    Ärmellänge: 58 cm + 3 cm zur Erweiterung
    Jackenlänge: 72 cm
    Achselbreite: 52 cm
    Taillenweite: 52 cm
    
    Hosenmaße:
    Taillenweite: 44 cm + 3 cm
    Gabelhöhe: 29 cm
    Beinöffnung: 24 cm
    Hosenlänge: 98 cm + 10 cm
    
    Material: 100% Baumwolle
    Zustand: Sehr guter Zustand, kaum getragen
    """


@pytest.fixture
def habilleur_beschreibung_franzoesisch():
    """Habilleur-Beschreibung mit Maßen auf Französisch."""
    return """
    Habilleur Costume Taille M
    
    Mesures de la veste:
    Largeur épaule: 44 cm
    Longueur manche: 63cm +3 cm
    Longueur veste: 72 cm
    Largeur aisselle: 52 cm
    Largeur taille: 50 cm
    
    Mesure du pantalon:
    Largeur au niveau de la taille: 45cm
    Hauteur de fourche: 28 cm
    Ouverture de jambe: 22 cm
    Longueur du pantalon: 98 cm +7cm
    """


@pytest.fixture
def habilleur_beschreibung_englisch():
    """Habilleur-Beschreibung mit Maßen auf Englisch."""
    return """
    Habilleur Jean Suit Size M
    
    Jacket measurements:
    shoulder width: 46 cm
    sleeve length: 60 cm + 2 cm
    jacket length: 74 cm
    armpit width: 54 cm
    waist width: 52 cm
    
    Trouser measurements:
    trouser waist: 48 cm + 2 cm
    rise: 30 cm
    leg opening: 26 cm
    trouser length: 102 cm + 8 cm
    """


@pytest.fixture
def habilleur_beschreibung_unvollstaendig():
    """Habilleur-Beschreibung mit fehlenden Maßen."""
    return """
    Habilleur Jean Anzug Größe M
    
    Maße der Jacke:
    Schulterbreite: 44 cm
    Ärmellänge: 58 cm + 3 cm
    
    Hosenmaße:
    Gabelhöhe: 29 cm
    (Übrige Maße nicht vorhanden)
    """


@pytest.fixture
def habilleur_artikel():
    """Ein typischer Habilleur-Artikel."""
    return {
        "url": "https://habilleurjean.com/de/products/anzug-m-vintage",
        "titel": "Vintage Habilleur Jean Anzug Größe M",
        "preis": "89 €",
        "kategorie": "Jacket",
        "beschreibung": """
        Schöner Habilleur Jean Anzug aus den 90ern.
        
        Maße der Jacke:
        Schulterbreite: 46 cm
        Ärmellänge: 65 cm + 2 cm
        Jackenlänge: 75 cm
        Achselbreite: 55 cm
        Taillenweite: 52 cm
        
        Hosenmaße:
        Taillenweite: 50 cm + 1 cm
        Gabelhöhe: 30 cm
        Beinöffnung: 26 cm
        Hosenlänge: 108 cm + 2 cm
        """,
        "material": "100% Wolle",
        "zustand": "Sehr guter Zustand"
    }


@pytest.fixture
def habilleur_html_mock():
    """Mock HTML für Habilleur-Produktseite."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Habilleur Jean Anzug</title></head>
    <body>
    <div class="product-item" data-product-item="1">
        <h2>Vintage Anzug Größe M</h2>
        <a href="/de/products/anzug-m-vintage">Link</a>
        <span class="price">89,50 EUR</span>
    </div>
    <div class="product-item" data-product-item="2">
        <h3>Cashmere Mantel Größe L</h3>
        <a href="/de/products/mantel-l-cashmere">Link</a>
        <div class="price">156,00 EUR</div>
    </div>
    <div class="product-card" class="product">
        <a href="/de/products/jacke-m">Jacke Größe M</a>
        <span class="product-price">120 EUR</span>
    </div>
    </body>
    </html>
    """