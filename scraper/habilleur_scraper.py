import asyncio
import random
from pathlib import Path
from typing import Optional, List, Dict
import httpx
from bs4 import BeautifulSoup

from database.config_defaults import HABILLEUR_GROESSEN, HABILLEUR_KATEGORIEN

"""
=== Habilleur Jean Scraper ===
Scraper für https://habilleurjean.com/de/

Habilleur Jean ist auf Second Hand Anzüge, Jacken und Mäntel spezialisiert.
Die Website verwendet ein E-Commerce-System mit kategoriebasierten URLs.

=== Workflow ===
1. STUFE 1 (Grob-Suche): 
   - Sammle alle Produktlinks einer Größe/Kategorie
   - Filtere nach Preis
   
2. STUFE 2 (Fein-Details):
   - Rufe jedes Produkt auf
   - Extrahiere: Titel, Preis, Beschreibung, Material, Zustand, etc.
"""

BASE_URL = "https://habilleurjean.com/de/collections"

# ─────────────────────────────────────────────
#  STUFE 1: GROB-SUCHE — Links + Preise sammeln
# ─────────────────────────────────────────────
async def scrape_suchergebnisse(
    kategorie: str, groesse: str, config: dict, client: Optional[httpx.AsyncClient] = None
) -> List[Dict[str, str]]:
    """
    Sammelt alle Produktlinks einer Kategorie und Größe von Habilleur Jean.
    
    Args:
        kategorie: Z.B. "Anzug", "Jacket", "Mantel"
        groesse: Z.B. "M", "L", "XL"
        config: Dict mit max_artikel, max_preis, etc.
        client: Optional: httpx.AsyncClient für Requests
    
    Returns:
        Liste mit Dicts: {"url": "...", "preis": "...", "titel": "..."}
    """
    
    kategorie_slug = HABILLEUR_KATEGORIEN.get(kategorie, kategorie.lower())
    groesse_slug = HABILLEUR_GROESSEN.get(groesse, groesse.lower())
    
    # Habilleur nutzt URL-Filter: /collections/{kategorie}-{groesse}
    url = f"{BASE_URL}/{kategorie_slug}-{groesse_slug}?filter.v.availability=1"
    
    max_artikel = config.get("max_artikel_pro_suche", 50)
    max_preis = config.get("max_preis", 200)
    
    print(f"\n🔍 Grobe Suche: '{kategorie}' | Größe: {groesse} | Max_Preis: {max_preis}€ | Max_Artikel: {max_artikel}")
    print(f"   URL: {url}")
    
    try:
        # Erstelle einen Client, wenn nicht vorhanden
        own_client = False
        if client is None:
            client = httpx.AsyncClient()
            own_client = True
        
        # Abrufen der Seite mit User-Agent und Verzögerung
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        response = await client.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        # Parse HTML mit BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        artikel_links = []
        
        # ─────────────────────────────────────────────
        #  Robuste Produktsuche: mehrere CSS-Selektoren testen
        # ─────────────────────────────────────────────
        
        # Typische E-Commerce Strukturen:
        selektoren_produkte = [
            "div[data-product-item]",           # Standard data-attribute
            "div[class*='product-item']",       # Klasse mit 'product-item'
            "div[class*='product-card']",       # Klasse mit 'product-card'
            "li[class*='product']",             # List-Item mit 'product'
            "article[class*='product']",        # Article mit 'product'
            "div.product",                      # Direkte product-Klasse
        ]
        
        produkt_divs = []
        for selektor in selektoren_produkte:
            try:
                produkt_divs = soup.select(selektor)
                if produkt_divs:
                    print(f"   ✓ {len(produkt_divs)} Produkte gefunden (Selektor: {selektor})")
                    break
            except:
                continue
        
        if not produkt_divs:
            print(f"   ⚠️  Keine Produkte gefunden. Website-Struktur könnte sich geändert haben.")
            print(f"   💡 Debug-Tipp: Überprüfe die HTML-Struktur unter {url}")
            return []
        
        # ─────────────────────────────────────────────
        #  Extrahiere Link, Titel und Preis aus jedem Produkt
        # ─────────────────────────────────────────────
        for produkt in produkt_divs[:max_artikel]:
            try:
                # Link extrahieren
                link_candidates = [
                    produkt.find("a"),
                    produkt.find("a", href=True),
                ]
               
                href = None
                for link in link_candidates:
                    if link and link.get("href"):
                        href = link.get("href")
                        break
                
                if not href:
                    continue
                
                # URL normalisieren
                if href.startswith("/"):
                    full_url = f"https://habilleurjean.com{href}"
                elif not href.startswith("http"):
                    full_url = f"https://habilleurjean.com/de/{href}"
                else:
                    full_url = href
                
                # Duplikate entfernen (Tracking-Parameter)
                full_url = full_url.split("?")[0]
                if full_url in [a["url"] for a in artikel_links]:
                    continue
                
                # Titel extrahieren
                titel_el = produkt.find("h2") or produkt.find("h3") or produkt.find("a")
                titel = titel_el.get_text(strip=True) if titel_el else "Unbekannt"
                
                # Preis extrahieren: mehrere Versuche
                preis_text = "?"
                for preis_selektor in ["span[class*='price']", "div[class*='price']", "span.price"]:
                    preis_el = produkt.select_one(preis_selektor)
                    if preis_el:
                        preis_text = preis_el.get_text(strip=True)
                        break
                
                # Fallback: nach '€' suchen
                if preis_text == "?":
                    for el in produkt.find_all(["span", "div"]):
                        text = el.get_text(strip=True)
                        if "€" in text or "," in text:
                            preis_text = text
                            break
                
                # Preis-Filter: nur Artikel unter max_preis
                preis_zahl = _parse_preis(preis_text)
                if preis_zahl and preis_zahl > max_preis:
                    continue  # ← Grob-Filter: zu teuer
                
                artikel_links.append({
                    "url": full_url,
                    "titel": titel,
                    "preis": preis_text.strip() or "?",
                })
                
            except Exception as e:
                continue
        
        print(f"  ✓ {len(artikel_links)} Artikel nach Grob-Filter")
        return artikel_links
    
    except Exception as e:
        print(f"  ❌ Fehler bei Grob-Suche: {e}")
        return []
    
    finally:
        if client and own_client:
            await client.aclose()


# ─────────────────────────────────────────────
#  STUFE 2: FEIN-DETAILS — Artikel-Details scrapen
# ─────────────────────────────────────────────
async def scrape_artikel_details(
    url: str, client: Optional[httpx.AsyncClient] = None, kategorie: Optional[str] = None
) -> Optional[Dict]:
    """
    Scrapt alle Details eines Produkts.
    
    Args:
        url: Produkt-URL
        client: Optional httpx.AsyncClient
        kategorie: Optional Kategorie (z.B. "Anzug", "Jacke", "Mantel") 
                  Falls nicht angegeben, wird versucht, sie aus der URL/dem Titel zu extrahieren
    
    Returns:
        Dict mit: titel, preis, beschreibung, material, zustand, kategorie, etc.
        oder None bei Fehler
    """
    
    try:
        # Erstelle einen Client, wenn nicht vorhanden
        own_client = False
        if client is None:
            client = httpx.AsyncClient()
            own_client = True
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        await asyncio.sleep(random.uniform(1, 2))
        
        response = await client.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Titel
        titel = "Unbekannt"
        for selektor in ["h1", "h2", "[data-product-title]"]:
            el = soup.select_one(selektor)
            if el:
                titel = el.get_text(strip=True)
                break
        
        # Preis (Verkaufspreis, nicht ursprünglicher Preis)
        preis = "Unbekannt"
        for selektor in [
            "span[class*='price']",
            "div[class*='price']",
            "[data-product-price]",
            "span.price",
        ]:
            el = soup.select_one(selektor)
            if el:
                preis = el.get_text(strip=True)
                break
        
        # Beschreibung
        beschreibung = "Keine Beschreibung"
        for selektor in [
            "div[class*='description']",
            "div[class*='product-description']",
            "[itemprop='description']",
            "div.description",
        ]:
            el = soup.select_one(selektor)
            if el:
                text = el.get_text(strip=True)
                if len(text) > 10:
                    beschreibung = text[:8000]
                    break
        
        # Zusätzliche Felder: Material, Zustand, Brand
        material = "Unbekannt"
        zustand = "Unbekannt"
        brand = "Habilleur Jean"
        
        # Suche nach Material im Text
        for selektor in [
            "span[class*='material']",
            "div[class*='material']",
            "[data-material]",
        ]:
            el = soup.select_one(selektor)
            if el:
                material = el.get_text(strip=True)
                break
        
        # Fallback: im gesamten Produkt-Text nach "Material:" suchen
        if material == "Unbekannt":
            all_text = soup.get_text()
            if "Material:" in all_text:
                for line in all_text.split("\n"):
                    if "Material:" in line:
                        material = line.split("Material:")[-1].strip()
                        break
        
        # ─────────────────────────────────────────────
        #  KATEGORIE-EXTRAKTION
        # ─────────────────────────────────────────────
        # Falls nicht übergeben, versuche aus URL oder Titel zu extrahieren
        if not kategorie:
            # Versuche aus URL zu extrahieren
            for kat in ["anzug", "costume", "jacke", "jacket", "veste", "mantel", "coat", "manteau"]:
                if kat in url.lower():
                    kategorie = "Anzug" if kat in ["anzug", "costume"] else \
                               "Jacke" if kat in ["jacke", "jacket", "veste"] else \
                               "Mantel" if kat in ["mantel", "coat", "manteau"] else "Unbekannt"
                    break
            
            # Falls nicht in URL: versuche aus Titel zu extrahieren
            if not kategorie:
                titel_lower = titel.lower()
                if any(w in titel_lower for w in ["anzug", "suit", "costumes", "costume"]):
                    kategorie = "Anzug"
                elif any(w in titel_lower for w in ["jacke", "jacket", "blazer", "sakko", "veste"]):
                    kategorie = "Jacke"
                elif any(w in titel_lower for w in ["mantel", "coat", "parka", "overcoat", "manteau"]):
                    kategorie = "Mantel"
                else:
                    kategorie = "Unbekannt"
        
        return {
            "url": url,
            "titel": titel,
            "preis": preis,
            "beschreibung": beschreibung,
            "material": material,
            "zustand": zustand,
            "brand": brand,
            "kategorie": kategorie,  # ← NEU: Kategorie hinzugefügt
        }
    
    except Exception as e:
        print(f"  ⚠️  Detail-Fehler bei {url}: {e}")
        return None
    
    finally:
        if client and own_client:
            await client.aclose()


# ─────────────────────────────────────────────
#  HILFSFUNKTION: Preis-Parser
# ─────────────────────────────────────────────
def _parse_preis(preis_text: str) -> Optional[float]:
    """
    Konvertiert einen Preis-String in eine Zahl.
    
    Beispiele:
        "19,99 €" → 19.99
        "€ 19.99" → 19.99
        "19.50" → 19.5
    
    Returns:
        float oder None
    """
    try:
        # Entferne alle Zeichen außer Ziffern, Komma, Punkt
        cleaned = "".join(c for c in preis_text if c.isdigit() or c in ".,")
        if not cleaned:
            return None
        
        # Ersetze Komma durch Punkt (deutsches Format)
        cleaned = cleaned.replace(",", ".")
        
        # Falls mehrere Punkte: behalte nur den letzten (z.B. "1.234,99" → "1234.99")
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        
        return float(cleaned)
    except:
        return None


# ─────────────────────────────────────────────
#  BEISPIEL: Kompletter Scrape-Workflow
# ─────────────────────────────────────────────
async def scrape_komplett(config: dict) -> dict:
    """
    Führt kompletten Scrape aus: Stufe 1 + Stufe 2
    
    Args:
        config: Dict mit kategorie, groesse, max_artikel_pro_suche, max_preis, etc.
    
    Returns:
        Dict mit: artikel_links (Stufe 1) und artikel_details (Stufe 2)
    """
    
    kategorie = config.get("kategorie", "Anzug")
    groesse = config.get("groesse", "M")
    
    # Verwende einen einzigen Client für alle Requests (effizienter)
    async with httpx.AsyncClient() as client:
        # Stufe 1: Sammle Links
        links = await scrape_suchergebnisse(kategorie, groesse, config, client)
        
        print(f"\n📄 Starte Detail-Scrape für {len(links)} Artikel...")
        
        # Stufe 2: Scrape Details
        artikel_details = []
        for i, link_info in enumerate(links, 1):
            details = await scrape_artikel_details(link_info["url"], client, kategorie)
            if details:
                artikel_details.append(details)
                print(f"  [{i}/{len(links)}] ✓ {details['titel'][:40]}...")
            else:
                print(f"  [{i}/{len(links)}] ✗ Fehler")
        
        print(f"\n✅ Scrape abgeschlossen: {len(artikel_details)}/{len(links)} erfolgreiche Details")
        
        return {
            "artikel_links": links,
            "artikel_details": artikel_details,
        }


# ─────────────────────────────────────────────
#  FOR DEBUGGING: Test ob BeautifulSoup ausreicht
# ─────────────────────────────────────────────
if __name__ == "__main__":
    """
    Test-Script: Versuche Habilleur Jean zu scrapen
    
    Wenn die Seite keine Produkte findet:
    → Die Website könnte JavaScript verwenden (dann: auf Playwright wechseln)
    → Oder die HTML-Struktur ist anders als erwartet (→ CSS-Selektoren anpassen)
    """
    
    import sys
    
    test_config = {
        "kategorie": "Anzug",
        "groesse": "M",
        "max_artikel_pro_suche": 10,
        "max_preis": 200,
    }
    
    print("🚀 Starte Habilleur Jean Scraper (Test)...")
    print("=" * 60)
    
    result = asyncio.run(scrape_komplett(test_config))
    
    print("\n" + "=" * 60)
    print(f"Ergebnis:")
    print(f"  Links gefunden: {len(result['artikel_links'])}")
    print(f"  Details gescrapt: {len(result['artikel_details'])}")
    
    if result["artikel_details"]:
        print(f"\n📋 Erste Produkt-Details:")
        print(f"   Titel: {result['artikel_details'][0]['titel']}")
        print(f"   Preis: {result['artikel_details'][0]['preis']}")
        print(f"   Material: {result['artikel_details'][0]['material']}")
        print(f"   Beschreibung: {result['artikel_details'][0]['beschreibung'][:10000]}...")
        print(f"   URL: {result['artikel_details'][0]['url']}")
