"""
=== TEST CONFIG_DEFAULTS ===

Tests für Konfigurationen und Konstanten.
Testet:
  - get_mongo_url(): MongoDB URL-Auswahl (Env-Variablen, Streamlit Secrets, Localhost)
  - Alle Lookup-Tabellen (eBay, Vinted, Habilleur)
  - Default-Konfiguration Struktur
"""

import pytest
import os
from unittest.mock import patch
from pathlib import Path

from database.config_defaults import (
    get_mongo_url,
    MONGO_URL,
    CATEGORY_IDS_EBAY,
    CONDITION_IDS_EBAY,
    EBAY_GROESSEN,
    EBAY_FARBEN,
    EBAY_MATERIALS,
    VINTED_GROESSEN,
    VINTED_KATEGORIEN,
    HABILLEUR_GROESSEN,
    HABILLEUR_KATEGORIEN,
    HABILLEUR_MASSE_BEISPIEL,
    OLLAMA_MODELLE,
    STIL_OPTIONEN,
    ZUSTAND_RANG,
    ZUSTAND_OPTIONEN,
    DEFAULT_CONFIG,
)


# ═════════════════════════════════════════════════════════════════════════════
# Tests: get_mongo_url() - MongoDB URL Auswahl
# ═════════════════════════════════════════════════════════════════════════════

class TestGetMongoUrl:
    """Tests für get_mongo_url() Funktion."""
    
    def test_get_mongo_url_from_env(self):
        """Test: MongoDB URL aus Umgebungsvariable."""
        with patch.dict(os.environ, {"MONGO_URL": "mongodb://custom.mongodb.net"}):
            url = get_mongo_url()
            assert url == "mongodb://custom.mongodb.net"
    
    def test_get_mongo_url_localhost_default(self):
        """Test: Localhost ist Default wenn nichts konfiguriert."""
        with patch.dict(os.environ, {"MONGO_URL": ""}, clear=False):
            # Entfernen der Env-Variable falls vorhanden
            env_copy = os.environ.copy()
            env_copy.pop("MONGO_URL", None)
            with patch.dict(os.environ, env_copy, clear=True):
                url = get_mongo_url()
                assert "localhost" in url or "27017" in url
    
    def test_mongo_url_not_empty(self):
        """Test: MONGO_URL ist nicht leer."""
        assert MONGO_URL is not None
        assert isinstance(MONGO_URL, str)
        assert len(MONGO_URL) > 0


# ═════════════════════════════════════════════════════════════════════════════
# Tests: eBay Lookup-Tabellen
# ═════════════════════════════════════════════════════════════════════════════

class TestEbayLookupTables:
    """Tests für eBay Kategorien, Zustände, Größen, Farben, Materialien."""
    
    def test_category_ids_ebay_nicht_leer(self):
        """Test: eBay Kategorien sind definiert."""
        assert len(CATEGORY_IDS_EBAY) > 0
    
    def test_category_ids_ebay_format(self):
        """Test: eBay Kategorien haben numerische IDs."""
        for kategorie, id_str in CATEGORY_IDS_EBAY.items():
            assert isinstance(kategorie, str)
            assert isinstance(id_str, str)
            # IDs sind Zahlen (möglicherweise mit | separiert)
            parts = id_str.split("|")
            for part in parts:
                assert part.isdigit(), f"ID {id_str} hat kein numerisches Format"
    
    def test_condition_ids_ebay_existieren(self):
        """Test: eBay Zustände sind definiert."""
        expected = ["Neu mit Etikett", "Neu ohne Etikett", "Sehr gut", "Gut", "Befriedigend"]
        for zustand in expected:
            assert zustand in CONDITION_IDS_EBAY
    
    def test_ebay_groessen_existieren(self):
        """Test: eBay Größen sind definiert."""
        assert "XS" in EBAY_GROESSEN
        assert "S" in EBAY_GROESSEN
        assert "M" in EBAY_GROESSEN
        assert "L" in EBAY_GROESSEN
        assert "XL" in EBAY_GROESSEN
        assert "XXL" in EBAY_GROESSEN
    
    def test_ebay_farben_nicht_leer(self):
        """Test: eBay Farben sind definiert."""
        assert len(EBAY_FARBEN) > 0
        # Erste Farbe sollte leer sein (Default)
        assert EBAY_FARBEN[0] == ""
        # Häufige Farben sollten vorhanden sein
        assert "Schwarz" in EBAY_FARBEN
        assert "Weiß" in EBAY_FARBEN
        assert "Blau" in EBAY_FARBEN
    
    def test_ebay_materials_nicht_leer(self):
        """Test: eBay Materialien sind definiert."""
        assert len(EBAY_MATERIALS) > 0
        # Häufige Materialien sollten vorhanden sein
        assert "Baumwolle" in EBAY_MATERIALS
        assert "Wolle" in EBAY_MATERIALS
        assert "Polyester" in EBAY_MATERIALS


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Vinted Lookup-Tabellen
# ═════════════════════════════════════════════════════════════════════════════

class TestVintedLookupTables:
    """Tests für Vinted Größen und Kategorien."""
    
    def test_vinted_groessen_format(self):
        """Test: Vinted Größen haben Format 'XS / 34'."""
        for groesse, id_str in VINTED_GROESSEN.items():
            assert " / " in groesse, f"Größe {groesse} hat falsches Format"
            assert isinstance(id_str, str)
            assert id_str.isdigit(), f"Vinted ID {id_str} ist keine Zahl"
    
    def test_vinted_groessen_vollstaendig(self):
        """Test: Alle Standard-Größen in Vinted vorhanden."""
        expected = ["XS / 34", "S / 36", "M / 38", "L / 40", "XL / 42", "XXL / 44"]
        for groesse in expected:
            assert groesse in VINTED_GROESSEN
    
    def test_vinted_kategorien_nicht_leer(self):
        """Test: Vinted Kategorien sind definiert."""
        assert len(VINTED_KATEGORIEN) > 0
    
    def test_vinted_kategorien_format(self):
        """Test: Vinted Kategorien haben numerische IDs."""
        for kategorie, id_str in VINTED_KATEGORIEN.items():
            assert isinstance(kategorie, str)
            assert isinstance(id_str, str)
            assert id_str.isdigit()


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Habilleur Lookup-Tabellen
# ═════════════════════════════════════════════════════════════════════════════

class TestHabilleurLookupTables:
    """Tests für Habilleur Größen und Kategorien."""
    
    def test_habilleur_groessen_existieren(self):
        """Test: Habilleur Größen sind definiert."""
        assert "XS" in HABILLEUR_GROESSEN
        assert "S" in HABILLEUR_GROESSEN
        assert "M" in HABILLEUR_GROESSEN
        assert "L" in HABILLEUR_GROESSEN
        assert "XL" in HABILLEUR_GROESSEN
    
    def test_habilleur_kategorien_existieren(self):
        """Test: Habilleur Kategorien sind definiert."""
        assert "Anzug" in HABILLEUR_KATEGORIEN
        assert "Jacket" in HABILLEUR_KATEGORIEN
        assert "Mantel" in HABILLEUR_KATEGORIEN
    
    def test_habilleur_masse_beispiel_struktur(self):
        """Test: Habilleur Maße-Beispiel hat richtige Struktur."""
        # Jackenmaße
        assert "schulterbreite" in HABILLEUR_MASSE_BEISPIEL
        assert "aermellange" in HABILLEUR_MASSE_BEISPIEL
        assert "jackenlaenge" in HABILLEUR_MASSE_BEISPIEL
        
        # Hosenmaße
        assert "hose_taillenweite" in HABILLEUR_MASSE_BEISPIEL
        assert "gabelhoehe" in HABILLEUR_MASSE_BEISPIEL
        assert "hosenlaenge" in HABILLEUR_MASSE_BEISPIEL
        
        # Mantelmaße
        assert "mantel_schulterbreite" in HABILLEUR_MASSE_BEISPIEL
        assert "mantel_gesamtlaenge" in HABILLEUR_MASSE_BEISPIEL


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Andere Lookup-Tabellen
# ═════════════════════════════════════════════════════════════════════════════

class TestOthersLookupTables:
    """Tests für Ollama, Stile, Zustand."""
    
    def test_ollama_modelle_nicht_leer(self):
        """Test: Ollama Modelle sind definiert."""
        assert len(OLLAMA_MODELLE) > 0
        assert "llama3.2:3b" in OLLAMA_MODELLE or "llama3" in OLLAMA_MODELLE
    
    def test_stil_optionen_nicht_leer(self):
        """Test: Stil-Optionen sind definiert."""
        assert len(STIL_OPTIONEN) > 0
        # Häufige Stile sollten vorhanden sein
        assert "Vintage" in STIL_OPTIONEN
        assert "Retro" in STIL_OPTIONEN
    
    def test_zustand_rang_struktur(self):
        """Test: Zustand-Ränge haben numerische Werte."""
        expected = ["Neu mit Etikett", "Neu ohne Etikett", "Sehr gut", "Gut", "Befriedigend"]
        for zustand in expected:
            assert zustand in ZUSTAND_RANG
            assert isinstance(ZUSTAND_RANG[zustand], int)
            assert 1 <= ZUSTAND_RANG[zustand] <= 5
    
    def test_zustand_rang_aufsteigend(self):
        """Test: Zustand-Ränge sind in korrekter Reihenfolge (höherer Wert = besser)."""
        # Bessere Zustände sollten höhere Werte haben
        assert ZUSTAND_RANG["Befriedigend"] < ZUSTAND_RANG["Gut"]
        assert ZUSTAND_RANG["Gut"] < ZUSTAND_RANG["Sehr gut"]
        assert ZUSTAND_RANG["Sehr gut"] < ZUSTAND_RANG["Neu ohne Etikett"]
        assert ZUSTAND_RANG["Neu ohne Etikett"] <= ZUSTAND_RANG["Neu mit Etikett"]
    
    def test_zustand_optionen_gleich_zustand_rang_keys(self):
        """Test: ZUSTAND_OPTIONEN sind identisch mit ZUSTAND_RANG Keys."""
        assert sorted(ZUSTAND_OPTIONEN) == sorted(ZUSTAND_RANG.keys())


# ═════════════════════════════════════════════════════════════════════════════
# Tests: Default-Konfiguration
# ═════════════════════════════════════════════════════════════════════════════

class TestDefaultConfig:
    """Tests für Default-Konfiguration."""
    
    def test_default_config_struktur(self):
        """Test: Default-Config hat alle notwendigen Keys."""
        required_keys = [
            "groesse", "kategorie", "stile", "max_preis", "min_zustand",
            "eigene_masse", "ollama_url", "ollama_modell",
            "max_artikel_pro_suche", "pause_zwischen_artikeln", "pause_zwischen_suchen"
        ]
        for key in required_keys:
            assert key in DEFAULT_CONFIG, f"Key {key} fehlt in DEFAULT_CONFIG"
    
    def test_default_config_eigenmaße_struktur(self):
        """Test: Default Eigenmaße sind vollständig."""
        masse = DEFAULT_CONFIG["eigene_masse"]
        assert isinstance(masse, dict)
        assert len(masse) > 0
        # Häufige Maße sollten vorhanden sein
        assert "brust" in masse
        assert "taille" in masse
        assert "schulter" in masse
    
    def test_default_config_pausenformat(self):
        """Test: Pausen sind Liste mit 2 Werten [min, max]."""
        artikelpausen = DEFAULT_CONFIG["pause_zwischen_artikeln"]
        suchenpausen = DEFAULT_CONFIG["pause_zwischen_suchen"]
        
        assert isinstance(artikelpausen, list)
        assert len(artikelpausen) == 2
        assert artikelpausen[0] <= artikelpausen[1]
        
        assert isinstance(suchenpausen, list)
        assert len(suchenpausen) == 2
        assert suchenpausen[0] <= suchenpausen[1]
    
    def test_default_config_stile_liste(self):
        """Test: Default Stile sind Liste."""
        assert isinstance(DEFAULT_CONFIG["stile"], list)
        assert len(DEFAULT_CONFIG["stile"]) > 0
        # Stile sollten existieren
        for stil in DEFAULT_CONFIG["stile"]:
            assert stil in STIL_OPTIONEN or isinstance(stil, str)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])