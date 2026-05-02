"""
=== MATCHFIT – PYTEST SUITE ===
Abgedeckte Module:
  - users.py          → registriere_user, deaktiviere_user, lade_alle_user

Alle externen Abhängigkeiten (Ollama, MongoDB, SMTP) werden gemockt,
damit die Tests ohne laufende Dienste funktionieren.
"""

import json
import pytest 
from unittest.mock import MagicMock, patch

from database.users import registriere_user, deaktiviere_user, lade_alle_user

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

        result = registriere_user("alt@example.com", basis_config)

        assert result["status"] == "updated"
        mock_col.update_one.assert_called_once()
        mock_col.insert_one.assert_not_called()

    @patch("database.users.pymongo.MongoClient")
    def test_ungueltige_email_wird_abgelehnt(self, mock_client_class, basis_config):
        """Ungültige E-Mail-Adresse → Fehlermeldung, kein DB-Call."""
        mock_col = self._mock_collection(mock_client_class)

        result = registriere_user("kein-at-zeichen", basis_config)

        assert "error" in result
        mock_col.insert_one.assert_not_called()

    @patch("database.users.pymongo.MongoClient")
    def test_user_wird_deaktiviert(self, mock_client_class):
        """Abmelden setzt aktiv=False via update_one."""
        mock_col = self._mock_collection(mock_client_class)

        deaktiviere_user("test@example.com")

        mock_col.update_one.assert_called_once_with(
            {"email": "test@example.com"},
            {"$set": {"aktiv": False}}
        )

    @patch("database.users.pymongo.MongoClient")
    def test_lade_alle_user_gibt_liste_zurueck(self, mock_client_class):
        """Aktive User werden geladen, _id wird entfernt."""
        mock_col = self._mock_collection(mock_client_class)
        mock_col.find.return_value = [
            {"_id": "mongo_id_1", "email": "a@example.com", "aktiv": True},
            {"_id": "mongo_id_2", "email": "b@example.com", "aktiv": True},
        ]

        result = lade_alle_user()

        assert len(result) == 2
        assert all("_id" not in u for u in result)  # _id muss entfernt sein
        assert result[0]["email"] == "a@example.com"


