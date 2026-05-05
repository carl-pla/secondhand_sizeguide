"""
=== DEBUG SCRIPT für Habilleur Größen-Extraktion ===

Dieses Script hilft dir, die Größen-Extraktion zu debuggen.
Nutze es, um zu prüfen:
1. Ob die Artikel-Details richtig gescraped werden
2. Welche Kategorien erkannt werden
3. Wie das LLM die Größen extrahiert

Verwendung:
    python debug_habilleur.py <artikel-url>
"""

import asyncio
import json
import sys
from scraper.habilleur_scraper import scrape_artikel_details
from ai.ollama import analysiere_artikel_habilleur
from database.config_defaults import lade_config


async def debug_habilleur(artikel_url: str):
    """
    Debugge einen einzelnen Habilleur-Artikel
    
    Args:
        artikel_url: URL des zu debuggenden Artikels
    """
    
    print(f"\n{'='*70}")
    print(f"  🔍 HABILLEUR DEBUG: {artikel_url}")
    print(f"{'='*70}\n")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCHRITT 1: ARTIKEL-DETAILS SCRAPEN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("📝 SCHRITT 1: Scrape Artikel-Details...\n")
    
    artikel = await scrape_artikel_details(artikel_url)
    
    if not artikel:
        print("❌ Fehler beim Scraping!")
        return
    
    print("✅ Artikel-Details gescraped:")
    print(f"   Titel: {artikel['titel']}")
    print(f"   Preis: {artikel['preis']}")
    print(f"   Material: {artikel['material']}\n")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCHRITT 2: CONFIG LADEN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("⚙️  SCHRITT 2: Lade Config...\n")
    
    config = lade_config()
    
    print(f"   Kategorie: {config.get('kategorie')}")
    print(f"   Größe (Label): {config.get('groesse')}")
    print(f"   Habilleur Maße: {config.get('habilleur_masse')}")
    print(f"   Max Preis: {config.get('max_preis')}€\n")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCHRITT 3: ANALYSIERE MIT OLLAMA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("🤖 SCHRITT 3: Analysiere mit Ollama...\n")
    
    analyse = await analysiere_artikel_habilleur(artikel, config)
    
    if analyse.get("analyse_fehler"):
        print("❌ Fehler bei der Analyse!")
        if "raw" in analyse:
            print(f"\n💾 Raw Ollama-Antwort:\n{analyse['raw']}")
        return
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCHRITT 4: ERGEBNISSE AUSGEBEN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("✅ SCHRITT 4: Analyseergebnisse\n")
    
    print("📏 Erkannte Maße:")
    masse = analyse.get("masse", {})
    if masse:
        for key, value in masse.items():
            if value is not None:
                expected = config.get("habilleur_masse", {}).get(key)
                if expected:
                    diff = value - expected
                    sign = "+" if diff > 0 else ""
                    print(f"   {key:25} = {value:3}cm  (deine: {expected}cm, {sign}{diff}cm)")
                else:
                    print(f"   {key:25} = {value:3}cm")
        print()
    else:
        print("   ⚠️  Keine Maße erkannt!\n")
    
    print("📊 Bewertung:")
    print(f"   Passt Größe: {analyse.get('passt_groesse')}")
    print(f"   Bewertung: {analyse.get('bewertung')}/10")
    print(f"   Empfohlen: {analyse.get('empfohlen')}")
    print(f"   Grund: {analyse.get('begruendung')}\n")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCHRITT 5: DIAGNOSTIK
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("🔧 DIAGNOSE:\n")
    
    # Check 1: Kategorie im Titel?
    kategorie = config.get("kategorie", "").lower()
    titel_lower = artikel["titel"].lower()
    if kategorie in titel_lower:
        print(f"   ✅ Kategorie '{kategorie}' im Artikel-Titel erkannt")
    else:
        print(f"   ⚠️  Kategorie '{kategorie}' NICHT im Titel. LLM könnte verwirrt sein!")
        print(f"      Titel: {artikel['titel']}")
    
    # Check 2: Größe im Titel?
    print(f"\n   Titel-Analyse:")
    print(f"   → '{artikel['titel']}'")
    print(f"   → Enthält diesen auch Größen-Label oder Maße?")
    
    # Check 3: Beschreibung-Länge
    beschr_len = len(artikel.get("beschreibung", ""))
    if beschr_len > 500:
        print(f"\n   ✅ Beschreibung ausreichend ({beschr_len} Zeichen)")
    elif beschr_len > 100:
        print(f"\n   ⚠️  Beschreibung kurz ({beschr_len} Zeichen)")
    else:
        print(f"\n   ❌ Beschreibung zu kurz ({beschr_len} Zeichen)")
        print(f"      Material: {artikel.get('material')}")
    
    # Check 4: Maße gefunden?
    masse_count = sum(1 for v in masse.values() if v is not None)
    if masse_count > 0:
        print(f"\n   ✅ {masse_count} Maße erkannt (von max 14)")
    else:
        print(f"\n   ❌ KEINE Maße erkannt!")
        print(f"      Prüfe die Beschreibung auf Maße:")
        print(f"      {artikel['beschreibung'][:300]}...")
    
    print(f"\n{'='*70}\n")


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n❌ Fehler: URL erforderlich!")
        print("\nBeispiel:")
        print("  python debug_habilleur.py 'https://habilleurjean.com/de/...'")
        return
    
    artikel_url = sys.argv[1]
    
    # URL-Validierung
    if not artikel_url.startswith("http"):
        print(f"❌ Ungültige URL: {artikel_url}")
        print("   URL muss mit 'http://' oder 'https://' beginnen")
        return
    
    await debug_habilleur(artikel_url)


if __name__ == "__main__":
    asyncio.run(main())
