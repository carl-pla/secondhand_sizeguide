import json
import httpx

ZUSTAND_RANG = {
    "Neu mit Etikett": 5, "Neu ohne Etikett": 4,
    "Sehr gut": 3, "Gut": 2, "Befriedigend": 1
}

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

    prompt = f"""You are a strict fashion buyer. Reject items that don't fit.

Buyer: {stile} style, size {config['groesse']}, max {config['max_preis']}€, min condition: {min_zustand}
Measurements: bust {eigene.get('brust','?')}cm, waist {eigene.get('taille','?')}cm, hips {eigene.get('huefte','?')}cm, shoulders {eigene.get('schulter','?')}cm

Listing:
Title: {artikel['titel']}
Price: {artikel['preis']}
Description: {artikel['beschreibung']}

Reject (empfohlen: false) if: wrong style, wrong size, price too high, bad condition, measurements off >6cm.
Score 1-10. Only empfohlen: true if score >= 7. Be strict.

JSON only:
{{"masse":{{"brust_cm":null,"taille_cm":null,"huefte_cm":null,"schulter_cm":null,"laenge_cm":null,"aermel_cm":null,"innennaht_cm":null}},"zustand":null,"material":null,"passt_groesse":false,"passt_stil":false,"begruendung":"Begründung auf Deutsch","bewertung":5,"empfohlen":false}}"""

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
        preis_zahl = float(''.join(
            c for c in artikel["preis"] if c.isdigit() or c == '.'
        ).strip('.'))
        if preis_zahl > config["max_preis"]:
            analyse["empfohlen"] = False
            analyse["bewertung"] = min(analyse.get("bewertung", 5), 4)
            analyse["begruendung"] = f"Preis {preis_zahl}€ > Maximum {config['max_preis']}€. " + analyse.get("begruendung", "")
    except:
        pass

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
        "material":          analyse.get("material"),
        "passt_groesse":     analyse.get("passt_groesse"),
        "passt_stil":        analyse.get("passt_stil"),
        "passform_hinweise": passform_hinweise or None,
        "begruendung":       analyse.get("begruendung"),
        "bewertung":         analyse.get("bewertung"),
        "empfohlen":         analyse.get("empfohlen", False),
    }