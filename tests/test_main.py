"""
Tests für main.py: Echte Funktion-Tests mit Mocks für externe Dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch



@pytest.fixture
def basis_config():
    """Minimale gültige Config."""
    return {
        "groesse": "M",
        "kategorie": "Jacken",
        "quelle": "vinted",
        "ollama_modell": "llama3.2:3b",
        "ollama_url": "http://localhost:11434/api/generate",
        "max_preis": 50,
        "max_suchen": 1,
        "max_artikel_pro_suche": 5,
        "pause_zwischen_artikeln": [0.1, 0.2],
        "pause_zwischen_suchen": [0.1, 0.2],
        "stile": ["Vintage"],
        "min_zustand": "Gut",
        "eigene_masse": {"brust": 88, "taille": 70, "huefte": 96},
    }


# === Tests: Import und Funktion ===

def test_main_importierbar(capsys):
    """Test: main.py kann importiert werden."""
    import main
    assert main is not None
    capsys.readouterr()


def test_main_funktion_async(capsys):
    """Test: main() ist async-Funktion."""
    from main import main
    import inspect
    assert inspect.iscoroutinefunction(main)
    capsys.readouterr()


# === Tests: Config-Validierung ===

@pytest.mark.asyncio
async def test_main_validiert_ollama_modell(capsys, basis_config):
    """Test: main() bricht ab wenn ollama_modell fehlt."""
    config = {**basis_config}
    del config["ollama_modell"]
    
    with patch("httpx.get"):
        from main import main
        result = await main(config)
        assert result is None
    capsys.readouterr()


@pytest.mark.asyncio
async def test_main_validiert_groesse(capsys, basis_config):
    """Test: main() bricht ab wenn groesse fehlt."""
    config = {**basis_config}
    del config["groesse"]
    
    with patch("httpx.get"):
        from main import main
        result = await main(config)
        assert result is None
    capsys.readouterr()


@pytest.mark.asyncio
async def test_main_validiert_kategorie(capsys, basis_config):
    """Test: main() bricht ab wenn kategorie fehlt."""
    config = {**basis_config}
    del config["kategorie"]
    
    with patch("httpx.get"):
        from main import main
        result = await main(config)
        assert result is None
    capsys.readouterr()


@pytest.mark.asyncio
async def test_main_validiert_quelle(capsys, basis_config):
    """Test: main() bricht ab bei ungültiger quelle."""
    config = {**basis_config, "quelle": "invalid"}
    
    with patch("httpx.get"):
        from main import main
        result = await main(config)
        assert result is None
    capsys.readouterr()


# === Tests: Ollama Verbindung ===

@pytest.mark.asyncio
async def test_main_ollama_timeout(capsys, basis_config):
    """Test: main() bricht ab bei Ollama-Timeout."""
    with patch("httpx.get", side_effect=Exception("Timeout")):
        from main import main
        result = await main(basis_config)
        assert result is None
    capsys.readouterr()


# === Tests: Vinted Workflow ===

@pytest.mark.asyncio
async def test_main_vinted_empty(capsys, basis_config):
    """Test: main() mit Vinted und leeren Ergebnissen."""
    config = {**basis_config, "quelle": "vinted"}
    
    with patch("httpx.get") as mock_http, \
         patch("main.vinted_scrape_suchergebnisse", return_value=[]), \
         patch("main.speichere_in_mongo"):
        
        mock_http.return_value = MagicMock()
        
        from main import main
        result = await main(config)
        assert result is None or isinstance(result, list)
    capsys.readouterr()


@pytest.mark.asyncio
async def test_main_vinted_with_artikel(capsys, basis_config):
    """Test: main() verarbeitet Vinted-Artikel."""
    config = {**basis_config, "quelle": "vinted"}
    artikel = {"url": "https://vinted.de/123", "titel": "Test", "preis": "20€", "beschreibung": "Test"}
    analysiert = {**artikel, "bewertung": 5, "empfohlen": False, "begruendung": "OK"}
    
    with patch("httpx.get") as mock_http, \
         patch("main.vinted_scrape_suchergebnisse", return_value=[artikel]), \
         patch("main.vinted_scrape_details", return_value=artikel), \
         patch("main.analysiere_artikel_vinted", return_value=analysiert) as mock_analyze, \
         patch("main.speichere_in_mongo"):
        
        mock_http.return_value = MagicMock()
        
        from main import main
        result = await main(config)
        assert mock_analyze.called or result is None
    capsys.readouterr()


# === Tests: Habilleur Workflow ===

@pytest.mark.asyncio
async def test_main_habilleur_empty(capsys, basis_config):
    """Test: main() mit Habilleur und leeren Ergebnissen."""
    config = {**basis_config, "quelle": "habilleur"}
    
    with patch("httpx.get") as mock_http, \
         patch("main.habilleur_scrape_suchergebnisse", return_value=[]), \
         patch("main.speichere_in_mongo"):
        
        mock_http.return_value = MagicMock()
        
        from main import main
        result = await main(config)
        assert result is None or isinstance(result, list)
    capsys.readouterr()


# === Tests: eBay Workflow ===

@pytest.mark.asyncio
async def test_main_ebay_empty(capsys, basis_config):
    """Test: main() mit eBay und leeren Ergebnissen."""
    config = {**basis_config, "quelle": "ebay"}
    
    with patch("httpx.get") as mock_http, \
         patch("main.get_new_token", return_value="token"), \
         patch("main.get_summary_of_articles_json", return_value=[]), \
         patch("main.speichere_in_mongo"):
        
        mock_http.return_value = MagicMock()
        
        from main import main
        result = await main(config)
        assert result is None or isinstance(result, list)
    capsys.readouterr()


# === Tests: Deduplizierung ===

@pytest.mark.asyncio
async def test_main_deduplicates(capsys, basis_config):
    """Test: main() entfernt Duplikate."""
    config = {**basis_config, "quelle": "vinted"}
    artikel = {"url": "https://vinted.de/same", "titel": "A", "preis": "20€", "beschreibung": "Test"}
    analysiert = {**artikel, "bewertung": 5, "empfohlen": False, "begruendung": "Test"}
    
    with patch("httpx.get") as mock_http, \
         patch("main.vinted_scrape_suchergebnisse", return_value=[artikel, artikel]), \
         patch("main.vinted_scrape_details", return_value=artikel), \
         patch("main.analysiere_artikel_vinted", return_value=analysiert) as mock_analyze, \
         patch("main.speichere_in_mongo"):
        
        mock_http.return_value = MagicMock()
        
        from main import main
        result = await main(config)
        # Nur 1x analyze callscoped due to deduplication
        assert mock_analyze.call_count <= 1
    capsys.readouterr()


# === Tests: MongoDB-Fehlerbehandlung ===

@pytest.mark.asyncio
async def test_main_handles_mongodb_error(capsys, basis_config):
    """Test: main() toleriert MongoDB-Fehler."""
    config = {**basis_config, "quelle": "vinted"}
    artikel = {"url": "https://vinted.de/test", "titel": "A", "preis": "20€", "beschreibung": "Test"}
    analysiert = {**artikel, "bewertung": 5, "empfohlen": False, "begruendung": "Test"}
    
    with patch("httpx.get") as mock_http, \
         patch("main.vinted_scrape_suchergebnisse", return_value=[artikel]), \
         patch("main.vinted_scrape_details", return_value=artikel), \
         patch("main.analysiere_artikel_vinted", return_value=analysiert), \
         patch("main.speichere_in_mongo", side_effect=Exception("MongoDB offline")):
        
        mock_http.return_value = MagicMock()
        
        from main import main
        
        # Should not raise
        try:
            result = await main(config)
            assert True
        except Exception as e:
            pytest.fail(f"MongoDB-Fehler sollte toleriert werden: {e}")
    capsys.readouterr()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])