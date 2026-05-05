import asyncio
import random
from pathlib import Path

from database.config_defaults import VINTED_GROESSEN, VINTED_KATEGORIEN


# ─────────────────────────────────────────────
#  STUFE 1: GROB — viele Links + Preis sammeln
# ─────────────────────────────────────────────
async def scrape_suchergebnisse(page, suchbegriff: str, config: dict) -> list:
    groesse_id   = VINTED_GROESSEN.get(config["groesse"], "207")
    kategorie_id = VINTED_KATEGORIEN.get(config["kategorie"], "1206")
    max_artikel  = config.get("max_artikel_pro_suche", 50)
    max_preis    = config.get("max_preis", 50)

    status_filter = "&status_ids[]=6&status_ids[]=1&status_ids[]=2&status_ids[]=3"

    base_url = (
        f"https://www.vinted.de/catalog"
        f"?search_text={suchbegriff.replace(' ', '+')}"
        f"&size_ids[]={groesse_id}"
        f"&price_to={max_preis}"
        f"&catalog[]={kategorie_id}"
        f"{status_filter}"
        f"&order=newest_first"
    )

    print(f"\nGrobe Suche: '{suchbegriff}' | Größe: {config['groesse']} | Max_Preis: {max_preis}€ | Max_Artikel: {max_artikel}")

    artikel_links = []
    seite = 1  # NEU: Seitenzähler startet bei 1

    while len(artikel_links) < max_artikel:  # NEU: nur noch Artikelanzahl als Abbruchbedingung
        
        # NEU: URL wird pro Schleifendurchlauf mit aktuellem page-Parameter gebaut
        url = f"{base_url}&page={seite}"
        print(f"  📄 Durchsuche Seite {seite}")

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(1, 2))

        # Cookie Banner nur auf Seite 1 wegklicken
        if seite == 1:  # NEU: Cookie-Banner nur einmal wegklicken
            try:
                await page.get_by_role("button", name="Akzeptieren").click(timeout=3000)
                await asyncio.sleep(1)
            except:
                pass

        try:
            await page.wait_for_selector("a[href*='/items/']", timeout=10000)
        except:
            break  # Keine Artikel mehr gefunden → Abbruch

        karten = await page.locator("[data-testid='grid-item']").all()

        # NEU: Wenn Seite leer ist, gibt es keine weiteren Seiten → Abbruch
        if not karten:
            print(f"  ✓ Keine weiteren Artikel auf Seite {seite}, Abbruch.")
            break

        for karte in karten:
            try:
                link_el = karte.locator("a[href*='/items/']").first
                href = await link_el.get_attribute("href")
                if not href or "/items/" not in href:
                    continue

                full_url = f"https://www.vinted.de{href}" if href.startswith("/") else href
                full_url = full_url.split("?")[0]

                if full_url in [a["url"] for a in artikel_links]:
                    continue

                preis_text = ""
                try:
                    preis_el = karte.locator("[data-testid='item-price'], [class*='price']").first
                    preis_text = await preis_el.inner_text(timeout=1000)
                except:
                    pass

                preis_zahl = _parse_preis(preis_text)
                if preis_zahl and preis_zahl > max_preis:
                    continue

                artikel_links.append({
                    "url":   full_url,
                    "preis": preis_text.strip() or "?",
                })

                if len(artikel_links) >= max_artikel:
                    break

            except:
                continue

        seite += 1  # NEU: nächste Seite
        await asyncio.sleep(random.uniform(1, 1.5))  # NEU: Pause zwischen Seiten statt nach Scroll

    print(f"  ✓ {len(artikel_links)} Artikel nach Grob-Filter")
    return artikel_links


# ─────────────────────────────────────────────
#  STUFE 2: FEIN — Detail-Seite scrapen (unverändert)
# ─────────────────────────────────────────────
async def scrape_artikel_details(page, url: str) -> dict | None:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(random.uniform(1.5, 2.5))
        await page.wait_for_selector("h1", timeout=20000)

        titel = await page.locator("h1").inner_text()

        preis = "Unbekannt"
        for s in ["[data-testid='item-price']", "[class*='ItemPrice']", "[itemprop='price']"]:
            try:
                preis = await page.locator(s).first.inner_text(timeout=3000)
                break
            except:
                continue

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
#  HILFSFUNKTION (unverändert)
# ─────────────────────────────────────────────
def _parse_preis(preis_text: str) -> float | None:
    try:
        cleaned = ''.join(c for c in preis_text if c.isdigit() or c in '.,')
        cleaned = cleaned.replace(',', '.')
        return float(cleaned.strip('.'))
    except:
        return None