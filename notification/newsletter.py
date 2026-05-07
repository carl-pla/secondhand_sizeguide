import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pymongo import MongoClient

MONGO_URL     = os.getenv("MONGO_URL") or ""
MAIL_FROM     = os.getenv("MAIL_FROM") or ""
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD") or ""

MAX_ARTIKEL = 10

if not MONGO_URL:
    raise ValueError("❌ Kritischer Fehler: MONGO_URL nicht gesetzt!")
if not MAIL_FROM:
    raise ValueError("❌ Kritischer Fehler: MAIL_FROM nicht gesetzt!")
if not MAIL_PASSWORD:
    raise ValueError("❌ Kritischer Fehler: MAIL_PASSWORD nicht gesetzt!")

def parse_gestartet_am(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    return None


def fetch_latest_empfehlungen():
    print("✅ MONGO_URL geladen. Verbinde mit MongoDB...")
    client = MongoClient(MONGO_URL)
    col = client["Secondhand_db"]["scraping_sessions"]

    gestern = datetime.now() - timedelta(days=1)
    sessions = list(col.find({"gestartet_am": {"$gte": gestern}}).sort("gestartet_am", -1))

    if not sessions:
        print("⚠️ Keine Sessions per Datetime-Query gefunden. Fallback auf String-Daten.")
        all_sessions = list(col.find().sort("gestartet_am", -1))
        sessions = [
            s for s in all_sessions
            if (parsed := parse_gestartet_am(s.get("gestartet_am"))) and parsed >= gestern
        ]

    print(f"📦 {len(sessions)} Sessions in den letzten 24h gefunden.")

    alle = []
    for s in sessions:
        user = s.get("user_email", "anonym")
        quelle = s.get("quelle") or s.get("config", {}).get("quelle", "vinted")
        empfehlungen = s.get("empfehlungen", [])
        print(f"  → Session von {user}: {len(empfehlungen)} Empfehlungen")
        for item in empfehlungen:
            item["_user"] = user
            item["_quelle"] = quelle
            alle.append(item)
    print(f"📊 Gesamt gesammelte Artikel: {len(alle)}")
    return alle

def generiere_html(items):
    if not items:
        return "<p>Heute wurden keine neuen Empfehlungen gefunden.</p>"
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
            <p style="margin:5px 0;color:#555;font-size: 8px">Quelle: {item.get('_quelle','')}</p>
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
    msg["Reply-To"] = MAIL_FROM

    plain_text = re.sub(r"<[^>]+>", "", html_content)
    msg.attach(MIMEText(plain_text, "plain"))
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
        raise

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