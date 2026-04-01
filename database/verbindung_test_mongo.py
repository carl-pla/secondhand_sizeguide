from pymongo import MongoClient

# Exakt diese URI nutzen:
uri = "mongodb://localhost:27017/"

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=2000)
    # Teste die Verbindung sofort
    client.admin.command('ping')
    print("Endlich! Die Verbindung steht.")
    
    db = client["uni_projekt_db"]
    collection = db["json_daten"]
    
    # Beispiel-Speicherung
    collection.insert_one({"status": "erfolgreich", "nachricht": "Datenbank läuft!"})
    
except Exception as e:
    print(f"Immer noch ein Fehler: {e}")