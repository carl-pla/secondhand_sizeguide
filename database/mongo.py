import pymongo
import json
import os

def speichere_in_mongo(data): # <--- Hier definieren wir die Funktion
    try:
        uri = "mongodb://localhost:27017/"
        my_client = pymongo.MongoClient(uri)
        mydb = my_client["Secondhand_db"]
        collection = mydb["vinted_empfehlungen"]

        # Daten in MongoDB speichern
        if isinstance(data, list):
            result = collection.insert_many(data)
            print(f"{len(result.inserted_ids)} Dokumente gespeichert")
        else:
            result = collection.insert_one(data)
            print("1 Dokument gespeichert")
            
        return result
    except Exception as e:
        print(f"Fehler beim Speichern in MongoDB: {e}")
        return None

# Dieser Teil sorgt dafür, dass die Datei trotzdem noch eigenständig 
# testbar bleibt, falls du sie direkt ausführst:
if __name__ == "__main__":
    dir_path = os.path.dirname(__file__)
    json_file = os.path.join(dir_path, "../secrets/vinted_empfehlungen.json")
    with open(json_file, "r", encoding="utf-8") as f:
        test_data = json.load(f)
    speichere_in_mongo(test_data)