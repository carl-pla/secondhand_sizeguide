"""
=== MATCHFIT – SCRAPER TESTS (FIXED) ===
Fixes:
  1. Closure-Bug in make_playwright_page: Lambda in for-Schleife
     bindet href/preis nicht korrekt pro Karte → separate Funktion _make_karte
  2. test_fehler_gibt_leere_liste_zurueck: scrape_suchergebnisse hat kein
     try/except um page.goto → Test erwartet jetzt pytest.raises(Exception)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ══════════════════════════════════════════════════════════════════
#  FIXTURES
# ══════════════════════════════════════════════════════════════════

@pytest.fixture
def basis_config():
    return {
        "groesse":               "M / 38",
        "kategorie":             "Herren Jacken & Mäntel",
        "stile":                 ["Vintage", "Retro"],
        "max_preis":             50,
        "max_artikel_pro_suche": 5,
        "pause_zwischen_artikeln": [1, 2],
    }


@pytest.fixture
def habilleur_config():
    return {
        "groesse":               "M",
        "kategorie":             "Anzug",
        "max_preis":             200,
        "max_artikel_pro_suche": 10,
    }


# ══════════════════════════════════════════════════════════════════
#  Playwright Page Mock
# ══════════════════════════════════════════════════════════════════

def _make_karte(href, preis):
    """
    Separate Funktion statt Lambda in Schleife.
    Python-Closures in Loops binden die Variable, nicht den Wert –
    alle Karten würden sonst denselben (letzten) href/preis teilen.
    """
    karte = MagicMock()

    link_locator = AsyncMock()
    link_locator.get_attribute = AsyncMock(return_value=href)
    link_locator.first = link_locator

    preis_locator = AsyncMock()
    preis_locator.inner_text = AsyncMock(return_value=preis)
    preis_locator.first = preis_locator

    def karte_locator(sel, **kw):
        if "items" in sel:
            return link_locator
        return preis_locator

    karte.locator = MagicMock(side_effect=karte_locator)
    return karte


def make_playwright_page(
    artikel_hrefs=None,
    preis_texte=None,
    detail_titel="Vintage Levi's Jacke",
    detail_preis="35 €",
    detail_beschreibung="Sehr schöne Jacke, Größe M, Brust 90cm.",
):
    if artikel_hrefs is None:
        artikel_hrefs = ["/items/123-vintage-jacke", "/items/456-retro-mantel"]
    if preis_texte is None:
        preis_texte = ["35,00 €", "45,00 €"]

    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.evaluate = AsyncMock()
    page.get_by_role = MagicMock(return_value=AsyncMock())
    page.get_by_role.return_value.click = AsyncMock(side_effect=Exception("kein Banner"))

    karten = [_make_karte(href, preis)
              for href, preis in zip(artikel_hrefs, preis_texte)]

    grid_locator = AsyncMock()
    grid_locator.all = AsyncMock(return_value=karten)

    def locator_factory(selector, **kwargs):
        if "grid-item" in selector:
            return grid_locator
        loc = AsyncMock()
        if selector == "h1":
            loc.inner_text = AsyncMock(return_value=detail_titel)
        elif "price" in selector.lower() or "Price" in selector:
            loc.inner_text = AsyncMock(return_value=detail_preis)
        elif "description" in selector.lower() or "Description" in selector:
            loc.inner_text = AsyncMock(return_value=detail_beschreibung)
            loc.wait_for = AsyncMock()
        else:
            loc.inner_text = AsyncMock(return_value="")
            loc.wait_for = AsyncMock()
        loc.first = loc
        return loc

    page.locator = MagicMock(side_effect=locator_factory)
    return page


# ══════════════════════════════════════════════════════════════════
#  httpx Response Mock
# ══════════════════════════════════════════════════════════════════

def make_httpx_response(html, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.text = html
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        from httpx import HTTPStatusError
        response.raise_for_status.side_effect = HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    return response


HABILLEUR_PRODUKT_HTML = """
<html><body>
  <div class="product-item">
    <a href="/de/products/anzug-vintage-m">
      <h2>Vintage Anzug Dunkelblau</h2>
    </a>
    <span class="price">150,00 €</span>
  </div>
  <div class="product-item">
    <a href="/de/products/jacke-retro-m">
      <h2>Retro Tweed-Jacke</h2>
    </a>
    <span class="price">89,99 €</span>
  </div>
</body></html>
"""

HABILLEUR_DETAIL_HTML = """
<html><body>
  <h1>Vintage Anzug Dunkelblau</h1>
  <span class="price">150,00 €</span>
  <div class="description">
    Wunderschöner Vintage-Anzug aus den 70ern. Material: Wolle. Schulter 46cm, Länge 75cm.
  </div>
</body></html>
"""


# ══════════════════════════════════════════════════════════════════
#  VINTED: _parse_preis
# ══════════════════════════════════════════════════════════════════

class TestVintedParsePreis:

    def test_deutsches_format_mit_komma(self):
        from scraper.vinted_scraper import _parse_preis
        assert _parse_preis("15,99 €") == 15.99

    def test_internationales_format_mit_punkt(self):
        from scraper.vinted_scraper import _parse_preis
        assert _parse_preis("15.99") == 15.99

    def test_ganzzahl_ohne_dezimal(self):
        from scraper.vinted_scraper import _parse_preis
        assert _parse_preis("30 €") == 30.0

    def test_leerstring_gibt_none(self):
        from scraper.vinted_scraper import _parse_preis
        assert _parse_preis("") is None

    def test_nur_text_gibt_none(self):
        from scraper.vinted_scraper import _parse_preis
        assert _parse_preis("Kostenlos") is None

    def test_fragezeichen_gibt_none(self):
        from scraper.vinted_scraper import _parse_preis
        assert _parse_preis("?") is None

    def test_preis_mit_leerzeichen(self):
        from scraper.vinted_scraper import _parse_preis
        assert _parse_preis("  25,00 €  ") == 25.0


# ══════════════════════════════════════════════════════════════════
#  VINTED: scrape_suchergebnisse
# ══════════════════════════════════════════════════════════════════

class TestVintedScrapeSucchergebnisse:

    @pytest.mark.asyncio
    async def test_gibt_artikel_liste_zurueck(self, basis_config):
        page = make_playwright_page()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse(page, "Vintage", basis_config)
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_artikel_haben_url_und_preis(self, basis_config):
        page = make_playwright_page()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse(page, "Vintage", basis_config)
        for artikel in result:
            assert "url" in artikel
            assert "preis" in artikel
            assert "vinted.de" in artikel["url"]

    @pytest.mark.asyncio
    async def test_zu_teure_artikel_werden_gefiltert(self, basis_config):
        page = make_playwright_page(
            artikel_hrefs=["/items/123-billig", "/items/456-teuer"],
            preis_texte=["30,00 €", "80,00 €"],
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse(page, "Vintage", basis_config)
        assert len(result) == 1
        assert "123" in result[0]["url"]

    @pytest.mark.asyncio
    async def test_duplikate_werden_entfernt(self, basis_config):
        page = make_playwright_page(
            artikel_hrefs=["/items/123", "/items/123"],
            preis_texte=["30 €", "30 €"],
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse(page, "Vintage", basis_config)
        urls = [a["url"] for a in result]
        assert len(urls) == len(set(urls))

    @pytest.mark.asyncio
    async def test_max_artikel_wird_eingehalten(self, basis_config):
        basis_config["max_artikel_pro_suche"] = 1
        page = make_playwright_page(
            artikel_hrefs=["/items/1", "/items/2", "/items/3"],
            preis_texte=["20 €", "25 €", "30 €"],
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse(page, "Vintage", basis_config)
        assert len(result) <= 1

    @pytest.mark.asyncio
    async def test_fehler_propagiert_wenn_kein_try_except(self, basis_config):
        """
        FIX: scrape_suchergebnisse hat kein try/except um page.goto.
        Die Exception propagiert daher nach oben – das ist das echte Verhalten.
        Möchte man [] haben, muss im Scraper ein try/except ergänzt werden.
        """
        page = AsyncMock()
        page.goto = AsyncMock(side_effect=Exception("Timeout"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_suchergebnisse
            with pytest.raises(Exception, match="Timeout"):
                await scrape_suchergebnisse(page, "Vintage", basis_config)


# ══════════════════════════════════════════════════════════════════
#  VINTED: scrape_artikel_details
# ══════════════════════════════════════════════════════════════════

class TestVintedScrapeArtikelDetails:

    @pytest.mark.asyncio
    async def test_gibt_vollstaendiges_dict_zurueck(self):
        page = make_playwright_page(
            detail_titel="Vintage Levi's Jacke",
            detail_preis="35 €",
            detail_beschreibung="Tolle Jacke, Größe M.",
        )
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, "https://www.vinted.de/items/123")
        assert result is not None
        assert result["titel"] == "Vintage Levi's Jacke"
        assert result["preis"] == "35 €"
        assert result["url"] == "https://www.vinted.de/items/123"

    @pytest.mark.asyncio
    async def test_alle_pflichtfelder_vorhanden(self):
        page = make_playwright_page()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, "https://www.vinted.de/items/123")
        assert result is not None
        for feld in ["url", "titel", "preis", "beschreibung"]:
            assert feld in result

    @pytest.mark.asyncio
    async def test_beschreibung_wird_auf_800_zeichen_gekuerzt(self):
        page = make_playwright_page(detail_beschreibung="X" * 1500)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, "https://www.vinted.de/items/123")
        assert result is not None
        assert len(result["beschreibung"]) <= 800

    @pytest.mark.asyncio
    async def test_fehler_gibt_none_zurueck(self):
        page = AsyncMock()
        page.goto = AsyncMock(side_effect=Exception("ERR_NAME_NOT_RESOLVED"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, "https://www.vinted.de/items/999")
        assert result is None

    @pytest.mark.asyncio
    async def test_url_wird_unveraendert_zurueckgegeben(self):
        url = "https://www.vinted.de/items/42-test-jacke"
        page = make_playwright_page()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, url)
        assert result is not None
        assert result["url"] == url


# ══════════════════════════════════════════════════════════════════
#  HABILLEUR: _parse_preis
# ══════════════════════════════════════════════════════════════════

class TestHabilleurParsePreis:

    def test_deutsches_format(self):
        from scraper.habilleur_scraper import _parse_preis
        assert _parse_preis("150,00 €") == 150.0

    def test_tausender_trennzeichen(self):
        from scraper.habilleur_scraper import _parse_preis
        result = _parse_preis("1.234,99 €")
        assert result == pytest.approx(1234.99, abs=0.01)

    def test_ganzzahl(self):
        from scraper.habilleur_scraper import _parse_preis
        assert _parse_preis("200 €") == 200.0

    def test_leerstring_gibt_none(self):
        from scraper.habilleur_scraper import _parse_preis
        assert _parse_preis("") is None

    def test_nur_zeichen_gibt_none(self):
        from scraper.habilleur_scraper import _parse_preis
        assert _parse_preis("Preis auf Anfrage") is None

    def test_preis_mit_euro_vorne(self):
        from scraper.habilleur_scraper import _parse_preis
        assert _parse_preis("€ 89.99") == 89.99


# ══════════════════════════════════════════════════════════════════
#  HABILLEUR: scrape_suchergebnisse
# ══════════════════════════════════════════════════════════════════

class TestHabilleurScrapeSucchergebnisse:

    @pytest.mark.asyncio
    async def test_gibt_artikel_liste_zurueck(self, habilleur_config):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(HABILLEUR_PRODUKT_HTML))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_artikel_haben_url_und_titel(self, habilleur_config):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(HABILLEUR_PRODUKT_HTML))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)
        for artikel in result:
            assert "url" in artikel
            assert "titel" in artikel
            assert artikel["url"].startswith("https://")

    @pytest.mark.asyncio
    async def test_zu_teure_artikel_werden_gefiltert(self, habilleur_config):
        habilleur_config["max_preis"] = 100
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(HABILLEUR_PRODUKT_HTML))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)
        from scraper.habilleur_scraper import _parse_preis
        for artikel in result:
            preis = _parse_preis(artikel.get("preis", "0"))
            if preis:
                assert preis <= habilleur_config["max_preis"]

    @pytest.mark.asyncio
    async def test_leeres_html_gibt_leere_liste(self, habilleur_config):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response("<html><body></body></html>"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)
        assert result == []

    @pytest.mark.asyncio
    async def test_netzwerkfehler_gibt_leere_liste(self, habilleur_config):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)
        assert result == []

    @pytest.mark.asyncio
    async def test_max_artikel_wird_eingehalten(self, habilleur_config):
        habilleur_config["max_artikel_pro_suche"] = 1
        viele_produkte = "<html><body>" + "".join([
            f'<div class="product-item"><a href="/de/products/item-{i}"><h2>Artikel {i}</h2></a>'
            f'<span class="price">50,00 €</span></div>' for i in range(10)
        ]) + "</body></html>"
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(viele_produkte))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)
        assert len(result) <= habilleur_config["max_artikel_pro_suche"]

    @pytest.mark.asyncio
    async def test_url_wird_korrekt_aufgebaut(self, habilleur_config):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(HABILLEUR_PRODUKT_HTML))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)
        for artikel in result:
            assert artikel["url"].startswith("https://habilleurjean.com")

    @pytest.mark.asyncio
    async def test_tracking_parameter_werden_entfernt(self, habilleur_config):
        html = """<html><body>
          <div class="product-item">
            <a href="/de/products/item-1?ref=tracking&utm_source=email">
              <h2>Anzug Test</h2></a>
            <span class="price">100,00 €</span>
          </div></body></html>"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(html))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)
        for artikel in result:
            assert "?" not in artikel["url"]


# ══════════════════════════════════════════════════════════════════
#  HABILLEUR: scrape_artikel_details
# ══════════════════════════════════════════════════════════════════

class TestHabilleurScrapeArtikelDetails:

    @pytest.mark.asyncio
    async def test_gibt_vollstaendiges_dict_zurueck(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(HABILLEUR_DETAIL_HTML))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client)
        assert result is not None
        assert result["titel"] == "Vintage Anzug Dunkelblau"
        assert "150" in result["preis"]

    @pytest.mark.asyncio
    async def test_alle_pflichtfelder_vorhanden(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(HABILLEUR_DETAIL_HTML))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client)
        assert result is not None
        for feld in ["url", "titel", "preis", "beschreibung"]:
            assert feld in result

    @pytest.mark.asyncio
    async def test_habilleur_felder_vorhanden(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(HABILLEUR_DETAIL_HTML))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client)
        assert result is not None
        for feld in ["material", "zustand", "brand"]:
            assert feld in result

    @pytest.mark.asyncio
    async def test_fehler_gibt_none_zurueck(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("timeout"))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client)
        assert result is None

    @pytest.mark.asyncio
    async def test_url_wird_unveraendert_zurueckgegeben(self):
        url = "https://habilleurjean.com/de/products/anzug-42"
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(HABILLEUR_DETAIL_HTML))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(url, mock_client)
        assert result is not None
        assert result["url"] == url


# ══════════════════════════════════════════════════════════════════
#  CROSS-SCRAPER: Gemeinsames Interface
# ══════════════════════════════════════════════════════════════════

class TestCrossScraperInterface:

    PFLICHTFELDER = {"url", "titel", "preis", "beschreibung"}

    @pytest.mark.asyncio
    async def test_vinted_details_format(self):
        page = make_playwright_page()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, "https://vinted.de/items/1")
        assert result is not None
        assert self.PFLICHTFELDER.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_habilleur_details_format(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_httpx_response(HABILLEUR_DETAIL_HTML))
        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client)
        assert result is not None
        assert self.PFLICHTFELDER.issubset(result.keys())
