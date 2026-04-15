import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from pymongo import MongoClient
import requests

# 1. Konfiguration & Umgebungsvariablen laden
MONGO_URI = os.getenv("MONGO_URI")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")       # Deine Absender-Adresse (z.B. Gmail)
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")   # Dein App-Passwort
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")   # Wer soll den Newsletter bekommen?

def fetch_latest_vinted_data():
    """Holt die gescrapten Daten der letzten 24 Stunden aus der MongoDB."""
    print("Verbinde mit MongoDB...")
    client = MongoClient(MONGO_URI)
    db = client["Secondhand_db"] 
    collection = db["vinted_empfehlungen"]       
    
    # Filter: Nur Einträge vom letzten Tag
    yesterday = datetime.now() - timedelta(days=1)
    # Annahme: Du speicherst ein Feld "scraped_at" als datetime in Mongo
    recent_items = list(collection.find({"scraped_at": {"$gte": yesterday}}).limit(20))
    
    # Falls du kein Datum speicherst, nutze stattdessen einfach die neuesten 20:
    # recent_items = list(collection.find().sort("_id", -1).limit(20))
    
    return recent_items

def generate_newsletter_content(items):
    """Schickt die Daten an Llama 3 und bittet um eine Zusammenfassung."""
    if not items:
        return "Heute wurden keine neuen Vinted-Artikel gefunden. Viel Glück beim nächsten Mal!"

    # Daten für den Prompt vorbereiten (als Text formatieren)
    items_text = ""
    for idx, item in enumerate(items, 1):
        titel = item.get("title", "Unbekannt")
        preis = item.get("price", "?")
        marke = item.get("brand", "Ohne Marke")
        items_text += f"{idx}. {titel} ({marke}) - Preis: {preis}€\n"

    print("Sende Daten an Ollama (Llama 3)...")
    
    prompt = (
        "Du bist ein persönlicher Shopping-Assistent. Schreibe einen kurzen, "
        "enthusiastischen Newsletter über die folgenden Vinted-Funde. "
        "Hebe die besten Deals hervor, die eine Empfehlung sind mit Begründung. Antworte auf Deutsch.\n\n"
        f"Hier sind die Artikel:\n{items_text}"
    )

    # API-Aufruf an das lokale Ollama (das durch die Pipeline gestartet wurde)
    try:
        response = requests.post('http://localhost:11434/api/generate', json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        })
        response.raise_for_status()
        return response.json()['response']
    except Exception as e:
        print(f"Fehler bei der Ollama-Generierung: {e}")
        return "Fehler bei der Generierung des Newsletters durch die KI."

def send_email(content):
    """Verschickt den generierten Text als E-Mail."""
    print("Bereite E-Mail vor...")
    
    msg = EmailMessage()
    msg.set_content(content)
    
    heute = datetime.now().strftime("%d.%m.%Y")
    msg['Subject'] = f"🛍️ Deine Vinted Deals des Tages - {heute}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    # SMTP-Verbindung aufbauen (Hier am Beispiel von Gmail)
    try:
        # Falls du einen anderen Anbieter (GMX, Web.de, Outlook) nutzt, 
        # musst du den smtp-Server und den Port (oft 587 oder 465) anpassen.
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Newsletter erfolgreich versendet!")
    except Exception as e:
        print(f"❌ Fehler beim E-Mail-Versand: {e}")

if __name__ == "__main__":
    # 1. Daten holen
    vinted_data = fetch_latest_vinted_data()
    
    # 2. KI-Text generieren
    newsletter_text = generate_newsletter_content(vinted_data)
    
    # 3. E-Mail senden
    send_email(newsletter_text)