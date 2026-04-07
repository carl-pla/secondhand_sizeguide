# 🛍️ Vinted Smart Finder

Ein automatisierter Secondhand-Artikel-Finder mit KI-gestützter Passform-Analyse.

## Setup

```bash
# 1. Abhängigkeiten installieren
pip(3) install -r requirements.txt --> "(3)", wenn Mac User

# 2. Playwright Browser
playwright install chromium

# 3. Projekt als Package registrieren (einmalig)
pip install -e .

# 4. Ollama starten (in separatem Terminal)
Mac:
OLLAMA_HOST=0.0.0.0:11435 ollama serve
Windows (Powershell):
$env:OLLAMA_HOST="0.0.0.0:11435"
ollama serve

# 5. Dashboard starten
streamlit run dashboard/dashboard.py

# 6. Scraper manuell starten
python3 main.py
```

---
## Workflow 
--> Konfiguration (Input) über das Streamlit Dashboard, Konfigurationsdaten landen in der config.json 
--> Datengewinnung durch Scraper: Biblitothek "Playwright" um Rohtext und Beschreibungen zu extrahieren, ohne geblockt zu werden
--> Auswertung der Scraping Ergebnisse mit ollama lokal. LLM fungiert als Parser: unstrukturiertre Daten zu harten Daten 
--> Specherung und Output: LLM gibt sauberes JSON zurück mit Empfehlungen (Grundlage für relationale Datenbank und dementesprechend Newsletter (Github kann automatisieren)

## Stand der Dinge ✅

### Scraping

- [x] Vinted Suchergebnisseiten scrapen (gefiltert nach Größe, Preis, Suchbegriff)
- [x] Einzelartikel aufrufen: Titel, Preis, Beschreibung extrahieren
- [x] Anti-Ban-Maßnahmen: randomisierte Pausen, Stealth-Modus, realistischer User-Agent
- [x] Cookie-Banner automatisch wegklicken
- [x] Deduplizierung gefundener Artikel

--> dauert sehr lange! Scrapt nur sehr wenig Volumen! 
==> Lösung?: zunächst nur erste Parameter des Artikels scannen, wenn true dann weiter 
==> Lösung?: Cookie-Persistenz, speichern der Cookies unter selben IP-Adresse, sonst wirkt auf hohes Volumen "verdächtig"

### KI-Analyse (Ollama / llama3, lokal)

- [x] Maße aus Artikelbeschreibung extrahieren (Brust, Taille, Hüfte, Schulter, Länge, Ärmel, Innennaht)
- [x] Zustand & Material aus Beschreibung erkennen
- [x] Stil-Matching (Vintage, Retro, Y2K, etc.)
- [x] Passform-Vergleich mit eigenen Maßen (Differenz in cm)
- [x] Bewertung 1–10 + Empfehlung ja/nein
- [x] Strukturierte JSON-Ausgabe pro Artikel, die in MongoDB gespeichert wird

### Konfiguration & UI

- [x] Zentrale `config_defaults.py` (ein Single Source of Truth für alle Module)
- [x] Streamlit Dashboard: Präferenzen, Maße, Suche, Ollama-Einstellungen
- [x] Ergebnisse & Empfehlungen als JSON 

### CI/CD

- [ ] GitHub Actions Pipeline (noch nicht automatisch --> bzw. tests, security, docker, deploy unvollständig)
- [ ] Ergebnisse als Workflow-Artifact herunterladbar

---


### Weitere geplante Features

- [ ] MongoDB aufsetzen und dort JSON speichern lassen
- [ ] Volumen des Scrapers erhöhen --> noch unzufriedene Ergebnisse!
- [ ] Zeit des Scrapers und AI-Analyse reduzieren 

- [ ] Wenn ein Artikel keine oder unvollständige Maßangaben in der Beschreibung hat, soll das System automatisch im Internet nach den Originalmaßen suchen.
1. Ollama erkennt dass Maße fehlen oder unvollständig sind
2. Suchquery wird automatisch generiert z.B. `"Levi's 501 W30 L32 Maße Brust Taille"`
3. Gezielte Suche auf Referenzseiten:
   - Marken-Größentabellen (z.B. levis.com, adidas.com)
   - Vintage-Maßtabellen (z.B. vintageshirts.com, sizecharter.com)
   - Allgemeine Modedatenbanken
4. Gefundene Maße werden mit Artikeldaten zusammengeführt
5. Ollama bewertet erneut mit vollständigen Informationen

- [ ] E-mail Benachrichtung als eine Art "Newsletter"
1. Daten aus Scrapper identifiziert 
2. in JSON Datei gespeichert, gleichzeitig landen Empfehlungen in MongoDB 
3. Empfehlungen werden pro Recherche agregiert und dann in einen Newsletter verpackt 
4. Newsletter soll automatisiert 1mal pro Woche kommen

---

## Aufgetretene Probleme

- Synchronisieren der Variablen des streamlit Dashboards und der JSON Dateien
- Scraper öfters blockiert, besonders sensibel ist Sellpy 

## Konfiguration

Alle Einstellungen werden über das Streamlit Dashboard gesetzt und in `config.json` gespeichert:

| Parameter | Beschreibung | Beispiel |

| `groesse` | Kleidungsgröße | `"M / 38"` |
| `stile` | Bevorzugte Stile | `["Vintage", "Retro"]` |
| `max_preis` | Maximaler Preis in € | `50` |
| `eigene_masse` | Eigene Körpermaße in cm | `{"brust": 88, "taille": 70}` |
| `suchbegriffe` | Vinted Suchbegriffe | `["vintage", "y2k"]` |
| `ollama_url` | Ollama API Endpunkt | `"http://localhost:11435/api/generate"` |
| `ollama_modell` | Lokales LLM | `"llama3"` |
| `max_artikel_pro_suche` | Artikel pro Suchbegriff | `5` |
| `pause_zwischen_artikeln` | Anti-Ban Pause (Sek.) | `[4, 7]` |

---

## Hinweise

- Für CI/CD den Inhalt von `secrets/config.json` als GitHub Secret `VINTED_CONFIG` hinterlegen
- Ollama muss lokal laufen – kein externer API-Key nötig
- Für die CI/CD Pipeline `headless=True` in `vinted_scraper.py` setzen

