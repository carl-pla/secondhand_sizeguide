"""
=== TEST USERS ===

Tests für User-Management und Newsletter-Funktionen.
Testet:
  - registriere_user(): Registriert neuen User oder updatet bestehenden
  - lade_alle_user(): Lädt alle aktiven User
  - deaktiviere_user(): Deaktiviert User
  - E-Mail Validierung
  - MongoDB Fehlerbehandlung
"""

import pytest
import datetime
from unittest.mock import patch, MagicMock

from database.users import registriere_user, lade_alle_user, deaktiviere_user


# ═════════════════════════════════════════════════════════════════════════════
# Tests: registriere_user - Erfolgreiche Registrierung
# ═════════════════════════════════════════════════════════════════════════════

class TestRegistriereUserSuccess:
    """Tests für erfolgreiche User-Registrierung."""
    
    def test_registriere_neuer_user(self, basis_config):
        """Test: Neuer User wird registriert."""
        email = "new@example.com"
        
        mock_collection = MagicMock()
        mock_collection.find_one = MagicMock(return_value=None)  # User existiert nicht
        mock_collection.insert_one = MagicMock()
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            result = registriere_user(email, basis_config)
        
        assert result["status"] == "neu"
        assert result["email"] == email
        mock_collection.insert_one.assert_called_once()
    
    def test_registriere_existierenden_user(self, basis_config):
        """Test: Bestehender User wird aktualisiert."""
        email = "existing@example.com"
        
        # Simuliere, dass User bereits existiert
        existing_user = {
            "_id": "123",
            "email": email,
            "groesse": "M / 38",
            "aktiv": True
        }
        
        mock_collection = MagicMock()
        mock_collection.find_one = MagicMock(return_value=existing_user)
        mock_collection.update_one = MagicMock()
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            result = registriere_user(email, basis_config)
        
        assert result["status"] == "updated"
        assert result["email"] == email
        mock_collection.update_one.assert_called_once()
    
    def test_registriere_user_speichert_config(self, basis_config):
        """Test: Konfiguration wird mit User gespeichert."""
        email = "config@example.com"
        
        saved_doc = {}
        
        def mock_insert_one(doc):
            saved_doc.update(doc)
        
        mock_collection = MagicMock()
        mock_collection.find_one = MagicMock(return_value=None)
        mock_collection.insert_one = MagicMock(side_effect=mock_insert_one)
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            registriere_user(email, basis_config)
        
        # Konfiguration sollte gespeichert sein
        assert saved_doc["groesse"] == basis_config["groesse"]
        assert saved_doc["max_preis"] == basis_config["max_preis"]
        assert saved_doc["stile"] == basis_config["stile"]
        assert saved_doc["eigene_masse"] == basis_config["eigene_masse"]
    
    def test_registriere_user_timestamp(self, basis_config):
        """Test: Registrierungszeitstempel wird gespeichert."""
        email = "timestamp@example.com"
        
        saved_doc = {}
        
        def mock_insert_one(doc):
            saved_doc.update(doc)
        
        mock_collection = MagicMock()
        mock_collection.find_one = MagicMock(return_value=None)
        mock_collection.insert_one = MagicMock(side_effect=mock_insert_one)
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            registriere_user(email, basis_config)
        
        assert "registriert_am" in saved_doc
        assert isinstance(saved_doc["registriert_am"], str)


# ═════════════════════════════════════════════════════════════════════════════
# Tests: registriere_user - E-Mail Validierung
# ═════════════════════════════════════════════════════════════════════════════

class TestRegistriereUserValidation:
    """Tests für E-Mail Validierung."""
    
    def test_registriere_user_ungueltige_email_kein_at(self, basis_config):
        """Test: E-Mail ohne @ wird abgelehnt."""
        result = registriere_user("invalid.email.com", basis_config)
        assert "error" in result
        assert "Ungültig" in result["error"]
    
    def test_registriere_user_ungueltige_email_kein_punkt(self, basis_config):
        """Test: E-Mail ohne Punkt in Domain wird abgelehnt."""
        result = registriere_user("invalid@email", basis_config)
        assert "error" in result
        assert "Ungültig" in result["error"]
    
    def test_registriere_user_ungueltige_email_leer(self, basis_config):
        """Test: Leere E-Mail wird abgelehnt."""
        result = registriere_user("", basis_config)
        assert "error" in result
    
    def test_registriere_user_gueltige_emails(self, basis_config):
        """Test: Gültige E-Mails werden akzeptiert."""
        valid_emails = [
            "user@example.com",
            "max@test.de",
            "test.user@subdomain.example.org"
        ]
        
        mock_collection = MagicMock()
        mock_collection.find_one = MagicMock(return_value=None)
        mock_collection.insert_one = MagicMock()
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            for email in valid_emails:
                result = registriere_user(email, basis_config)
                assert "error" not in result
                assert result["email"] == email


# ═════════════════════════════════════════════════════════════════════════════
# Tests: lade_alle_user
# ═════════════════════════════════════════════════════════════════════════════

class TestLadeAlleUser:
    """Tests für lade_alle_user()."""
    
    def test_lade_alle_user_existieren(self):
        """Test: Alle aktiven User werden geladen."""
        mock_users = [
            {
                "_id": "id1",
                "email": "user1@example.com",
                "groesse": "M / 38",
                "aktiv": True
            },
            {
                "_id": "id2",
                "email": "user2@example.com",
                "groesse": "L / 40",
                "aktiv": True
            }
        ]
        
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_users)
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            users = lade_alle_user()
        
        assert len(users) == 2
        assert users[0]["email"] == "user1@example.com"
        assert users[1]["email"] == "user2@example.com"
    
    def test_lade_alle_user_nur_aktive(self):
        """Test: Nur aktive User werden geladen."""
        mock_users = [
            {
                "_id": "id1",
                "email": "active@example.com",
                "aktiv": True
            },
            {
                "_id": "id2",
                "email": "inactive@example.com",
                "aktiv": False
            }
        ]
        
        mock_collection = MagicMock()
        # find() wird mit {"aktiv": True} aufgerufen
        mock_collection.find = MagicMock(return_value=mock_users)
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            users = lade_alle_user()
        
        # Es sollte ein find() mit aktiv: True aufgerufen worden sein
        mock_collection.find.assert_called_with({"aktiv": True})
    
    def test_lade_alle_user_leere_liste(self):
        """Test: Leere Liste wenn keine User vorhanden."""
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=[])
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            users = lade_alle_user()
        
        assert users == []
    
    def test_lade_alle_user_entfernt_ids(self):
        """Test: _id Feld wird entfernt."""
        mock_users = [
            {
                "_id": "id1",
                "email": "user@example.com",
                "aktiv": True
            }
        ]
        
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_users)
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            users = lade_alle_user()
        
        # _id sollte nicht mehr enthalten sein
        assert "_id" not in users[0]
        assert "email" in users[0]


# ═════════════════════════════════════════════════════════════════════════════
# Tests: deaktiviere_user
# ═════════════════════════════════════════════════════════════════════════════

class TestDeaktiviereUser:
    """Tests für deaktiviere_user()."""
    
    def test_deaktiviere_user(self):
        """Test: User wird deaktiviert."""
        email = "user@example.com"
        
        mock_collection = MagicMock()
        mock_collection.update_one = MagicMock()
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            deaktiviere_user(email)
        
        # update_one sollte mit Abmelde-Filter aufgerufen worden sein
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"email": email}
        assert call_args[0][1] == {"$set": {"aktiv": False}}
    
    def test_deaktiviere_user_mehrmals(self):
        """Test: User kann mehrmals deaktiviert werden (idempotent)."""
        email = "user@example.com"
        
        mock_collection = MagicMock()
        mock_collection.update_one = MagicMock()
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            deaktiviere_user(email)
            deaktiviere_user(email)
        
        # Sollte 2x aufgerufen worden sein
        assert mock_collection.update_one.call_count == 2


# ═════════════════════════════════════════════════════════════════════════════
# Tests: User Management Workflow
# ═════════════════════════════════════════════════════════════════════════════

class TestUserWorkflow:
    """Tests für vollständige User Management Workflows."""
    
    def test_user_workflow_register_and_load(self, basis_config):
        """Test: Vollständiger Workflow Registrierung → Laden."""
        email = "workflow@example.com"
        
        # Mock Collection mit registriertem User
        mock_users = [
            {
                "_id": "id1",
                "email": email,
                "groesse": basis_config["groesse"],
                "aktiv": True
            }
        ]
        
        mock_collection = MagicMock()
        mock_collection.find_one = MagicMock(return_value=None)  # Für Registrierung
        mock_collection.insert_one = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_users)  # Für Laden
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            # Registrierung
            reg_result = registriere_user(email, basis_config)
            assert reg_result["status"] == "neu"
            
            # Laden
            users = lade_alle_user()
            assert len(users) > 0
            assert any(u["email"] == email for u in users)
    
    def test_user_workflow_register_deactivate(self, basis_config):
        """Test: Workflow Registrierung → Deaktivierung."""
        email = "deactive@example.com"
        
        mock_collection = MagicMock()
        mock_collection.find_one = MagicMock(return_value=None)
        mock_collection.insert_one = MagicMock()
        mock_collection.update_one = MagicMock()
        
        with patch('database.users.get_users_collection', return_value=mock_collection):
            # Registrierung
            registriere_user(email, basis_config)
            assert mock_collection.insert_one.called
            
            # Deaktivierung
            deaktiviere_user(email)
            assert mock_collection.update_one.called

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])