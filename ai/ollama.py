import json
import httpx
from pathlib import Path


# ─────────────────────────────────────────────
#  OLLAMA
# ─────────────────────────────────────────────
def frage_ollama(prompt: str, ollama_url: str, modell: str) -> str:
    if not modell:
        print("  ⚠️  Fehler: Kein Modellname übergeben!")
        return ""
    try:
        payload = {"model": modell, "prompt": prompt, "stream": False}
        response = httpx.post(ollama_url, json=payload, timeout=120.0)
        
        # Debug: Zeige was wirklich zurückkommt, wenn es kein 200 OK ist
        if response.status_code != 200:
            print(f"  ⚠️  Ollama HTTP Fehler {response.status_code}: {response.text}")
            return ""

        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"  ⚠️  Ollama-Verbindungsfehler: {e}")
        return ""

def analysiere_artikel(artikel: dict, config: dict) -> dict:
    eigene = config.get("eigene_masse", {})
    stile = ", ".join(config.get("stile", ["Vintage"]))

    prompt = f"""You are a fashion assistant analyzing a secondhand clothing listing.
Buyer preferences: {stile} style, size {config['groesse']}, max price {config['max_preis']}€.
Buyer measurements: bust {eigene.get('brust','?')}cm, waist {eigene.get('taille','?')}cm, hips {eigene.get('huefte','?')}cm, shoulders {eigene.get('schulter','?')}cm.

Listing: 
Title: {artikel['titel']}
Price: {artikel['preis']}
Description: {artikel['beschreibung']}

Tasks:
1. Extract ALL measurements (bust, waist, hips, shoulders, length, sleeve, inseam, rise, any cm/inch values)
2. Extract condition and material if mentioned
3. Assess fit for buyer's style and size
4. Rate relevance 1-10

Respond ONLY with JSON, no text before or after:
{{
  "masse": {{
    "brust_cm": null, "taille_cm": null, "huefte_cm": null,
    "schulter_cm": null, "laenge_cm": null, "aermel_cm": null,
    "innennaht_cm": null, "sonstiges": {{}}
  }},
  "zustand": null,
  "material": null,
  "passt_groesse": true,
  "passt_stil": true,
  "begruendung": "kurze Begründung auf Deutsch",
  "bewertung": 7,
  "empfohlen": true
}}"""

    print(f"    🤖 Analysiere: {artikel['titel'][:50]}...")
    antwort = frage_ollama(prompt, config["ollama_url"], config["ollama_modell"])
    if not antwort:
        return {**artikel, "analyse_fehler": True}

    try:
        analyse = json.loads(antwort)
    except:
        try:
            start = antwort.find("{")
            end = antwort.rfind("}") + 1
            analyse = json.loads(antwort[start:end])
        except:
            return {**artikel, "analyse_fehler": True, "raw": antwort[:200]}

    # Passform-Vergleich
    passform_hinweise = []
    masse = analyse.get("masse", {})
    for key, label, eigener_wert in [
        ("brust_cm", "Brust", eigene.get("brust")),
        ("taille_cm", "Taille", eigene.get("taille")),
        ("huefte_cm", "Hüfte", eigene.get("huefte")),
        ("schulter_cm", "Schulter", eigene.get("schulter")),
    ]:
        if masse.get(key) and eigener_wert:
            diff = masse[key] - eigener_wert
            if abs(diff) <= 4:
                passform_hinweise.append(f"{label}: passt gut")
            elif diff > 0:
                passform_hinweise.append(f"{label}: +{diff}cm größer")
            else:
                passform_hinweise.append(f"{label}: {diff}cm kleiner")

    return {
        "url": artikel["url"],
        "titel": artikel["titel"],
        "preis": artikel["preis"],
        "beschreibung": artikel["beschreibung"],
        "masse": analyse.get("masse", {}),
        "zustand": analyse.get("zustand"),
        "material": analyse.get("material"),
        "passt_groesse": analyse.get("passt_groesse"),
        "passt_stil": analyse.get("passt_stil"),
        "passform_hinweise": passform_hinweise or None,
        "begruendung": analyse.get("begruendung"),
        "bewertung": analyse.get("bewertung"),
        "empfohlen": analyse.get("empfohlen", False),
    }