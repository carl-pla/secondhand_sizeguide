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

### 1. Systemarchitektur & Containerisierung (Docker)

- Isolation der Abhängigkeiten: MongoDB und Ollama (Llama 3) laufen in isolierten Umgebungen. Das verhindert Konflikte mit dem Host-System
- Ressourcenmanagement: Du kannst genau steuern, wie viel RAM oder GPU-Leistung der Ollama-Container bekommt.
- Skalierbarkeit: Theoretisch könntest du den MongoDB-Container auf einen Server auslagern, ohne eine Zeile Code in deiner main.py zu ändern (außer der URI).

### 2. Asynchrone Datenakquise (Playwright & Asyncio)

- Das ist technisch einer der anspruchsvollsten Teile. Stichwort synchrones vs. asynchrones Scraping
- Non-blocking I/O: Während Playwright auf die Antwort von Vinted wartet (Netzwerk-Latenz), blockiert das Programm nicht. Das ist die Basis für die Effizienz.
- Stealth-Technologie: Einsatz von playwright-stealth? Hier geht es um das "Fingerprinting". Vinted prüft Parameter wie navigator.webdriver. Stealth überschreibt diese im Browser-Kern, um die Automatisierung zu tarnen.
- State-Management: Page durchreichen: Cookies und Session-Daten konsistent zu halten.

### 3. Natural Language Processing (LLM-Inferenz)

- Hier gehst du tief in die KI-Logik ein.
- Prompt-Engineering als Interface: Beschreibe den Prompt nicht als "Text", sondern als Schnittstellen-Definition. Er wandelt unstrukturierte natürliche Sprache (Vinted-Beschreibung) in ein strukturiertes Datenschema (JSON) um.
- Lokale Inferenz vs. API: Vorteil von Ollama: Datenschutz, keine Kosten pro Token, geringe Latenz im lokalen Netzwerk, gegenüber OpenAI bspw.
- Concurrency (Threading): Erkläre, warum du für die KI-Analyse concurrent.futures.ThreadPoolExecutor nutzt. Da die KI-Analyse CPU/GPU-lastig ist und über HTTP-Requests läuft, ist Parallelisierung hier der größte Hebel für die Geschwindigkeit.

### 4. Datenvalidierung & Business Logic (Die "Harten Checks")

- wissenschaftliche Diskussion: Warum reicht die KI/LLM allein nicht aus?
=> Deterministik vs. Probabilistik: Python-Code ist deterministisch (1+1 ist immer 2). Eine KI ist probabilistisch (sie rät basierend auf Wahrscheinlichkeiten)!!!
- Validierungsschicht: hybride Architektur. Die KI übernimmt das Verständnis, aber die Validierung (Preis-Checks, Zustands-Ranking) übernimmt der Python-Code. Das erhöht die Zuverlässigkeit des Gesamtsystems ("Robust AI").

### 5. Datenhaltung (NoSQL vs. Relational)

- Warum MongoDB? Schema-Flexibilität: Da die JSON-Antworten der KI variieren können (z.B. findet sie mal Maße, mal nicht), ist ein starres SQL-Schema unpraktisch. MongoDB (BSON) speichert die Daten so, wie sie reinkommen.
- JSON-Native: gesamter Workflow auf JSON basiert (Scraper -> Ollama -> MongoDB), gibt es keinen "Impedance Mismatch" (Daten müssen nicht umständlich umgewandelt werden).

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
- [ ] Für die GitHub Actions brauchen wir in der Ergebnis Json ein Zeitfeld, also bei jedem gespeicherten Objekt ein "created_at"-item, damit die Actions wissen, was jede Woche neu ist
- [ ] Ergebnisse als Workflow-Artifact herunterladbar
- [ ] Github Actions timed die Code Ausführung und "Resend" verschickt die Mail (sehr simple API, weil wir brauchen nur API-Key, Absender-/ Empfängeradresse)
- [ ] ### wichtig: GitHub erreicht MongoDB nur, wenn die Datenbank öffentlich erreichbar ist (mit Connection URI in MongoDB-Atlas)
- [ ] Wir brauchen jetzt eine weekly_newsletter.YML Datei im /workflow Ordner auf dem Default Branch (GitHub erkennt automatisch den Flow) und eine workflow_dispatch Datei. Dann erscheint bei den Actions ein Button mit "Run Workflow"
- [ ] Auch brauchen wir in den Secrets: MONGO_URI, RESEND_API_KEY und MAIL_FROM und MAIL_TO

---

### Weitere geplante Features

- [ ] MongoDB aufsetzen und dort JSON speichern lassen
- [ ] Volumen des Scrapers erhöhen --> noch unzufriedene Ergebnisse!
- [ ] LLM-Analyse zu wenig kritisch
- [ ] Pytests schreiben
- [ ] App containerisieren
- [ ] Deployen der streamlit App
- [ ] CI/CD Pipeline integrieren

- [ ] E-mail Benachrichtung als eine Art "Newsletter"
    1. Daten aus Scrapper identifiziert
    2. in JSON Datei gespeichert, gleichzeitig landen Empfehlungen in MongoDB
    3. Empfehlungen werden pro Recherche agregiert und dann in einen Newsletter verpackt
    4. Newsletter soll automatisiert 1mal pro Woche kommen

---

## Aufgetretene Probleme

- Synchronisieren der Variablen des streamlit Dashboards und der JSON Dateien
- Scraper öfters blockiert, besonders sensibel ist Sellpy
- Überblick geht schenll verloren, über Service
- Robustness Strategy beim Scraping anspruchsvoll zu wissen, da sich Seiten mit den Metadaten und keys ständig ändern

## Design Entscheidungen und Learnings

- zentrale Ressourcensteuerung der main.py: Anstatt zustandslose Einzel-Scraper zu verwenden, verwaltet die Hauptsteuerung (main.py) den Browser-Kontext. Dies ermöglicht eine persistente Session über mehrere Suchbegriffe hinweg. Die anschließende Deduplizierung auf Applikationsebene stellt sicher, dass die rechenintensive KI-Analyse (LLM-Inferenz) für jeden Datensatz nur genau einmal ausgeführt wird, was die Gesamtlaufzeit des Prozesses signifikant reduziert.

- Die „JSON-Klammer-Suche“ (Robustheit)
Beobachtung: In deiner ollama.py versuchst du nicht nur json.loads(), sondern nutzt antwort.find("{").
Warum das wichtig ist: KIs neigen dazu, zu „plappern“ (z. B. „Hier ist das Ergebnis: { ... }“). Ein normaler Parser würde abstürzen.
Bericht-Argument: Du hast hier ein „Error-Handling für nicht-deterministische KI-Outputs“ implementiert. Du diskutierst die Schwierigkeit, eine Brücke zwischen der unstrukturierten Sprache der KI und der strukturierten Welt der Datenbanken (JSON/MongoDB) zu schlagen.

- Der „Human-Mimicry“ Faktor (Stealth-Technik)
Beobachtung: Du nutzt Stealth(), zufällige Pausen (random.uniform) und echte User-Agents.
Warum das wichtig ist: Vinted nutzt hochentwickelte Bot-Detection (wie Cloudflare oder Akamai). Ohne diese Feinheiten würde dein Projekt nach 30 Sekunden gesperrt.
Bericht-Argument: Diskussion über „Ethisches Scraping und Bot-Detection-Umgehung“. Du erklärst, wie du durch Simulation menschlichen Verhaltens (Latenzen, Viewport-Größen) die Verfügbarkeit deiner Datenquelle sicherstellst.

- Das „Wahrheit-Problem“ (KI vs. Python-Code)
Beobachtung: Du hast „Harte Checks“ eingebaut, die das Urteil der KI überschreiben (z. B. beim Preis-Parsing-Fix).
Warum das wichtig ist: Eine KI ist gut im Verstehen von Kontext, aber oft schlecht im Rechnen (Halluzinationen bei Zahlen).
Bericht-Argument: Du thematisiert die „Validierung von KI-generierten Inhalten“. Das ist ein hochaktuelles Thema: „Human-in-the-loop“ oder in diesem Fall „Code-in-the-loop“. Du zeigst auf, dass die KI die Vorarbeit leistet, aber die Letztentscheidung bei harten Regeln (Business Logic) verbleibt.

- Parallelisierung (Effizienz vs. Rate-Limiting)
Beobachtung: Du nutzt den ThreadPoolExecutor mit genau 3 Workern.
Warum das wichtig ist: Würdest du 100 Artikel gleichzeitig an Ollama schicken, würde dein Mac/PC einfrieren. Würdest du sie nacheinander schicken, würde es ewig dauern.
Bericht-Argument: Optimierung der „System-Performance durch Thread-Pooling“. Du erklärst die Abwägung zwischen Hardware-Ressourcen (CPU/RAM-Last durch Llama 3) und der benötigten Durchlaufzeit des Scrapers.

## Konfiguration

Alle Einstellungen werden über das Streamlit Dashboard gesetzt und in `config.json` gespeichert:

| Parameter | Beschreibung | Beispiel |

| `groesse` | Kleidungsgröße | `"M / 38"` |
| `stile` | Bevorzugte Stile | `["Vintage", "Retro"]` |
| `max_preis` | Maximaler Preis in € | `50` |
| `eigene_masse` | Eigene Körpermaße in cm | `{"brust": 88, "taille": 70}` |
| `suchbegriffe` | Vinted Suchbegriffe | `["vintage", "y2k"]` | --> soll gelöscht werden
| `ollama_url` | Ollama API Endpunkt | `"http://localhost:11435/api/generate"` |
| `ollama_modell` | Lokales LLM | `"llama3"` |
| `max_artikel_pro_suche` | Artikel pro Suchbegriff | `5` |
| `pause_zwischen_artikeln` | Anti-Ban Pause (Sek.) | `[4, 7]` |

---

## Hinweise

- Für CI/CD den Inhalt von `secrets/config.json` als GitHub Secret `VINTED_CONFIG` hinterlegen
- Ollama muss lokal laufen – kein externer API-Key nötig
- Für die CI/CD Pipeline `headless=True` in `vinted_scraper.py` setzen
