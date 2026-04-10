import requests
from get_new_token import get_new_token


def get_summary_of_articles_json(curr="EUR", price=(0,20), conditions=("NEW","USED"), buyopt=("FIXED_PRICE")):
    """
    Holt json mit Artikeln und allgemeinen zugehörigen Daten über Browse API.
    Enthält keine genauen Größen oder Artikelbeschreibung.

    :return: json mit Artikeln und zugehörigen Daten
    """
    user_token = get_new_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    # Achtung: Holt nicht die lange Artikelbeschreibung, die manchmal genauere Maße enthält. FIX!!!

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }

    # Beispiel: Wir suchen eine Spanne für die Bundweite (Waist 32 bis 34)
    # Syntax: aspectIds:{ID:(Wert1|Wert2|Wert3)}

    # NOTIZ ZU IDS:
    # 11427 = Bundweite (z.B. 32, 34)
    # 11428 = Schrittlänge (z.B. 30, 32)
    # 11429 = Konfektionsgröße (z.B. 48, 52, L)

    selected_sizes = "32|33|34" # Hier deine Spanne als ODER-Verknüpfung

    filter_options = [
        f"priceCurrency:{curr}",
        f"price:[{price[0]}..{price[1]}]",
        f"conditions:{{{"|".join(conditions)}}}",
        f"buyingOptions:{{{buyopt}}}", # mit 
        f"aspectIds:{{11427:({selected_sizes})}}"  # Filtert auf Bundweite 32, 33 oder 34
    ]

    params = {
        "q": "chino herren",
        "filter": ",".join(filter_options),
        "category_ids": "11450",
        "sort": "price",
        "limit": "10",
        # HINZUFÜGEN: Liefert die Liste aller verfügbaren Merkmale im JSON zurück
        # "fieldgroups": "ASPECT_REFINEMENTS"
    }

    try:

        articles_raw = requests.get(url, headers=headers, params=params, timeout=(5, 30))

        # HTTP-Fehler prüfen (4xx, 5xx)
        articles_raw.raise_for_status()

        # JSON validieren: Prüft, ob Antwort valides JSON ist und in Python-Dict umformatiert werden kann
        summary_json = articles_raw.json()

        # Zugriff auf die verfügbaren Größen in der Antwort (zum Debuggen oder für dynamische Menüs)
        if 'aspectDistributions' in str(summary_json):

            print("\n--- Verfügbare Filterwerte (Aspects) ---")
            for aspect in summary_json['aspectDistributions']:
                # Klarnamen der Merkmale ausgeben
                print(f"Merkmal: {aspect['localizedAspectName']} (ID: {aspect.get('aspectId', 'N/A')})")
                # Die ersten 3 verfügbaren Werte anzeigen
                for value in aspect['aspectValues'][:3]:
                    print(f"  - Wert: {value['localizedValue']} ({value['matchCount']} Treffer)")

        return summary_json

    except ValueError:
        print("Fehler: Antwort ist kein gültiges JSON")

    except requests.exceptions.Timeout:
        print("Fehler: Anfrage hat zu lange gedauert (Timeout)")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP-Fehler: {e} - Statuscode: {e.response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Allgemeiner Request-Fehler: {e}")

    except Exception as e:
        print(f"Unerwarteter Fehler: {e}")

    return None


def get_single_item_details(item_id):
    """
    Holt json mit genaueren Details zu einem einzelnen Item über Browse API.

    :return: json mit genauen Produktdaten (Größe, Beschreibung usw.)
    """
    user_token = get_new_token()
    url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"
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
        single_json = articles_raw.json()

        # Zugriff auf die verfügbaren Größen in der Antwort (zum Debuggen oder für dynamische Menüs)
        if 'aspectDistributions' in single_json:
            print("\n--- Verfügbare Filterwerte (Aspects) ---")
            for aspect in single_json['aspectDistributions']:
                # Klarnamen der Merkmale ausgeben
                print(f"Merkmal: {aspect['localizedAspectName']} (ID: {aspect.get('aspectId', 'N/A')})")
                # Die ersten 3 verfügbaren Werte anzeigen
                for value in aspect['aspectValues'][:3]:
                    print(f"  - Wert: {value['localizedValue']} ({value['matchCount']} Treffer)")

        return single_json

    except ValueError:
        print("Fehler: Antwort ist kein gültiges JSON")

    except requests.exceptions.Timeout:
        print("Fehler: Anfrage hat zu lange gedauert (Timeout)")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP-Fehler: {e} - Statuscode: {e.response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Allgemeiner Request-Fehler: {e}")

    except Exception as e:
        print(f"Unerwarteter Fehler: {e}")

    return None


# Tests (werden entfernt)
res = get_summary_of_articles_json()

# Zugriff auf die Treffer
if res and 'itemSummaries' in str(res):
    for item in res['itemSummaries']:
        print(f"Gefunden: {item['title']} - Preis: {item['price']['value']} {item['price']['currency']}")
