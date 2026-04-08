import requests
from get_new_token import get_new_token
import re

def get_articles_json():
    """
    Holt json mit Artikeln und zugehörigen Daten über Browse API.

    :return: json mit Artikeln und zugehörigen Daten
    """
    user_token = get_new_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    # Achtung: Holt nicht die lange Artikelbeschreibung, die manchmal genauere Maße enthält. FIX!!!

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }

    filter_options = ["priceCurrency:EUR", # nur eine Währung kann angegeben werden
                    "price:[0..20]",
                    "conditions:{NEW|USED}", # evtl. LIKE_NEW|VERY_GOOD|GOOD|ACCEPTABLE hinzufügen
                    ""]

    params = {
        "q": "chino herren", # Eingabe in Suchleiste
        "filter": ",".join(filter_options),
        "category_ids": "11450",  # Kategorie: Kleidung & Accessoires
        "sort": "price", # vorerst nach Preis sortieren
        "limit": "10"
    }


    try:
        #
        articles_raw = requests.get(url, headers=headers, params=params, timeout=(5, 30))

        # HTTP-Fehler prüfen (4xx, 5xx)
        articles_raw.raise_for_status()

        # JSON validieren: Prüft, ob Antwort valides JSON ist und in Python-Dict umformatiert werden kann
        return articles_raw.json()

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
prices_list = re.findall(r"'value':\s*'([^']*)'", text)

for title in titles_list:
    print(title.strip())

print(res)