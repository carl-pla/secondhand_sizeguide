import json
import httpx # type: ignore
from database.config_defaults import ZUSTAND_RANG
from ai.habilleur_regex import extract_measurements_habilleur

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
async def frage_ollama(prompt: str, ollama_url: str, modell: str) -> str:
    if not modell:
        print("  ⚠️  Kein Modellname übergeben!")
        return ""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ollama_url,
                json={"model": modell, "prompt": prompt, "stream": False,
                      "options": {"temperature": 0.1}
                      },
                timeout=800.0  # 10 Minuten - LLM braucht Zeit für komplexe Prompts
            )
        # Fehlerbehandlung, falls Ollama nicht erreichbar ist
        if response.status_code != 200:
            print(f"  ⚠️  Ollama HTTP {response.status_code}")
            return ""
        
        if response.status_code == 404:
            print(f"  ⚠️  Ollama 404 – URL falsch: {ollama_url}")
            print(f"  ⚠️  Verfügbare Endpoints: {httpx.get(ollama_url.replace('/api/generate','/')).text[:200]}")
            return ""
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"  ⚠️  Ollama-Fehler: {type(e).__name__}: {e}")
        return ""


# ─────────────────────────────────────────────
# Regeln für LLM
# ─────────────────────────────────────────────

SCORING_RULES = """SCORING RULES (be conservative and critical):
- 9-10: ALL client properties match AND measurements explicitly found AND fit perfectly (±4cm)
- 7-8:  MOST properties match AND size tag matches, NO measurements found → max 7
- 5-6:  Some properties match but style/color/material deviates noticeably OR size uncertain
- 3-4:  Price too high OR condition below minimum OR significant property mismatch
- 1-2:  Multiple mismatches, wrong size, wrong category
- NEVER give 8+ without at least 3 matching properties
- NEVER give 7+ if price exceeds budget
- NEVER give 6+ if condition is below minimum
- Default to lower score when uncertain"""

UNIT_CONVERSION_RULES = """UNIT CONVERSION RULES:
- ALWAYS check the unit of measurement in the description
- If measurements are in inches ("), ALWAYS convert to cm (multiply by 2.54)
- If measurements are in mm, ALWAYS convert to cm (divide by 10)
- Common indicators for inches: ", inch, Zoll, '
- Example: 34" Taille = 34 × 2.54 = 86cm → hose_taillenweite = 43 (half circumference)
- NEVER copy the raw number without converting"""

MEASUREMENT_RULES_VINTED = """MEASUREMENT RULES (all values in cm, convert if necessary, null if uncertain):
- brust_cm           = chest circumference at the widest point
- taille_cm          = waist circumference at the narrowest point
- huefte_cm          = hip circumference at the widest point
- schulter_cm        = shoulder width from seam to seam
- laenge_oberteil_cm = body length from shoulder to hem for tops/jackets. NOT coat length, NOT total body height
- laenge_hosen_cm    = total length from waistband to ankle for pants/trousers
- innennaht_cm       = inseam length from crotch to ankle ONLY, NOT outseam, NOT total leg length
- aermellaenge_cm    = sleeve length from shoulder seam to cuff (full length), ONLY for tops/jackets
- gabelhoehe_cm      = rise from crotch seam to waistband (full length), ONLY for pants
- beinoeffnung_cm    = leg opening laid flat (HALF width), ONLY for pants
- If a measurement is ambiguous, unclear or missing, use null

- There may be descriptions that contain content in multiple languages. Make sure to check and possibly translate the given measurements 
  correctly into German / the predetermined keys in the given JSON structure."""

MEASUREMENT_RULES_EBAY = """MEASUREMENT RULES (all values in cm, convert if necessary, null if not found):
JACKET:
If article is a jacket, ONLY fill the following 5 fields. ALL other masse fields MUST be null.
- schulterbreite     = shoulder width seam to seam (full width)
- aermelleange        = sleeve length shoulder seam to cuff (full length)
- jackenlaenge       = jacket length shoulder to hem (full length)
- achselbreite       = chest width underarm to underarm laid flat (full width, NOT half)
- jacke_taillenweite = jacket waist laid flat (HALF circumference). Divide by 2 if full circumference given.

TROUSERS:
If article is a pair of trousers, ONLY fill the following 4 fields. ALL other masse fields MUST be null.
- hose_taillenweite  = trouser waist laid flat (HALF circumference). Divide by 2 if full circumference given.
- gabelhoehe         = rise from crotch seam to waistband (full length)
- beinoeffnung       = leg opening laid flat (HALF width). Divide by 2 if full opening given.
- hosenlaenge        = total trouser length waistband to hem (full length)

COAT:
If article is a coat, ONLY fill the following 5 fields. ALL other masse fields MUST be null.
- mantel_schulterbreite = shoulder width seam to seam (full width)
- mantel_gesamtlaenge   = coat length shoulder to hem (full length). NOT jacket length.
- mantel_aermellaenge    = sleeve length shoulder seam to cuff (full length)
- mantel_achselbreite   = chest width underarm to underarm laid flat (full width, NOT half)
- mantel_taillenweite   = coat waist laid flat (HALF circumference). Divide by 2 if full circumference given.

- For each measurement, determine whether the given value in the article description is a full or half measurement before inserting. 
  Convert to the format specified above (some require half, some full).
- There may be descriptions that contain content in multiple languages. Make sure to check and possibly translate the given measurements 
  correctly into German / the predetermined keys in the given JSON structure.

When uncertain which measurement is meant, use null"""

MEASUREMENT_RULES_HAB = """MEASUREMENT RULES - CRITICAL READING INSTRUCTIONS:
ALWAYS read the description word-by-word and extract EXACT numbers. NEVER estimate or round.
If you cannot find a measurement, use null. NEVER guess or make up numbers.

CATEGORY DETECTION (READ TITLE & DESCRIPTION FIRST):
- If title/description contains "Anzug", "Suit", "3-piece", "costume" = SUIT category
- If contains "Jacke", "Jacket", "Blazer" (but NOT "Anzug") = JACKET category  
- If contains "Mantel", "Coat", "Parka" (but NOT "Anzug") = COAT category

SUIT EXTRACTION (Anzug / 3-piece suit / costume):
This is the MOST COMMON category. For a SUIT, MUST fill ALL of these 9 fields:
1. schulterbreite      = shoulder width seam to seam (full width). Search "Schulterbreite"
2. aermellaenge        = sleeve length shoulder to cuff. Search "Ärmellänge" or "Armlaenge". ADD any "+ X cm" values.
3. jackenlaenge        = jacket length shoulder to hem. Search "Jackenlänge"
4. achselbreite        = chest width underarm to underarm. Search "Achselbreite"
5. jacke_taillenweite  = jacket waist (HALF if measured flat). Search "Taillenweite" (jacket section). Divide by 2 ONLY if context indicates full circumference.
6. hose_taillenweite   = trouser waist (HALF if measured flat). Search "Taillenweite" (trouser section). Divide by 2 ONLY if context indicates full circumference. ADD any "+ X cm".
7. gabelhoehe          = rise from crotch to waistband. Search "Gabelhöhe" or "Schritthoehe"
8. beinoeffnung        = leg opening width (HALF if measured flat). Search "Beinöffnung" or "Hosenbein-Öffnung". Divide by 2 ONLY if context indicates full circumference.
9. hosenlaenge         = total trouser length waistband to hem. Search "Hosenlänge". ADD any "+ X cm".

SET ALL mantel_* fields to null for suits.

SUIT EXAMPLE FROM DESCRIPTION:
"Schulterbreite: 44 cm, Ärmellänge: 58 cm + 3 cm, Jackenlänge: 72 cm, Achselbreite: 52 cm, Taillenweite: 52 cm, Gabelhöhe: 29 cm, Beinöffnung: 24 cm, Hosenlänge: 98 cm + 10 cm"
EXTRACTION:
- schulterbreite: 44
- aermellaenge: 61 (= 58 + 3)
- jackenlaenge: 72
- achselbreite: 52
- jacke_taillenweite: 52
- hose_taillenweite: 47 (= 44 + 3) [Note: if separate trouser section says "44 cm + 3 cm"]
- gabelhoehe: 29
- beinoeffnung: 24
- hosenlaenge: 108 (= 98 + 10)

JACKET ONLY:
ONLY fill these 5 fields. SET ALL others to null:
- schulterbreite
- aermellaenge (ADD any "+ X cm")
- jackenlaenge
- achselbreite
- jacke_taillenweite

COAT ONLY:
ONLY fill these 5 fields. SET ALL others to null:
- mantel_schulterbreite
- mantel_gesamtlaenge
- mantel_aermellaenge (ADD any "+ X cm")
- mantel_achselbreite
- mantel_taillenweite

ADDITION RULE (CRITICAL):
When you see "X cm + Y cm" in the description, you MUST ADD them.
Examples:
- "58 cm + 3 cm zur Erweiterung" = 58 + 3 = 61 cm
- "44 cm + 3 cm" = 44 + 3 = 47 cm
- "98 cm + 10 cm" = 98 + 10 = 108 cm
NEVER ignore the addition instruction.

LANGUAGE NOTE:
Description may mix German, French, English. Common terms:
- "Schulterbreite" = shoulder width
- "Ärmellänge" / "Armlaenge" = sleeve length
- "Jackenlänge" = jacket length
- "Achselbreite" = chest/armpit width
- "Taillenweite" = waist width
- "Gabelhöhe" / "Schritthoehe" = rise/inseam
- "Beinöffnung" = leg opening
- "Hosenlänge" = trouser length

CRITICAL: If you find any measurement in the description, you MUST extract it. If you cannot find a measurement despite seeing the correct field name, use null."""

RETURN_JSON_VINTED = """{
  "masse": {
        "brust_cm": <insert value as integer/null>,
        "taille_cm": <insert value as integer/null>,
        "huefte_cm": <insert value as integer/null>,
        "schulter_cm": <insert value as integer/null>,
        "laenge_oberteil_cm": <insert value as integer/null>,
        "laenge_hosen_cm": <insert value as integer/null>,
        "innennaht_cm": <insert value as integer/null>,
        "aermellaenge_cm": <insert value as integer/null>,
        "gabelhoehe_cm": <insert value as integer/null>,
        "beinoeffnung_cm": <insert value as integer/null>
  },
  "zustand": <insert either "Neu mit Etikett", "Neu ohne Etikett", "Sehr gut", "Gut" or "Befriedigend" depending on what matches best>,
  "passt_groesse": true/false,
  "passt_stil": true/false,
  "begruendung": "<insert max 2 Sätze auf Deutsch>",
  "bewertung": 1-10 (rating out of ten),
  "empfohlen": true/false,
  "material": <insert value as string/null>
}"""

RETURN_JSON_EBAY = """{
  "masse": {
      "schulterbreite": <insert value as integer/null>,
      "aermellaenge": <insert value as integer/null>,
      "jackenlaenge": <insert value as integer/null>,
      "achselbreite": <insert value as integer/null>,
      "jacke_taillenweite": <insert value as integer/null>,
      "hose_taillenweite": <insert value as integer/null>,
      "gabelhoehe": <insert value as integer/null>,
      "beinoeffnung": <insert value as integer/null>,
      "hosenlaenge": <insert value as integer/null>,
      "mantel_schulterbreite": <insert value as integer/null>,
      "mantel_gesamtlaenge": <insert value as integer/null>,
      "mantel_aermellaenge": <insert value as integer/null>,
      "mantel_achselbreite": <insert value as integer/null>,
      "mantel_taillenweite": <insert value as integer/null>},
    },
  "zustand": <insert either "Neu mit Etikett", "Neu ohne Etikett", "Sehr gut", "Gut" or "Befriedigend" depending on what matches best>,
  "passt_groesse": true/false,
  "begruendung": "<insert max 2 Sätze auf Deutsch>",
  "bewertung": 1-10 (rating out of ten),
  "empfohlen": true/false,
  "material": <insert value as string/null>
}"""

RETURN_JSON_HAB = """{
  "masse": {
    "schulterbreite": <fill with number or null>,
    "aermellaenge": <fill with number or null>,
    "jackenlaenge": <fill with number or null>,
    "achselbreite": <fill with number or null>,
    "jacke_taillenweite": <fill with number or null>,
    "hose_taillenweite": <fill with number or null>,
    "gabelhoehe": <fill with number or null>,
    "beinoeffnung": <fill with number or null>,
    "hosenlaenge": <fill with number or null>,
    "mantel_schulterbreite": <fill with number or null>,
    "mantel_gesamtlaenge": <fill with number or null>,
    "mantel_aermellaenge": <fill with number or null>,
    "mantel_achselbreite": <fill with number or null>,
    "mantel_taillenweite": <fill with number or null>
  },
  "zustand": "Sehr gut" or "Gut" or "Befriedigend" or null,
  "passt_groesse": true or false or null,
  "begruendung": "<2-3 sentences max>",
  "bewertung": <integer 1-10>,
  "empfohlen": true or false,
  "material": "<text or null>"
}"""


"""
=== STUFE 2 ===
Hauptfunktion der Datei: Schritt 1. Subjektive LLM Analyse, 2. Harter Faktencheck 
"""
async def analysiere_artikel_vinted(artikel: dict, config: dict) -> dict:
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
    - Detailled Size: {config['eigene_masse']}
    - Max Price: {config['max_preis']}€
    - Min Condition: {min_zustand}

    Item:
    - Title: {artikel['titel']}
    - Price: {artikel['preis']}
    - Description: {artikel['beschreibung']}

    CRITICAL RULES:
    {SCORING_RULES}

    {UNIT_CONVERSION_RULES}

    {MEASUREMENT_RULES_VINTED}

    Respond ONLY with this JSON (No comments, no explanation, no markdown code blocks.):
    {RETURN_JSON_VINTED}"""
    
    # Nach Prompt kommt der Analyseteil 
    print(f"    🤖 Analysiere: {artikel['titel'][:50]}...")
    antwort = await frage_ollama(prompt, config["ollama_url"], config["ollama_modell"])

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
        
       # Falls mehrere Punkte entstanden sind (z.B. durch Tippfehler), nimm nur den letzten (macht mehr Sinn, da das Komma immer der letzte Punkt ist)
        if preis_bereinigt.count('.') > 1:
            teile = preis_bereinigt.split('.')
            preis_bereinigt = "".join(teile[:-1]) + "." + teile[-1]
            
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
    3.3 Mindestbewertung prüfen
    """
    mindest_bewertung = config.get("min_empfehlung", 6)
    if analyse.get("bewertung", 0) < mindest_bewertung:
        analyse["empfohlen"] = False
    else:
        analyse["empfohlen"] = True # ← Überschreibt Ollamas zu strenges Urteil
    
    """
    4. PASSFORM-VERGLEICH: Mathematische Berechnung der Differenz von Maßen, was gefunden wurde und was angegeben wurde
    """
    passform_hinweise = []
    masse = analyse.get("masse", {}) or {}
    for key, label, eigener_wert in [
        ("brust_cm",           "Brust",       eigene.get("brust")),
        ("taille_cm",          "Taille",      eigene.get("taille")),
        ("huefte_cm",          "Hüfte",       eigene.get("huefte")),
        ("schulter_cm",        "Schulter",    eigene.get("schulter")),
        ("laenge_oberteil_cm", "Länge Top",   eigene.get("laenge_oberteil")),
        ("laenge_hosen_cm",    "Länge Hose",  eigene.get("laenge_hosen")),
        ("innennaht_cm",       "Innennaht",   eigene.get("innennaht")),
        ("aermellaenge_cm",    "Ärmellänge",  eigene.get("aermellaenge")),
        ("gabelhoehe_cm",      "Gabelhöhe",   eigene.get("gabelhoehe")),
        ("beinoeffnung_cm",    "Beinöffnung", eigene.get("beinoeffnung")),
    ]:
        if masse.get(key) and eigener_wert:
            diff = masse[key] - eigener_wert
            if abs(diff) <= 4: # Differenzwert liegt hardgecodet bei 4cm??? --> so lassen??? ja, bin dafür
                passform_hinweise.append(f"{label}: passt gut")
            elif abs(diff) > 10:
                analyse["empfohlen"] = False
                analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
                analyse["begruendung"] = (f"Maß '{key}' weicht zu stark ab ({masse[key]} vs {eigener_wert} cm). "
                                          + analyse.get("begruendung", ""))
            elif diff > 0:
                passform_hinweise.append(f"{label}: +{diff}cm größer")
            else:
                passform_hinweise.append(f"{label}: {diff}cm kleiner")

    
    """
    5. RÜCKGABE: Alle Daten für MongoDB und das Dashboard zusammenführen --> an main.py geschickt 
    """
    return {
        "url":               artikel.get("url"),
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
        "material":          analyse.get("material", "Unbekannt")
    }


async def analysiere_artikel_habilleur(artikel: dict, config: dict) -> dict:
    # lädt Daten aus der Konfiguration (config.json, die in streamlit personalisert wird)
    # Size Label ist zu allgemein für einen Anzug, daher rausgenommen
    # da zustand und brand bisher gehardcoded sind bei habilleur, werden diese keys erstmal ignoriert
    habilleur_masse = config.get("habilleur_masse", {})
    # keine Zustandsprüfung nötig
    
    # WICHTIG: Nutze die Kategorie aus dem Artikel oder aus der Config
    artikel_kategorie = artikel.get("kategorie", config.get("kategorie", "Unbekannt"))
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PRE-EXTRACTION: Nutze Regex um kritische Maße zu extrahieren
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pre_extracted = extract_measurements_habilleur(artikel['beschreibung'])
    
    # Formatiere die pre-extracted Maße für den Prompt
    pre_extract_text = ""
    if pre_extracted:
        pre_extract_text = "\n\nIMPORTANT: I pre-extracted these measurements from the description. Verify they are correct:\n"
        for key, value in pre_extracted.items():
            pre_extract_text += f"- {key}: {value} cm\n"

    """
    1.Prompt: Was soll das LLM machen, wie soll sie bewerten, 
    und schlussendlich soll sie ihre Ergebnisse in einer JSON zurückgeben
    """
    prompt = f"""You are a vintage fashion curator. Evaluate if this item fits the client.

    Client:
    - Max Price: {config['max_preis']}€
    - Category: {config.get("kategorie")}
    - Detailled Size: {config.get("habilleur_masse")}

    Item:
    - Title: {artikel['titel']}
    - Price: {artikel['preis']}
    - Category: {artikel_kategorie}
    - Description: {artikel['beschreibung']}
    - Material: {artikel['material']}

    CRITICAL RULES:
    {SCORING_RULES}

    {UNIT_CONVERSION_RULES}

    {MEASUREMENT_RULES_HAB}
    {pre_extract_text}

    Respond ONLY with this JSON (No comments, no explanation, no markdown code blocks.):
    {RETURN_JSON_HAB}"""

    # Nach Prompt kommt der Analyseteil
    print(f"    🤖 Analysiere: {artikel['titel'][:50]}...")
    antwort = await frage_ollama(prompt, config["ollama_url"], config["ollama_modell"])

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
            end = antwort.rfind("}") + 1
            analyse = json.loads(antwort[start:end])
        except:
            return {**artikel, "analyse_fehler": True, "raw": antwort[:200]}

    """
    2.1 STRUKTUR-FIX: Falls die Massfelder auf TOP-LEVEL sind statt in "masse", packe sie rein
    Das LLM hat manchmal Schwierigkeiten mit Verschachtelung und packt die Felder auf TOP-LEVEL.
    """
    masse_felder = [
        "schulterbreite", "aermellaenge", "jackenlaenge", "achselbreite",
        "jacke_taillenweite", "hose_taillenweite", "gabelhoehe", "beinoeffnung", "hosenlaenge",
        "mantel_schulterbreite", "mantel_gesamtlaenge", "mantel_aermellaenge", "mantel_achselbreite", "mantel_taillenweite"
    ]
    
    # Prüfe, ob diese Felder auf TOP-LEVEL sind (falsch)
    top_level_masse = {k: analyse.pop(k, None) for k in masse_felder if k in analyse}
    
    # Falls Felder auf TOP-LEVEL waren: packe sie in "masse"
    if top_level_masse:
        if "masse" not in analyse or not isinstance(analyse["masse"], dict):
            analyse["masse"] = {}
        # Merge die top-level Felder ins masse-Objekt
        for key, val in top_level_masse.items():
            if val is not None:  # Überschreibe nicht mit None
                analyse["masse"][key] = val
        # Debug-Output: Zeige was fixiert wurde
        fixed_count = sum(1 for v in top_level_masse.values() if v is not None)
        print(f"    [STRUKTUR-FIX] {fixed_count} Maße von TOP-LEVEL ins 'masse'-Objekt gepackt")

    """
    3. POST-PROCESSING: Nutze Pre-Extracted Measurements als Fallback
    Falls das LLM ein Feld nicht extrahiert hat (null), nutze den Regex-Wert
    """
    if pre_extracted:
        for key, regex_value in pre_extracted.items():
            if analyse.get("masse", {}).get(key) is None:
                if "masse" not in analyse:
                    analyse["masse"] = {}
                analyse["masse"][key] = regex_value
                print(f"    [REGEX FALLBACK] {key}: {regex_value}cm (LLM konnte es nicht finden)")

    """
    4. Harte Python-Checks mit eigenen Maßen (), verhindert auch Hallzunationen 
    """
    try:
        """
        4.1 Preis-Parsing und harter Check, ob ollama nicht falsche Preise ausgegeben hat oder formatiert hat
        """
        # Ersetze Komma durch Punkt, falls vorhanden
        preis_roh = artikel["preis"].replace(',', '.')

        # Extrahiere nur Ziffern und den (jetzt vorhandenen) Punkt
        preis_bereinigt = ''.join(c for c in preis_roh if c.isdigit() or c == '.')

        # Falls mehrere Punkte entstanden sind (z.B. durch Tippfehler), nimm nur den letzten
        if preis_bereinigt.count('.') > 1:
            teile = preis_bereinigt.split('.')
            preis_bereinigt = "".join(teile[:-1]) + "." + teile[-1]

        preis_zahl = float(preis_bereinigt)

        # Wenn Preis > Budget: Artikel ablehnen (Score auf 4 runter)
        if preis_zahl > config["max_preis"]:
            analyse["empfohlen"] = False
            analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
            analyse["begruendung"] = f"Preis {preis_zahl}€ zu hoch (Max: {config['max_preis']}€)."
    except Exception as e:
        print(f"DEBUG: Preis-Parsing fehlgeschlagen für '{artikel['preis']}': {e}")

    """
    4.2 Zustandsprüfung entfällt
    """

    """
    4.3 Mindestbewertung kann mit Schieberegler in "Ergebnissen" angepasst werden
    """
    mindest_bewertung = config.get("min_empfehlung", 6)
    if analyse.get("bewertung", 0) < mindest_bewertung:
        analyse["empfohlen"] = False
    else:
        analyse["empfohlen"] = True  # ← Überschreibt Ollamas zu strenges Urteil

    """
    5. PASSFORM-VERGLEICH: Mathematische Berechnung der Differenz von Maßen, was gefunden wurde und was angegeben wurde
    """
    passform_hinweise = []
    masse = analyse.get("masse", {}) or {}
    for key, label, eigener_wert in [
        ("schulterbreite", "Schulterbreite", habilleur_masse.get("schulterbreite")),
        ("aermellaenge", "Ärmellänge", habilleur_masse.get("aermellaenge")),
        ("jackenlaenge", "Jackenlänge", habilleur_masse.get("jackenlaenge")),
        ("achselbreite", "Achselbreite", habilleur_masse.get("achselbreite")),
        ("jacke_taillenweite", "Jacke Taillenweite", habilleur_masse.get("jacke_taillenweite")),
        ("hose_taillenweite", "Hose Taillenweite", habilleur_masse.get("hose_taillenweite")),
        ("gabelhoehe", "Gabelhöhe", habilleur_masse.get("gabelhoehe")),
        ("beinoeffnung", "Beinöffnung", habilleur_masse.get("beinoeffnung")),
        ("hosenlaenge", "Hosenlänge", habilleur_masse.get("hosenlaenge")),
        ("mantel_schulterbreite", "Mantel Schulterbreite", habilleur_masse.get("mantel_schulterbreite")),
        ("mantel_gesamtlaenge", "Mantel Gesamtlänge", habilleur_masse.get("mantel_gesamtlaenge")),
        ("mantel_aermellaenge", "Mantel Ärmellänge", habilleur_masse.get("mantel_aermellaenge")),
        ("mantel_achselbreite", "Mantel Achselbreite", habilleur_masse.get("mantel_achselbreite")),
        ("mantel_taillenweite", "Mantel Taillenweite", habilleur_masse.get("mantel_taillenweite")),
    ]:
        if masse.get(key) and eigener_wert:
            diff = masse[key] - eigener_wert
            if abs(diff) <= 4:  # Differenzwert liegt hardgecodet bei 4cm??? --> so lassen??? ja
                passform_hinweise.append(f"{label}: passt gut")
            elif abs(diff) > 10:
                analyse["empfohlen"] = False
                analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
                analyse["begruendung"] = (f"Maß '{key}' weicht zu stark ab ({masse[key]} vs {eigener_wert} cm). "
                                          + analyse.get("begruendung", ""))
            elif diff > 0:
                passform_hinweise.append(f"{label}: +{diff}cm größer")
            else:
                passform_hinweise.append(f"{label}: {diff}cm kleiner")

    """
    6. RÜCKGABE: Alle Daten für MongoDB und das Dashboard zusammenführen --> an main.py geschickt 
    """
    return {
        "url":               artikel.get("url"),
        "titel":             artikel["titel"],
        "preis":             artikel["preis"],
        "beschreibung":      artikel["beschreibung"],
        "masse":             analyse.get("masse", {}),
        "zustand":           analyse.get("zustand"),
        "passt_groesse":     analyse.get("passt_groesse"),
        "passt_stil":        "Unbekannt, da Habilleur-Ergebnis",
        "passform_hinweise": passform_hinweise or None,
        "begruendung":       analyse.get("begruendung"),
        "bewertung":         analyse.get("bewertung"),
        "empfohlen":         analyse.get("empfohlen", False),
        "material":          analyse.get("material", "Unbekannt")
    }


"""
separate Implementierung für eBay aufgrund der detaillierteren Response
"""
async def analysiere_artikel_ebay(artikel: dict, config: dict) -> dict:
    # lädt Daten aus der Konfiguration (config.json, die in streamlit personalisert wird)
    ebay_masse = config.get("ebay_masse", {})
    min_zustand = config.get("min_zustand", "Gut")
    min_rang    = ZUSTAND_RANG.get(min_zustand, 2)

    """
    1.Prompt: Was soll das LLM machen, wie soll sie bewerten, 
    und schlussendlich soll sie ihre Ergebnisse in einer JSON zurückgeben
    """
    prompt = f"""You are a vintage fashion curator. Evaluate if this item fits the client.

    Client:
    - Size: {config['groesse']}
    - Max Price: {config['max_preis']}€
    - Minimal Condition: {min_zustand}
    - Brand: {config.get("marke") or "No Preference"}
    - Color: {config.get("farbe") or "No Preference"}
    - Custom keywords: {config.get("suchbegriffe") or "No Preference"}
    - Category: {config.get("kategorie")}
    - Material: {config.get("material") or "No Preference"}
    - URL: {config.get("url")}

    Item:
    - Title: {artikel['title']}
    - Price: {artikel['price']}
    - Description: {artikel['description']}
    - Condition: {artikel['condition']}
    - Condition ID: {artikel['conditionId']}
    - Brand: {artikel['brand']}
    - Color: {artikel['color']}
    - Size: {artikel['size']}
    - Material: {artikel['material']}
    - Additonal Information: {artikel['localizedAspects']}
    - Short Description: {artikel['shortDescription']}

    CRITICAL RULES:
    {SCORING_RULES}

    {UNIT_CONVERSION_RULES}

    {MEASUREMENT_RULES_EBAY}

    Respond ONLY with this JSON (No comments, no explanation, no markdown code blocks.):
    {RETURN_JSON_EBAY}"""

    # Nach Prompt kommt der Analyseteil
    print(f"    🤖 Analysiere: {artikel['title'][:50]}...")
    antwort = await frage_ollama(prompt, config["ollama_url"], config["ollama_modell"])

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
            end = antwort.rfind("}") + 1
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
        preis_roh = artikel["price"].replace(',', '.')

        # Extrahiere nur Ziffern und den (jetzt vorhandenen) Punkt
        preis_bereinigt = ''.join(c for c in preis_roh if c.isdigit() or c == '.')

        # Falls mehrere Punkte entstanden sind (z.B. durch Tippfehler), nimm nur den letzten
        if preis_bereinigt.count('.') > 1:
            teile = preis_bereinigt.split('.')
            preis_bereinigt = "".join(teile[:-1]) + "." + teile[-1]

        preis_zahl = float(preis_bereinigt)

        # Wenn Preis > Budget: Artikel ablehnen (Score auf 4 runter)
        if preis_zahl > config["max_preis"]:
            analyse["empfohlen"] = False
            analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
            analyse["begruendung"] = f"Preis {preis_zahl}€ zu hoch (Max: {config['max_preis']}€)."
    except Exception as e:
        print(f"DEBUG: Preis-Parsing fehlgeschlagen für '{artikel['price']}': {e}")

    """
    3.2 Zustand überprüfen (hier Nutzung von Vinted-Zuständen, da für eBay gleiche Namen gewählt wurden)
    """
    zustand = analyse.get("zustand", "")
    if zustand in ZUSTAND_RANG:
        if ZUSTAND_RANG[zustand] < min_rang:
            analyse["empfohlen"] = False
            analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
            analyse["begruendung"] = f"Zustand '{zustand}' unter '{min_zustand}'. " + analyse.get("begruendung", "")

    """
    3.3 Mindestbewertung kann mit Schieberegler in "Ergebnissen" angepasst werden
    """
    mindest_bewertung = config.get("min_empfehlung", 6)
    if analyse.get("bewertung", 0) < mindest_bewertung:
        analyse["empfohlen"] = False
    else:
        analyse["empfohlen"] = True  # ← Überschreibt Ollamas zu strenges Urteil

    """
    4. PASSFORM-VERGLEICH: Mathematische Berechnung der Differenz von Maßen, was gefunden wurde und was angegeben wurde
    """
    passform_hinweise = []
    masse = analyse.get("masse", {}) or {}
    for key, label, eigener_wert in [
        ("schulterbreite", "Schulterbreite", ebay_masse.get("schulterbreite")),
        ("aermellaenge", "Ärmellänge", ebay_masse.get("aermellaenge")),
        ("jackenlaenge", "Jackenlänge", ebay_masse.get("jackenlaenge")),
        ("achselbreite", "Achselbreite", ebay_masse.get("achselbreite")),
        ("jacke_taillenweite", "Jacke Taillenweite", ebay_masse.get("jacke_taillenweite")),
        ("hose_taillenweite", "Hose Taillenweite", ebay_masse.get("hose_taillenweite")),
        ("gabelhoehe", "Gabelhöhe", ebay_masse.get("gabelhoehe")),
        ("beinoeffnung", "Beinöffnung", ebay_masse.get("beinoeffnung")),
        ("hosenlaenge", "Hosenlänge", ebay_masse.get("hosenlaenge")),
        ("mantel_schulterbreite", "Mantel Schulterbreite", ebay_masse.get("mantel_schulterbreite")),
        ("mantel_gesamtlaenge", "Mantel Gesamtlänge", ebay_masse.get("mantel_gesamtlaenge")),
        ("mantel_aermellaenge", "Mantel Ärmellänge", ebay_masse.get("mantel_aermellaenge")),
        ("mantel_achselbreite", "Mantel Achselbreite", ebay_masse.get("mantel_achselbreite")),
        ("mantel_taillenweite", "Mantel Taillenweite", ebay_masse.get("mantel_taillenweite")),
    ]:
        if masse.get(key) and eigener_wert:
            diff = masse[key] - eigener_wert
            if abs(diff) <= 4:  # Differenzwert liegt hardgecodet bei 4cm??? --> so lassen??? ja
                passform_hinweise.append(f"{label}: passt gut")
            elif abs(diff) > 10:
                analyse["empfohlen"] = False
                analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
                analyse["begruendung"] = (f"Maß '{key}' weicht zu stark ab ({masse[key]} vs {eigener_wert} cm). "
                                          + analyse.get("begruendung", ""))
            elif diff > 0:
                passform_hinweise.append(f"{label}: +{diff}cm größer")
            else:
                passform_hinweise.append(f"{label}: {diff}cm kleiner")

    """
    5. RÜCKGABE: Alle Daten für MongoDB und das Dashboard zusammenführen --> an main.py geschickt 
    """
    return {
        "url": artikel.get("url"),
        "titel": artikel["title"],
        "preis": artikel["price"],
        "beschreibung": artikel["description"]
                        + f" Marke: {artikel['brand']},"
                        + f" Farbe: {artikel['color']},"
                        + f" Größenlabel: {artikel['size']},"
                        + f" Material: {artikel['material']},",
        "masse": analyse.get("masse", {}),
        "zustand": zustand,
        "passt_groesse": analyse.get("passt_groesse"),
        "passt_stil": "Unbekannt, da eBay-Ergebnis",
        "passform_hinweise": passform_hinweise or None,
        "begruendung": analyse.get("begruendung"),
        "bewertung": analyse.get("bewertung"),
        "empfohlen": analyse.get("empfohlen", False),
        "material": analyse.get("material", "Unbekannt"),
    }