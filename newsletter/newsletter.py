import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pymongo import MongoClient # type: ignore

MONGO_URL      = os.getenv("MONGO_URL")
MAIL_FROM      = os.getenv("MAIL_FROM")
MAIL_PASSWORD  = os.getenv("MAIL_PASSWORD")

def fetch_latest_empfehlungen():
    MONGO_URL = os.getenv("MONGO_URL")

    if not MONGO_URL:
    # Das wird im GitHub Log rot angezeigt und stoppt das Skript sofort
        raise ValueError("❌ Kritischer Fehler: Die Umgebungsvariable MONGO_URL wurde nicht gefunden!")
    print("✅ MONGO_URL erfolgreich geladen.")
    print("Verbinde mit MongoDB...")
    client = MongoClient(MONGO_URL)
    col = client["Secondhand_db"]["scraping_sessions"]

    # Letzte 24h – als String-Vergleich passend zu deinem Schema
    gestern = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    sessions = list(col.find({"gestartet_am": {"$gte": gestern}}).sort("gestartet_am", -1))

    # Alle Empfehlungen aus allen Sessions sammeln
    alle = []
    for s in sessions:
        user = s.get("user_email", "anonym")
        for item in s.get("empfehlungen", []):
            item["_user"] = user
            alle.append(item)
    return alle

def generiere_html(items):
    if not items:
        return "<p>Heute wurden keine neuen Empfehlungen gefunden.</p>"

    heute = datetime.now().strftime("%d.%m.%Y")
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
    <h1 style="color:#1a1a2e">🛍️ Deine Vinted Deals – {heute}</h1>
    <p>Heute wurden <b>{len(items)} Artikel</b> für dich gefunden:</p>
    <hr>
    """
    for item in items[:10]:  # max 10 Artikel
        bewertung = item.get("bewertung", "?")
        sterne = "⭐" * int(bewertung) if isinstance(bewertung, int) else ""
        html += f"""
        <div style="border:1px solid #eee;border-radius:8px;padding:15px;margin:10px 0">
            <h3 style="margin:0"><a href="{item.get('url','#')}">{item.get('titel','?')}</a></h3>
            <p style="margin:5px 0">💶 <b>{item.get('preis','?')}</b> &nbsp;|&nbsp; {sterne} {bewertung}/10</p>
            <p style="margin:5px 0;color:#555">{item.get('begruendung','')}</p>
        </div>
        """
    html += "</body></html>"
    return html

def sende_email(html_content, empfaenger: str):
    print(f"Sende Newsletter an {empfaenger}...")
    msg = MIMEMultipart("alternative")
    heute = datetime.now().strftime("%d.%m.%Y")
    msg["Subject"] = f"🛍️ Deine Vinted Deals – {heute}"
    msg["From"]    = MAIL_FROM
    msg["To"]      = empfaenger
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(MAIL_FROM, MAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Newsletter gesendet an {empfaenger}")
    except Exception as e:
        print(f"❌ Fehler: {e}")

def lade_alle_empfaenger():
    client = MongoClient(MONGO_URL)
    users = list(client["Secondhand_db"]["users"].find({"aktiv": True}))
    return [u["email"] for u in users if "email" in u]

if __name__ == "__main__":
    items    = fetch_latest_empfehlungen()
    html     = generiere_html(items)
    empfaenger = lade_alle_empfaenger()

    if not empfaenger:
        print("Keine aktiven Abonnenten gefunden.")
    else:
        for email in empfaenger:
            sende_email(html, email)