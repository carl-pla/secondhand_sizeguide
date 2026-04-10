import json
import asyncio
import random
import argparse
import httpx
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from scraper.vinted_scraper import scrape_artikel_details, scrape_suchergebnisse
from ai.ollama import analysiere_artikel
from database.config_defaults import lade_config, ERGEBNISSE_FILE, EMPFEHLUNGEN_FILE
from database.mongo import speichere_in_mongo
import concurrent.futures

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
async def main(config: dict):
    print(f"DEBUG: Lade Config von {config.get('_pfad', 'unbekannt')}")

    # Pflichtfelder prüfen
    if not config.get("ollama_modell"):
        print("❌ KRITISCH: ollama_modell ist leer!")
        return
    if not config.get("groesse"):
        print("❌ KRITISCH: groesse ist leer!")
        return

    print(f"🚀 Vinted Scraper | Modell: {config['ollama_modell']} | {config['groesse']} | max {config['max_preis']}€\n")

    # Ollama prüfen
    try:
        httpx.get(config["ollama_url"].replace("/api/generate", ""), timeout=3)
        print("✓ Ollama erreichbar\n")
    except:
        print("❌ Ollama nicht erreichbar! Starte mit: ollama serve")
        return

    pauses_art  = config.get("pause_zwischen_artikeln", [2, 4])
    pauses_such = config.get("pause_zwischen_suchen", [3, 6])
    max_suchen  = config.get("max_suchen", 2)

    alle_roh = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        for suchbegriff in config["suchbegriffe"][:max_suchen]:
            try:
                # ── STUFE 1: Grob-Suche ──────────────────────
                grob_links = await scrape_suchergebnisse(page, suchbegriff, config)
                print(f"  → {len(grob_links)} Artikel nach Grob-Filter\n")

                # ── STUFE 2: Detail-Scraping ──────────────────
                for link in grob_links:
                    details = await scrape_artikel_details(page, link["url"])
                    if details:
                        # Preis aus Grob-Suche als Fallback
                        if details["preis"] == "Unbekannt" and link.get("preis", "?") != "?":
                            details["preis"] = link["preis"]
                        alle_roh.append(details)
                        print(f"    ✓ {details['titel'][:50]} – {details['preis']}")
                    await asyncio.sleep(random.uniform(*pauses_art))

            except Exception as e:
                print(f"  ⚠️  Fehler bei '{suchbegriff}': {e}")

            await asyncio.sleep(random.uniform(*pauses_such))

        await browser.close()

    # ── Deduplizieren ─────────────────────────────────
    seen, unique = set(), []
    for a in alle_roh:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)


    # ── STUFE 3: Ollama-Analyse (parallel) ───────────────────
    print(f"\n✨ {len(unique)} Artikel → Ollama (parallel, 3 gleichzeitig)...\n")

    def analysiere_wrapper(artikel):
        return analysiere_artikel(artikel, config)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        ergebnisse = list(executor.map(analysiere_wrapper, unique))

    ergebnisse.sort(key=lambda x: x.get("bewertung") or 0, reverse=True)
    empfohlen = [a for a in ergebnisse if a.get("empfohlen")]

    # ── Speichern ─────────────────────────────────────
    ERGEBNISSE_FILE.parent.mkdir(exist_ok=True)
    with open(ERGEBNISSE_FILE, "w", encoding="utf-8") as f:
        json.dump(ergebnisse, f, ensure_ascii=False, indent=2)
    with open(EMPFEHLUNGEN_FILE, "w", encoding="utf-8") as f:
        json.dump(empfohlen, f, ensure_ascii=False, indent=2)

    # MongoDB
    try:
        speichere_in_mongo(ergebnisse, config)
    except Exception as e:
        print(f"⚠️  MongoDB nicht erreichbar: {e}")

    print(f"\n{'='*60}")
    print(f"✅ {len(empfohlen)} von {len(ergebnisse)} empfohlen")
    print(f"   Stufe 1 (Grob):  {min(max_suchen, len(config['suchbegriffe']))} Suchen")
    print(f"   Stufe 2 (Detail): {len(unique)} Artikel gescrapt")
    print(f"   Stufe 3 (Ollama): {len(ergebnisse)} analysiert")
    print(f"💾 {ERGEBNISSE_FILE}")
    print(f"💾 {EMPFEHLUNGEN_FILE}")
    print("="*60)

    return ergebnisse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="dashboard/secrets/config.json")
    args = parser.parse_args()
    cfg = lade_config(args.config)
    cfg["_pfad"] = args.config
    asyncio.run(main(cfg))