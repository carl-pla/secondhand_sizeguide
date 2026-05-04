import asyncio
import subprocess
import sys
import json
import os
from pathlib import Path
from database.users import lade_alle_user

async def run_fuer_einen_user():
    # Welcher User soll laufen? Kommt aus der GitHub Actions Matrix
    target_email = os.environ.get("TARGET_USER_EMAIL")
    if not target_email:
        print("❌ Keine TARGET_USER_EMAIL gesetzt")
        sys.exit(1)

    # Alle User laden, dann den einen herausfiltern
    users = lade_alle_user()
    user = next((u for u in users if u["email"] == target_email), None)

    if not user:
        print(f"❌ User {target_email} nicht in der Datenbank gefunden")
        sys.exit(1)

    print(f"👤 Starte Scrape für: {user['email']}")

    # Ab hier: exakt deine bestehende Logik aus runner.py, nur für einen User
    config = {
        "groesse":                 user["groesse"],
        "kategorie":               user.get("kategorie", "Herren Jacken & Mäntel"),
        "max_preis":               user["max_preis"],
        "stile":                   user["stile"],
        "eigene_masse":            user.get("eigene_masse", {}),
        "min_zustand":             user.get("min_zustand", "Gut"),
        "ollama_url":              "http://localhost:11434/api/generate",  # ← kein Docker mehr
        "ollama_modell":           "llama3.1:8b",
        "max_artikel_pro_suche":   10,
        "max_suchen":              1,
        "pause_zwischen_artikeln": [2, 4],
        "pause_zwischen_suchen":   [3, 6],
        "_user_email":             user["email"],
    }

    tmp = Path(f"/tmp/config_{user['email'].replace('@','_')}.json")
    with open(tmp, "w") as f:
        json.dump(config, f, ensure_ascii=False)

    try:
        result = subprocess.run(
            [sys.executable, "main.py", "--config", str(tmp)],
            timeout=600
        )
        if result.returncode == 0:
            print(f"✅ {user['email']}: fertig")
        else:
            print(f"❌ {user['email']}: Fehler (returncode {result.returncode})")
            sys.exit(result.returncode)
    except subprocess.TimeoutExpired:
        print(f"⏱️  {user['email']}: Timeout nach 10 Min")
        sys.exit(1)
    finally:
        tmp.unlink(missing_ok=True)

if __name__ == "__main__":
    asyncio.run(run_fuer_einen_user())