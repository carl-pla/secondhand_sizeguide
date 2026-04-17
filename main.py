import json
import asyncio
import random
import argparse
import httpx # type: ignore
from pathlib import Path
from playwright.async_api import async_playwright # type: ignore
from playwright_stealth import Stealth # type: ignore
from scraper.vinted_scraper import scrape_artikel_details, scrape_suchergebnisse
from ai.ollama import analysiere_artikel
from database.config_defaults import lade_config, ERGEBNISSE_FILE, EMPFEHLUNGEN_FILE
from database.scrapping_sessions import speichere_in_mongo
import concurrent.futures

"""
=== WORFLOW GROB 
ORCHESTER-ZENTRUM: Scraping --> AI Analyse/Bewertung --> Database
"""

"""
1. Setup & Validierung 
"""
# Prüft, ob alle Werkzeuge bereit sind (LLM und Config.json)
async def main(config: dict, user_email: str=None):
    print(f"DEBUG: Lade Config von {config.get('_pfad', 'unbekannt')}")

    # Pflichtfelder prüfen
    if not config.get("ollama_modell"):
        print("❌ KRITISCH: ollama_modell ist leer!")
        return
    if not config.get("groesse"):
        print("❌ KRITISCH: groesse ist leer!")
        return
    if not config.get("kategorie"):
        print("❌ KRITISCH: kategorie ist leer!")
        return

    print(f"🚀 Vinted Scraper | Modell: {config['ollama_modell']} | {config['groesse']} | {config['kategorie']} | max {config['max_preis']}€\n")

    # Verbindungstest zu Ollama wird gestartet 
    try:
        httpx.get(config["ollama_url"].replace("/api/generate", ""), timeout=3)
        print("✓ Ollama erreichbar\n")
    except:
        print("❌ Ollama nicht erreichbar! Starte mit: ollama serve")
        return

    # eingelegte Pausen, sodass es zu keinem IP-Ban kommt
    pauses_art  = config.get("pause_zwischen_artikeln", [2, 4])
    pauses_such = config.get("pause_zwischen_suchen", [3, 6])
    max_suchen  = config.get("max_suchen", 2)

    #hier werden alle Daten gesammelt
    alle_roh = []

    
    """
    2. BROWSER-AUTOMATISIERUNG (Playwright)
    """
    # Unsichtbarer Browser wird gestartet und als echter Mensch "getarnt" (Stealth)
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

        
        """
        SCRAPING-LOOP mit Teil A und Teil B ==> Warum hier und nicht in der scraper Datei? 
        ==> sonst würde es bei jedem neuen Scrapen einen neuen Browser erstellen, weshalb man 
        gesperrt werden könnte, durch das integrieren in main.py wird nur ein einziges Mal der Browser ausgeführt 
        """
        # jeder Suchbegriff kann durchgegangen werden
        for suchbegriff in config["stile"][:max_suchen]:
            try:
                
                # ── STUFE 1: Grob-Suche: Links sammeln und Suchergebnisse scannen──────────────────────
                grob_links = await scrape_suchergebnisse(page, suchbegriff, config)
                print(f"  → {len(grob_links)} Artikel nach Grob-Filter\n")

                # ── STUFE 2: Detail-Scraping: Details der Artikel genauer analysiert wie Beschreibung ──────────────────
                for link in grob_links:
                    details = await scrape_artikel_details(page, link["url"])
                    if details:
                        
                        # Preis aus Grob-Suche als Fallback, wenn in Detailsuche nichts gefunden
                        if details["preis"] == "Unbekannt" and link.get("preis", "?") != "?":
                            details["preis"] = link["preis"]
                        alle_roh.append(details)
                        print(f"    ✓ {details['titel'][:50]} – {details['preis']}")
                    await asyncio.sleep(random.uniform(*pauses_art))

            except Exception as e:
                print(f"  ⚠️  Fehler bei '{suchbegriff}': {e}")

            # menschliche Pausen, aufgrund IP-Ban
            await asyncio.sleep(random.uniform(*pauses_such))

        await browser.close()


    """
    3. DEDUPLIZIERUNG --> verhindert, dass Artikel mehrfach gescannt werden
    """
    seen, unique = set(), []
    for a in alle_roh:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)


    """
    4. LLM-Analyse (ollama) 
    --> gesammelte Daten werden an ollama geschickt (Performance/Größe gut)
    --> "ThreadPoolExecuter", um 3 Artikel parallel zu analysieren (spart Zeit)
    """
    print(f"\n✨ {len(unique)} Artikel → Ollama (parallel, 3 gleichzeitig)...\n")

    def analysiere_wrapper(artikel):
        return analysiere_artikel(artikel, config)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # hier wird "analyse_artikel"-Funktion aus ollama.py aufgerufen, um die fertig gescannten Artikel zu analysieren
        # WICHTIGES ZUSAMMENSPIEL!
        ergebnisse = list(executor.map(analysiere_wrapper, unique))

    # sortieren: Beste Empfehlungen nach oben 
    ergebnisse.sort(key=lambda x: x.get("bewertung") or 0, reverse=True)
    empfohlen = [a for a in ergebnisse if a.get("empfohlen")]


    """
    5. SPEICHERUNG UND EXPORT: 
    """
    # Speicherung A: lokale JSON-Dateien für das streamlit-dashboard erstellen
    ERGEBNISSE_FILE.parent.mkdir(exist_ok=True)
    with open(ERGEBNISSE_FILE, "w", encoding="utf-8") as f:
        json.dump(ergebnisse, f, ensure_ascii=False, indent=2)
    with open(EMPFEHLUNGEN_FILE, "w", encoding="utf-8") as f:
        json.dump(empfohlen, f, ensure_ascii=False, indent=2)

    # Speicherung B: MongoDB (Docker) für Langezeit-Speicherung oder andersweitige Validierung 
    try:
        speichere_in_mongo(ergebnisse, config, user_email=config.get("user_email"))
    except Exception as e:
        print(f"⚠️  MongoDB nicht erreichbar: {e}")

    
    # Ausgabe im Terminal über momentanen Ablauf
    print(f"\n{'='*60}")
    print(f"✅ {len(empfohlen)} von {len(ergebnisse)} empfohlen")
    print(f"   Stufe 1 (Grob):  {min(max_suchen, len(config['stile']))} Suchen")
    print(f"   Stufe 2 (Detail): {len(unique)} Artikel gescrapt")
    print(f"   Stufe 3 (Ollama): {len(ergebnisse)} analysiert")
    print(f"💾 {ERGEBNISSE_FILE}")
    print(f"💾 {EMPFEHLUNGEN_FILE}")
    print("="*60)

    return ergebnisse

"""
STARTPUNKT DER DATEI --> ermöglicht via Terminal zu starten
"""
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="dashboard/secrets/config.json")
    args = parser.parse_args()
    cfg = lade_config(args.config)
    cfg["_pfad"] = args.config
    asyncio.run(main(cfg))