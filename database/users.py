import pymongo # type: ignore
import datetime
import re
import os 

from dotenv import load_dotenv # type: ignore
from pymongo import MongoClient # type: ignore

from database.config_defaults import MONGO_URL

# Variablen abrufen
user = os.getenv("MONGO_USER")
password = os.getenv("MONGO_PASS")
cluster = os.getenv("MONGO_CLUSTER")



def get_users_collection():
    client = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
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
                "quelle":         config.get("quelle"),
                "groesse":        config.get("groesse"),
                "kategorie":      config.get("kategorie"),
                "stile":          config.get("stile"),
                "max_preis":      config.get("max_preis"),
                "min_zustand":    config.get("min_zustand"),
                "eigene_masse":   config.get("eigene_masse"),
                "farbe":          config.get("farbe"),
                "suchbegriffe":   config.get("suchbegriffe"),
                "marke":          config.get("marke"),
                "material":       config.get("material"),
                "ebay_masse":     config.get("ebay_masse"),
                "habilleur_masse":  config.get("habilleur_masse"),
                "max_artikel_pro_suche": config.get("max_artikel_pro_suche"),
                "max_suchen":      config.get("max_suchen"),
                "pause_zwischen_artikeln": config.get("pause_zwischen_artikeln"),
                "pause_zwischen_suchen": config.get("pause_zwischen_suchen"),
                "min_empfehlung": config.get("min_empfehlung"),
                "aktiv":        True,
            }}
        )
        return {"status": "updated", "email": email}

    # Neu registrieren
    doc = {
        "email":          email,
        "quelle":         config.get("quelle"),
        "groesse":        config.get("groesse"),
        "kategorie":      config.get("kategorie"),
        "stile":          config.get("stile"),
        "max_preis":      config.get("max_preis"),
        "min_zustand":    config.get("min_zustand"),
        "eigene_masse":   config.get("eigene_masse"),
        "farbe":          config.get("farbe"),
        "suchbegriffe":   config.get("suchbegriffe"),
        "marke":          config.get("marke"),
        "material":       config.get("material"),
        "ebay_masse":     config.get("ebay_masse"),
        "habilleur_masse":  config.get("habilleur_masse"),
        "max_artikel_pro_suche": config.get("max_artikel_pro_suche"),
        "max_suchen":      config.get("max_suchen"),
        "pause_zwischen_artikeln": config.get("pause_zwischen_artikeln"),
        "pause_zwischen_suchen": config.get("pause_zwischen_suchen"),
        "min_empfehlung": config.get("min_empfehlung"),
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