import asyncio
import random
from pathlib import Path

from database.config_defaults import VINTED_GROESSEN 

"""
=== Workflow grob ===
URL bauen: Suchbegriff + Filter (Größe, Preis).

Stufe 1 (Grob-Suche): Scrollen, Links einsammeln, Preise oberflächlich prüfen.

Stufe 2 (Fein-Suche): Für jeden Link aus Stufe 1 wird scrape_artikel_details aufgerufen.

Daten-Check: Mit _parse_preis wird sichergestellt, dass das Budget wirklich eingehalten wurde.
"""


# ─────────────────────────────────────────────
#  STUFE 1: GROB — viele Links + Preis sammeln
# ─────────────────────────────────────────────
"""
3 wichtigsten Parameter nach denen vorgefiltert wird, um nicht alles bis ins detail zu analysieren
"""
async def scrape_suchergebnisse(page, suchbegriff: str, config: dict) -> list:
    groesse_id  = VINTED_GROESSEN.get(config["groesse"], "207")  # ← richtig, aus VINTED_GROESSEN
    max_artikel = config.get("max_artikel_pro_suche", 50)        # ← aus config, nicht VINTED_GROESSEN
    max_preis   = config.get("max_preis", 50)   
    """
    Zustand filtern (Beispiel: Alles ab "Gut" aufwärts)
    Wenn wir 6, 1, 2 und 3 übergeben, filtert Vinted den Schrott (Zufriedenstellend) raus.
    """
    status_filter = "&status_ids[]=6&status_ids[]=1&status_ids[]=2&status_ids[]=3"  

    """
    spezieller Link für Vinted, um die Konfiguration zu finden --> Hier eventuell try/except Block einbauen, 
    ob Anfrage durchkommt
    """
    url = (
        f"https://www.vinted.de/catalog"
        f"?search_text={suchbegriff.replace(' ', '+')}"
        f"&size_ids[]={groesse_id}"
        f"&price_to={max_preis}"
        f"{status_filter}"
        f"&order=newest_first"
    )
    print(f"DEBUG: Generierte URL: {url}")
   
    """
    Vinted-URL wird mit Playwright geöffnet, wartet bis Seite "fertig" geladen ist, 
    muss durch asyncio "nachdenken" o-ä. simulieren, dass Anfrage des Scrapers nicht gleich gesperrt wird 
    """ 
    print(f"\nGrobe Suche: '{suchbegriff}' | Größe: {config['groesse']} | Max_Preis: {max_preis}€ | Max_Artikel: {max_artikel}")
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(random.uniform(1, 2))

    """
    Cookie Banner werden weggeglickt, falls diese vorhanden sein sollten 
    """ 
    try:
        await page.get_by_role("button", name="Akzeptieren").click(timeout=3000)
        await asyncio.sleep(1)
    except:
        pass
    

    """
    === Strategie: Vinted nutzt Infinte-Scrollen wie zB. Instagram 
    === hier läuft der eigentliche Scraper Prozess 
    """
    artikel_links = []
    scroll_versuche = 0
    max_scrolls = max(3, max_artikel // 20)  # ~20 Artikel pro Scroll

    """
    while-Schleife: prüft 1.max_artikel gesucht oder 2.max_scrolls erreicht, vermeidet nicht ewiges weiterlaufen 
    """
    while len(artikel_links) < max_artikel and scroll_versuche < max_scrolls:
        # Warten bis Grid geladen
        try:
            await page.wait_for_selector("a[href*='/items/']", timeout=10000)
        except:
            break

        """
        Skript schaut nach Bildschirminhalten: Artikeln 
        - Sucht nach Link, der zu dem spezifischen Artikel führt
        - "Tracking-Müll wird entfernt"
        - Duplikate werden überprüft, ob nicht etwas zweimal eingescant wurde 
        """
        karten = await page.locator("[data-testid='grid-item']").all()

        for karte in karten:
            try:
                # Link
                link_el = karte.locator("a[href*='/items/']").first
                href = await link_el.get_attribute("href")
                if not href or "/items/" not in href:
                    continue

                full_url = f"https://www.vinted.de{href}" if href.startswith("/") else href
                # tracking Müll
                full_url = full_url.split("?")[0]

                # Duplikat-Check
                if full_url in [a["url"] for a in artikel_links]: 
                    continue

                """
                === Grob Filter
                - Liest Preis direkt von kacheln ab 
                - HILFSFUNKTION _parse_preis soll "15,00€" --> "15.0"
                - Falls Artikel über max_preis, direkt gefiltert 
                -
                """
                preis_text = ""
                try:
                    preis_el = karte.locator("[data-testid='item-price'], [class*='price']").first
                    preis_text = await preis_el.inner_text(timeout=1000)
                except:
                    pass

                # Preis parsen und filtern
                preis_zahl = _parse_preis(preis_text)
                if preis_zahl and preis_zahl > max_preis:
                    continue  # ← Grob-Filter: zu teuer, überspringen

                artikel_links.append({
                    "url":   full_url,
                    "preis": preis_text.strip() or "?",
                })

                if len(artikel_links) >= max_artikel:
                    break

            except:
                continue

        """
        Falls noch nciht genug Artikel gescrapt worden sind --> durch einen Bildschirm Sprung nach unten
        können neue Artikel geladen werden, was Infinte Scrolling auspielt:)
        """
        await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        await asyncio.sleep(random.uniform(1, 1.5))
        scroll_versuche += 1

    print(f"  ✓ {len(artikel_links)} Artikel nach Grob-Filter")
    return artikel_links



# ─────────────────────────────────────────────
#  STUFE 2: FEIN — Detail-Seite scrapen
# ─────────────────────────────────────────────
"""
öffnet Link erneut und imitiert wieder menschliches Verhalten 
"""
async def scrape_artikel_details(page, url: str) -> dict | None:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(random.uniform(1.5, 2.5))
        await page.wait_for_selector("h1", timeout=20000)

        titel = await page.locator("h1").inner_text()
        
        """
        Hier wird nach Preis gesucht, mit Absicht von Systemkosten, Lieferkosten, 
        was beim Groben Durchsuchen nicht durchsucht wird
        
        Robuste Suchstrategie: CSS-Selektoren. Vinted erschwert Bots zugang durch A/B-Tests und dynamische Klassen
        => Lösung: schaut erst nach Standardpreisschild, wenn nichts dann itemprop Metatag nachschauen 
        und wenn wieder nichts dann irgendwas mit 'price'
        """
        preis = "Unbekannt"
        for s in ["[data-testid='item-price']", "[class*='ItemPrice']", "[itemprop='price']"]:
            try:
                preis = await page.locator(s).first.inner_text(timeout=3000)
                break
            except:
                continue
        
        """
        Hier wird nach den Beschreibungen gesucht, braucht mind. 10 Zeilen, aber stopt bei 800 Zeichen  
        Eventualitäten der Selektoren: Metadaten, Test-ID (sehr zuverlässig), 
        klassen-suche (eine Klasse mit dem enthaltenen Wort), Notfall-Suche (schau nach Wort "description")
        """
        beschreibung = None
        for s in ["[itemprop='description']", "[data-testid='item-description']",
                  "[class*='ItemDescription']", "[class*='item-description']", "[class*='description']"]:
            try:
                el = page.locator(s).first
                await el.wait_for(timeout=3000)
                text = await el.inner_text()
                if text and len(text) > 10:
                    beschreibung = text
                    break
            except:
                continue

        """
        => Dictionary wird zurückgegebn, mit den erhaltenen Daten in der Fein-Suche, 
            wenn Fehler dann except-Block bspw. Artikel verkauft
        """
        return {
            "url": url,
            "titel": titel.strip(),
            "preis": preis.strip(),
            "beschreibung": (beschreibung or "Keine Beschreibung").strip()[:800],
        }
    except Exception as e:
        print(f"  ⚠️  Detail-Fehler bei {url}: {e}")
        return None


# ─────────────────────────────────────────────
#  HILFSFUNKTION => schreibt Währung-Betrag in float (leichter zum Verarbeiten)
# ─────────────────────────────────────────────
def _parse_preis(preis_text: str) -> float | None:
    try:
        cleaned = ''.join(c for c in preis_text if c.isdigit() or c in '.,')
        cleaned = cleaned.replace(',', '.')
        # Falls "12.99" oder "12" → float
        return float(cleaned.strip('.'))
    except:
        return None