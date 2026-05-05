# 🔍 Habilleur Größen-Debugging Guide

## Problem Zusammenfassung

Du hattest das Problem, dass Artikel von Habilleur erfolgreich gescraped werden, aber die Maße falsch erkannt werden. Beispiel: Ein Anzug bekam Mantel-Größen zugeordnet.

## Gefundene Bugs ✅

Ich habe **3 Probleme** identifiziert und behoben:

### 1. **Falsches JSON-Schema für Habilleur** (kritisch)
- **Problem**: Die Funktion `analysiere_artikel_habilleur()` nutzte das falsche JSON-Schema (`JSON_MASSE_EBAY_HAB` statt `JSON_MASSE_HAB`)
- **Auswirkung**: Das LLM war verwirrt über das erwartete Format
- **Fix**: ✅ Behoben - jetzt nutzt sie `JSON_MASSE_HAB` mit den korrekten Regeln

### 2. **Keine Kategorie-Information in Artikel-Details** (mittel)
- **Problem**: Der Scraper extrahierte nicht, ob ein Artikel Anzug/Jacke/Mantel ist
- **Auswirkung**: Das LLM konnte nicht unterscheiden, welche Maße zu extrahieren sind
- **Fix**: ✅ Behoben - der Scraper extrahiert jetzt die Kategorie aus URL und Titel

### 3. **Veraltete/doppelte JSON-Definitionen** (minor)
- **Problem**: `JSON_MASSE_HAB` war doppelt definiert
- **Fix**: ✅ Bereinigt

---

## 🧪 So testest du die Fixes

### Option 1: Interaktives Debugging (empfohlen)

```bash
# Aktiviere virtuelle Umgebung
.\venv\Scripts\Activate.ps1

# Starte Ollama (falls nicht laufen)
ollama serve

# Teste einen einzelnen Artikel (öffne ein neues Terminal)
python debug_habilleur.py "https://habilleurjean.com/de/products/ARTIKEL-URL"
```

Das Debug-Script zeigt dir:
- ✅ Was der Scraper extrahiert hat
- ✅ Welche Kategorie erkannt wurde
- ✅ Welche Maße das LLM gefunden hat
- ✅ Wie die erkannten Maße mit deinen Maßen vergleichen

Beispiel-Output:
```
📝 SCHRITT 1: Scrape Artikel-Details...
   Titel: Anzug Blau Größe 52
   Preis: 89€

🤖 SCHRITT 3: Analysiere mit Ollama...
   ✓ Kategorie erkannt: Anzug
   ✓ Maße gefunden: 5

📏 Erkannte Maße:
   schulterbreite       = 45cm  (deine: 44cm, +1cm)
   jackenlaenge         = 72cm  (deine: 73cm, -1cm)
```

### Option 2: Test über den regulären Scraper

```bash
# Starte normal deine Config mit einer bestimmten Kategorie
python main.py
```

Nach dem Scraping solltest du im Dashboard sehen:
- ✅ Artikel bekommen die richtige Kategorie zugeordnet
- ✅ Größen werden kategorienspezifisch extrahiert:
  - **Anzug**: schulterbreite, ärmellänge, jackenlänge, jacke_taillenweite, hose_taillenweite, etc.
  - **Jacke**: schulterbreite, ärmellänge, jackenlänge (hose-Felder = null)
  - **Mantel**: mantel_schulterbreite, mantel_gesamtlaenge, mantel_ärmellänge, etc.

---

## 📋 Checkliste zum Debuggen

Falls immer noch Probleme auftreten, nutze diese Checkliste:

### Bei "Falsche Kategorien" 🏷️

```python
# Prüfe, ob der Scraper die Kategorie erkannt hat
# Im debug_habilleur.py Output solltest du sehen:
# "✅ Kategorie 'Anzug' im Artikel-Titel erkannt"

# Falls NICHT erkannt:
# → Der Titel enthält nicht das Wort "Anzug", "Jacke" oder "Mantel"
# → Manuell in habilleur_scraper.py die Kategorien-Erkennungs-Liste erweitern
```

### Bei "Falsche Maße extrahiert" 📏

```python
# Gründe für falsch extrahierte Maße:

1. Die Beschreibung ist zu kurz (<100 Zeichen)
   → Habilleur hat möglicherweise wenig Info
   → Das LLM kann weniger extrahieren

2. Maße sind in Zoll (") statt cm
   → Das LLM sollte das umrechnen
   → Falls nicht: Check die UNIT_CONVERSION_RULES

3. Artikel ist nicht das, was erwartet wurde
   → Beispiel: Anzug-Kategorie, aber Artikel ist Jacke
   → Prüfe den Titel und die Beschreibung
```

### Bei "0 Maße erkannt" ❌

```bash
# Das Artikel-HTML könnte JavaScript nutzen
# Versuche manuell im Browser die Seite zu öffnen
# und schaue auf die Struktur

# Falls die Seite sich bewegt/lädt, könnte Habilleur
# auf JavaScript setzen → dann: Playwright nutzen
```

---

## 🔧 Spezifische Messfehler beheben

### Problem: Anzug bekommt Mantel-Maße

```
Grund: Der Titel sagt nicht klar "Anzug"
Lösung: 
1. In habilleur_scraper.py die Kategorie-Erkennungs-Wörter erweitern:

    if any(w in titel_lower for w in ["suit", "completo", "costume"]):
        kategorie = "Anzug"

2. Oder: Kategorie manuell übergeben beim Scraping
   details = await scrape_artikel_details(url, client, kategorie="Anzug")
```

### Problem: Jacke wird als Anzug erkannt

```
Grund: Titel enthält "Jacke" UND "Hose", wird als Anzug interpretiert
Lösung: Prüfe die Erkennungs-Logik und verfeinere sie
```

---

## 📊 Erweiterte Tests

### Test mit verschiedenen Kategorien

```bash
# Teste Anzug
python debug_habilleur.py "https://habilleurjean.com/de/collections/anzug-m"

# Teste Jacke
python debug_habilleur.py "https://habilleurjean.com/de/collections/jacket-m"

# Teste Mantel
python debug_habilleur.py "https://habilleurjean.com/de/collections/mantel-m"
```

### Performance-Test

```bash
# Teste mehrere Artikel hintereinander
for url in \
  "https://habilleurjean.com/de/products/ARTICLE1" \
  "https://habilleurjean.com/de/products/ARTICLE2" \
  "https://habilleurjean.com/de/products/ARTICLE3"
do
  python debug_habilleur.py "$url"
  sleep 2  # Pause zum Schutz vor Rate-Limiting
done
```

---

## 🎯 Nächste Schritte

1. **Teste das Debug-Script** mit einem realen Habilleur-Artikel
2. **Vergleiche die erkannten Maße** mit den echten Maßen im Artikel
3. **Falls noch Probleme**: Schreib die Artikel-URL und das Debug-Output hier hin
4. **Führe einen kompletten Scrape durch** mit main.py und prüfe die Ergebnisse

---

## 📝 Wichtige Hinweise

### Ollama muss laufen!

```bash
# In separatem Terminal:
ollama serve
```

### Config muss habilleur_masse enthalten

In `dashboard/secrets/config.json`:
```json
{
  "habilleur_masse": {
    "schulterbreite": 44,
    "aermellaenge": 65,
    "jackenlaenge": 72,
    ...
  }
}
```

---

## 💡 Wenn alles fehlschlägt

Falls auch nach den Fixes immer noch Probleme auftreten:

1. **Aktiviere Verbose-Logging**:
```python
# In main.py, nach dem Scraping:
print(json.dumps(artikel, indent=2))
```

2. **Speichere die Raw-Ollama-Antwort**:
```python
# Die wird bereits im Debug-Script gezeigt
# Falls zu kurz: Check die Ollama-Logs
```

3. **Prüfe die Habilleur-Website selbst**:
   - Hat sich die HTML-Struktur geändert?
   - Nutzen sie jetzt JavaScript?
   - Sind die Größen-Felder an anderer Stelle?

---

**Viel Erfolg beim Debuggen! 🚀**
