import json

import html2text
import requests

from get_new_token import get_new_token


def get_summary_of_articles_json(

        max_price=40,
        keywords="",
        sort_type="-",
        brand=None,
        color="",
        category=None,
        size="",
        min_condition=None

):
    """
    Holt json mit Artikeln und allgemeinen zugehörigen Daten über Browse API.
    Enthält keine genauen Größen oder Artikelbeschreibung.

    :param max_price: maximaler Preis
    :param min_condition: schlechtester erlaubter Zustand des Zielprodukts
    :param keywords: Suchbegriffe
    :param sort_type: Aufsteigend ("") oder absteigend ("-") nach Preis sortiert
    :param brand: Marke
    :param color: Farbe
    :param category: gesuchte Kategorie
    :param size: Größe
    :param min_condition: schlechtester erlaubter Zustand des Artikels

    :return: json mit Artikeln und zugehörigen Daten
    """
    user_token = get_new_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    # Achtung: Holt nicht die lange Artikelbeschreibung, die manchmal genauere Maße enthält.

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }

    category_ids = {
        "Kleidung & Accessoires": "11450",  # allgemeine ID (übergeordnet)

        "Herren Alles": "260012",
        "Herren Anzüge & Blazer": "3001",
        "Herren Badebekleidung": "15690",
        "Herren Fitnessmode": "185099",
        "Herren Hosen": "57989",
        "Herren Jacken, Mäntel und Westen": "57988",
        "Herren Jeans": "11483",
        "Herren Nachtwäsche": "11510",
        "Herren Pullover & Strick": "11484",
        "Herren Shirts und Hemden": "185100",
        "Herren Shorts und Bermudas": "15689",
        "Herren Unterwäsche": "11507",
        "Herren Stiefel": "11498",
        "Herren Business-Schuhe": "53120",
        "Herren Sneaker": "15709",
        "Herren Halbschuhe": "24087",
        "Herren Hüte und Mützen": "52365",
        "Herren Schals & Tücher": "52382",
        "Herren Krawatten & Fliegen": "15662",
        "Herren Gürtel": "2993",
        "Herren Handschuhe und Fäustlinge": "2994",
        "Herren Taschen": "52357",
        "Herren Schmuck": "10290",
        "Herren Armbanduhren & Taschenuhren": "260325",

        "Damen Alles": "260010",
        "Damen Pullover & Strickpullover": "63866",
        "Damen Kleider": "63861",
        "Damen Jeans": "11554",
        "Damen Shorts & Bermudas": "11555",
        "Damen Bademode": "63867",
        "Damen Jacken, Mäntel und Westen": "63862",
        "Damen Anzüge & Anzugteile": "63865",
        "Damen Röcke": "63864",
        "Damen Blusen, Tops & Shirts": "53159",
        "Damen Hosen & Leggings": "169001",
        "Damen Unterwäsche & Nachtwäsche": "11514",
        "Damen Stiefel & Stiefeletten": "53557",
        "Damen Absatzschuhe": "55793",
        "Damen Hausschuhe": "11632",
        "Damen Sneaker": "95672",
        "Damen Halbschuhe & Ballerinas": "45333",
        "Damen Sandalen": "62107",
        "Damen Taschen": "169291",
        "Damen Schals & Tücher": "45238",
        "Damen Hüte und Mützen": "45230",
        "Damen Handschuhe & Fäustlinge": "105559",
        "Damen Modeschmuck": "10968",
        "Damen Armbanduhren & Taschenuhren": "260325",
        "Damen Kopfschmuck & Fascinators": "168998",
        "Damen Gürtel": "3003"
    }

    condition_ids = {
        "Neu mit Etikett": "1000",
        "Neu ohne Etikett": "1000|1500|1750",
        "Sehr gut": "1000|1500|1750|2000|2010|2020|2500|2750|2990|3000|4000",
        "Gut": "1000|1500|1750|2000|2010|2020|2030|2500|2750|2990|3000|3010|4000|5000",
        "Befriedigend": "1000|1500|1750|2000|2010|2020|2030|2500|2750|2990|3000|3010|4000|5000|6000"
    }

    keywords = f"{keywords} {color} {size}"

    try:
        cat_id = category_ids[category]
    except KeyError:
        cat_id = category_ids["Kleidung & Accessoires"]  # Kleidung & Accessoires als Default

    try:
        min_condition = condition_ids[min_condition]
    except KeyError:
        min_condition = condition_ids["Befriedigend"]  # Befriedigend als Default

    filter_options = [
        f"priceCurrency:EUR",
        f"price:[0..{max_price}]",
        "buyingOptions:{FIXED_PRICE|BEST_OFFER}",  # Festpreis oder verhandelbar
        f"conditionIds:{{{min_condition}}}"
    ]

    # Brand hinzufügen funktioniert, Farbe entfernt (funktioniert trotz richtigem Parameternamen aus aspect_refinements nicht)
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
        "sort": f"{sort_type}price",
        "limit": "200"  # Maximum 200
    }

    try:

        articles_raw = requests.get(url, headers=headers, params=params, timeout=(5, 30))

        # HTTP-Fehler prüfen (4xx, 5xx)
        articles_raw.raise_for_status()

        # JSON validieren: Prüft, ob Antwort valides JSON ist und in Python-Dict umformatiert werden kann
        summary_json = articles_raw.json()

        piece_ids = set()

        for piece in summary_json["itemSummaries"]:
            piece_ids.add(piece["itemId"])

        return summary_json, piece_ids

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


def clean_description(html_content):
    # Falls Beschreibung nicht gefunden wird
    if not html_content:
        return ""

    converter = html2text.HTML2Text()

    converter.ignore_links = True  # Links entfernen
    converter.ignore_images = True  # Bilder-URLs entfernen
    converter.bypass_tables = False  # Tabellen in Text umwandeln

    # Umwandlung
    markdown_text = converter.handle(html_content)

    return markdown_text.strip()


def extract_important_data(single_json):
    raw_aspects = {aspect['name']: aspect['value'] for aspect in single_json.get("localizedAspects", [])}

    clean_item = {
        "itemId": single_json.get("itemId"),
        "title": single_json.get("title"),
        "price": single_json.get("price", {}).get("value"),
        "currency": single_json.get("price", {}).get("currency"),

        "brand": raw_aspects.get("Marke"),
        "color": raw_aspects.get("Farbe"),
        "size": raw_aspects.get("Größe"),
        "material": raw_aspects.get("Material"),
        "description": clean_description(single_json.get("description"))
        # description wird als HTML zurückgegeben, muss noch für LLM zu markdown konvertiert werden
    }

    return clean_item


def get_single_item_details(item_ids):
    """
    Holt json mit genaueren Details zu einem einzelnen Item über Browse API.
    2 in 1-Funktion, damit nicht mehr Details zu Einzelnartikeln geholt werden müssen als nötig.

    :param item_ids: Set mit allen gefundenen Item-IDs
    :return: json mit genauen Produktdaten (Größe, Beschreibung usw.)
    """
    user_token = get_new_token()

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }

    list_of_single_jsons = []

    for item_id in item_ids:

        try:
            url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"

            item_raw = requests.get(url, headers=headers, timeout=(5, 30))

            # HTTP-Fehler prüfen (4xx, 5xx)
            item_raw.raise_for_status()

            # JSON validieren: Prüft, ob Antwort valides JSON ist und in Python-Dict umformatiert werden kann
            single_json = item_raw.json()

            # nur bestimmte Informationen raussuchen
            cleaned_single_json = extract_important_data(single_json)

            list_of_single_jsons.append(cleaned_single_json)

        except Exception as e:
            print(f"Fehler bei Artikel mit ID {item_id}: {e}")

    with open('single_item_details.json', 'w', encoding='utf-8') as f:
        json.dump(list_of_single_jsons, f, indent=4, ensure_ascii=False)

    return list_of_single_jsons


# Tests (werden entfernt)
res, piece_ids = get_summary_of_articles_json(sort_type="-", brand="Givenchy", max_price=10)
print(res)

print(piece_ids)

print(get_single_item_details(piece_ids))

# Zugriff auf die Treffer
if res and 'itemSummaries' in res:
    for item in res['itemSummaries']:
        print(f"Gefunden: {item['title']} - Preis: {item['price']['value']} {item['price']['currency']}")