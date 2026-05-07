"""
=== TEST MONGO (Legacy) ===

Tests für die ursprüngliche MongoDB-Integration in mongo.py.
Diese Funktion ist möglicherweise deprecated, wird aber noch getestet.

Testet:
  - speichere_in_mongo(): Speichert Empfehlungen in MongoDB
  - Fehlerbehandlung bei leeren Listen
  - Filterung von nicht-empfohlenen Artikeln
  - Timestamping
  - MongoDB Verbindungsfehler
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from database.mongo import speichere_in_mongo as speichere_in_mongo_legacy


# ═════════════════════════════════════════════════════════════════════════════
# Tests: speichere_in_mongo (Legacy) - Erfolgreiche Speicherung
# ═════════════════════════════════════════════════════════════════════════════

class TestSpeichereInMongoLegacySuccess:
    """Tests für erfolgreiche MongoDB-Speicherung (Legacy)."""
    
    def test_speichere_in_mongo_legacy_success(self, basis_config):
        """Test: Artikel werden erfolgreich in MongoDB gespeichert."""
        ergebnisse = [
            {
                "url": "https://vinted.de/items/1",
                "titel": "Artikel 1",
                "preis": "50 €",
                "empfohlen": True,
                "bewertung": 8
            },
            {
                "url": "https://vinted.de/items/2",
                "titel": "Artikel 2",
                "preis": "30 €",
                "empfohlen": False,
                "bewertung": 5
            }
        ]
        
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.inserted_ids = ["id1"]
        mock_collection.insert_many = MagicMock(return_value=mock_result)
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        
        with patch('database.mongo.pymongo.MongoClient', return_value=mock_client):
            with patch.dict('os.environ', {"MONGO_URL": "mongodb://localhost:27017"}):
                result = speichere_in_mongo_legacy(ergebnisse, basis_config)
        
        # Sollte Result-Objekt zurückgeben
        assert result is not None
        # Insert-Many sollte aufgerufen worden sein
        mock_collection.insert_many.assert_called_once()
    
    def test_speichere_in_mongo_legacy_filtert_empfohlene(self, basis_config):
        """Test: Nur empfohlene Artikel werden gespeichert."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Empfohlen"},
            {"url": "https://vinted.de/items/2", "empfohlen": False, "titel": "Nicht empfohlen"},
            {"url": "https://vinted.de/items/3", "empfohlen": True, "titel": "Empfohlen"},
        ]
        
        saved_items = []
        
        def mock_insert_many(items):
            saved_items.extend(items)
            result = MagicMock()
            result.inserted_ids = ["id1", "id2"]
            return result
        
        mock_collection = MagicMock()
        mock_collection.insert_many = MagicMock(side_effect=mock_insert_many)
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        
        with patch('database.mongo.pymongo.MongoClient', return_value=mock_client):
            with patch.dict('os.environ', {"MONGO_URL": "mongodb://localhost:27017"}):
                speichere_in_mongo_legacy(ergebnisse, {})
        
        # Nur 2 Artikel sollten gespeichert sein (die empfohlenen)
        assert len(saved_items) == 2
        assert all(item["empfohlen"] is True for item in saved_items)


# ═════════════════════════════════════════════════════════════════════════════
# Tests: speichere_in_mongo (Legacy) - Fehlerbehandlung
# ═════════════════════════════════════════════════════════════════════════════

class TestSpeichereInMongoLegacyErrors:
    """Tests für Fehlerbehandlung (Legacy)."""
    
    def test_speichere_in_mongo_legacy_leere_liste(self):
        """Test: Leere Liste wird nicht gespeichert."""
        result = speichere_in_mongo_legacy([], {})
        assert result is None
    
    def test_speichere_in_mongo_legacy_nur_nicht_empfohlen(self):
        """Test: Wenn nur nicht-empfohlene Artikel, Nothing happens."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": False, "titel": "Test1"},
            {"url": "https://vinted.de/items/2", "empfohlen": False, "titel": "Test2"},
        ]
        
        result = speichere_in_mongo_legacy(ergebnisse, {})
        assert result is None
    
    def test_speichere_in_mongo_legacy_mongodb_timeout(self):
        """Test: Timeout bei MongoDB Verbindung wird abgefangen."""
        import pymongo
        
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(
            side_effect=pymongo.errors.ServerSelectionTimeoutError("Timeout")
        )
        
        with patch('database.mongo.pymongo.MongoClient', return_value=mock_client):
            result = speichere_in_mongo_legacy(ergebnisse, {})
        
        assert result is None
    
    def test_speichere_in_mongo_legacy_allgemeiner_fehler(self):
        """Test: Allgemeiner Fehler wird abgefangen."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(side_effect=Exception("Fehler"))
        
        with patch('database.mongo.pymongo.MongoClient', return_value=mock_client):
            result = speichere_in_mongo_legacy(ergebnisse, {})
        
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Tests: speichere_in_mongo (Legacy) - Timestamps
# ═════════════════════════════════════════════════════════════════════════════

class TestSpeichereInMongoLegacyTimestamps:
    """Tests für Timestamp-Handling."""
    
    def test_speichere_in_mongo_legacy_add_timestamp(self, basis_config):
        """Test: Artikel erhalten Timestamp 'gespeichert_am'."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        saved_items = []
        
        def mock_insert_many(items):
            saved_items.extend(items)
            result = MagicMock()
            result.inserted_ids = ["id1"]
            return result
        
        mock_collection = MagicMock()
        mock_collection.insert_many = MagicMock(side_effect=mock_insert_many)
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        
        with patch('database.mongo.pymongo.MongoClient', return_value=mock_client):
            with patch.dict('os.environ', {"MONGO_URL": "mongodb://localhost:27017"}):
                speichere_in_mongo_legacy(ergebnisse, basis_config)
        
        # Timestamp sollte hinzugefügt worden sein
        assert len(saved_items) == 1
        assert "gespeichert_am" in saved_items[0]
        # Timestamp sollte im Format "YYYY-MM-DD HH:MM:SS" sein
        assert len(saved_items[0]["gespeichert_am"]) == 19  # "2024-01-01 12:00:00"
    
    def test_speichere_in_mongo_legacy_timestamp_format(self, basis_config):
        """Test: Timestamp hat korrektes Format."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        saved_items = []
        
        def mock_insert_many(items):
            saved_items.extend(items)
            result = MagicMock()
            result.inserted_ids = ["id1"]
            return result
        
        mock_collection = MagicMock()
        mock_collection.insert_many = MagicMock(side_effect=mock_insert_many)
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        
        with patch('database.mongo.pymongo.MongoClient', return_value=mock_client):
            with patch.dict('os.environ', {"MONGO_URL": "mongodb://localhost:27017"}):
                speichere_in_mongo_legacy(ergebnisse, basis_config)
        
        # Versuche, den Timestamp zu parsen
        timestamp_str = saved_items[0]["gespeichert_am"]
        try:
            parsed = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            assert parsed is not None
        except ValueError:
            pytest.fail(f"Timestamp {timestamp_str} hat falsches Format")


# ═════════════════════════════════════════════════════════════════════════════
# Tests: speichere_in_mongo (Legacy) - Datenbank Collections
# ═════════════════════════════════════════════════════════════════════════════

class TestSpeichereInMongoLegacyCollections:
    """Tests für Datenbank und Collections."""
    
    def test_speichere_in_mongo_legacy_correct_database(self, basis_config):
        """Test: Korrekte Datenbank wird verwendet."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.insert_many = MagicMock(return_value=MagicMock(inserted_ids=["id1"]))
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        
        with patch('database.mongo.pymongo.MongoClient', return_value=mock_client):
            with patch.dict('os.environ', {"MONGO_URL": "mongodb://localhost:27017"}):
                speichere_in_mongo_legacy(ergebnisse, basis_config)
        
        # Sollte "Secondhand_db" aufgerufen haben
        mock_client.__getitem__.assert_called_with("Secondhand_db")
    
    def test_speichere_in_mongo_legacy_correct_collection(self, basis_config):
        """Test: Korrekte Collection wird verwendet."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        mock_collection = MagicMock()
        mock_collection.insert_many = MagicMock(return_value=MagicMock(inserted_ids=["id1"]))
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        
        with patch('database.mongo.pymongo.MongoClient', return_value=mock_client):
            with patch.dict('os.environ', {"MONGO_URL": "mongodb://localhost:27017"}):
                speichere_in_mongo_legacy(ergebnisse, basis_config)
        
        # Sollte "vinted_empfehlungen" Collection aufgerufen haben
        mock_db.__getitem__.assert_called_with("vinted_empfehlungen")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])