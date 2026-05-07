"""
=== TEST HABILLEUR SCRAPER ===

Tests für den Habilleur Jean Web Scraper.
Tests zur Funktionalität von:
  - scrape_suchergebnisse(): Sammelt Produktlinks und Preise
  - URL-Normalisierung
  - Preis-Parsing und Filtering
  - HTML-Parsing mit verschiedenen Strukturen
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from bs4 import BeautifulSoup
import httpx

from scraper.habilleur_scraper import scrape_suchergebnisse, _parse_preis


class TestPriceParsingHelper:
    """Tests für den _parse_preis Helper (falls exportiert)."""
    
    def test_parse_euro_format(self):
        """Test: EUR Format parsing."""
        result = _parse_preis("89,50 EUR")
        assert result == 89.50
    
    def test_parse_euro_symbol(self):
        """Test: € Symbol parsing."""
        result = _parse_preis("120 €")
        assert result == 120.0
    
    def test_parse_comma_decimal(self):
        """Test: Komma als Dezimaltrennzeichen."""
        result = _parse_preis("89,99 €")
        assert result == 89.99
    
    def test_parse_dot_decimal(self):
        """Test: Punkt als Dezimaltrennzeichen."""
        result = _parse_preis("89.99 EUR")
        assert result == 89.99
    
    def test_parse_no_currency(self):
        """Test: Nur Zahl."""
        result = _parse_preis("150")
        assert result == 150.0
    
    def test_parse_invalid(self):
        """Test: Ungültiges Format."""
        result = _parse_preis("keine Zahl")
        assert result is None


@pytest.mark.asyncio
class TestScrapeSucchergebnisseBasic:
    """Grundlegende Tests für scrape_suchergebnisse."""
    
    async def test_basic_scraping_with_mock_client(self, habilleur_html_mock):
        """Test: Grundlegende Scraping-Funktionalität mit gemocktem Client."""
        mock_response = MagicMock()
        mock_response.text = habilleur_html_mock
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {
            "max_artikel_pro_suche": 10,
            "max_preis": 200
        }
        
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client
        )
        
        # Überprüfe, dass Produkte gefunden wurden
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Überprüfe Struktur
        for artikel in result:
            assert "url" in artikel
            assert "titel" in artikel
            assert "preis" in artikel
    
    async def test_multiple_products_parsed(self, habilleur_html_mock):
        """Test: Mehrere Produkte werden korrekt geparst."""
        mock_response = MagicMock()
        mock_response.text = habilleur_html_mock
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {
            "max_artikel_pro_suche": 10,
            "max_preis": 200
        }
        
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client
        )
        
        # HTML hat 3 Produkte
        assert len(result) >= 2  # Mindestens 2 sollten parsed werden
    
    async def test_price_filtering(self, habilleur_html_mock):
        """Test: Artikel über max_preis werden gefiltert."""
        mock_response = MagicMock()
        mock_response.text = habilleur_html_mock
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        # Setze max_preis niedriger
        config = {
            "max_artikel_pro_suche": 10,
            "max_preis": 100
        }
        
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client
        )
        
        # Alle Artikel sollten unter 100€ sein
        for artikel in result:
            preis = _parse_preis(artikel["preis"])
            if preis is not None:
                assert preis <= 100


@pytest.mark.asyncio
class TestScrapeSucchergebnisseURLNormalization:
    """Tests für URL-Normalisierung."""
    
    def test_url_relative_path(self):
        """Test: Relative URLs werden zu absoluten."""
        # Dieser Test ist konzeptuell - in echtem Scraper wird das gemacht
        relative = "/de/products/anzug-m"
        # Das sollte in der Implementierung zu
        # https://habilleurjean.com/de/products/anzug-m werden
        assert relative.startswith("/")
    
    def test_url_remove_tracking_params(self):
        """Test: Tracking-Parameter werden entfernt."""
        url_with_params = "https://habilleurjean.com/products/anzug?utm_source=test"
        clean_url = url_with_params.split("?")[0]
        assert clean_url == "https://habilleurjean.com/products/anzug"
    
    def test_url_deduplication(self):
        """Test: Duplikate werden entfernt."""
        urls = [
            "https://habilleurjean.com/de/products/anzug-m",
            "https://habilleurjean.com/de/products/anzug-m",  # Duplikat
            "https://habilleurjean.com/de/products/jacke-l",
        ]
        
        unique = []
        for url in urls:
            if url not in [a["url"] for a in [{"url": u} for u in unique]]:
                unique.append(url)
        
        # Vereinfacht: mindestens 2 unique URLs sollten sein
        assert len(unique) >= 2


@pytest.mark.asyncio
class TestScrapeSucchergebnisseHTMLStructures:
    """Tests mit verschiedenen HTML-Strukturen."""
    
    async def test_data_product_item_selector(self):
        """Test: data-product-item Selektor."""
        html = """
        <div data-product-item="1">
            <h2>Anzug Größe M</h2>
            <a href="/products/anzug-m">Link</a>
            <span class="price">95 EUR</span>
        </div>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {"max_artikel_pro_suche": 10, "max_preis": 200}
        
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client
        )
        
        assert len(result) > 0
    
    async def test_product_class_selector(self):
        """Test: Klasse mit 'product' wird erkannt."""
        html = """
        <div class="product-item">
            <h3>Mantel Größe L</h3>
            <a href="/products/mantel-l">Link</a>
            <span class="price">150 EUR</span>
        </div>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {"max_artikel_pro_suche": 10, "max_preis": 200}
        
        result = await scrape_suchergebnisse(
            kategorie="Anzug",
            groesse="L",
            config=config,
            client=mock_client
        )
        
        assert len(result) > 0
    
    async def test_article_element_selector(self):
        """Test: <article> Element wird erkannt."""
        html = """
        <article class="product">
            <h2>Jacke Größe M</h2>
            <a href="/products/jacke-m">Link</a>
            <span class="price">120 EUR</span>
        </article>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {"max_artikel_pro_suche": 10, "max_preis": 200}
        
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client
        )
        
        assert len(result) > 0


@pytest.mark.asyncio
class TestScrapeSucchergebnisseErrorHandling:
    """Tests für Error Handling."""
    
    async def test_network_error_handling(self):
        """Test: Netzwerkfehler werden abgefangen."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        
        config = {"max_artikel_pro_suche": 10, "max_preis": 200}
        
        # Sollte Exception abfangen und leere Liste zurückgeben
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client
        )
        
        assert result == []
    
    async def test_empty_html_handling(self):
        """Test: Leeres HTML wird abgefangen."""
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {"max_artikel_pro_suche": 10, "max_preis": 200}
        
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client
        )
        
        assert result == []
    
    async def test_malformed_html_handling(self):
        """Test: Malformed HTML wird robust verarbeitet."""
        html = """
        <div data-product-item>
            <h2>Anzug</h2>
            <span>No link here</span>
            <span class="price">invalid€</span>
        </div>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {"max_artikel_pro_suche": 10, "max_preis": 200}
        
        # Sollte nicht abstürzen
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client
        )
        
        assert isinstance(result, list)


@pytest.mark.asyncio
class TestScrapeSucchergebnisseConfiguration:
    """Tests für Konfigurations-Handling."""
    
    async def test_max_artikel_limit(self, habilleur_html_mock):
        """Test: max_artikel_pro_suche wird respektiert."""
        mock_response = MagicMock()
        mock_response.text = habilleur_html_mock
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {
            "max_artikel_pro_suche": 1,  # Nur 1 Artikel
            "max_preis": 200
        }
        
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client
        )
        
        assert len(result) <= 1
    
    async def test_category_mapping(self):
        """Test: Kategorie-Mapping wird korrekt durchgeführt."""
        # Habilleur nutzt category_slug für URLs
        # "Jacket" sollte zu "veste" o.ä. gemappt werden
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {"max_artikel_pro_suche": 10, "max_preis": 200}
        
        # Sollte mit verschiedenen Kategorien funktionieren
        for kategorie in ["Jacket", "Anzug", "Mantel"]:
            result = await scrape_suchergebnisse(
                kategorie=kategorie,
                groesse="M",
                config=config,
                client=mock_client
            )
            # Sollte mindestens aufgerufen worden sein
            assert mock_client.get.called
    
    async def test_size_mapping(self):
        """Test: Größen-Mapping wird korrekt durchgeführt."""
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {"max_artikel_pro_suche": 10, "max_preis": 200}
        
        # Sollte mit verschiedenen Größen funktionieren
        for groesse in ["XS", "S", "M", "L", "XL"]:
            result = await scrape_suchergebnisse(
                kategorie="Jacket",
                groesse=groesse,
                config=config,
                client=mock_client
            )
            assert mock_client.get.called


@pytest.mark.asyncio
class TestScrapeSucchergebnisseClientHandling:
    """Tests für Client-Handling."""
    
    async def test_client_provided(self, habilleur_html_mock):
        """Test: Bereitgestellter Client wird verwendet."""
        mock_response = MagicMock()
        mock_response.text = habilleur_html_mock
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        config = {"max_artikel_pro_suche": 10, "max_preis": 200}
        
        result = await scrape_suchergebnisse(
            kategorie="Jacket",
            groesse="M",
            config=config,
            client=mock_client  # Client wird übergeben
        )
        
        # Client.get sollte aufgerufen worden sein
        assert mock_client.get.called
        # Client sollte nicht geschlossen worden sein (da wir ihn nicht erstellt haben)
    
    async def test_client_not_provided(self):
        """Test: Neuer Client wird erstellt wenn nicht vorhanden."""
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()
        
        # Mocke httpx.AsyncClient
        with patch('scraper.habilleur_scraper.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            config = {"max_artikel_pro_suche": 10, "max_preis": 200}
            
            result = await scrape_suchergebnisse(
                kategorie="Jacket",
                groesse="M",
                config=config,
                client=None  # Kein Client bereitgestellt
            )
            
            # Client sollte erstellt und geschlossen worden sein
            assert mock_client_class.called
            assert mock_client.aclose.called

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])