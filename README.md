# 🛍️ Vinted Smart Finder

Ein automatisierter Secondhand-Artikel-Finder mit KI-gestützter Passform-Analyse.

## Setup

```bash
# 1. Abhängigkeiten installieren
pip install streamlit playwright playwright-stealth httpx

# 2. Playwright Browser
playwright install chromium

# 3. Projekt als Package registrieren (einmalig)
pip install -e .

# 4. Ollama starten (in separatem Terminal)
OLLAMA_HOST=0.0.0.0:11435 ollama serve

# 5. Dashboard starten
cd dashboard
streamlit run dashboard.py

# 6. Scraper manuell starten
python3 main.py
```

---

## Stand der Dinge ✅

### Scraping

- [x] Vinted Suchergebnisseiten scrapen (gefiltert nach Größe, Preis, Suchbegriff)
- [x] Einzelartikel aufrufen: Titel, Preis, Beschreibung extrahieren
- [x] Anti-Ban-Maßnahmen: randomisierte Pausen, Stealth-Modus, realistischer User-Agent
- [x] Cookie-Banner automatisch wegklicken
- [x] Deduplizierung gefundener Artikel

### KI-Analyse (Ollama / llama3, lokal)

- [x] Maße aus Artikelbeschreibung extrahieren (Brust, Taille, Hüfte, Schulter, Länge, Ärmel, Innennaht)
- [x] Zustand & Material aus Beschreibung erkennen
- [x] Stil-Matching (Vintage, Retro, Y2K, etc.)
- [x] Passform-Vergleich mit eigenen Maßen (Differenz in cm)
- [x] Bewertung 1–10 + Empfehlung ja/nein
- [x] Strukturierte JSON-Ausgabe pro Artikel

### Konfiguration & UI

- [x] Zentrale `config_defaults.py` (ein Single Source of Truth für alle Module)
- [x] Streamlit Dashboard: Präferenzen, Maße, Suche, Ollama-Einstellungen
- [x] Config wird in `secrets/config.json` gespeichert (nicht im Repo)
- [x] Ergebnisse & Empfehlungen als JSON in `secrets/`

### CI/CD

- [x] GitHub Actions Pipeline (noch nicht automatisch)
- [x] Ergebnisse als Workflow-Artifact herunterladbar
- [x] Optional: automatischer Commit der Ergebnisse ins Repo

---

## Roadmap 🚀

### Nächster Schritt: Web-Recherche für fehlende Maße

Wenn ein Artikel keine oder unvollständige Maßangaben in der Beschreibung hat, soll das System automatisch im Internet nach den Originalmaßen suchen.

**Geplanter Ablauf:**

1. Ollama erkennt dass Maße fehlen oder unvollständig sind
2. Suchquery wird automatisch generiert z.B. `"Levi's 501 W30 L32 Maße Brust Taille"`
3. Gezielte Suche auf Referenzseiten:
   - Marken-Größentabellen (z.B. levis.com, adidas.com)
   - Vintage-Maßtabellen (z.B. vintageshirts.com, sizecharter.com)
   - Allgemeine Modedatenbanken
4. Gefundene Maße werden mit Artikeldaten zusammengeführt
5. Ollama bewertet erneut mit vollständigen Informationen

**Technisch geplant:**

- [ ] Web-Search-Modul in `ai/` integrieren (httpx + HTML-Parsing oder Search-API)
- [ ] Ollama-Prompt erweitern: "Welche Maße fehlen? Generiere Suchquery."
- [ ] Fallback-Logik: Beschreibung → Web-Recherche → Markentabelle
- [ ] Konfidenz-Score: wie sicher sind die gefundenen Maße (direkt vs. recherchiert)
- [ ] Quellenangabe pro Maß im JSON (`"brust_quelle": "levis.com/sizeguide"`)

### Weitere geplante Features

- [ ] Vinted Benachrichtigung: Push-Notification bei neuen Top-Artikeln
- [ ] Preishistorie: Artikel über Zeit beobachten
- [ ] Mehrere Nutzerprofile (z.B. für verschiedene Personen)
- [ ] Sellpy-Support (sobald Anti-Bot-Schutz umgehbar)
- [ ] Bildanalyse: Stil-Erkennung anhand des Artikelfotos (LLaVA oder ähnlich)
- [ ] Exportfunktion im Dashboard (CSV, PDF)

---

## Konfiguration

Alle Einstellungen werden über das Streamlit Dashboard gesetzt und in `secrets/config.json` gespeichert:

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

- `secrets/` wird via `.gitignore` nie ins Repository gepusht
- Für CI/CD den Inhalt von `secrets/config.json` als GitHub Secret `VINTED_CONFIG` hinterlegen
- Ollama muss lokal laufen – kein externer API-Key nötig
- Für die CI/CD Pipeline `headless=True` in `vinted_scraper.py` setzen
