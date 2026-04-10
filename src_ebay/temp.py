import requests
from get_new_token import get_new_token
import re
import json

def get_articles_json():
    """
    Holt json mit Artikeln und zugehörigen Daten über Browse API.

    :return: json mit Artikeln und zugehörigen Daten
    """
    user_token = get_new_token()
    url = "https://api.ebay.com/buy/browse/v1/item/v1|388630721336|0"
    # Achtung: Holt nicht die lange Artikelbeschreibung, die manchmal genauere Maße enthält. FIX!!!

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }

    try:

        articles_raw = requests.get(url, headers=headers, timeout=(5, 30))

        # HTTP-Fehler prüfen (4xx, 5xx)
        articles_raw.raise_for_status()

        # JSON validieren: Prüft, ob Antwort valides JSON ist und in Python-Dict umformatiert werden kann
        data = articles_raw.json()

        # Zugriff auf die verfügbaren Größen in der Antwort (zum Debuggen oder für dynamische Menüs)
        if 'aspectDistributions' in data:
            print("\n--- Verfügbare Filterwerte (Aspects) ---")
            for aspect in data['aspectDistributions']:
                # Klarnamen der Merkmale ausgeben
                print(f"Merkmal: {aspect['localizedAspectName']} (ID: {aspect.get('aspectId', 'N/A')})")
                # Die ersten 3 verfügbaren Werte anzeigen
                for value in aspect['aspectValues'][:3]:
                    print(f"  - Wert: {value['localizedValue']} ({value['matchCount']} Treffer)")

        return data

    except ValueError:
        print("Fehler: Antwort ist kein gültiges JSON")

    except requests.exceptions.Timeout:
        print("Fehler: Anfrage hat zu lange gedauert (Timeout)")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP-Fehler: {e} - Statuscode: {articles_raw.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Allgemeiner Request-Fehler: {e}")

    except Exception as e:
        print(f"Unerwarteter Fehler: {e}")

    return None


# Tests (werden entfernt)
res = get_articles_json()
text = str(res)

titles_list = re.findall(r"'title':\s*'([^']*)'", text)

for title in titles_list:
    print(title.strip())

# Zugriff auf die Treffer
if res and 'itemSummaries' in res:
    for item in res['itemSummaries']:
        print(f"Gefunden: {item['title']} - Preis: {item['price']['value']} {item['price']['currency']}")

# response in JSON schreiben
with open("specific_item.json", "w", encoding="utf-8") as file:
    json.dump(res, file, indent=4, ensure_ascii=False)


