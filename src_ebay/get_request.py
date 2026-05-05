import asyncio

import httpx
import requests

import src_ebay.ebay_helper as helper
from database.config_defaults import CATEGORY_IDS_EBAY, CONDITION_IDS_EBAY


def get_summary_of_articles_json(
        max_price=40,
        keywords="",
        brand=None,
        color="",
        category=None,
        size="",
        min_condition=None,
        item_amount=5,
        material="",

        user_token="",
):
    """
    Holt JSON-Objekt mit Produkten und zugehörigen Produktdaten über Browse API.
    Enthält keine genauen Details wie Größen oder Artikelbeschreibungen.

    :param max_price: maximaler Preis
    :param min_condition: schlechtester erlaubter Zustand des Zielprodukts
    :param keywords: Suchbegriffe
    :param brand: Marke
    :param color: Farbe
    :param category: gesuchte Kategorie
    :param size: Größe
    :param min_condition: schlechtester erlaubter Zustand des Artikels
    :param item_amount: Menge von zu prüfenden Artikeln, die geholt werden soll
    :param material: Material des Kleidungsstücks
    :param user_token: Authentifizierungstoken für get-Request

    :return: set der gefundenen Item-IDs
    """
    # falls unmögliche item-Menge angefordert wird
    if item_amount > 200:
        return None

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }

    keywords = f"{keywords} {color} {size} {material}"

    try:
        cat_id = CATEGORY_IDS_EBAY[category]
    except KeyError:
        cat_id = CATEGORY_IDS_EBAY["Kleidung & Accessoires"]  # Kleidung & Accessoires als Default

    try:
        min_condition = CONDITION_IDS_EBAY[min_condition]
    except KeyError:
        min_condition = CONDITION_IDS_EBAY["Gut"]  # Gut als Default

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
        "category_ids": cat_id,
        "filter": ",".join(filter_options),
        "aspect_filter": aspect_string,
        "sort": "-price",  # teuere Produkte zuerst, sonst kriegt man nur Pfennigartikel angezeigt
        "limit": f"{item_amount}"  # Maximum 200
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

    return None


# einzeln, weil get_items nur für eBay-Partner reserviert
async def fetch_one_item(client, item_id):
    """
    Asynchroner Abruf der Daten zu einem einzelnen Item.

    :param client: Client mit Header-Daten
    :param item_id: ID eines einzelnen Items
    :return: dict mit relevanten Eckdaten zum Artikel
    """
    url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"
    try:
        response = await client.get(url)
        response.raise_for_status()
        return helper.extract_important_data(response.json())
    except Exception as e:
        print(f"Fehler bei Item {item_id}: {e}")
        return None


async def get_detailed_items_async(item_ids, user_token):
    """
    Führt nicht-blockierende HTTP-GET-Requests für eine Menge von Item-IDs aus.

    Stellt Anfragen via httpx, um die Latenz durch gleichzeitige Anfragen zu
    minimieren. Resultate werden durch helper.extract_important_data gesäubert.

    :param item_ids: Set mit allen gefundenen Item-IDs
    :param user_token: Authentifizierungstoken für get-Request
    :return: Liste von dicts mit genauen Produktdaten (Größe, Beschreibung, Material usw.)
    """

    if not item_ids:
        print("❌ Keine Artikel gefunden")
        return None

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }

    # EINEN Client für alle Anfragen (Connection Pooling) erstellen
    async with httpx.AsyncClient(headers=headers,
                                 limits=httpx.Limits(max_connections=20),
                                 timeout=10.0) as client:
        tasks = [fetch_one_item(client, item_id) for item_id in item_ids]

        # 'gather' führt alle Tasks gleichzeitig aus und wartet auf alle Ergebnisse
        results = await asyncio.gather(*tasks)

    return [res for res in results if res is not None]