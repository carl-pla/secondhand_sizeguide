import json
import httpx
from database.config_defaults import ZUSTAND_RANG

"""
=== WORKFLOW GROB ===

"""


def frage_ollama(prompt: str, ollama_url: str, modell: str) -> str:
    if not modell:
        print("  ⚠️  Kein Modellname übergeben!")
        return ""
    try:
        response = httpx.post(
            ollama_url,
            json={"model": modell, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.1}},
            timeout=120.0
        )
        if response.status_code != 200:
            print(f"  ⚠️  Ollama HTTP {response.status_code}")
            return ""
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"  ⚠️  Ollama-Fehler: {e}")
        return ""


def analysiere_artikel(artikel: dict, config: dict) -> dict:
    eigene      = config.get("eigene_masse", {})
    stile       = ", ".join(config.get("stile", ["Vintage"]))
    min_zustand = config.get("min_zustand", "Gut")
    min_rang    = ZUSTAND_RANG.get(min_zustand, 2)

    prompt = f"""You are an expert vintage fashion curator. Your goal is to find the best items for a client.

Client Preferences:
- Style: {stile}
- Targeted Size: {config['groesse']} (Note: vintage sizes vary, trust measurements more than tags)
- Max Price: {config['max_preis']}€
- Min Condition: {min_zustand}
- Client Body Measurements: Bust {eigene.get('brust','?')}cm, Waist {eigene.get('taille','?')}cm, Hips {eigene.get('huefte','?')}cm

Listing Data:
- Title: {artikel['titel']}
- Price: {artikel['preis']}
- Description: {artikel['beschreibung']}

Evaluation Rules:
1. MANDATORY: If you find measurements (cm) in the description, compare them strictly with the client's body data.
2. TOLERANCE: For explicit measurements, allow a max difference of +/- 4cm for a "perfect fit".
3. NO MEASUREMENTS? If cm-data is missing, you MUST estimate based on the brand's typical fit for size {config['groesse']}. 
4. SCORE WEIGHTING: 
   - 9-10: Style matches AND measurements are perfect.
   - 7-8: Style matches AND size is {config['groesse']}, but no exact cm-measurements found.
   - <7: Style mismatch or size/price concerns.

JSON format only:
{{
  "masse": {{"brust_cm":null,"taille_cm":null,"laenge_cm":null}},
  "zustand": "kurze Einschätzung",
  "passt_groesse": true/false,
  "begruendung": "Begründung auf Deutsch (max 2 Sätze)",
  "bewertung": 1-10,
  "empfohlen": true/false
}}"""

    print(f"    🤖 Analysiere: {artikel['titel'][:50]}...")
    antwort = frage_ollama(prompt, config["ollama_url"], config["ollama_modell"])

    if not antwort:
        return {**artikel, "analyse_fehler": True}

    # JSON parsen
    try:
        analyse = json.loads(antwort)
    except:
        try:
            start = antwort.find("{")
            end   = antwort.rfind("}") + 1
            analyse = json.loads(antwort[start:end])
        except:
            return {**artikel, "analyse_fehler": True, "raw": antwort[:200]}

    # ── Harte Python-Checks ──────────────────────────
    # 1. Preis nochmal prüfen (Ollama könnte falsch liegen)
    try:
        # Ersetze Komma durch Punkt, falls vorhanden
        preis_roh = artikel["preis"].replace(',', '.')
        
        # Extrahiere nur Ziffern und den (jetzt vorhandenen) Punkt
        preis_bereinigt = ''.join(c for c in preis_roh if c.isdigit() or c == '.')
        
       # Falls mehrere Punkte entstanden sind (z.B. durch Tippfehler), nimm nur den ersten
        if preis_bereinigt.count('.') > 1:
            teile = preis_bereinigt.split('.')
            preis_bereinigt = teile[0] + "." + "".join(teile[1:])
            
        preis_zahl = float(preis_bereinigt)

        if preis_zahl > config["max_preis"]:
            analyse["empfohlen"] = False
            analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
            analyse["begruendung"] = f"Preis {preis_zahl}€ zu hoch (Max: {config['max_preis']}€). "
    except Exception as e:
        print(f"DEBUG: Preis-Parsing fehlgeschlagen für '{artikel['preis']}': {e}")


    # 2. Zustand prüfen
    zustand = analyse.get("zustand", "")
    if zustand in ZUSTAND_RANG:
        if ZUSTAND_RANG[zustand] < min_rang:
            analyse["empfohlen"] = False
            analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
            analyse["begruendung"] = f"Zustand '{zustand}' unter '{min_zustand}'. " + analyse.get("begruendung", "")

    # 3. Bewertung unter 7 → nie empfohlen
    if (analyse.get("bewertung") or 0) < 7:
        analyse["empfohlen"] = False

    # ── Passform-Vergleich ───────────────────────────
    passform_hinweise = []
    masse = analyse.get("masse", {})
    for key, label, eigener_wert in [
        ("brust_cm",     "Brust",     eigene.get("brust")),
        ("taille_cm",    "Taille",    eigene.get("taille")),
        ("huefte_cm",    "Hüfte",     eigene.get("huefte")),
        ("schulter_cm",  "Schulter",  eigene.get("schulter")),
        ("laenge_cm",    "Länge",     eigene.get("laenge_oberteil")),
        ("innennaht_cm", "Innennaht", eigene.get("innennaht")),
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
        "url":               artikel["url"],
        "titel":             artikel["titel"],
        "preis":             artikel["preis"],
        "beschreibung":      artikel["beschreibung"],
        "masse":             analyse.get("masse", {}),
        "zustand":           zustand,
        "passt_groesse":     analyse.get("passt_groesse"),
        "passt_stil":        analyse.get("passt_stil"),
        "passform_hinweise": passform_hinweise or None,
        "begruendung":       analyse.get("begruendung"),
        "bewertung":         analyse.get("bewertung"),
        "empfohlen":         analyse.get("empfohlen", False),
    }