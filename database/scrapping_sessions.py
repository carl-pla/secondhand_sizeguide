import pymongo # type: ignore
import datetime
import uuid
from database.config_defaults import URI_MONGO

def speichere_in_mongo(ergebnisse: list, config: dict = None, user_email: str = None):
    if not ergebnisse:
        print("MongoDB: Keine Empfehlungen zum Speichern gefunden.")
        return None

    empfehlungen = [e for e in ergebnisse if isinstance(e, dict) and e.get("empfohlen") is True]

    if not empfehlungen:
        print("MongoDB: Liste enthielt keine Artikel mit Status 'empfohlen'.")
        return None

    try:
        client = pymongo.MongoClient(URI_MONGO, serverSelectionTimeoutMS=5000)
        db = client["Secondhand_db"]

        jetzt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Session-Dokument erstellen
        session = {
            "session_id":         str(uuid.uuid4()),
            "user_email":         user_email or "anonym",
            "gestartet_am":       jetzt,
            "config": {
                "groesse":        config.get("groesse"),
                "max_preis":      config.get("max_preis"),
                "stile":          config.get("stile"),
                "kategorie":      config.get("kategorie"),
            } if config else {},
            "empfehlungen":       empfehlungen,
            "anzahl_empfohlen":   len(empfehlungen),
            "anzahl_analysiert":  len(ergebnisse),
        }

        db["scraping_sessions"].insert_one(session)
        print(f"✅ MongoDB: Session gespeichert ({len(empfehlungen)} Empfehlungen) für {user_email or 'anonym'}")
        return session["session_id"]

    except pymongo.errors.ServerSelectionTimeoutError:
        print("❌ MongoDB Fehler: Verbindung fehlgeschlagen")
    except Exception as e:
        print(f"❌ Fehler beim Speichern in MongoDB: {e}")
        return None