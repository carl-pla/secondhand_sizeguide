import requests
from concurrent.futures import ThreadPoolExecutor

from get_new_token import get_new_token
import ebay_helper as helper
from database.config_defaults import category_ids_ebay, condition_ids_ebay


def get_summary_of_articles_json(
        max_price=40,
        keywords="",
        brand=None,
        color="",
        category=None,
        size="",
        min_condition=None,
        styles=None
):
    """
    Holt json mit Produkten und allgemeinen Produktdaten über Browse API.
    Enthält keine genauen Größen oder Artikelbeschreibung.

    :param max_price: maximaler Preis
    :param min_condition: schlechtester erlaubter Zustand des Zielprodukts
    :param keywords: Suchbegriffe
    :param brand: Marke
    :param color: Farbe
    :param category: gesuchte Kategorie
    :param size: Größe
    :param min_condition: schlechtester erlaubter Zustand des Artikels
    :param styles: Styles

    :return: Tupel von json mit Produkten und allgemeinen zugehörigen Daten,
    """
    user_token = get_new_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }

    keywords = f"{keywords} {color} {size} {" ".join(styles)}"

    try:
        cat_id = category_ids_ebay[category]
    except KeyError:
        cat_id = category_ids_ebay["Kleidung & Accessoires"]  # Kleidung & Accessoires als Default

    try:
        min_condition = condition_ids_ebay[min_condition]
    except KeyError:
        min_condition = condition_ids_ebay["Befriedigend"]  # Befriedigend als Default

    filter_options = [
        f"priceCurrency:EUR",
        f"price:[0..{max_price}]",
        "buyingOptions:{FIXED_PRICE|BEST_OFFER}",  # Festpreis oder verhandelbar
        f"conditionIds:{{{min_condition}}}"
    ]

    if brand:
        brand_val = brand if isinstance(brand, str) else "|".join(brand)
        aspect_string = f"categoryId:{cat_id},Marke:{{{brand_val}|{brand_val.lower()}}}"
    else:
        aspect_string = f"categoryId:{cat_id}"

    params = {
        "q": keywords,
        "category_ids_ebay": cat_id,
        "filter": ",".join(filter_options),
        "aspect_filter": aspect_string,
        "sort": "-price", # teuere Produkte zuerst, sonst kriegt man nur Pfennigartikel angezeigt
        "limit": "200"  # Maximum 200
    }

    try:

        articles_raw = requests.get(url, headers=headers, params=params, timeout=(3, 10))

        # HTTP-Fehler prüfen (4xx, 5xx)
        articles_raw.raise_for_status()

        # JSON validieren: Prüft, ob Antwort valides JSON ist und in Python-Dict umformatiert werden kann
        summary_json = articles_raw.json()

        piece_ids = set()
        for piece in summary_json["itemSummaries"]:
            try:
                piece_ids.add(piece["itemId"])
            except KeyError:
                print(f"Fehler: Item (ID: {piece['itemId']}) konnte nicht hinzugefügt werden.")
                continue

        return piece_ids

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

    return None, None


# einzeln, weil get_items nur für eBay-Partner reserviert
def get_detailed_items(item_ids):
    """
    Holt jsons mit genaueren Details zu einzelnen Items über Browse API.

    :param item_ids: Set mit allen gefundenen Item-IDs
    :return: Liste von dicts mit genauen Produktdaten (Größe, Beschreibung usw.)
    """
    user_token = get_new_token()
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    })

    def fetch_one_item(item_id):
        """Holt nur wichtige Daten zu genau EINEM Produkt als dict."""
        try:
            url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"
            response = session.get(url, timeout=(3, 10))
            response.raise_for_status()

            return helper.extract_important_data(response.json())

        except Exception as e:
            print(f"Fehler bei {item_id}: {e}")
            return None

    # Laufzeitoptimum bei 20 Workers
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_one_item, item_ids))

    return [res for res in results if res is not None]

# jetzt: jeden Artikel von Ollama auf Größe bewerten lassen, nur wenn größe passt +1, bis Zahl der gewollten Artikel erreicht