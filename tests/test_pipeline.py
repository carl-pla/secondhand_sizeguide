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
from unittest.mock import MagicMock, patch, call
from datetime import datetime


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
            from ai.ollama import frage_ollama
            result = frage_ollama("Test-Prompt", "http://localhost:11434/api/generate", "llama3.2:3b")

        assert result == "Hier ist die Antwort"  # strip() muss funktionieren

    def test_gibt_leerstring_zurueck_bei_http_fehler(self):
        """Ollama liefert HTTP 500 → leerer String, kein Absturz."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.post", return_value=mock_response):
            from ai.ollama import frage_ollama
            result = frage_ollama("Test", "http://localhost:11434/api/generate", "llama3.2:3b")

        assert result == ""

    def test_gibt_leerstring_zurueck_bei_netzwerkfehler(self):
        """Verbindungsabbruch → leerer String, kein Absturz."""
        with patch("httpx.post", side_effect=Exception("Connection refused")):
            from ai.ollama import frage_ollama
            result = frage_ollama("Test", "http://localhost:11434/api/generate", "llama3.2:3b")

        assert result == ""

    def test_gibt_leerstring_zurueck_ohne_modell(self):
        """Kein Modell angegeben → sofortiger Abbruch, kein HTTP-Call."""
        with patch("httpx.post") as mock_post:
            from ai.ollama import frage_ollama
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
            from ai.ollama import analysiere_artikel
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
            from ai.ollama import analysiere_artikel
            result = analysiere_artikel(basis_artikel, basis_config)

        assert "analyse_fehler" not in result
        assert result.get("bewertung") == 8

    def test_leere_ollama_antwort_gibt_fehler_zurueck(
        self, basis_artikel, basis_config
    ):
        """Kein LLM-Output → analyse_fehler-Flag gesetzt, kein Absturz."""
        with patch("ai.ollama.frage_ollama", return_value=""):
            from ai.ollama import analysiere_artikel
            result = analysiere_artikel(basis_artikel, basis_config)

        assert result.get("analyse_fehler") is True

    def test_kein_json_in_antwort_gibt_fehler_zurueck(
        self, basis_artikel, basis_config
    ):
        """Ollama gibt reinen Text ohne JSON zurück → robuste Fehlerbehandlung."""
        with patch("ai.ollama.frage_ollama", return_value="Das ist kein JSON."):
            from ai.ollama import analysiere_artikel
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
            from ai.ollama import analysiere_artikel
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
            from ai.ollama import analysiere_artikel
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
            from ai.ollama import analysiere_artikel
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
            from ai.ollama import analysiere_artikel
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
            from ai.ollama import analysiere_artikel
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
            from ai.ollama import analysiere_artikel
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
            from ai.ollama import analysiere_artikel
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
            from ai.ollama import analysiere_artikel
            result = analysiere_artikel(basis_artikel, basis_config)

        assert result.get("passform_hinweise") is None


# ══════════════════════════════════════════════════════════════════
#  NEWSLETTER – generiere_html()
# ══════════════════════════════════════════════════════════════════

class TestGeneriereHtml:

    def test_gibt_fallback_text_zurueck_bei_leerer_liste(self):
        """Keine Artikel → verständliche Meldung, kein Absturz."""
        from notification.newsletter import generiere_html
        result = generiere_html([])
        assert "keine" in result.lower() or "nicht" in result.lower()

    def test_html_enthaelt_artikeltitel(self, beispiel_empfehlungen):
        """Titel der Artikel müssen im generierten HTML auftauchen."""
        from notification.newsletter import generiere_html
        result = generiere_html(beispiel_empfehlungen)

        assert "Vintage Levi's Jacke" in result
        assert "Retro Wollmantel" in result

    def test_html_enthaelt_preise(self, beispiel_empfehlungen):
        """Preise müssen im Newsletter sichtbar sein."""
        from notification.newsletter import generiere_html
        result = generiere_html(beispiel_empfehlungen)

        assert "35 €" in result
        assert "45 €" in result

    def test_html_enthaelt_links(self, beispiel_empfehlungen):
        """Artikel-URLs müssen als anklickbare Links vorhanden sein."""
        from notification.newsletter import generiere_html
        result = generiere_html(beispiel_empfehlungen)

        assert "https://vinted.de/items/1" in result

    def test_maximal_10_artikel_im_newsletter(self):
        """Auch bei 20 Artikeln dürfen maximal MAX_ARTIKEL (10) angezeigt werden."""
        from notification.newsletter import generiere_html, MAX_ARTIKEL
        viele_artikel = [
            {"url": f"https://vinted.de/items/{i}", "titel": f"Artikel {i}",
             "preis": f"{20+i} €", "bewertung": 7, "begruendung": "Ok."}
            for i in range(20)
        ]
        result = generiere_html(viele_artikel)

        # Der (MAX_ARTIKEL+1)-te Artikel darf nicht auftauchen
        assert f"Artikel {MAX_ARTIKEL}" not in result
        assert f"Artikel {MAX_ARTIKEL - 1}" in result

    def test_html_zeigt_gesamtanzahl_an(self, beispiel_empfehlungen):
        """HTML muss die Gesamtzahl der gefundenen Artikel nennen."""
        from notification.newsletter import generiere_html
        result = generiere_html(beispiel_empfehlungen)

        assert "2" in result  # 2 Artikel gefunden


# ══════════════════════════════════════════════════════════════════
#  NEWSLETTER – sende_email()
# ══════════════════════════════════════════════════════════════════

class TestSendeEmail:
    """
    FIX: @patch auf Modul-Attribute (MAIL_FROM, MAIL_PASSWORD) injiziert
    KEINEN Mock-Parameter in die Methode – nur @patch auf aufrufbare Objekte
    (Klassen, Funktionen) erzeugt einen Parameter.
    Reihenfolge der Parameter: bottom-up, also innerster Decorator zuerst.
    Lösung: Modul-Attribute per monkeypatch oder direkt im Test setzen,
    statt als @patch-Decorator.
    """

    def test_sendet_email_erfolgreich(self, monkeypatch):
        """Normalfall: SMTP-Verbindung klappt, E-Mail wird gesendet."""
        import newsletter
        monkeypatch.setattr(newsletter, "MAIL_FROM", "sender@example.com")
        monkeypatch.setattr(newsletter, "MAIL_PASSWORD", "test-password")

        mock_server = MagicMock()
        mock_smtp = MagicMock(return_value=mock_smtp)
        mock_smtp = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        with patch("newsletter.smtplib.SMTP", mock_smtp):
            newsletter.sende_email("<html>Test</html>", "empfaenger@example.com")

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@example.com", "test-password")
        mock_server.send_message.assert_called_once()

    def test_starttls_vor_login_aufgerufen(self, monkeypatch):
        """Kritische Reihenfolge: starttls() MUSS vor login() kommen."""
        import newsletter
        monkeypatch.setattr(newsletter, "MAIL_FROM", "sender@example.com")
        monkeypatch.setattr(newsletter, "MAIL_PASSWORD", "test-password")

        mock_server = MagicMock()
        mock_smtp = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        call_order = []
        mock_server.starttls.side_effect = lambda: call_order.append("starttls")
        mock_server.login.side_effect = lambda *a: call_order.append("login")

        with patch("newsletter.smtplib.SMTP", mock_smtp):
            newsletter.sende_email("<html>Test</html>", "empfaenger@example.com")

        assert call_order.index("starttls") < call_order.index("login"), \
            "starttls() muss VOR login() aufgerufen werden!"

    def test_smtp_fehler_wirft_keinen_absturz(self, monkeypatch):
        """SMTP-Fehler → kein unkontrollierter Absturz der Pipeline."""
        from notification.newsletter import sende_email
        monkeypatch.setattr("MAIL_FROM", "sender@example.com")
        monkeypatch.setattr("MAIL_PASSWORD", "test-password")

        with patch("newsletter.smtplib.SMTP", side_effect=Exception("Connection refused")):
            # Darf keine Exception werfen
            sende_email("<html>Test</html>", "empfaenger@example.com")


# ══════════════════════════════════════════════════════════════════
#  SCRAPING SESSION – speichere_in_mongo()
# ══════════════════════════════════════════════════════════════════

class TestSpeichereInMongo:

    @patch("database.scrapping_sessions.pymongo.MongoClient")
    def test_speichert_session_mit_empfehlungen(
        self, mock_client_class, beispiel_empfehlungen, basis_config
    ):
        """Normalfall: Empfehlungen werden als Session in MongoDB gespeichert."""
        mock_col = MagicMock()
        mock_client_class.return_value.__getitem__.return_value.__getitem__.return_value = mock_col

        from database.scraping_sessions import speichere_in_mongo
        result = speichere_in_mongo(beispiel_empfehlungen, basis_config, "test@example.com")

        mock_col.insert_one.assert_called_once()
        inserted = mock_col.insert_one.call_args[0][0]
        assert inserted["user_email"] == "test@example.com"
        assert inserted["anzahl_empfohlen"] == 2

    @patch("database.scrapping_sessions.pymongo.MongoClient")
    def test_leere_liste_speichert_nichts(self, mock_client_class, basis_config):
        """Keine Artikel → kein DB-Call, kein Absturz."""
        from database.scraping_sessions import speichere_in_mongo
        result = speichere_in_mongo([], basis_config)

        mock_client_class.assert_not_called()
        assert result is None

    @patch("database.scrapping_sessions.pymongo.MongoClient")
    def test_nur_empfohlene_werden_gespeichert(
        self, mock_client_class, basis_config
    ):
        """Nicht-empfohlene Artikel dürfen nicht in die Session."""
        mock_col = MagicMock()
        mock_client_class.return_value.__getitem__.return_value.__getitem__.return_value = mock_col

        gemischt = [
            {"url": "u1", "titel": "Gut", "preis": "20€", "empfohlen": True, "bewertung": 8},
            {"url": "u2", "titel": "Schlecht", "preis": "10€", "empfohlen": False, "bewertung": 3},
        ]

        from database.scraping_sessions import speichere_in_mongo
        speichere_in_mongo(gemischt, basis_config)

        inserted = mock_col.insert_one.call_args[0][0]
        assert inserted["anzahl_empfohlen"] == 1
        assert all(a.get("empfohlen") for a in inserted["empfehlungen"])

    @patch("database.scrapping_sessions.pymongo.MongoClient")
    def test_keine_empfohlenen_speichert_nichts(
        self, mock_client_class, basis_config
    ):
        """Liste mit Artikeln, aber keiner empfohlen → kein DB-Call."""
        nicht_empfohlen = [
            {"url": "u1", "titel": "X", "preis": "10€", "empfohlen": False},
        ]
        from database.scraping_sessions import speichere_in_mongo
        result = speichere_in_mongo(nicht_empfohlen, basis_config)

        mock_client_class.assert_not_called()
        assert result is None

    @patch("database.scrapping_sessions.pymongo.MongoClient",
           side_effect=Exception("DB offline"))
    def test_db_fehler_gibt_none_zurueck(
        self, mock_client_class, beispiel_empfehlungen, basis_config
    ):
        """Datenbankfehler → None zurück, kein Absturz."""
        from database.scraping_sessions import speichere_in_mongo
        result = speichere_in_mongo(beispiel_empfehlungen, basis_config)
        assert result is None


# ══════════════════════════════════════════════════════════════════
#  USERS – registriere_user(), lade_alle_user(), deaktiviere_user()
# ══════════════════════════════════════════════════════════════════

class TestUsers:

    def _mock_collection(self, mock_client_class, find_one_return=None):
        """Hilfsmethode: gibt eine gemockte MongoDB Collection zurück."""
        mock_col = MagicMock()
        mock_col.find_one.return_value = find_one_return
        mock_client_class.return_value.__getitem__.return_value.__getitem__.return_value = mock_col
        return mock_col

    @patch("database.users.pymongo.MongoClient")
    def test_neuer_user_wird_registriert(self, mock_client_class, basis_config):
        """User existiert noch nicht → insert_one wird aufgerufen."""
        mock_col = self._mock_collection(mock_client_class, find_one_return=None)

        from database.users import registriere_user
        result = registriere_user("neu@example.com", basis_config)

        assert result["status"] == "neu"
        assert result["email"] == "neu@example.com"
        mock_col.insert_one.assert_called_once()

    @patch("database.users.pymongo.MongoClient")
    def test_bestehender_user_wird_aktualisiert(
        self, mock_client_class, basis_config
    ):
        """User existiert bereits → update_one statt insert_one."""
        bestehend = {"email": "alt@example.com", "aktiv": True}
        mock_col = self._mock_collection(mock_client_class, find_one_return=bestehend)

        from database.users import registriere_user
        result = registriere_user("alt@example.com", basis_config)

        assert result["status"] == "updated"
        mock_col.update_one.assert_called_once()
        mock_col.insert_one.assert_not_called()

    @patch("database.users.pymongo.MongoClient")
    def test_ungueltige_email_wird_abgelehnt(self, mock_client_class, basis_config):
        """Ungültige E-Mail-Adresse → Fehlermeldung, kein DB-Call."""
        mock_col = self._mock_collection(mock_client_class)

        from database.users import registriere_user
        result = registriere_user("kein-at-zeichen", basis_config)

        assert "error" in result
        mock_col.insert_one.assert_not_called()

    @patch("database.users.pymongo.MongoClient")
    def test_user_wird_deaktiviert(self, mock_client_class):
        """Abmelden setzt aktiv=False via update_one."""
        mock_col = self._mock_collection(mock_client_class)

        from database.users import deaktiviere_user
        deaktiviere_user("test@example.com")

        mock_col.update_one.assert_called_once_with(
            {"email": "test@example.com"},
            {"$set": {"aktiv": False}}
        )

    @patch("database.users.pymongo.MongoClient")
    def test_lade_alle_user_gibt_liste_zurueck(self, mock_client_class):
        """Aktive User werden geladen, _id wird entfernt."""
        from bson import ObjectId
        mock_col = self._mock_collection(mock_client_class)
        mock_col.find.return_value = [
            {"_id": "mongo_id_1", "email": "a@example.com", "aktiv": True},
            {"_id": "mongo_id_2", "email": "b@example.com", "aktiv": True},
        ]

        from database.users import lade_alle_user
        result = lade_alle_user()

        assert len(result) == 2
        assert all("_id" not in u for u in result)  # _id muss entfernt sein
        assert result[0]["email"] == "a@example.com"


# ══════════════════════════════════════════════════════════════════
#  MAIN – Validierungslogik (ohne echtes Scraping)
# ══════════════════════════════════════════════════════════════════

class TestMainValidierung:
    """
    Testet die Pflichtfeld-Validierung in main.py, ohne Playwright zu starten.
    main() gibt bei fehlenden Pflichtfeldern None zurück.
    """

    @pytest.mark.asyncio
    async def test_fehlende_groesse_bricht_ab(self, basis_config):
        """Ohne Größe darf der Scraper nicht starten."""
        basis_config["groesse"] = ""
        with patch("httpx.get"):  # Ollama-Check überspringen
            from main import main
            result = await main(basis_config)
        assert result is None

    @pytest.mark.asyncio
    async def test_fehlendes_modell_bricht_ab(self, basis_config):
        """Ohne Ollama-Modell darf der Scraper nicht starten."""
        basis_config["ollama_modell"] = ""
        with patch("httpx.get"):
            from main import main
            result = await main(basis_config)
        assert result is None

    @pytest.mark.asyncio
    async def test_fehlende_kategorie_bricht_ab(self, basis_config):
        """Ohne Kategorie darf der Scraper nicht starten."""
        basis_config["kategorie"] = ""
        with patch("httpx.get"):
            from main import main
            result = await main(basis_config)
        assert result is None

    @pytest.mark.asyncio
    async def test_ungueltige_quelle_bricht_ab(self, basis_config):
        """Quelle darf nur 'vinted' oder 'habilleur' sein."""
        basis_config["quelle"] = "ebay"
        with patch("httpx.get"):
            from main import main
            result = await main(basis_config)
        assert result is None

    @pytest.mark.asyncio
    async def test_ollama_nicht_erreichbar_bricht_ab(self, basis_config):
        """Wenn Ollama offline ist, soll main() sauber abbrechen."""
        with patch("httpx.get", side_effect=Exception("Connection refused")):
            from main import main
            result = await main(basis_config)
        assert result is None


# ══════════════════════════════════════════════════════════════════
#  INTEGRATIONS-TEST – Ollama → Analyse → Speicherung
# ══════════════════════════════════════════════════════════════════

class TestIntegration:

    @patch("database.scraping_sessions.pymongo.MongoClient")
    def test_vollstaendiger_analyse_und_speicher_flow(
        self, mock_client_class, basis_artikel, basis_config, ollama_antwort_gut
    ):
        """
        End-to-end: Artikel analysieren → empfohlen → in DB speichern.
        Testet das Zusammenspiel von analysiere_artikel() und speichere_in_mongo().
        """
        mock_col = MagicMock()
        mock_client_class.return_value.__getitem__.return_value.__getitem__.return_value = mock_col

        # 1. Analyse
        with patch("ai.ollama.frage_ollama", return_value=ollama_antwort_gut):
            from ai.ollama import analysiere_artikel
            analysiert = analysiere_artikel(basis_artikel, basis_config)

        assert analysiert["empfohlen"] is True

        # 2. Speicherung
        from database.scraping_sessions import speichere_in_mongo
        speichere_in_mongo([analysiert], basis_config, "test@example.com")

        mock_col.insert_one.assert_called_once()
        session = mock_col.insert_one.call_args[0][0]
        assert session["anzahl_empfohlen"] == 1
        assert session["empfehlungen"][0]["titel"] == basis_artikel["titel"]
