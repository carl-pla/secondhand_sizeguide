import requests
from get_new_token import get_new_token
import json

def get_summary_of_articles_json(

        price=(0,40),
        conditions=("NEW","USED"),
        buyopt="FIXED_PRICE|BEST_OFFER",
        keywords="",
        sort_type="",
        brand=None,
        color=None

):
    """
    Holt json mit Artikeln und allgemeinen zugehörigen Daten über Browse API.
    Enthält keine genauen Größen oder Artikelbeschreibung.

    :param price: Preisbereich
    :param conditions: Zustände des Zielprodukts
    :param buyopt: Auktion oder Festpreis
    :param keywords: Suchbegriffe
    :param sort_type: Aufsteigend ("") oder absteigend ("-") nach Preis sortiert
    :param brand: Marke
    :param color: Farbe
    :return: json mit Artikeln und zugehörigen Daten
    """
    user_token = get_new_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    # Achtung: Holt nicht die lange Artikelbeschreibung, die manchmal genauere Maße enthält.

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }


    filter_options = [
        f"priceCurrency:EUR",
        f"price:[{price[0]}..{price[1]}]"
    ]

    dynamic_filter_options = {
        "conditions": conditions,
        "buyingOptions": buyopt
    }

    # str als Werte für dynamische Optionen zulassen
    for options_name, value in dynamic_filter_options.items():
        if value:
            if not isinstance(value, str):
                value = "|".join(value)
            filter_options.append(f"{options_name}:{{{value}}}")

    aspect_list = []

    # Brand hinzufügen funktioniert
    if brand:
        brand_val = brand if isinstance(brand, str) else "|".join(brand)
        aspect_list.append(f"Marke:{{{brand_val}|{brand_val.lower()}}}")

    # Farbsuche funktioniert noch nicht
    if color:
        color_val = color if isinstance(color, str) else "|".join(color)
        aspect_list.append(f"Farbe:{{{color_val}|{color_val.lower()}}}")

    cat_id = 11450 # ID für Kleidung & Accessoires allgemein
    if aspect_list:
        aspect_string = f"categoryId:{cat_id}," + ",".join(aspect_list)
    else:
        aspect_string = f"categoryId:{cat_id}"

    params = {
        "q": keywords,
        "category_ids": "11450",
        "filter": ",".join(filter_options),
        "aspect_filter": aspect_string,
        "sort": f"{sort_type}price",
        "limit": "5" # Maximum 200
    }

    try:

        articles_raw = requests.get(url, headers=headers, params=params, timeout=(5, 30))

        # HTTP-Fehler prüfen (4xx, 5xx)
        articles_raw.raise_for_status()

        # JSON validieren: Prüft, ob Antwort valides JSON ist und in Python-Dict umformatiert werden kann
        summary_json = articles_raw.json()

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
    # Achtung: Holt nicht die lange Artikelbeschreibung, die manchmal genauere Maße enthält.

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
res = get_summary_of_articles_json(keywords="hose", color="Rot", sort_type="-")
print(res)

# Zugriff auf die Treffer
if res and 'itemSummaries' in res:
    for item in res['itemSummaries']:
        print(f"Gefunden: {item['title']} - Preis: {item['price']['value']} {item['price']['currency']}")