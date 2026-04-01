import pymongo
import json

uri = "mongodb://localhost:27017/"
file = "/Users/carlplacek/Desktop/Uni/DataScienceProjekt/secrets/vinted_empfehlungen.json"

# Verbindung zur MongoDB herstellen
my_client = pymongo.MongoClient(uri)
# Datenabnk erstellen (Container für Daten)
mydb = my_client["Secondhand_db"]

# collection erstellen (eine Gruppe von Dokumenten)
collection = mydb[file]

# Deine JSON-Datei laden 
with open(file, "r", encoding="utf-8") as file:
    data = json.load(file)

# Daten in MongoDB speichern
result = collection.insert_many(data)
print(f"{len(result.inserted_ids)} Dokumente gespeichert")
print(f"Gesamtanzahl Dokumente in der Collection: {collection.count_documents({})}")
