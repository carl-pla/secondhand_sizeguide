"""
=== MATCHFIT – PYTEST SUITE ===
Abgedeckte Module:
  - newsletter.py     → generiere_html, sende_email

Alle externen Abhängigkeiten (Ollama, MongoDB, SMTP) werden gemockt,
damit die Tests ohne laufende Dienste funktionieren.
"""

import json
import pytest 
from unittest.mock import MagicMock, patch

from newsletter.newsletter import generiere_html, sende_email, MAX_ARTIKEL


# ══════════════════════════════════════════════════════════════════
#  NEWSLETTER – generiere_html()
# ══════════════════════════════════════════════════════════════════

class TestGeneriereHtml:

    def test_gibt_fallback_text_zurueck_bei_leerer_liste(self):
        """Keine Artikel → verständliche Meldung, kein Absturz."""
        result = generiere_html([])
        assert "keine" in result.lower() or "nicht" in result.lower()

    def test_html_enthaelt_artikeltitel(self, beispiel_empfehlungen):
        """Titel der Artikel müssen im generierten HTML auftauchen."""
        result = generiere_html(beispiel_empfehlungen)

        assert "Vintage Levi's Jacke" in result
        assert "Retro Wollmantel" in result

    def test_html_enthaelt_preise(self, beispiel_empfehlungen):
        """Preise müssen im Newsletter sichtbar sein."""
        result = generiere_html(beispiel_empfehlungen)

        assert "35 €" in result
        assert "45 €" in result

    def test_html_enthaelt_links(self, beispiel_empfehlungen):
        """Artikel-URLs müssen als anklickbare Links vorhanden sein."""
        result = generiere_html(beispiel_empfehlungen)

        assert "https://vinted.de/items/1" in result

    def test_maximal_10_artikel_im_newsletter(self):
        """Auch bei 20 Artikeln dürfen maximal MAX_ARTIKEL (10) angezeigt werden."""
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
        result = generiere_html(beispiel_empfehlungen)

        assert "2" in result  # 2 Artikel gefunden


# ══════════════════════════════════════════════════════════════════
#  NEWSLETTER – sende_email()
# ══════════════════════════════════════════════════════════════════

class TestSendeEmail:

    @patch("newsletter.smtplib.SMTP")
    @patch("newsletter.MAIL_FROM", "sender@example.com")
    @patch("newsletter.MAIL_PASSWORD", "test-password")
    def test_sendet_email_erfolgreich(self, mock_smtp_class):
        """Normalfall: SMTP-Verbindung klappt, E-Mail wird gesendet."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        sende_email("<html>Test</html>", "empfaenger@example.com")

        # TLS muss vor Login aufgerufen werden (wichtige Reihenfolge!)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@example.com", "test-password")
        mock_server.send_message.assert_called_once()

    @patch("newsletter.smtplib.SMTP")
    @patch("newsletter.MAIL_FROM", "sender@example.com")
    @patch("newsletter.MAIL_PASSWORD", "test-password")
    def test_starttls_vor_login_aufgerufen(self, mock_smtp_class):
        """Kritische Reihenfolge: starttls() MUSS vor login() kommen."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        call_order = []
        mock_server.starttls.side_effect = lambda: call_order.append("starttls")
        mock_server.login.side_effect = lambda *a: call_order.append("login")

        sende_email("<html>Test</html>", "empfaenger@example.com")

        assert call_order.index("starttls") < call_order.index("login"), \
            "starttls() muss VOR login() aufgerufen werden!"

    @patch("newsletter.smtplib.SMTP", side_effect=Exception("Connection refused"))
    @patch("newsletter.MAIL_FROM", "sender@example.com")
    @patch("newsletter.MAIL_PASSWORD", "test-password")
    def test_smtp_fehler_wirft_keinen_absturz(self, mock_smtp_class):
        """SMTP-Fehler → kein unkontrollierter Absturz der Pipeline."""
        # Darf keine Exception werfen
        sende_email("<html>Test</html>", "empfaenger@example.com")
