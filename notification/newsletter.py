import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pymongo import MongoClient

MONGO_URL     = os.getenv("MONGO_URL")
MAIL_FROM     = os.getenv("MAIL_FROM")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

MAX_ARTIKEL = 10

def fetch_latest_empfehlungen():
    if not MONGO_URL:
        raise ValueError("❌ Kritischer Fehler: MONGO_URL nicht gesetzt!")
    print("✅ MONGO_URL geladen. Verbinde mit MongoDB...")
    client = MongoClient(MONGO_URL)
    col = client["Secondhand_db"]["scraping_sessions"]

    # ✅ Fix #1: datetime-Objekt statt String
    gestern = datetime.now() - timedelta(days=1)
    sessions = list(col.find({"gestartet_am": {"$gte": gestern}}).sort("gestartet_am", -1))
    print(f"📦 {len(sessions)} Sessions in den letzten 24h gefunden.")

    alle = []
    for s in sessions:
        user = s.get("user_email", "anonym")
        empfehlungen = s.get("empfehlungen", [])
        print(f"  → Session von {user}: {len(empfehlungen)} Empfehlungen")
        for item in empfehlungen:
            item["_user"] = user
            alle.append(item)
    print(f"📊 Gesamt gesammelte Artikel: {len(alle)}")
    return alle

def generiere_html(items):
    if not items:
        return "<p>Heute wurden keine neuen Empfehlungen gefunden.</p>"
    heute = datetime.now().strftime("%d.%m.%Y")
    anzahl_gesamt    = len(items)
    anzahl_angezeigt = min(anzahl_gesamt, MAX_ARTIKEL)

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
    <p>Heute wurden <b>{anzahl_gesamt} Artikel</b> gefunden –
       hier sind die besten <b>{anzahl_angezeigt}</b>:</p>
    <hr>
    """

    for item in items[:MAX_ARTIKEL]:
        bewertung = item.get("bewertung", "?")
        sterne = "⭐" * int(bewertung) if isinstance(bewertung, int) else ""
        html += f"""
        <div style="border:1px solid #eee;border-radius:8px;padding:15px;margin:10px 0">
            <h3 style="margin:0">
                <a href="{item.get('url','#')}">{item.get('titel','?')}</a>
            </h3>
            <p style="margin:5px 0">💶 <b>{item.get('preis','?')}</b>
               &nbsp;|&nbsp; {sterne} {bewertung}/10</p>
            <p style="margin:5px 0;color:#555">{item.get('begruendung','')}</p>
            <p style="margin:3px 0;color:#555">{item.get('quelle','')}</p>
        </div>
        """  # ✅ Fix #2: 'quelle' statt 'Quelle: '

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
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(MAIL_FROM, MAIL_PASSWORD)
            server.send_message(msg)
            print(f"✅ Newsletter gesendet an {empfaenger}")
    except Exception as e:
        print(f"❌ Fehler beim Senden: {e}")

def lade_alle_empfaenger():
    client = MongoClient(MONGO_URL)
    users = list(client["Secondhand_db"]["users"].find({"aktiv": True}))
    return [u["email"] for u in users if "email" in u]

if __name__ == "__main__":
    items      = fetch_latest_empfehlungen()
    html       = generiere_html(items)
    empfaenger = lade_alle_empfaenger()

    if not empfaenger:
        print("Keine aktiven Abonnenten gefunden.")
    else:
        for email in empfaenger:
            sende_email(html, email)