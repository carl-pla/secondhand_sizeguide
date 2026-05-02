import json
import pytest 
from unittest.mock import MagicMock, patch

from ai.ollama import frage_ollama, analysiere_artikel


"""
=== MATCHFIT – PYTEST SUITE ===
Abgedeckte Module:
  - ollama.py         → frage_ollama, analysiere_artikel

Alle externen Abhängigkeiten (Ollama, MongoDB, SMTP) werden gemockt,
damit die Tests ohne laufende Dienste funktionieren.
"""


# ══════════════════════════════════════════════════════════════════
#  OLLAMA – frage_ollama()
# ══════════════════════════════════════════════════════════════════

class TestFrageOllama:

    def test_gibt_antwort_zurueck_bei_erfolg(self):
        """Normalfall: Ollama antwortet mit HTTP 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "  Hier ist die Antwort  "}

        with patch("httpx.post", return_value=mock_response):
            result = frage_ollama("Test-Prompt", "http://localhost:11434/api/generate", "llama3.2:3b")

        assert result == "Hier ist die Antwort"  # strip() muss funktionieren

    def test_gibt_leerstring_zurueck_bei_http_fehler(self):
        """Ollama liefert HTTP 500 → leerer String, kein Absturz."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.post", return_value=mock_response):
            result = frage_ollama("Test", "http://localhost:11434/api/generate", "llama3.2:3b")

        assert result == ""

    def test_gibt_leerstring_zurueck_bei_netzwerkfehler(self):
        """Verbindungsabbruch → leerer String, kein Absturz."""
        with patch("httpx.post", side_effect=Exception("Connection refused")):
            result = frage_ollama("Test", "http://localhost:11434/api/generate", "llama3.2:3b")

        assert result == ""

    def test_gibt_leerstring_zurueck_ohne_modell(self):
        """Kein Modell angegeben → sofortiger Abbruch, kein HTTP-Call."""
        with patch("httpx.post") as mock_post:
            result = frage_ollama("Test", "http://localhost:11434/api/generate", "")

        assert result == ""
        mock_post.assert_not_called()  # kein unnötiger Netzwerk-Call


# ══════════════════════════════════════════════════════════════════
#  OLLAMA – analysiere_artikel()
# ══════════════════════════════════════════════════════════════════

class TestAnalysiereArtikel:

    def test_normalfall_gibt_vollstaendiges_dict_zurueck(
        self, basis_artikel, basis_config, ollama_antwort_gut
    ):
        """Gültige Ollama-Antwort → Pflichtfelder im Rückgabe-Dict vorhanden."""
        with patch("ai.ollama.frage_ollama", return_value=ollama_antwort_gut):
            result = analysiere_artikel(basis_artikel, basis_config)

        assert "url" in result
        assert "titel" in result
        assert "bewertung" in result
        assert "empfohlen" in result
        assert result["url"] == basis_artikel["url"]

    def test_json_mit_praembel_wird_korrekt_geparst(
        self, basis_artikel, basis_config, ollama_antwort_mit_praembel
    ):
        """Ollama schreibt Text vor JSON → find('{') extrahiert JSON trotzdem."""
        with patch("ai.ollama.frage_ollama", return_value=ollama_antwort_mit_praembel):
            result = analysiere_artikel(basis_artikel, basis_config)

        assert "analyse_fehler" not in result
        assert result.get("bewertung") == 8

    def test_leere_ollama_antwort_gibt_fehler_zurueck(
        self, basis_artikel, basis_config
    ):
        """Kein LLM-Output → analyse_fehler-Flag gesetzt, kein Absturz."""
        with patch("ai.ollama.frage_ollama", return_value=""):
            result = analysiere_artikel(basis_artikel, basis_config)

        assert result.get("analyse_fehler") is True

    def test_kein_json_in_antwort_gibt_fehler_zurueck(
        self, basis_artikel, basis_config
    ):
        """Ollama gibt reinen Text ohne JSON zurück → robuste Fehlerbehandlung."""
        with patch("ai.ollama.frage_ollama", return_value="Das ist kein JSON."):
            result = analysiere_artikel(basis_artikel, basis_config)

        assert result.get("analyse_fehler") is True

    # ── Deterministische Checks ──────────────────────────────────

    def test_preis_ueber_budget_wird_abgelehnt(
        self, basis_artikel, basis_config
    ):
        """Artikel kostet 80€, Budget 50€ → empfohlen=False, bewertung≤4."""
        teurer_artikel = {**basis_artikel, "preis": "80 €"}
        antwort = json.dumps({
            "masse": {}, "zustand": "Gut", "passt_groesse": True,
            "begruendung": "Schön.", "bewertung": 8, "empfohlen": True,
        })

        with patch("ai.ollama.frage_ollama", return_value=antwort):
            result = analysiere_artikel(teurer_artikel, basis_config)

        assert result["empfohlen"] is False
        assert result["bewertung"] <= 4

    def test_preis_mit_komma_wird_korrekt_geparst(
        self, basis_artikel, basis_config
    ):
        """Preis '29,99 €' muss korrekt zu 29.99 float geparst werden."""
        artikel = {**basis_artikel, "preis": "29,99 €"}
        antwort = json.dumps({
            "masse": {}, "zustand": "Gut", "passt_groesse": True,
            "begruendung": "Ok.", "bewertung": 7, "empfohlen": True,
        })

        with patch("ai.ollama.frage_ollama", return_value=antwort):
            result = analysiere_artikel(artikel, basis_config)

        # Preis 29.99€ liegt unter Budget 50€ → darf nicht abgelehnt werden
        assert "Preis" not in result.get("begruendung", "")

    def test_zustand_unter_minimum_wird_abgelehnt(
        self, basis_artikel, basis_config
    ):
        """Artikel in 'Befriedigend', Minimum 'Gut' → empfohlen=False."""
        antwort = json.dumps({
            "masse": {}, "zustand": "Befriedigend", "passt_groesse": True,
            "begruendung": "Leichte Gebrauchsspuren.", "bewertung": 7, "empfohlen": True,
        })

        with patch("ai.ollama.frage_ollama", return_value=antwort):
            result = analysiere_artikel(basis_artikel, basis_config)

        assert result["empfohlen"] is False

    def test_bewertung_unter_6_wird_abgelehnt(
        self, basis_artikel, basis_config
    ):
        """Score 5 → empfohlen=False, auch wenn Ollama 'True' gesagt hätte."""
        antwort = json.dumps({
            "masse": {}, "zustand": "Gut", "passt_groesse": False,
            "begruendung": "Passt nicht wirklich.", "bewertung": 5, "empfohlen": True,
        })

        with patch("ai.ollama.frage_ollama", return_value=antwort):
            result = analysiere_artikel(basis_artikel, basis_config)

        assert result["empfohlen"] is False

    def test_bewertung_ueber_6_wird_empfohlen(
        self, basis_artikel, basis_config
    ):
        """Score 7 → empfohlen=True, auch wenn Ollama fälschlicherweise 'False' gesagt hat.
        
        Das ist der zentrale hybride Architektur-Test:
        Python überschreibt Ollamas inkonsistentes Urteil.
        """
        antwort = json.dumps({
            "masse": {}, "zustand": "Gut", "passt_groesse": True,
            "begruendung": "Schönes Stück.", "bewertung": 7,
            "empfohlen": False,  # ← Ollama wäre zu streng
        })

        with patch("ai.ollama.frage_ollama", return_value=antwort):
            result = analysiere_artikel(basis_artikel, basis_config)

        assert result["empfohlen"] is True  # Python korrigiert Ollama

    # ── Passform-Berechnung ──────────────────────────────────────

    def test_passform_passt_gut_bei_kleiner_differenz(
        self, basis_artikel, basis_config
    ):
        """Brust-Differenz ≤4cm → 'passt gut' in passform_hinweise."""
        # Eigene Brust: 88cm, Artikel: 90cm → Diff +2cm → soll passen
        antwort = json.dumps({
            "masse":        {"brust_cm": 90, "taille_cm": None, "laenge_cm": None},
            "zustand":      "Gut", "passt_groesse": True,
            "begruendung":  "Gut.", "bewertung": 8, "empfohlen": True,
        })

        with patch("ai.ollama.frage_ollama", return_value=antwort):
            result = analysiere_artikel(basis_artikel, basis_config)

        hinweise = result.get("passform_hinweise") or []
        assert any("passt gut" in h for h in hinweise)

    def test_passform_zeigt_differenz_bei_grossem_unterschied(
        self, basis_artikel, basis_config
    ):
        """Brust-Differenz >4cm → Hinweis mit konkreter cm-Angabe."""
        # Eigene Brust: 88cm, Artikel: 100cm → Diff +12cm
        antwort = json.dumps({
            "masse":        {"brust_cm": 100, "taille_cm": None, "laenge_cm": None},
            "zustand":      "Gut", "passt_groesse": True,
            "begruendung":  "Etwas groß.", "bewertung": 7, "empfohlen": True,
        })

        with patch("ai.ollama.frage_ollama", return_value=antwort):
            result = analysiere_artikel(basis_artikel, basis_config)

        hinweise = result.get("passform_hinweise") or []
        assert any("cm" in h and "Brust" in h for h in hinweise)

    def test_keine_passform_hinweise_ohne_masse(
        self, basis_artikel, basis_config
    ):
        """Wenn Ollama keine Maße extrahiert, gibt es keine Passform-Hinweise."""
        antwort = json.dumps({
            "masse":        {"brust_cm": None, "taille_cm": None, "laenge_cm": None},
            "zustand":      "Gut", "passt_groesse": True,
            "begruendung":  "Keine Maße angegeben.", "bewertung": 7, "empfohlen": True,
        })

        with patch("ai.ollama.frage_ollama", return_value=antwort):
            result = analysiere_artikel(basis_artikel, basis_config)

        assert result.get("passform_hinweise") is None
