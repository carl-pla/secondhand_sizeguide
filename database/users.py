import pymongo # type: ignore
import datetime
import re
import os 

from dotenv import load_dotenv # type: ignore
from pymongo import MongoClient # type: ignore

from database.config_defaults import URL_MONGO

# Variablen abrufen
user = os.getenv("MONGO_USER")
password = os.getenv("MONGO_PASS")
cluster = os.getenv("MONGO_CLUSTER")



def get_users_collection():
    client = pymongo.MongoClient(URL_MONGO, serverSelectionTimeoutMS=2000)
    return client["Secondhand_db"]["users"]

def registriere_user(email: str, config: dict) -> dict:
    """Neuen User registrieren oder bestehenden updaten"""
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return {"error": "Ungültige Email-Adresse"}

    col = get_users_collection()

    # Bereits registriert?
    bestehend = col.find_one({"email": email})
    if bestehend:
        # Update bestehenden User
        col.update_one(
            {"email": email},
            {"$set": {
                "groesse":      config.get("groesse"),
                "max_preis":    config.get("max_preis"),
                "stile":        config.get("stile"),
                "eigene_masse": config.get("eigene_masse"),
                "aktiv":        True,
            }}
        )
        return {"status": "updated", "email": email}

    # Neu registrieren
    doc = {
        "email":          email,
        "groesse":        config.get("groesse"),
        "max_preis":      config.get("max_preis"),
        "stile":          config.get("stile"),
        "eigene_masse":   config.get("eigene_masse"),
        "aktiv":          True,
        "registriert_am": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    col.insert_one(doc)
    return {"status": "neu", "email": email}


def lade_alle_user() -> list:
    """Alle aktiven User laden"""
    col = get_users_collection()
    users = list(col.find({"aktiv": True}))
    for u in users:
        u.pop("_id", None)
    return users


def deaktiviere_user(email: str):
    """User vom Newsletter abmelden"""
    col = get_users_collection()
    col.update_one({"email": email}, {"$set": {"aktiv": False}})