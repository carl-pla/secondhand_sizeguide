import os
from datetime import datetime, timedelta, timezone
from html import escape

import requests
from pymongo import MongoClient


MONGO_URI = os.environ["MONGO_URI"]
MONGO_DB = os.environ["MONGO_DB"]
MONGO_COLLECTION = os.environ["MONGO_COLLECTION"]

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
MAIL_FROM = os.environ["MAIL_FROM"]
MAIL_TO = os.environ["MAIL_TO"]


def fetch_weekly_items():
    client = MongoClient(MONGO_URI)
    collection = client[MONGO_DB][MONGO_COLLECTION]

    since = datetime.now(timezone.utc) - timedelta(days=7)

    items = list(collection.find({
        "created_at": {"$gte": since}
    }))

    client.close()
    return items


def weighted_score(item):
    score = item.get("bewertung", 0)

    if item.get("passt_groesse") is True:
        score += 2
    if item.get("passt_stil") is True:
        score += 1
    if item.get("begruendung"):
        score += 0.5
    if item.get("masse", {}).get("schulter_cm") is not None:
        score += 0.5

    return score


def build_reason(item):
    if item.get("begruendung"):
        return item["begruendung"]

    hints = item.get("passform_hinweise") or []
    if hints:
        return "; ".join(hints)

    parts = []
    if item.get("passt_stil") is True:
        parts.append("Stil passt")
    if item.get("passt_groesse") is True:
        parts.append("Größenpassung wirkt passend")
    if item.get("zustand"):
        parts.append(f"Zustand: {item['zustand']}")

    return ", ".join(parts) if parts else "Keine detaillierte Begründung vorhanden."


def build_html(items):
    total = len(items)
    recommended = [x for x in items if x.get("empfohlen") is True]
    recommended.sort(key=weighted_score, reverse=True)

    top5 = recommended[:5]
    avg_rating = round(sum(x.get("bewertung", 0) for x in items) / total, 2) if total else 0

    blocks = []
    for item in top5:
        titel = escape(str(item.get("titel", "Ohne Titel")))
        preis = escape(str(item.get("preis", "k. A.")))
        zustand = escape(str(item.get("zustand", "k. A.")))
        material = escape(str(item.get("material", "k. A.")))
        url = escape(str(item.get("url", "#")))
        reason = escape(build_reason(item))
        bewertung = item.get("bewertung", 0)

        blocks.append(f"""
        <div style="border:1px solid #ddd;padding:16px;margin-bottom:16px;border-radius:8px;">
            <h3 style="margin-top:0;">{titel}</h3>
            <p><strong>Preis:</strong> {preis}</p>
            <p><strong>Bewertung:</strong> {bewertung}/10</p>
            <p><strong>Zustand:</strong> {zustand}</p>
            <p><strong>Material:</strong> {material}</p>
            <p><strong>Warum interessant:</strong> {reason}</p>
            <p><a href="{url}">Zum Artikel</a></p>
        </div>
        """)

    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:24px;">
        <h1>Vinted Smart Finder – Weekly Digest</h1>
        <p>Automatisch generierter Wochenreport.</p>

        <ul>
          <li>Analysierte Artikel: <strong>{total}</strong></li>
          <li>Empfohlene Artikel: <strong>{len(recommended)}</strong></li>
          <li>Durchschnittsbewertung: <strong>{avg_rating}</strong></li>
        </ul>

        <h2>Top 5 Empfehlungen</h2>
        {''.join(blocks) if blocks else '<p>Diese Woche gab es keine empfohlenen Artikel.</p>'}
      </body>
    </html>
    """


def send_email(html):
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "from": MAIL_FROM,
            "to": [MAIL_TO],
            "subject": "Vinted Smart Finder – Weekly Digest",
            "html": html
        },
        timeout=30
    )
    response.raise_for_status()
    print("Newsletter erfolgreich versendet.")


def main():
    items = fetch_weekly_items()
    html = build_html(items)
    send_email(html)


if __name__ == "__main__":
    main()
