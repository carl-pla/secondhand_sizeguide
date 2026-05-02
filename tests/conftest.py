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






