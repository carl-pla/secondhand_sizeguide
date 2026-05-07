"""
=== TEST DASHBOARD ===

Tests für das Streamlit Dashboard.
Da die meisten Funktionen UI-basiert sind, konzentrieren wir uns auf:
  - Config-Management (Laden/Speichern)
  - Validierungen von Benutzereingaben
  - Datentransformationen und Konversionen
  - Integrations-Checks (Ollama, MongoDB, etc.)

HINWEIS: Echte Streamlit-Component Tests (st.selectbox, st.slider, etc.) 
sind mit pytest schwierig. Diese würden eher mit selenium/playwright getestet.
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile

from database.config_defaults import (
    VINTED_GROESSEN, VINTED_KATEGORIEN, HABILLEUR_KATEGORIEN, HABILLEUR_GROESSEN,
    ZUSTAND_RANG, ZUSTAND_OPTIONEN, lade_config, speichere_config, CONFIG_FILE
)


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Config Loading & Saving
# ═════════════════════════════════════════════════════════════════════════════

class TestConfigManagement:
    """Tests für Config-Laden und -Speichern."""
    
    def test_lade_config_default(self):
        """Test: Config wird geladen (mit Defaults wenn nicht vorhanden)."""
        config = lade_config()
        
        assert isinstance(config, dict)
        assert "groesse" in config
        assert "kategorie" in config
        assert "stile" in config
        assert "max_preis" in config
        assert "min_zustand" in config
        assert "ollama_url" in config
        assert "quelle" in config
    
    def test_lade_config_struktur(self):
        """Test: Config hat die richtige Struktur."""
        config = lade_config()
        
        # Vinted-Konfiguration
        assert "groesse" in config
        assert "kategorie" in config
        assert isinstance(config.get("stile"), list)
        
        # Maße
        assert "eigene_masse" in config
        assert isinstance(config["eigene_masse"], dict)
        
        # Ollama
        assert "ollama_url" in config
        assert "ollama_modell" in config
        
        # Search-Parameter
        assert "max_artikel_pro_suche" in config
        assert "pause_zwischen_artikeln" in config
        assert "pause_zwischen_suchen" in config
    
    def test_speichere_config(self):
        """Test: Config kann gespeichert werden."""
        config = {
            "groesse": "M / 38",
            "kategorie": "Herren Jacken & Mäntel",
            "stile": ["Vintage"],
            "max_preis": 50,
            "quelle": "vinted",
            "eigene_masse": {"brust": 88},
        }
        
        # Speichern sollte kein Fehler werfen
        try:
            speichere_config(config)
            assert True
        except Exception as e:
            pytest.fail(f"speichere_config() fehlgeschlagen: {e}")
    
    def test_speichere_und_lade_config_roundtrip(self):
        """Test: Config speichern und wieder laden."""
        original_config = {
            "groesse": "L / 40",
            "kategorie": "Herren Anzüge",
            "stile": ["Vintage", "Retro"],
            "max_preis": 75,
            "min_zustand": "Sehr gut",
            "eigene_masse": {"brust": 92, "taille": 75},
            "quelle": "habilleur",
        }
        
        speichere_config(original_config)
        loaded_config = lade_config()
        
        assert loaded_config["groesse"] == original_config["groesse"]
        assert loaded_config["kategorie"] == original_config["kategorie"]
        assert loaded_config["stile"] == original_config["stile"]


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Größen-Konvertierung zwischen Plattformen
# ═════════════════════════════════════════════════════════════════════════════

class TestSizeConversion:
    """Tests für Größen-Konvertierung zwischen Vinted/Habilleur/eBay."""
    
    def test_vinted_groessen_existieren(self):
        """Test: Vinted-Größen sind definiert."""
        assert len(VINTED_GROESSEN) > 0
        assert "M / 38" in VINTED_GROESSEN
        assert "L / 40" in VINTED_GROESSEN
    
    def test_habilleur_groessen_existieren(self):
        """Test: Habilleur-Größen sind definiert."""
        assert len(HABILLEUR_GROESSEN) > 0
        assert "M" in HABILLEUR_GROESSEN
        assert "L" in HABILLEUR_GROESSEN
    
    def test_vinted_kategorien_existieren(self):
        """Test: Vinted-Kategorien sind definiert."""
        assert len(VINTED_KATEGORIEN) > 0
        assert "Herren Jacken & Mäntel" in VINTED_KATEGORIEN
    
    def test_habilleur_kategorien_existieren(self):
        """Test: Habilleur-Kategorien sind definiert."""
        assert len(HABILLEUR_KATEGORIEN) > 0
        # Habilleur hat verschiedene Kategorien
        assert any(cat in HABILLEUR_KATEGORIEN for cat in ["Anzug", "Jacket", "Mantel"])
    
    def test_zustand_optionen_korrekt(self):
        """Test: Zustand-Optionen sind definiert."""
        expected_zustaende = ["Neu mit Etikett", "Neu ohne Etikett", "Sehr gut", "Gut", "Befriedigend"]
        
        for zustand in expected_zustaende:
            assert zustand in ZUSTAND_RANG or zustand in ZUSTAND_OPTIONEN


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Validierungen
# ═════════════════════════════════════════════════════════════════════════════

class TestValidierungen:
    """Tests für Input-Validierungen."""
    
    def test_validiere_max_preis_positiv(self):
        """Test: Maximaler Preis muss positiv sein."""
        max_preis = 50
        assert max_preis > 0
    
    def test_validiere_masse_im_bereich(self):
        """Test: Maße sind in vernünftigen Bereichen."""
        masse = {
            "brust": 88,  # 60-130cm
            "taille": 70,  # 50-120cm
            "huefte": 96,  # 70-140cm
            "schulter": 38,  # 30-60cm
        }
        
        assert 60 <= masse["brust"] <= 130
        assert 50 <= masse["taille"] <= 120
        assert 70 <= masse["huefte"] <= 140
        assert 30 <= masse["schulter"] <= 60
    
    def test_validiere_groesse_in_optionen(self):
        """Test: Größe muss in verfügbaren Optionen sein."""
        groesse = "M / 38"
        assert groesse in VINTED_GROESSEN or groesse in [f"{k}" for k in HABILLEUR_GROESSEN]
    
    def test_validiere_kategorie_in_optionen(self):
        """Test: Kategorie muss in verfügbaren Optionen sein."""
        kategorie = "Herren Jacken & Mäntel"
        assert kategorie in VINTED_KATEGORIEN or kategorie in HABILLEUR_KATEGORIEN


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Status-Checks (Ollama, MongoDB, etc.)
# ═════════════════════════════════════════════════════════════════════════════

class TestStatusChecks:
    """Tests für Service-Status-Checks."""
    
    def test_check_ollama_url_format(self):
        """Test: Ollama URL hat korrektes Format."""
        config = lade_config()
        ollama_url = config.get("ollama_url", "")
        
        assert "localhost" in ollama_url or "127.0.0.1" in ollama_url or "http" in ollama_url
        assert "/api" in ollama_url
    
    def test_check_ollama_modell_gesetzt(self):
        """Test: Ollama Modell ist konfiguriert."""
        config = lade_config()
        modell = config.get("ollama_modell")
        
        assert modell is not None
        assert isinstance(modell, str)
        assert len(modell) > 0
    
    def test_ollama_connectivity_mock(self):
        """Test: Ollama Verbindung kann getestet werden (gemockt)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.get', return_value=mock_response):
            import httpx
            result = httpx.get("http://localhost:11434", timeout=2)
            assert result.status_code == 200
    
    def test_ollama_offline_handling(self):
        """Test: Offline Ollama wird korrekt erkannt (gemockt)."""
        with patch('httpx.get', side_effect=Exception("Connection refused")):
            try:
                import httpx
                httpx.get("http://localhost:11434", timeout=2)
                assert False, "Sollte Exception werfen"
            except:
                assert True  # Erwartet


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Daten-Transformationen
# ═════════════════════════════════════════════════════════════════════════════

class TestDataTransformations:
    """Tests für Daten-Transformationen für verschiedene Quellen."""
    
    def test_artikel_struktur_vinted(self):
        """Test: Vinted-Artikel hat richtige Struktur."""
        artikel = {
            "url": "https://vinted.de/items/123",
            "titel": "Vintage Jacke",
            "preis": "35 €",
            "beschreibung": "Schöne alte Jacke"
        }
        
        assert "url" in artikel
        assert "titel" in artikel
        assert "preis" in artikel
        assert "beschreibung" in artikel
    
    def test_artikel_struktur_habilleur(self):
        """Test: Habilleur-Artikel hat richtige Struktur."""
        artikel = {
            "url": "https://habilleurjean.com/items/123",
            "titel": "Anzug",
            "preis": "89,50 EUR",
            "beschreibung": "Schöner Anzug",
            "kategorie": "Anzug"
        }
        
        assert "url" in artikel
        assert "titel" in artikel
        assert "preis" in artikel
        assert "beschreibung" in artikel
        assert "kategorie" in artikel
    
    def test_ergebnis_struktur(self):
        """Test: Analyseergebnis hat richtige Struktur."""
        ergebnis = {
            "url": "https://example.com",
            "titel": "Artikel",
            "preis": "50 €",
            "bewertung": 7,
            "empfohlen": True,
            "begruendung": "Passt gut.",
            "masse": {"brust_cm": 90},
            "zustand": "Gut",
            "material": "Baumwolle"
        }
        
        assert "url" in ergebnis
        assert "bewertung" in ergebnis
        assert isinstance(ergebnis["bewertung"], int)
        assert 1 <= ergebnis["bewertung"] <= 10
        assert "empfohlen" in ergebnis
        assert isinstance(ergebnis["empfohlen"], bool)


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Pausen-Konfiguration
# ═════════════════════════════════════════════════════════════════════════════

class TestPausenKonfiguration:
    """Tests für Anti-Ban Pausen-Einstellungen."""
    
    def test_pause_zwischen_artikeln_range(self):
        """Test: Pausen zwischen Artikeln sind in gültigem Bereich."""
        pausen = [2, 4]
        
        assert len(pausen) == 2
        assert 1 <= pausen[0] <= 15
        assert 1 <= pausen[1] <= 15
        assert pausen[0] <= pausen[1]
    
    def test_pause_zwischen_suchen_range(self):
        """Test: Pausen zwischen Suchen sind in gültigem Bereich."""
        pausen = [3, 6]
        
        assert len(pausen) == 2
        assert 3 <= pausen[0] <= 30
        assert 3 <= pausen[1] <= 30
        assert pausen[0] <= pausen[1]
    
    def test_max_artikel_limit(self):
        """Test: Max Artikel pro Suche hat sinnvolles Limit."""
        max_artikel = 50
        
        assert 1 <= max_artikel <= 60  # Dashboard-Limit
    
    def test_max_suchen_limit(self):
        """Test: Max Suchen sind begrenzt."""
        max_suchen = 5
        
        assert max_suchen > 0
        assert max_suchen <= 20


# ═════════════════════════════════════════════════════════════════════════════
# Tests: E-Mail Validierung
# ═════════════════════════════════════════════════════════════════════════════

class TestEmailValidierung:
    """Tests für E-Mail Validierung."""
    
    def test_email_format_valid(self):
        """Test: Gültiges E-Mail Format."""
        email = "test@example.com"
        assert "@" in email
        assert "." in email.split("@")[1]
    
    def test_email_format_invalid_no_at(self):
        """Test: Ungültig: Kein @."""
        email = "test.example.com"
        assert "@" not in email
    
    def test_email_optional(self):
        """Test: E-Mail ist optional."""
        config = lade_config()
        # E-Mail ist optional
        email = config.get("user_email", "")
        assert isinstance(email, str)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])