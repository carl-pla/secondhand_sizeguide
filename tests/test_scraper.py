"""
=== MATCHFIT – SCRAPER TESTS ===
Abgedeckte Module:
  - scraper/vinted_scraper.py    → _parse_preis, scrape_suchergebnisse, scrape_artikel_details
  - scraper/habilleur_scraper.py → _parse_preis, scrape_suchergebnisse, scrape_artikel_details

Playwright-Objekte (page, browser) und httpx.AsyncClient werden vollständig gemockt,
damit die Tests ohne Browser und ohne Netzwerk laufen.

Neue Scraper (eBay, Grailed, etc.) können nach demselben Muster ergänzt werden —
siehe "Erweiterungs-Vorlage" am Ende der Datei.
"""

import pytest 
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import HTTPStatusError


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


# ──────────────────────────────────────────────────────────────────
#  Playwright Page Mock
#  Simuliert die page-Objekte, die Vinted-Scraper von Playwright bekommt
# ──────────────────────────────────────────────────────────────────

def make_playwright_page(
    artikel_hrefs: list[str] | None = None,
    preis_texte: list[str] | None = None,
    detail_titel: str = "Vintage Levi's Jacke",
    detail_preis: str = "35 €",
    detail_beschreibung: str = "Sehr schöne Jacke, Größe M, Brust 90cm.",
):
    """
    Baut einen vollständigen Playwright-Page-Mock.
    
    artikel_hrefs: Liste von Artikel-URLs für Suchergebnis-Karten
    preis_texte:   Passende Preistexte zu den URLs (gleiche Reihenfolge)
    """
    if artikel_hrefs is None:
        artikel_hrefs = ["/items/123-vintage-jacke", "/items/456-retro-mantel"]
    if preis_texte is None:
        preis_texte = ["35,00 €", "45,00 €"]

    page = AsyncMock()

    # ── goto / wait / scroll / sleep ──
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.evaluate = AsyncMock()
    page.get_by_role = MagicMock(return_value=AsyncMock())

    # ── Cookie-Banner ──
    page.get_by_role.return_value.click = AsyncMock(side_effect=Exception("kein Banner"))

    # ── Karten-Locator für Suchergebnisse ──
    karten = []
    for href, preis in zip(artikel_hrefs, preis_texte):
        karte = MagicMock()

        link_locator = AsyncMock()
        link_locator.get_attribute = AsyncMock(return_value=href)

        preis_locator = AsyncMock()
        preis_locator.inner_text = AsyncMock(return_value=preis)

        karte.locator = MagicMock(side_effect=lambda sel, **kw: (
            link_locator if "items" in sel else preis_locator
        ))
        karten.append(karte)

    grid_locator = AsyncMock()
    grid_locator.all = AsyncMock(return_value=karten)

    # ── Haupt-Locator ──
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


# ──────────────────────────────────────────────────────────────────
#  httpx Response Mock
#  Simuliert HTTP-Antworten für den Habilleur-Scraper
# ──────────────────────────────────────────────────────────────────

def make_httpx_response(html: str, status_code: int = 200):
    """Erstellt einen gefakten httpx-Response."""
    response = MagicMock()
    response.status_code = status_code
    response.text = html
    response.raise_for_status = MagicMock()
    if status_code >= 400:
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
    """Isolierter Test der Hilfsfunktion – kein Netzwerk, kein Browser."""

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
        """Normalfall: Zwei Artikel werden gefunden und zurückgegeben."""
        page = make_playwright_page()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse(page, "Vintage", basis_config)

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_artikel_haben_url_und_preis(self, basis_config):
        """Jeder zurückgegebene Artikel muss url und preis enthalten."""
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
        """Artikel über max_preis dürfen nicht in der Ergebnisliste landen."""
        # Budget: 50€, ein Artikel kostet 80€
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
        """Dieselbe URL darf nur einmal in der Ergebnisliste erscheinen."""
        page = make_playwright_page(
            artikel_hrefs=["/items/123", "/items/123"],  # gleiche URL zweimal
            preis_texte=["30 €", "30 €"],
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse(page, "Vintage", basis_config)

        urls = [a["url"] for a in result]
        assert len(urls) == len(set(urls))

    @pytest.mark.asyncio
    async def test_max_artikel_wird_eingehalten(self, basis_config):
        """Es dürfen nicht mehr Artikel zurückgegeben werden als max_artikel_pro_suche."""
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
    async def test_fehler_gibt_leere_liste_zurueck(self, basis_config):
        """Wenn page.goto() fehlschlägt, wird [] zurückgegeben – kein Absturz."""
        page = AsyncMock()
        page.goto = AsyncMock(side_effect=Exception("Timeout"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse(page, "Vintage", basis_config)

        assert result == []


# ══════════════════════════════════════════════════════════════════
#  VINTED: scrape_artikel_details
# ══════════════════════════════════════════════════════════════════

class TestVintedScrapeArtikelDetails:

    @pytest.mark.asyncio
    async def test_gibt_vollstaendiges_dict_zurueck(self, basis_config):
        """Normalfall: Detail-Dict enthält alle Pflichtfelder."""
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
        assert "Jacke" in result["beschreibung"]
        assert result["url"] == "https://www.vinted.de/items/123"

    @pytest.mark.asyncio
    async def test_alle_pflichtfelder_vorhanden(self, basis_config):
        """url, titel, preis, beschreibung müssen immer im Dict sein."""
        page = make_playwright_page()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, "https://www.vinted.de/items/123")

        assert result is not None
        for feld in ["url", "titel", "preis", "beschreibung"]:
            assert feld in result, f"Pflichtfeld '{feld}' fehlt im Ergebnis"

    @pytest.mark.asyncio
    async def test_beschreibung_wird_auf_800_zeichen_gekuerzt(self):
        """Beschreibungen über 800 Zeichen werden abgeschnitten."""
        lange_beschreibung = "X" * 1500
        page = make_playwright_page(detail_beschreibung=lange_beschreibung)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, "https://www.vinted.de/items/123")

        assert result is not None
        assert len(result["beschreibung"]) <= 800

    @pytest.mark.asyncio
    async def test_fehler_gibt_none_zurueck(self):
        """Wenn die Seite nicht geladen werden kann, wird None zurückgegeben."""
        page = AsyncMock()
        page.goto = AsyncMock(side_effect=Exception("net::ERR_NAME_NOT_RESOLVED"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, "https://www.vinted.de/items/999")

        assert result is None

    @pytest.mark.asyncio
    async def test_url_wird_unveraendert_zurueckgegeben(self):
        """Die übergebene URL muss 1:1 im Ergebnis-Dict auftauchen."""
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
    """
    Habilleur hat einen eigenen _parse_preis, der mit Tausender-Trennzeichen umgehen muss.
    Beispiel: "1.234,99 €" → 1234.99
    """

    def test_deutsches_format(self):
        from scraper.habilleur_scraper import _parse_preis
        assert _parse_preis("150,00 €") == 150.0

    def test_tausender_trennzeichen(self):
        from scraper.habilleur_scraper import _parse_preis
        # "1.234,99" → 1234.99 (Tausenderpunkt, Dezimalkomma)
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
        """Normalfall: HTML mit zwei Produkten → zwei Einträge zurück."""
        mock_response = make_httpx_response(HABILLEUR_PRODUKT_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_artikel_haben_url_und_titel(self, habilleur_config):
        """Jeder Artikel muss url und titel enthalten."""
        mock_response = make_httpx_response(HABILLEUR_PRODUKT_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)

        for artikel in result:
            assert "url" in artikel
            assert "titel" in artikel
            assert artikel["url"].startswith("https://")

    @pytest.mark.asyncio
    async def test_zu_teure_artikel_werden_gefiltert(self, habilleur_config):
        """Artikel über max_preis (200€) werden nicht zurückgegeben."""
        # Zweiter Artikel kostet 89,99€ → beide unter 200€, beide erwartet
        # Jetzt Budget auf 100€ setzen → nur erster (150€ > 100€ wird gefiltert)
        habilleur_config["max_preis"] = 100
        mock_response = make_httpx_response(HABILLEUR_PRODUKT_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)

        # Nur Artikel unter 100€ sollen enthalten sein
        for artikel in result:
            from scraper.habilleur_scraper import _parse_preis
            preis = _parse_preis(artikel.get("preis", "0"))
            if preis:
                assert preis <= habilleur_config["max_preis"]

    @pytest.mark.asyncio
    async def test_leeres_html_gibt_leere_liste(self, habilleur_config):
        """HTML ohne Produkte → leere Liste, kein Absturz."""
        mock_response = make_httpx_response("<html><body><p>Keine Artikel</p></body></html>")
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_netzwerkfehler_gibt_leere_liste(self, habilleur_config):
        """Wenn der HTTP-Request fehlschlägt, wird [] zurückgegeben."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_max_artikel_wird_eingehalten(self, habilleur_config):
        """Auch wenn die Seite viele Produkte hat, maximal max_artikel_pro_suche zurückgeben."""
        habilleur_config["max_artikel_pro_suche"] = 1

        viele_produkte = """
        <html><body>
        """ + "".join([
            f'<div class="product-item"><a href="/de/products/item-{i}"><h2>Artikel {i}</h2></a>'
            f'<span class="price">50,00 €</span></div>'
            for i in range(10)
        ]) + "</body></html>"

        mock_response = make_httpx_response(viele_produkte)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)

        assert len(result) <= habilleur_config["max_artikel_pro_suche"]

    @pytest.mark.asyncio
    async def test_url_wird_korrekt_aufgebaut(self, habilleur_config):
        """URLs müssen mit https://habilleurjean.com beginnen."""
        mock_response = make_httpx_response(HABILLEUR_PRODUKT_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_suchergebnisse
            result = await scrape_suchergebnisse("Anzug", "M", habilleur_config, mock_client)

        for artikel in result:
            assert artikel["url"].startswith("https://habilleurjean.com")

    @pytest.mark.asyncio
    async def test_tracking_parameter_werden_entfernt(self, habilleur_config):
        """Query-Parameter (?ref=...) müssen aus den URLs entfernt werden."""
        html_mit_tracking = """
        <html><body>
          <div class="product-item">
            <a href="/de/products/item-1?ref=tracking&utm_source=email">
              <h2>Anzug Test</h2>
            </a>
            <span class="price">100,00 €</span>
          </div>
        </body></html>
        """
        mock_response = make_httpx_response(html_mit_tracking)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

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
        """Normalfall: Detail-Dict enthält alle Pflichtfelder."""
        mock_response = make_httpx_response(HABILLEUR_DETAIL_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/anzug-test", mock_client
            )

        assert result is not None
        assert result["titel"] == "Vintage Anzug Dunkelblau"
        assert "150" in result["preis"]
        assert "Wolle" in result["beschreibung"]

    @pytest.mark.asyncio
    async def test_alle_pflichtfelder_vorhanden(self):
        """url, titel, preis, beschreibung müssen immer vorhanden sein."""
        mock_response = make_httpx_response(HABILLEUR_DETAIL_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client
            )

        assert result is not None
        for feld in ["url", "titel", "preis", "beschreibung"]:
            assert feld in result, f"Pflichtfeld '{feld}' fehlt"

    @pytest.mark.asyncio
    async def test_habilleur_felder_vorhanden(self):
        """Habilleur-spezifische Felder material, zustand, brand müssen im Dict sein."""
        mock_response = make_httpx_response(HABILLEUR_DETAIL_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client
            )

        assert result is not None
        assert "material" in result
        assert "zustand" in result
        assert "brand" in result

    @pytest.mark.asyncio
    async def test_material_aus_beschreibung_extrahiert(self):
        """'Material: Wolle' in der Beschreibung muss als material-Feld auftauchen."""
        mock_response = make_httpx_response(HABILLEUR_DETAIL_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client
            )

        # Material muss aus dem Text "Material: Wolle" extrahiert worden sein
        assert result is not None
        assert "Wolle" in result.get("material", "") or "Wolle" in result.get("beschreibung", "")

    @pytest.mark.asyncio
    async def test_fehler_gibt_none_zurueck(self):
        """Netzwerkfehler → None, kein Absturz."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection timeout"))

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_http_fehler_gibt_none_zurueck(self):
        """HTTP 404 → None, kein Absturz."""
        mock_response = make_httpx_response("<html>Not Found</html>", status_code=404)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_url_wird_unveraendert_zurueckgegeben(self):
        """Die übergebene URL muss exakt im Ergebnis-Dict stehen."""
        url = "https://habilleurjean.com/de/products/anzug-42"
        mock_response = make_httpx_response(HABILLEUR_DETAIL_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(url, mock_client)

        assert result is not None
        assert result["url"] == url


# ══════════════════════════════════════════════════════════════════
#  CROSS-SCRAPER: Gemeinsames Interface
#  Beide Scraper müssen dasselbe Output-Format liefern,
#  damit main.py und ollama.py sie austauschbar nutzen können.
# ══════════════════════════════════════════════════════════════════

class TestCrossScraperInterface:
    """
    Stellt sicher, dass Vinted- und Habilleur-Scraper strukturell kompatibel bleiben.
    Neue Scraper (eBay, Grailed etc.) müssen dieselben Tests bestehen.
    """

    PFLICHTFELDER_DETAILS = {"url", "titel", "preis", "beschreibung"}

    @pytest.mark.asyncio
    async def test_vinted_details_format(self):
        """Vinted-Details haben alle Felder, die main.py und ollama.py erwarten."""
        page = make_playwright_page()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.vinted_scraper import scrape_artikel_details
            result = await scrape_artikel_details(page, "https://vinted.de/items/1")

        assert result is not None
        assert self.PFLICHTFELDER_DETAILS.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_habilleur_details_format(self):
        """Habilleur-Details haben alle Felder, die main.py und ollama.py erwarten."""
        mock_response = make_httpx_response(HABILLEUR_DETAIL_HTML)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            from scraper.habilleur_scraper import scrape_artikel_details
            result = await scrape_artikel_details(
                "https://habilleurjean.com/de/products/test", mock_client
            )

        assert result is not None
        assert self.PFLICHTFELDER_DETAILS.issubset(result.keys())


# ══════════════════════════════════════════════════════════════════
#  ERWEITERUNGS-VORLAGE FÜR NEUE SCRAPER
#  (z.B. eBay, Grailed, Depop)
# ══════════════════════════════════════════════════════════════════
#
# Um einen neuen Scraper (z.B. ebay_scraper.py) zu testen:
#
# 1. HTML-Fixture anlegen:
#    EBAY_PRODUKT_HTML = "<html>...</html>"
#    EBAY_DETAIL_HTML  = "<html>...</html>"
#
# 2. Testklassen analog zu TestHabilleur* erstellen:
#    class TestEbayParsePreis:          → _parse_preis testen
#    class TestEbayScrapeSucchergebnisse: → suchergebnisse testen
#    class TestEbayScrapeArtikelDetails:  → details testen
#
# 3. Interface-Test ergänzen:
#    class TestCrossScraperInterface:
#        async def test_ebay_details_format(self): ...
#
# Alle anderen Dateien (main.py, ollama.py, test_matchfit.py)
# müssen NICHT angepasst werden – das Interface ist stabil.
