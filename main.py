import json
import asyncio
import random
import json
import argparse
import httpx
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

from scraper.vinted_scraper import scrape_artikel_details, scrape_suchergebnisse, analysiere_artikel, lade_config

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
async def main(config: dict):
    database_dir = Path("database")
    database_dir.mkdir(exist_ok=True)

    # Ausgabepfade in secrets/
    ergebnisse_path = database_dir / "vinted_ergebnisse.json"
    empfehlungen_path = database_dir / "vinted_empfehlungen.json"

    print(f"🚀 Vinted Scraper | Modell: {config['ollama_modell']} | {config['groesse']} | max {config['max_preis']}€\n")

    try:
        httpx.get(config["ollama_url"].replace("/api/generate", ""), timeout=3)
        print("✓ Ollama erreichbar\n")
    except:
        print("❌ Ollama nicht erreichbar! Starte mit: ollama serve")
        return

    alle_roh = []
    pauses_art = config.get("pause_zwischen_artikeln", [4, 7])
    pauses_such = config.get("pause_zwischen_suchen", [6, 10])
    max_suchen = config.get("max_suchen", 2)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1440, 'height': 900},
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )
        page = await context.new_page()
        await stealth_async(page)

        for suchbegriff in config["suchbegriffe"][:max_suchen]:
            try:
                links = await scrape_suchergebnisse(page, suchbegriff, config)
                for link in links:
                    details = await scrape_artikel_details(page, link["url"])
                    if details:
                        alle_roh.append(details)
                        print(f"    ✓ {details['titel']} – {details['preis']}")
                    await asyncio.sleep(random.uniform(*pauses_art))
            except Exception as e:
                print(f"Fehler: {e}")
            await asyncio.sleep(random.uniform(*pauses_such))

        await browser.close()

    # Deduplizieren
    seen, unique = set(), []
    for a in alle_roh:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    print(f"\n📦 {len(unique)} Artikel → Ollama analysiert...\n")

    ergebnisse = [analysiere_artikel(a, config) for a in unique]
    ergebnisse.sort(key=lambda x: x.get("bewertung") or 0, reverse=True)
    empfohlen = [a for a in ergebnisse if a.get("empfohlen")]

    # In secrets/ speichern
    with open(ergebnisse_path, "w", encoding="utf-8") as f:
        json.dump(ergebnisse, f, ensure_ascii=False, indent=2)
    with open(empfehlungen_path, "w", encoding="utf-8") as f:
        json.dump(empfohlen, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ {len(empfohlen)} von {len(ergebnisse)} empfohlen")
    print(f"💾 {ergebnisse_path}")
    print(f"💾 {empfehlungen_path}")
    print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="secrets/config.json", help="Pfad zur config.json")
    args = parser.parse_args()
    cfg = lade_config(args.config)
    asyncio.run(main(cfg))
