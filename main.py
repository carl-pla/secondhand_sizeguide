import json
import asyncio
import random
import argparse
import datetime
import sys
import os
import httpx # type: ignore
from playwright.async_api import async_playwright # type: ignore
from playwright_stealth import Stealth # type: ignore
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Erzwinge UTF-8 Encoding für Windows-Konsole
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from scraper.vinted_scraper import scrape_artikel_details as vinted_scrape_details, scrape_suchergebnisse as vinted_scrape_suchergebnisse
from scraper.habilleur_scraper import scrape_artikel_details as scrape_artikel_details, scrape_suchergebnisse as habilleur_scrape_suchergebnisse
from src_ebay.get_request import get_summary_of_articles_json, get_detailed_items_async
from src_ebay.get_new_token import get_new_token
from ai.ollama import analysiere_artikel_vinted, analysiere_artikel_habilleur, analysiere_artikel_ebay
from database.config_defaults import lade_config, ERGEBNISSE_FILE, EMPFEHLUNGEN_FILE
from database.scraping_sessions import speichere_in_mongo
import concurrent.futures

"""
=== WORKFLOW GROB 
ORCHESTER-ZENTRUM: Scraping --> AI Analyse/Bewertung --> Database
Unterstützt nun: Vinted (mit Browser) und Habilleur (ohne Browser)
"""

"""
1. Setup & Validierung 
"""
# Prüft, ob alle Werkzeuge bereit sind (LLM und Config.json)
async def main(config: dict, user_email: str=None): # type: ignore
    print(f"DEBUG: Lade Config von {config.get('_pfad', 'unbekannt')}")
    print(f"DEBUG user_email: {config.get('user_email')}")  # ← neu
    print(f"DEBUG alle keys: {list(config.keys())}") 

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

    # Quelle festlegen (Vinted oder Habilleur)
    quelle = config.get("quelle", "vinted").lower()
    if quelle not in ["vinted", "habilleur", "ebay"]:
        print(f"❌ KRITISCH: quelle muss 'vinted', 'habilleur' oder 'ebay' sein, erhalten: {quelle}")
        return

    print(f"🚀 {quelle.upper()} Scraper | Modell: {config['ollama_modell']} | {config['groesse']} | {config['kategorie']} | max {config['max_preis']}€\n")

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
    2. SCRAPING – VINTED (mit Browser) oder HABILLEUR (ohne Browser) oder EBAY (API-Requests)
    """
    if quelle == "vinted":
        # ─────────────────────────────────────────────
        #  VINTED: BROWSER-AUTOMATISIERUNG (Playwright)
        # ─────────────────────────────────────────────
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

            # Jeder Suchbegriff wird durchgegangen
            for suchbegriff in config["stile"][:max_suchen]:
                try:
                    # ── STUFE 1: Grob-Suche: Links sammeln ──
                    grob_links = await vinted_scrape_suchergebnisse(page, suchbegriff, config)
                    print(f"  → {len(grob_links)} Artikel nach Grob-Filter\n")

                    # ── STUFE 2: Detail-Scraping ──
                    for link in grob_links:
                        details = await vinted_scrape_details(page, link["url"])
                        if details:
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

    elif quelle == "habilleur":  # habilleur
        # ─────────────────────────────────────────────
        #  HABILLEUR: DIREKTE HTTP-REQUESTS (kein Browser)
        # ─────────────────────────────────────────────
        groesse = config.get("groesse", "M")
        kategorie = config.get("kategorie", "Anzug")

        async with httpx.AsyncClient() as client:
            # Habilleur braucht Kategorie + Größe, nicht Suchbegriffe
            print(f"  Kategorien-Scrape: {kategorie} / {groesse}\n")

            try:
                # ── STUFE 1: Grob-Suche ──
                grob_links = await habilleur_scrape_suchergebnisse(kategorie, groesse, config, client)
                print(f"  → {len(grob_links)} Artikel nach Grob-Filter\n")

                # ── STUFE 2: Detail-Scraping ──
                for link in grob_links:
                    details = await scrape_artikel_details(link["url"], client)
                    if details:
                        alle_roh.append(details)
                        print(f"    ✓ {details['titel'][:50]} – {details['preis']}")
                    await asyncio.sleep(random.uniform(*pauses_art))

            except Exception as e:
                print(f"  ⚠️  Fehler bei Habilleur Scrape: {e}")

    elif quelle == "ebay":
        # ─────────────────────────────────────────────
        #  EBAY: REST-API-Calls
        # ─────────────────────────────────────────────

        kategorie = config.get("kategorie", None)
        groesse = config.get("groesse", "M")

        print(f"  Artikelsuche auf eBay gestartet.\n")

        user_token = get_new_token()

        item_ids = get_summary_of_articles_json(
            max_price=config.get("max_preis", 40),
            keywords=config.get("suchbegriffe", ""),
            brand=config.get("marke", None),
            color=config.get("farbe", ""),
            category=kategorie,
            size=groesse,
            min_condition=config.get("min_zustand", "Gut"),
            item_amount=config.get("max_artikel_pro_suche", 10),
            material=config.get("material", ""),

            user_token=user_token,
        )


        product_details = await get_detailed_items_async(item_ids=item_ids, user_token=user_token)

        if not product_details:
            return

        print("    Gefundene Artikel:\n")

        for product in product_details: # type: ignore
            alle_roh.append(product)
            print(f"    ✓ {product['title'][:50]} – {product['price']}")

    else:
        print("Error bei der Marketplace-Wahl.")


    """
    3. DEDUPLIZIERUNG --> verhindert, dass Artikel mehrfach gescannt werden
    """
    seen, unique = set(), []
    for artikel in alle_roh:
        if artikel["url"] not in seen:
            seen.add(artikel["url"])
            unique.append(artikel)


    """
    4. LLM-Analyse (ollama) 
    --> gesammelte Daten werden an ollama geschickt (Performance/Größe gut)
    --> "ThreadPoolExecuter", um 3 Artikel parallel zu analysieren (spart Zeit)
    """
    print(f"\n✨ {len(unique)} Artikel → Ollama (asynchron)...\n")

    if quelle == "vinted":
        tasks = [analysiere_artikel_vinted(artikel, config) for artikel in unique]
        ergebnisse = await asyncio.gather(*tasks)

    elif quelle == "habilleur":
        tasks = [analysiere_artikel_habilleur(artikel, config) for artikel in unique]
        ergebnisse = await asyncio.gather(*tasks)

    elif quelle == "ebay":
        tasks = [analysiere_artikel_ebay(artikel, config) for artikel in unique]
        ergebnisse = await asyncio.gather(*tasks)

    else:
        print("Error bei der Marketplace-Wahl.")
        return

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

    if quelle == "vinted":
        print(f"   Stufe 1 (Grob):  {min(max_suchen, len(config['stile']))} Suchen")
    elif quelle == "habilleur":
        print(f"   Stufe 1 (Grob):  {config.get('kategorie')} / {config.get('groesse')}")
    elif quelle == "ebay":
        print(f"   Stufe 1 (Grob):  {config.get('kategorie')} / {config.get('groesse')}")
    print(f"   Stufe 2 (Detail): {len(unique)} Artikel erhalten")
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
    parser.add_argument("--user_email", default=None)  #
    args = parser.parse_args()
    cfg = lade_config(args.config)
    cfg["_pfad"] = args.config
    if args.user_email:
        cfg["user_email"] = args.user_email
    asyncio.run(main(cfg))