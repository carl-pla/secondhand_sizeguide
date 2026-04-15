# runner.py
import asyncio
from database.users import lade_alle_user
from main import main

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

        # User-Daten als Config zusammenbauen
        config = {
            "groesse":                 user["groesse"],
            "kategorie":               user.get("kategorie", "Herren Jacken & Mäntel"),
            "max_preis":               user["max_preis"],
            "stile":                   user["stile"],
            "eigene_masse":            user.get("eigene_masse", {}),
            "min_zustand":             user.get("min_zustand", "Gut"),
            "ollama_url":              "http://localhost:11435/api/generate",
            "ollama_modell":           "llama3",
            "max_artikel_pro_suche":   20,
            "max_suchen":              2,
            "pause_zwischen_artikeln": [2, 4],
            "pause_zwischen_suchen":   [3, 6],
        }

        try:
            ergebnisse = await main(config, user_email=user["email"])
            empfohlen = [e for e in (ergebnisse or []) if e.get("empfohlen")]
            print(f"✅ {user['email']}: {len(empfohlen)} Empfehlungen")
        except Exception as e:
            print(f"❌ Fehler bei {user['email']}: {e}")

if __name__ == "__main__":
    asyncio.run(run_fuer_alle_user())