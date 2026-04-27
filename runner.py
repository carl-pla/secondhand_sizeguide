"""
Hilfsskript für main.py und die ci/cd pipline für newsletter
"""

import asyncio
import subprocess
import sys
from database.users import lade_alle_user
from database.config_defaults import CONFIG_FILE
from database.scrapping_sessions import speichere_in_mongo
import json
import os
import tempfile
from pathlib import Path

async def run_fuer_alle_user():
    users = lade_alle_user()

    if not users:
        print("Keine aktiven User gefunden.")
        return

    print(f"🚀 {len(users)} aktive User gefunden\n")

    for user in users:
        print(f"\n{'='*60}")
        print(f"👤 User: {user['email']}")
        print(f"{'='*60}")

        # User-Config als temporäre JSON speichern
        config = {
            "groesse":                 user["groesse"],
            "kategorie":               user.get("kategorie", "Herren Jacken & Mäntel"),
            "max_preis":               user["max_preis"],
            "stile":                   user["stile"],
            "eigene_masse":            user.get("eigene_masse", {}),
            "min_zustand":             user.get("min_zustand", "Gut"),
            "ollama_url":              os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434") + "/api/generate",
            "ollama_modell":           "llama3.2:3b",
            "max_artikel_pro_suche":   10,
            "max_suchen":              1,
            "pause_zwischen_artikeln": [2, 4],
            "pause_zwischen_suchen":   [3, 6],
            "_user_email":             user["email"],
        }

        # Temporäre Config-Datei pro User
        tmp = Path(f"/tmp/config_{user['email'].replace('@','_')}.json")
        with open(tmp, "w") as f:
            json.dump(config, f, ensure_ascii=False)

        # main.py als separaten Prozess starten
        try:
            result = subprocess.run(
                [sys.executable, "main.py", "--config", str(tmp)],
                timeout=600
            )
            if result.returncode == 0:
                print(f"✅ {user['email']}: fertig")
            else:
                print(f"❌ {user['email']}: Fehler (returncode {result.returncode})")
        except subprocess.TimeoutExpired:
            print(f"⏱️  {user['email']}: Timeout nach 10 Min")
        except Exception as e:
            print(f"❌ {user['email']}: {e}")
        finally:
            tmp.unlink(missing_ok=True)

if __name__ == "__main__":
    asyncio.run(run_fuer_alle_user())