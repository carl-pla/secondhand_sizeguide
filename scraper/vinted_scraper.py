import asyncio
import random
from pathlib import Path

from database.config_defaults import VINTED_GROESSEN 


# ─────────────────────────────────────────────
#  SCRAPING
# ─────────────────────────────────────────────
async def scrape_suchergebnisse(page, suchbegriff: str, config: dict) -> list:
    groesse_id = VINTED_GROESSEN.get(config["groesse"], "207")
    url = (
        f"https://www.vinted.de/catalog"
        f"?search_text={suchbegriff.replace(' ', '+')}"
        f"&size_ids={groesse_id}"
        f"&price_to={config['max_preis']}"
        f"&order=newest_first"
    )
    print(f"\n🔍 Suche: '{suchbegriff}'")
    await page.goto(url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(random.uniform(2, 4))

    try:
        await page.get_by_role("button", name="Akzeptieren").click(timeout=3000)
        await asyncio.sleep(1)
    except:
        pass

    try:
        await page.wait_for_selector("[data-testid='grid-item']", timeout=15000)
    except:
        try:
            await page.wait_for_selector("[class*='feed-grid__item']", timeout=10000)
        except:
            return []

    artikel_links = []
    elemente = await page.locator("a[href*='/items/']").all()
    for el in elemente[:config["max_artikel_pro_suche"]]:
        try:
            href = await el.get_attribute("href")
            if href and "/items/" in href:
                full_url = f"https://www.vinted.de{href}" if href.startswith("/") else href
                full_url = full_url.split("?")[0]
                if full_url not in [a["url"] for a in artikel_links]:
                    artikel_links.append({"url": full_url})
        except:
            continue

    print(f"  ✓ {len(artikel_links)} Artikel gefunden")
    return artikel_links

async def scrape_artikel_details(page, url: str) -> dict | None:
    try:
        await page.goto(url, wait_until="networkidle", timeout=45000)
        await asyncio.sleep(random.uniform(2, 3))
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
        print(f"  ⚠️  Fehler: {e}")
        return None

