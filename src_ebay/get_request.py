import requests
from get_new_token import get_new_token


def get_summary_of_articles_json(

        price=(0,100),
        conditions=("NEW","USED"),
        buyopt="FIXED_PRICE",
        keywords="",
        sort_type="+",
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
    :param sort_type: Aufsteigend (+) oder absteigend (-) nach Preis sortiert
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
        f"priceCurrency:EUR", # kein ODER (|) erlaubt, deswegen hardgecodet (EUR macht für uns in DE am meisten Sinn)
        f"price:[{price[0]}..{price[1]}]",
        f"conditions:{{{"|".join(conditions)}}}",
        f"buyingOptions:{{{"|".join(buyopt)}}}"
    ]

    dynamic_options = {
        "conditions": conditions,
        "buyingOptions": buyopt,
        "Brand": brand,
        "Color": color
    }

    # str als Werte für dynamische Optionen zulassen
    for options_name, value in dynamic_options.items():
        if value:
            if not isinstance(value, str):
                value = "|".join(value)

            if options_name in {"Brand", "Color"}:
                filter_options.append(f"aspectIds:{{{options_name}:({value})}}")

            else:
                filter_options.append(f"{options_name}:{{{value}}}")

    params = {
        "q": keywords,
        "filter": ",".join(filter_options),
        "category_ids": "11450", # ID für Kleidung & Accessoires
        "sort": f"{sort_type}price",
        "limit": "200" # Maximum
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
res = get_summary_of_articles_json(keywords="chino herren", color="Rot")

# Zugriff auf die Treffer
if res and 'itemSummaries' in str(res):
    for item in res['itemSummaries']:
        print(f"Gefunden: {item['title']} - Preis: {item['price']['value']} {item['price']['currency']}")
