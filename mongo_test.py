# Einmalig lokal ausführen zur Diagnose
from pymongo import MongoClient
import os

client = MongoClient(os.getenv("MONGO_URL"))
col = client["Secondhand_db"]["scraping_sessions"]

print(f"Gesamt Sessions: {col.count_documents({})}")
letzte = col.find_one(sort=[("gestartet_am", -1)])
if letzte:
    print(f"Letzte Session: {letzte['gestartet_am']}")
    print(f"User: {letzte['user_email']}")
    print(f"Empfehlungen: {letzte['anzahl_empfohlen']}")