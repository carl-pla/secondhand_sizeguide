"""
=== TEST MONGO ===

Tests für MongoDB-Integration (Speicherung von Scraping-Sessions).
Testet:
  - speichere_in_mongo(): Speichert Empfehlungen in MongoDB
  - Fehlerbehandlung bei leeren Listen
  - Filterung von nicht-empfohlenen Artikeln
  - MongoDB Verbindungsfehler
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from database.scraping_sessions import speichere_in_mongo


# ═════════════════════════════════════════════════════════════════════════════
# Tests: speichere_in_mongo - Erfolgreiche Speicherung
# ═════════════════════════════════════════════════════════════════════════════

class TestSpeichereInMongoSuccess:
    """Tests für erfolgreiche MongoDB-Speicherung."""
    
    def test_speichere_in_mongo_success(self, basis_config):
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
        mock_collection.insert_one = MagicMock(return_value=MagicMock(inserted_ids=["id1"]))
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.admin = MagicMock()
        mock_client.admin.command = MagicMock()
        
        with patch('database.scraping_sessions.pymongo.MongoClient', return_value=mock_client):
            result = speichere_in_mongo(
                ergebnisse=ergebnisse,
                config=basis_config,
                user_email="test@example.com",
                quelle="vinted"
            )
        
        # Sollte Session-ID zurückgeben
        assert result is not None
        # Insert-One sollte aufgerufen worden sein
        mock_collection.insert_one.assert_called_once()
    
    def test_speichere_in_mongo_session_struktur(self, basis_config):
        """Test: Session-Dokument hat richtige Struktur."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"},
        ]
        
        inserted_session = {}
        
        def mock_insert_one(session):
            inserted_session.update(session)
        
        mock_collection = MagicMock()
        mock_collection.insert_one = MagicMock(side_effect=mock_insert_one)
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.admin.command = MagicMock()
        
        with patch('database.scraping_sessions.pymongo.MongoClient', return_value=mock_client):
            speichere_in_mongo(
                ergebnisse=ergebnisse,
                config=basis_config,
                user_email="test@example.com",
                quelle="vinted"
            )
        
        # Session sollte richtige Felder haben
        assert "session_id" in inserted_session
        assert "user_email" in inserted_session
        assert "quelle" in inserted_session
        assert "gestartet_am" in inserted_session
        assert "empfehlungen" in inserted_session
        assert "anzahl_empfohlen" in inserted_session


# ═════════════════════════════════════════════════════════════════════════════
# Tests: speichere_in_mongo - Fehlerbehandlung
# ═════════════════════════════════════════════════════════════════════════════

class TestSpeichereInMongoErrors:
    """Tests für Fehlerbehandlung bei speichere_in_mongo."""
    
    def test_speichere_in_mongo_leere_liste(self, basis_config):
        """Test: Leere Liste wird nicht gespeichert."""
        result = speichere_in_mongo(
            ergebnisse=[],
            config=basis_config,
            user_email="test@example.com",
            quelle="vinted"
        )
        
        assert result is None
    
    def test_speichere_in_mongo_nur_nicht_empfohlen(self, basis_config):
        """Test: Artikel mit empfohlen=False werden ignoriert."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": False, "titel": "Test1"},
            {"url": "https://vinted.de/items/2", "empfohlen": False, "titel": "Test2"},
        ]
        
        result = speichere_in_mongo(
            ergebnisse=ergebnisse,
            config=basis_config,
            user_email="test@example.com",
            quelle="vinted"
        )
        
        assert result is None
    
    def test_speichere_in_mongo_mongodb_nicht_erreichbar(self, basis_config):
        """Test: Fehler bei MongoDB Verbindung wird abgefangen."""
        import pymongo
        
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        mock_client = MagicMock()
        mock_client.admin.command = MagicMock(
            side_effect=pymongo.errors.ServerSelectionTimeoutError("Connection refused")
        )
        
        with patch('database.scraping_sessions.pymongo.MongoClient', return_value=mock_client):
            result = speichere_in_mongo(
                ergebnisse=ergebnisse,
                config=basis_config,
                user_email="test@example.com",
                quelle="vinted"
            )
        
        assert result is None
    
    def test_speichere_in_mongo_allgemeiner_fehler(self, basis_config):
        """Test: Allgemeiner Fehler wird abgefangen."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        mock_client = MagicMock()
        mock_client.admin.command = MagicMock(side_effect=Exception("Allgemeiner Fehler"))
        
        with patch('database.scraping_sessions.pymongo.MongoClient', return_value=mock_client):
            result = speichere_in_mongo(
                ergebnisse=ergebnisse,
                config=basis_config,
                user_email="test@example.com",
                quelle="vinted"
            )
        
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Tests: speichere_in_mongo - Filterung
# ═════════════════════════════════════════════════════════════════════════════

class TestSpeichereInMongoFiltering:
    """Tests für Filterung von Artikeln."""
    
    def test_speichere_in_mongo_filtert_empfohlene(self, basis_config):
        """Test: Nur empfohlene Artikel werden gespeichert."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Empfohlen"},
            {"url": "https://vinted.de/items/2", "empfohlen": False, "titel": "Nicht empfohlen"},
            {"url": "https://vinted.de/items/3", "empfohlen": True, "titel": "Empfohlen"},
        ]
        
        saved_empfehlungen = []
        
        def mock_insert_one(session):
            saved_empfehlungen.extend(session["empfehlungen"])
        
        mock_collection = MagicMock()
        mock_collection.insert_one = MagicMock(side_effect=mock_insert_one)
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.admin.command = MagicMock()
        
        with patch('database.scraping_sessions.pymongo.MongoClient', return_value=mock_client):
            speichere_in_mongo(
                ergebnisse=ergebnisse,
                config=basis_config,
                user_email="test@example.com",
                quelle="vinted"
            )
        
        # Nur 2 Artikel sollten gespeichert sein (die empfohlenen)
        assert len(saved_empfehlungen) == 2
        assert all(a["empfohlen"] is True for a in saved_empfehlungen)
    
    def test_speichere_in_mongo_ignoriert_non_dict(self, basis_config):
        """Test: Non-Dict Einträge werden ignoriert."""
        ergebnisse = [
            "String statt Dict",
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"},
            None,
        ]
        
        saved_empfehlungen = []
        
        def mock_insert_one(session):
            saved_empfehlungen.extend(session["empfehlungen"])
        
        mock_collection = MagicMock()
        mock_collection.insert_one = MagicMock(side_effect=mock_insert_one)
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.admin.command = MagicMock()
        
        with patch('database.scraping_sessions.pymongo.MongoClient', return_value=mock_client):
            result = speichere_in_mongo(
                ergebnisse=ergebnisse,
                config=basis_config,
                user_email="test@example.com",
                quelle="vinted"
            )
        
        # Nur 1 Artikel sollte gespeichert sein
        assert len(saved_empfehlungen) == 1


# ═════════════════════════════════════════════════════════════════════════════
# Tests: speichere_in_mongo - User & Quelle
# ═════════════════════════════════════════════════════════════════════════════

class TestSpeichereInMongoUserQuelle:
    """Tests für User und Quelle Information."""
    
    def test_speichere_in_mongo_user_email(self, basis_config):
        """Test: User-Email wird korrekt gespeichert."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        inserted_session = {}
        
        def mock_insert_one(session):
            inserted_session.update(session)
        
        mock_collection = MagicMock()
        mock_collection.insert_one = MagicMock(side_effect=mock_insert_one)
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.admin.command = MagicMock()
        
        with patch('database.scraping_sessions.pymongo.MongoClient', return_value=mock_client):
            speichere_in_mongo(
                ergebnisse=ergebnisse,
                config=basis_config,
                user_email="max@example.com",
                quelle="vinted"
            )
        
        assert inserted_session["user_email"] == "max@example.com"
    
    def test_speichere_in_mongo_quelle(self, basis_config):
        """Test: Quelle wird korrekt gespeichert."""
        ergebnisse = [
            {"url": "https://vinted.de/items/1", "empfohlen": True, "titel": "Test"}
        ]
        
        inserted_session = {}
        
        def mock_insert_one(session):
            inserted_session.update(session)
        
        mock_collection = MagicMock()
        mock_collection.insert_one = MagicMock(side_effect=mock_insert_one)
        
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)
        
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        mock_client.admin.command = MagicMock()
        
        with patch('database.scraping_sessions.pymongo.MongoClient', return_value=mock_client):
            speichere_in_mongo(
                ergebnisse=ergebnisse,
                config=basis_config,
                user_email="test@example.com",
                quelle="habilleur"
            )
        
        assert inserted_session["quelle"] == "habilleur"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])