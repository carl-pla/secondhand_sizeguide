import pymongo # type: ignore 

uri = "mongodb+srv://carlplacek_db_user:DSjrL4Azu3sYbEL1@secondhandguide.az2roej.mongodb.net/"
client = pymongo.MongoClient(uri)

try:
    # Versuche eine Liste der Datenbanken zu holen
    dbs = client.list_database_names()
    print("✅ Verbindung erfolgreich!")
    print("Vorhandene Datenbanken:", dbs)
    
    # Test-Daten einfügen
    db = client["test_db"]
    db.test_collection.insert_one({"status": "erfolgreich", "nachricht": "Hallo Cloud!"})
    print("✅ Test-Daten wurden geschrieben!")
except Exception as e:
    print(f"❌ Fehler bei der Verbindung: {e}")