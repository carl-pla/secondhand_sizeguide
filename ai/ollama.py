import json
import httpx # type: ignore
from database.config_defaults import ZUSTAND_RANG

"""
=== WORKFLOW GROB ===
1. Informationen werden reingebracht --> frage_ollama
2. Informationen werden geprüft --> analysiere_artikel 
"""


"""
=== STUFE 1 ===
Funktion nur als Schnittstelle zwischen menschlichem Prompt und dem LLM Gehirn (ollama), 
weiss nichts über Vinted o.ä.
"""
def frage_ollama(prompt: str, ollama_url: str, modell: str) -> str:
    # Prüft, ob Modell vorhanden bzw. angegebebn und erreicht werden muss 
    if not modell:
        print("  ⚠️  Kein Modellname übergeben!")
        return ""
    # Versand der Informationen via HTTP-Post an ollama (max 2min)
    try:
        response = httpx.post(
            ollama_url,
            json={"model": modell, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.1} # Niedrige Temp = KI bleibt sachlich und "erfindet" weniger
                  }, 
            timeout=180.0
        )
        # Fehlerbehandlung: ollama erreichbar?
        if response.status_code != 200:
            print(f"  ⚠️  Ollama HTTP {response.status_code}")
            return ""
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"  ⚠️  Ollama-Fehler: {e}")
        return ""

"""
=== STUFE 2 ===
Hauptfunktion der Datei: Schritt 1. Subjektive LLM Analyse, 2. Harter Faktencheck 
"""
def analysiere_artikel(artikel: dict, config: dict) -> dict:
    # lädt Daten aus der Konfiguration (config.json, die in streamlit personalisert wird)
    eigene      = config.get("eigene_masse", {})
    stile       = ", ".join(config.get("stile", ["Vintage"]))
    min_zustand = config.get("min_zustand", "Gut")
    min_rang    = ZUSTAND_RANG.get(min_zustand, 2)

    """
    1.Prompt: Was soll das LLM machen, wie soll sie bewerten, 
    und schlussendlich soll sie ihre Ergebnisse in einer JSON zurückgeben
    """
    prompt = f"""You are a vintage fashion curator. Evaluate if this item fits the client.

Client:
- Style: {stile}
- Size: {config['groesse']}
- Max Price: {config['max_preis']}€
- Min Condition: {min_zustand}

Item:
- Title: {artikel['titel']}
- Price: {artikel['preis']}
- Description: {artikel['beschreibung']}

CRITICAL RULES:
1. For "masse": ONLY extract cm-values explicitly written in the description. If none found, set ALL to null. DO NOT use the client's measurements.
2. If no measurements in description: score 7 if style+size match, 6 if uncertain.
3. If measurements found AND they fit (±4cm): score 8-10.
4. If measurements found AND they DON'T fit: score 3-5.

Respond ONLY with this JSON:
{{
  "masse": {{"brust_cm":null,"taille_cm":null,"laenge_cm":null}},
  "zustand": "Gut/Sehr gut/Wie neu/Befriedigend",
  "passt_groesse": true/false,
  "begruendung": "max 2 Sätze auf Deutsch",
  "bewertung": 1-10,
  "empfohlen": true/false
}}"""

# SCORE WEIGHTING: relativ euphorisch angesetzt, um mehr reinzubringen und dann harter auszusortiren 
    
    # Nach Prompt kommt der Analyseteil 
    print(f"    🤖 Analysiere: {artikel['titel'][:50]}...")
    antwort = frage_ollama(prompt, config["ollama_url"], config["ollama_modell"])

    if not antwort:
        return {**artikel, "analyse_fehler": True}

    
    
    """
    2. JSON Parsen: LLM Ausgabe in Dict packen
    """
    try:
        analyse = json.loads(antwort)
    except:
    # Falls die KI Text vor oder nach dem JSON schreibt, suchen wir nur die Klammern { } --> flexibler 
        try:
            start = antwort.find("{")
            end   = antwort.rfind("}") + 1
            analyse = json.loads(antwort[start:end])
        except:
            return {**artikel, "analyse_fehler": True, "raw": antwort[:200]}

    
    """
    3. Harte Python-Checks mit eigenen Maßen (), verhindert auch Hallzunationen 
    """
    try:
        """
        3.1 Preis-Parsing und harter Check, ob ollama nicht falsche Preise ausgegeben hat oder formatiert hat
        """
        # Ersetze Komma durch Punkt, falls vorhanden
        preis_roh = artikel["preis"].replace(',', '.')
        
        # Extrahiere nur Ziffern und den (jetzt vorhandenen) Punkt
        preis_bereinigt = ''.join(c for c in preis_roh if c.isdigit() or c == '.')
        
       # Falls mehrere Punkte entstanden sind (z.B. durch Tippfehler), nimm nur den ersten
        if preis_bereinigt.count('.') > 1:
            teile = preis_bereinigt.split('.')
            preis_bereinigt = teile[0] + "." + "".join(teile[1:])
            
        preis_zahl = float(preis_bereinigt)
        
        # Wenn Preis > Budget: Artikel ablehnen (Score auf 4 runter)
        if preis_zahl > config["max_preis"]:
            analyse["empfohlen"] = False
            analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
            analyse["begruendung"] = f"Preis {preis_zahl}€ zu hoch (Max: {config['max_preis']}€). "
    except Exception as e:
        print(f"DEBUG: Preis-Parsing fehlgeschlagen für '{artikel['preis']}': {e}")


    
    """
    3.2 Zustand überprüfen
    """
    zustand = analyse.get("zustand", "")
    if zustand in ZUSTAND_RANG:
        if ZUSTAND_RANG[zustand] < min_rang:
            analyse["empfohlen"] = False
            analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
            analyse["begruendung"] = f"Zustand '{zustand}' unter '{min_zustand}'. " + analyse.get("begruendung", "")

    """
    3.3 Mindestbewertung, jedoch aktuell auf 6 hardgecodet --> soll mit Schieberegl in "Ergebnissen" angepasst werden
    was dann letztendlich in der Empfehlung JSON landet
    """
    if (analyse.get("bewertung") or 0) < 6:
        analyse["empfohlen"] = False

    
    """
    4. PASSFORM-VERGLEICH: Mathematische Berechnung der Differenz von Maßen, was gefunden wurde und was angegeben wurde
    """
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
            if abs(diff) <= 4: # Differenzwert liegt hardgecodet bei 4cm??? --> so lassen???
                passform_hinweise.append(f"{label}: passt gut")
            elif diff > 0:
                passform_hinweise.append(f"{label}: +{diff}cm größer")
            else:
                passform_hinweise.append(f"{label}: {diff}cm kleiner")

    
    """
    5. RÜCKGABE: Alle Daten für MongoDB und das Dashboard zusammenführen --> an main.py geschickt 
    """
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