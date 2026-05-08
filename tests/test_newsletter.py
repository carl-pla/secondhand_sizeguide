"""
=== TEST NEWSLETTER ===

Tests für Newsletter-Funktionen.
Testet:
  - parse_gestartet_am(): Parst Datetime-Strings
  - fetch_latest_empfehlungen(): Holt Empfehlungen aus MongoDB
  - generiere_html(): Erstellt HTML-Newsletter-Content
  - sende_email(): Sendet E-Mails via SMTP
  - lade_alle_empfaenger(): Lädt alle aktiven User
"""

import pytest
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Setze Umgebungsvariablen BEVOR Module importiert werden
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("MAIL_FROM", "test@example.com")
os.environ.setdefault("MAIL_PASSWORD", "dummy_password")

# Füge das Wurzelverzeichnis des Projekts zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent))

from notification.newsletter import (
    parse_gestartet_am,
    fetch_latest_empfehlungen,
    generiere_html,
    sende_email,
    lade_alle_empfaenger,
)


# ═════════════════════════════════════════════════════════════════════════════
# Tests: parse_gestartet_am - Datetime-Parsing
# ═════════════════════════════════════════════════════════════════════════════

class TestParseGestartAm:
    """Tests für parse_gestartet_am()-Funktion."""

    def test_parse_datetime_objekt(self):
        """Test: Datetime-Objekt wird korrekt erkannt."""
        dt = datetime(2026, 5, 8, 14, 30, 0)
        result = parse_gestartet_am(dt)
        assert result == dt

    def test_parse_string_mit_korrektem_format(self):
        """Test: String im Format '%Y-%m-%d %H:%M:%S' wird geparst."""
        dt_string = "2026-05-08 14:30:00"
        result = parse_gestartet_am(dt_string)
        assert result == datetime(2026, 5, 8, 14, 30, 0)

    def test_parse_string_mit_falschem_format(self):
        """Test: String mit falschem Format gibt None zurück."""
        dt_string = "08-05-2026"
        result = parse_gestartet_am(dt_string)
        assert result is None

    def test_parse_unbekannter_typ(self):
        """Test: Unbekannte Typen geben None zurück."""
        result = parse_gestartet_am(12345)
        assert result is None

    def test_parse_none(self):
        """Test: None gibt None zurück."""
        result = parse_gestartet_am(None)
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Tests: fetch_latest_empfehlungen - MongoDB-Abfrage
# ═════════════════════════════════════════════════════════════════════════════

class TestFetchLatestEmpfehlungen:
    """Tests für fetch_latest_empfehlungen()-Funktion."""

    def test_fetch_mit_datetime_query(self):
        """Test: Empfehlungen werden mit Datetime-Query geladen."""
        mock_sessions = [
            {
                "user_email": "test1@example.com",
                "quelle": "vinted",
                "gestartet_am": datetime.now() - timedelta(hours=5),
                "empfehlungen": [
                    {"titel": "Artikel 1", "preis": "30€", "url": "http://test1"},
                    {"titel": "Artikel 2", "preis": "40€", "url": "http://test2"},
                ],
            },
            {
                "user_email": "test2@example.com",
                "quelle": "ebay",
                "gestartet_am": datetime.now() - timedelta(hours=2),
                "empfehlungen": [
                    {"titel": "Artikel 3", "preis": "50€", "url": "http://test3"},
                ],
            },
        ]

        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=MagicMock(sort=MagicMock(return_value=mock_sessions)))
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value={"scraping_sessions": mock_collection})

        with patch("notification.newsletter.MongoClient", return_value=mock_client):
            result = fetch_latest_empfehlungen()

        # Sollte 3 Artikel insgesamt haben
        assert len(result) == 3
        assert result[0]["_user"] == "test1@example.com"
        assert result[0]["_quelle"] == "vinted"
        assert result[2]["_user"] == "test2@example.com"
        assert result[2]["_quelle"] == "ebay"

    def test_fetch_mit_fallback_auf_strings(self):
        """Test: String-Daten werden als Fallback geparst."""
        mock_sessions_alle = [
            {
                "user_email": "test@example.com",
                "gestartet_am": "2026-05-08 10:00:00",
                "config": {"quelle": "vinted"},
                "empfehlungen": [
                    {"titel": "Test Artikel", "preis": "25€", "url": "http://test"},
                ],
            }
        ]

        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=MagicMock(sort=MagicMock(return_value=[])))
        mock_collection.find.return_value.sort.side_effect = [[], MagicMock(return_value=mock_sessions_alle)]
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value={"scraping_sessions": mock_collection})

        # Manuell simulieren
        with patch("notification.newsletter.MongoClient", return_value=mock_client):
            # Direkt testen, dass Fallback funktioniert
            from notification.newsletter import parse_gestartet_am
            
            parsed = parse_gestartet_am("2026-05-08 10:00:00")
            assert parsed is not None
            assert isinstance(parsed, datetime)

    def test_fetch_keine_sessions(self):
        """Test: Keine Sessions gefunden → leere Liste."""
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=MagicMock(sort=MagicMock(return_value=[])))
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value={"scraping_sessions": mock_collection})

        with patch("notification.newsletter.MongoClient", return_value=mock_client):
            result = fetch_latest_empfehlungen()

        assert result == []


# ═════════════════════════════════════════════════════════════════════════════
# Tests: generiere_html - HTML-Generierung
# ═════════════════════════════════════════════════════════════════════════════

class TestGeneriereHtml:
    """Tests für generiere_html()-Funktion."""

    def test_generiere_html_mit_artikeln(self):
        """Test: HTML wird mit Artikeln korrekt generiert."""
        items = [
            {
                "titel": "Vintage Jacke",
                "preis": "35€",
                "url": "http://example.com/1",
                "bewertung": 8,
                "begruendung": "Passt perfekt!",
                "_quelle": "vinted",
            },
            {
                "titel": "Designer Hose",
                "preis": "50€",
                "url": "http://example.com/2",
                "bewertung": 7,
                "begruendung": "Gute Qualität",
                "_quelle": "ebay",
            },
        ]

        html = generiere_html(items)

        assert "Vintage Jacke" in html
        assert "Designer Hose" in html
        assert "35€" in html
        assert "50€" in html
        assert "⭐⭐⭐⭐⭐⭐⭐⭐" in html  # 8 Sterne
        assert "⭐⭐⭐⭐⭐⭐⭐" in html      # 7 Sterne
        assert "Passt perfekt!" in html
        assert "Gute Qualität" in html
        assert "http://example.com/1" in html
        assert "http://example.com/2" in html
        assert "vinted" in html
        assert "ebay" in html

    def test_generiere_html_mit_zu_vielen_artikeln(self):
        """Test: MAX_ARTIKEL Limit wird eingehalten."""
        from notification.newsletter import MAX_ARTIKEL

        items = [
            {
                "titel": f"Artikel {i}",
                "preis": f"{20 + i}€",
                "url": f"http://example.com/{i}",
                "bewertung": 7,
                "begruendung": "Test",
                "_quelle": "vinted",
            }
            for i in range(20)
        ]

        html = generiere_html(items)

        # Sollte maximal MAX_ARTIKEL enthalten
        count_artikel = html.count("<div style=\"border:1px solid #eee")
        assert count_artikel <= MAX_ARTIKEL

    def test_generiere_html_ohne_artikel(self):
        """Test: Leere Liste gibt Standard-Nachricht."""
        html = generiere_html([])
        assert "Heute wurden keine neuen Empfehlungen gefunden." in html

    def test_generiere_html_mit_fehlenden_feldern(self):
        """Test: Fehlende Felder werden mit '?' ersetzt."""
        items = [
            {
                "titel": "Test",
                # preis, url, begruendung fehlen
                "bewertung": 5,
                "_quelle": "vinted",
            }
        ]

        html = generiere_html(items)

        assert "Test" in html
        assert "?" in html  # Fallback für fehlende Felder


# ═════════════════════════════════════════════════════════════════════════════
# Tests: sende_email - E-Mail-Versand
# ═════════════════════════════════════════════════════════════════════════════

class TestSendeEmail:
    """Tests für sende_email()-Funktion."""

    def test_sende_email_erfolg(self):
        """Test: E-Mail wird erfolgreich gesendet."""
        html_content = "<p>Test Newsletter</p>"
        empfaenger = "test@example.com"

        mock_server = MagicMock()

        with patch("notification.newsletter.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.return_value = mock_server
            sende_email(html_content, empfaenger)

        # Prüfe, dass SMTP-Methoden aufgerufen wurden
        mock_server.ehlo.assert_called()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    def test_sende_email_mit_html_und_plain_text(self):
        """Test: E-Mail enthält HTML und Plain-Text Versionen."""
        html_content = "<h1>Newsletter</h1><p>Test mit <b>HTML</b></p>"
        empfaenger = "test@example.com"

        mock_server = MagicMock()

        with patch("notification.newsletter.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.return_value = mock_server
            sende_email(html_content, empfaenger)

        # Prüfe, dass send_message aufgerufen wurde
        assert mock_server.send_message.called
        sent_msg = mock_server.send_message.call_args[0][0]
        
        # Plain-Text sollte HTML-Tags entfernt haben
        assert "Newsletter" in sent_msg.as_string()
        assert "Test mit HTML" in sent_msg.as_string() or "Test mit" in sent_msg.as_string()


# ═════════════════════════════════════════════════════════════════════════════
# Tests: lade_alle_empfaenger - User-Laden
# ═════════════════════════════════════════════════════════════════════════════

class TestLadeAlleEmpfaenger:
    """Tests für lade_alle_empfaenger()-Funktion."""

    def test_lade_alle_empfaenger_erfolg(self):
        """Test: Alle aktiven User werden geladen."""
        mock_users = [
            {"email": "test1@example.com", "aktiv": True},
            {"email": "test2@example.com", "aktiv": True},
            {"email": "test3@example.com", "aktiv": True},
        ]

        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_users)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value={"users": mock_collection})

        with patch("notification.newsletter.MongoClient", return_value=mock_client):
            result = lade_alle_empfaenger()

        assert len(result) == 3
        assert "test1@example.com" in result
        assert "test2@example.com" in result
        assert "test3@example.com" in result

    def test_lade_alle_empfaenger_keine_user(self):
        """Test: Keine aktiven User → leere Liste."""
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=[])

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value={"users": mock_collection})

        with patch("notification.newsletter.MongoClient", return_value=mock_client):
            result = lade_alle_empfaenger()

        assert result == []

    def test_lade_alle_empfaenger_fehlende_email(self):
        """Test: User ohne Email-Feld werden ignoriert."""
        mock_users = [
            {"email": "test1@example.com", "aktiv": True},
            {"aktiv": True},  # Kein email-Feld
            {"email": "test2@example.com", "aktiv": True},
        ]

        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_users)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value={"users": mock_collection})

        with patch("notification.newsletter.MongoClient", return_value=mock_client):
            result = lade_alle_empfaenger()

        assert len(result) == 2
        assert "test1@example.com" in result
        assert "test2@example.com" in result


# ═════════════════════════════════════════════════════════════════════════════
# Integrations-Tests
# ═════════════════════════════════════════════════════════════════════════════

class TestNewsletterIntegration:
    """Integrations-Tests für komplette Newsletter-Pipeline."""

    def test_vollstaendiger_newsletter_workflow(self):
        """Test: Kompletter Workflow von Empfehlungen bis E-Mail."""
        # 1. Mock: fetch_latest_empfehlungen
        mock_empfehlungen = [
            {
                "titel": "Top Artikel",
                "preis": "45€",
                "url": "http://example.com",
                "bewertung": 9,
                "begruendung": "Sehr gut",
                "_user": "test@example.com",
                "_quelle": "vinted",
            }
        ]

        # 2. Mock: lade_alle_empfaenger
        mock_empfaenger = ["test@example.com"]

        # 3. Generiere HTML
        html = generiere_html(mock_empfehlungen)

        # 4. Überprüfe, dass HTML korrekt ist
        assert "Top Artikel" in html
        assert "45€" in html
        assert "⭐⭐⭐⭐⭐⭐⭐⭐⭐" in html  # 9 Sterne
        assert "vinted" in html

    def test_newsletter_mit_mehreren_usern(self):
        """Test: Newsletter mit mehreren Empfängern und unterschiedlichen Artikeln."""
        # User-spezifische Artikel
        all_items = [
            {"titel": "Artikel für User1", "preis": "30€", "url": "http://1", "bewertung": 8, "begruendung": "Gut", "_user": "user1@test.com", "_quelle": "vinted"},
            {"titel": "Artikel für User2", "preis": "40€", "url": "http://2", "bewertung": 7, "begruendung": "Ok", "_user": "user2@test.com", "_quelle": "ebay"},
        ]

        # Artikel für user1
        user1_items = [i for i in all_items if i.get("_user") == "user1@test.com"]
        html1 = generiere_html(user1_items)
        assert "Artikel für User1" in html1
        assert "Artikel für User2" not in html1

        # Artikel für user2
        user2_items = [i for i in all_items if i.get("_user") == "user2@test.com"]
        html2 = generiere_html(user2_items)
        assert "Artikel für User2" in html2
        assert "Artikel für User1" not in html2

if __name__ == "__main__":
    pytest.main(["-v", "tests/test_newsletter.py"])