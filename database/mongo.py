import pymongo # type: ignore 
import datetime
import os 

from config_defaults import MONGO_URL
from dotenv import load_dotenv

load_dotenv()

def speichere_in_mongo(ergebnisse: list, config: dict = None):
    """
    Speichert die Analyse-Ergebnisse in MongoDB. 
    Verhindert Fehler bei leeren Listen und stellt Verbindungen sicher.
    """
    
    # 1. Sofort-Check: Wenn keine Empfehlungen da sind, nichts tun
    if not ergebnisse:
        print("MongoDB: Keine Empfehlungen zum Speichern gefunden.")
        return None

    # Sicherstellen, dass wir wirklich nur Empfehlungen speichern (empfohlen == True)
    empfehlungen = [e for e in ergebnisse if isinstance(e, dict) and e.get("empfohlen") is True]
    
    if not empfehlungen:
        print("MongoDB: Liste enthielt keine Artikel mit Status 'empfohlen'.")
        return None

    try:
        # Verbindung aufbauen (mit Timeout, falls DB nicht läuft)
        load_dotenv()
        uri = os.getenv(MONGO_URL) 
        my_client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
        mydb = my_client["Secondhand_db"]
        collection = mydb["vinted_empfehlungen"]

        # Zeitstempel hinzufügen, damit du im Dashboard nach "Neu" sortieren kannst
        jetzt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for artikel in empfehlungen:
            artikel["gespeichert_am"] = jetzt

        # 2. Der entscheidende Fix: Nur insert_many aufrufen, wenn die Liste gefüllt ist
        result = collection.insert_many(empfehlungen)
        
        print(f"✅ MongoDB: {len(result.inserted_ids)} neue Empfehlungen gespeichert.")
        return result

    except pymongo.errors.ServerSelectionTimeoutError:
        print("❌ MongoDB Fehler: Verbindung zum Server fehlgeschlagen (läuft MongoDB?)")
    except Exception as e:
        print(f"❌ Fehler beim Speichern in MongoDB: {e}")
        return None