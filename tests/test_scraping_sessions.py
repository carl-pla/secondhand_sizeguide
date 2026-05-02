import json
import pytest 
from unittest.mock import MagicMock, patch

from database.scraping_sessions import speichere_in_mongo

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

        result = speichere_in_mongo(beispiel_empfehlungen, basis_config, "test@example.com")

        mock_col.insert_one.assert_called_once()
        inserted = mock_col.insert_one.call_args[0][0]
        assert inserted["user_email"] == "test@example.com"
        assert inserted["anzahl_empfohlen"] == 2

    @patch("database.scrapping_sessions.pymongo.MongoClient")
    def test_leere_liste_speichert_nichts(self, mock_client_class, basis_config):
        """Keine Artikel → kein DB-Call, kein Absturz."""
  
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
        result = speichere_in_mongo(nicht_empfohlen, basis_config)

        mock_client_class.assert_not_called()
        assert result is None

    @patch("database.scrapping_sessions.pymongo.MongoClient",
           side_effect=Exception("DB offline"))
    def test_db_fehler_gibt_none_zurueck(
        self, mock_client_class, beispiel_empfehlungen, basis_config
    ):
        """Datenbankfehler → None zurück, kein Absturz."""
        result = speichere_in_mongo(beispiel_empfehlungen, basis_config)
        assert result is None
