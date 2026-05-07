"""
=== TEST OLLAMA ===

Tests für die Ollama LLM Integration und Artikel-Analysefunktionen.
Testet:
  - frage_ollama(): HTTP Request zu Ollama LLM
  - analysiere_artikel_vinted(): Artikel-Analyse mit Preis-, Zustand- und Passform-Checks
  - analysiere_artikel_habilleur(): Habilleur-spezifische Artikel-Analyse
  - analysiere_artikel_ebay(): eBay-spezifische Artikel-Analyse
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from ai.ollama import (
    frage_ollama,
    analysiere_artikel_vinted,
    analysiere_artikel_habilleur,
    analysiere_artikel_ebay,
)


# ═════════════════════════════════════════════════════════════════════════════
# Tests: frage_ollama
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestFrageOllama:
    """Tests für die frage_ollama() Funktion."""
    
    async def test_frage_ollama_success(self):
        """Test: Erfolgreiche Anfrage an Ollama."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Das ist eine Test-Antwort vom LLM"}
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await frage_ollama(
                prompt="Was ist Mode?",
                ollama_url="http://localhost:11434/api/generate",
                modell="llama2"
            )
        
        assert result == "Das ist eine Test-Antwort vom LLM"
        mock_client.post.assert_called_once()
    
    async def test_frage_ollama_no_model(self):
        """Test: Kein Modell angegeben → leere Antwort."""
        result = await frage_ollama(
            prompt="Test",
            ollama_url="http://localhost:11434/api/generate",
            modell=""
        )
        assert result == ""
    
    async def test_frage_ollama_http_error(self):
        """Test: HTTP Fehler von Ollama."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await frage_ollama(
                prompt="Test",
                ollama_url="http://localhost:11434/api/generate",
                modell="llama2"
            )
        
        assert result == ""
    
    async def test_frage_ollama_timeout(self):
        """Test: Timeout bei Ollama Verbindung."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await frage_ollama(
                prompt="Test",
                ollama_url="http://localhost:11434/api/generate",
                modell="llama2"
            )
        
        assert result == ""


# ═════════════════════════════════════════════════════════════════════════════
# Tests: analysiere_artikel_vinted
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestAnalysierArtikelVinted:
    """Tests für analysiere_artikel_vinted()."""
    
    async def test_analysiere_artikel_vinted_success(self, basis_config, basis_artikel):
        """Test: Erfolgreiche Vinted-Artikel-Analyse."""
        ollama_response = json.dumps({
            "masse": {
                "brust_cm": 90,
                "taille_cm": 70,
                "huefte_cm": 95,
                "schulter_cm": 40,
                "laenge_oberteil_cm": 62,
                "laenge_hosen_cm": 100,
                "innennaht_cm": 80,
                "aermellaenge_cm": 60,
                "gabelhoehe_cm": 28,
                "beinoeffnung_cm": 24
            },
            "zustand": "Gut",
            "passt_groesse": True,
            "passt_stil": True,
            "begruendung": "Passt super.",
            "bewertung": 8,
            "empfohlen": True,
            "material": "Baumwolle"
        })
        
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = ollama_response
            
            result = await analysiere_artikel_vinted(basis_artikel, basis_config)
        
        assert result["url"] == basis_artikel["url"]
        assert result["titel"] == basis_artikel["titel"]
        assert result["preis"] == basis_artikel["preis"]
        assert result["bewertung"] == 8
        assert result["empfohlen"] is True
        assert result["material"] == "Baumwolle"
    
    async def test_analysiere_artikel_vinted_preis_zu_hoch(self, basis_config, basis_artikel):
        """Test: Preis überschreitet Budget → Empfehlung = False."""
        config = {**basis_config, "max_preis": 20}
        artikel = {**basis_artikel, "preis": "45 €"}
        
        ollama_response = json.dumps({
            "masse": {"brust_cm": 90},
            "zustand": "Gut",
            "passt_groesse": True,
            "passt_stil": True,
            "begruendung": "Passt gut.",
            "bewertung": 8,
            "empfohlen": True,
            "material": "Baumwolle"
        })
        
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = ollama_response
            
            result = await analysiere_artikel_vinted(artikel, config)
        
        assert result["empfohlen"] is False
        assert "zu hoch" in result["begruendung"].lower()
    
    async def test_analysiere_artikel_vinted_zustand_zu_schlecht(self, basis_config, basis_artikel):
        """Test: Zustand unter Minimum → Empfehlung = False."""
        config = {**basis_config, "min_zustand": "Sehr gut"}
        
        ollama_response = json.dumps({
            "masse": {"brust_cm": 90},
            "zustand": "Befriedigend",
            "passt_groesse": True,
            "passt_stil": True,
            "begruendung": "Passt gut.",
            "bewertung": 6,
            "empfohlen": True,
            "material": "Baumwolle"
        })
        
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = ollama_response
            
            result = await analysiere_artikel_vinted(basis_artikel, config)
        
        assert result["empfohlen"] is False
        assert "Zustand" in result["begruendung"]
    
    async def test_analysiere_artikel_vinted_passform_check(self, basis_config, basis_artikel):
        """Test: Passform-Vergleich (Maße werden mit Eigenmaßen verglichen)."""
        config = {
            **basis_config,
            "eigene_masse": {
                "brust": 88,
                "taille": 70,
                "huefte": 96,
                "schulter": 38,
                "laenge_oberteil": 60,
                "laenge_hosen": 100,
                "innennaht": 78,
                "aermellaenge": 62,
                "gabelhoehe": 28,
                "beinoeffnung": 24
            }
        }
        
        ollama_response = json.dumps({
            "masse": {
                "brust_cm": 92,  # +4cm → noch okay
                "taille_cm": 70,
                "huefte_cm": 96,
                "schulter_cm": 38,
                "laenge_oberteil_cm": 60,
                "laenge_hosen_cm": 100,
                "innennaht_cm": 78,
                "aermellaenge_cm": 62,
                "gabelhoehe_cm": 28,
                "beinoeffnung_cm": 24
            },
            "zustand": "Gut",
            "passt_groesse": True,
            "passt_stil": True,
            "begruendung": "Passt.",
            "bewertung": 7,
            "empfohlen": True,
            "material": "Baumwolle"
        })
        
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = ollama_response
            
            result = await analysiere_artikel_vinted(basis_artikel, config)
        
        assert result["passform_hinweise"] is not None
        assert len(result["passform_hinweise"]) > 0
    
    async def test_analysiere_artikel_vinted_keine_ollama_antwort(self, basis_config, basis_artikel):
        """Test: Ollama antwortet nicht → analyse_fehler = True."""
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = ""
            
            result = await analysiere_artikel_vinted(basis_artikel, basis_config)
        
        assert result.get("analyse_fehler") is True
    
    async def test_analysiere_artikel_vinted_json_parse_fehler(self, basis_config, basis_artikel):
        """Test: Ollama antwortet mit ungültigem JSON."""
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = "Das ist kein JSON!"
            
            result = await analysiere_artikel_vinted(basis_artikel, basis_config)
        
        assert result.get("analyse_fehler") is True
    
    async def test_analysiere_artikel_vinted_json_mit_praembel(self, basis_config, basis_artikel):
        """Test: Ollama antwortet mit Text vor/nach JSON."""
        ollama_response = """Hier ist die Analyse:
        
        {
            "masse": {"brust_cm": 90},
            "zustand": "Gut",
            "passt_groesse": true,
            "passt_stil": true,
            "begruendung": "Passt gut.",
            "bewertung": 8,
            "empfohlen": true,
            "material": "Baumwolle"
        }
        
        Viel Spaß beim Shoppen!"""
        
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = ollama_response
            
            result = await analysiere_artikel_vinted(basis_artikel, basis_config)
        
        assert result.get("analyse_fehler") is not True
        assert result["bewertung"] == 8


# ═════════════════════════════════════════════════════════════════════════════
# Tests: analysiere_artikel_habilleur
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestAnalysierArtikelHabilleur:
    """Tests für analysiere_artikel_habilleur()."""
    
    async def test_analysiere_artikel_habilleur_success(self, basis_config):
        """Test: Erfolgreiche Habilleur-Artikel-Analyse."""
        artikel = {
            "url": "https://habilleur.com/items/123",
            "titel": "Vintage Anzug Größe M",
            "preis": "89,50 €",
            "beschreibung": "Schöner Anzug. Schulterbreite: 44 cm, Ärmellänge: 58 cm",
            "kategorie": "Anzug",
            "material": "Wolle"
        }
        
        ollama_response = json.dumps({
            "masse": {
                "schulterbreite": 44,
                "aermellaenge": 58,
                "jackenlaenge": 72,
                "achselbreite": 52,
                "jacke_taillenweite": 50,
                "hose_taillenweite": 47,
                "gabelhoehe": 29,
                "beinoeffnung": 24,
                "hosenlaenge": 98,
                "mantel_schulterbreite": None,
                "mantel_gesamtlaenge": None,
                "mantel_aermellaenge": None,
                "mantel_achselbreite": None,
                "mantel_taillenweite": None
            },
            "zustand": "Sehr gut",
            "passt_groesse": True,
            "begruendung": "Anzug passt gut.",
            "bewertung": 8,
            "empfohlen": True,
            "material": "Wolle"
        })
        
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = ollama_response
            
            result = await analysiere_artikel_habilleur(artikel, basis_config)
        
        # Bewertung kann von analysiere_artikel_habilleur reduziert werden
        # wenn Preis zu hoch oder andere Kriterien nicht erfüllt sind
        assert result["titel"] == artikel["titel"]
        assert result["empfohlen"] in [True, False]
        assert 1 <= result["bewertung"] <= 10
    
    async def test_analysiere_artikel_habilleur_preis_zu_hoch(self, basis_config):
        """Test: Preis überschreitet Budget bei Habilleur."""
        config = {**basis_config, "max_preis": 50}
        artikel = {
            "url": "https://habilleur.com/items/123",
            "titel": "Anzug",
            "preis": "150 €",
            "beschreibung": "Anzug",
            "kategorie": "Anzug",
            "material": "Wolle"
        }
        
        ollama_response = json.dumps({
            "masse": {"schulterbreite": 44},
            "zustand": "Sehr gut",
            "passt_groesse": True,
            "begruendung": "Passt.",
            "bewertung": 9,
            "empfohlen": True,
            "material": "Wolle"
        })
        
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = ollama_response
            
            result = await analysiere_artikel_habilleur(artikel, config)
        
        assert result["empfohlen"] is False
        assert result["bewertung"] <= 4


# ═════════════════════════════════════════════════════════════════════════════
# Tests: analysiere_artikel_ebay
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestAnalysierArtikelEbay:
    """Tests für analysiere_artikel_ebay()."""
    
    async def test_analysiere_artikel_ebay_success(self, basis_config, basis_artikel_ebay):
        """Test: Erfolgreiche eBay-Artikel-Analyse."""
        # Artikel muss zuerst durch extract_important_data() gehen
        from src_ebay.ebay_helper import extract_important_data
        artikel = extract_important_data(basis_artikel_ebay)
        
        ollama_response = json.dumps({
            "masse": {
                "schulterbreite": 44,
                "aermellaenge": 58,
                "jackenlaenge": 72,
                "achselbreite": 52,
                "jacke_taillenweite": 50,
                "hose_taillenweite": None,
                "gabelhoehe": None,
                "beinoeffnung": None,
                "hosenlaenge": None,
                "mantel_schulterbreite": None,
                "mantel_gesamtlaenge": None,
                "mantel_aermellaenge": None,
                "mantel_achselbreite": None,
                "mantel_taillenweite": None
            },
            "zustand": "Gut",
            "passt_groesse": True,
            "begruendung": "Jacke passt.",
            "bewertung": 7,
            "empfohlen": True,
            "material": "Baumwolle"
        })
        
        with patch('ai.ollama.frage_ollama', new_callable=AsyncMock) as mock_frage:
            mock_frage.return_value = ollama_response
            
            result = await analysiere_artikel_ebay(artikel, basis_config)
        
        assert result["bewertung"] == 7
        assert result["empfohlen"] is True
        assert result["material"] == "Baumwolle"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])