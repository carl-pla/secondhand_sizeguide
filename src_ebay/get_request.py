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
        "Herren Sportartikel": "185099",  # Fitnessmode
        "Herren Hosen": "57989",
        "Herren Jacken & Mäntel": "57988",  # Jacken, Mäntel und Westen
        "Herren Jeans": "11483",
        "Herren Nachtwäsche": "11510",
        "Herren Pullover & Sweater": "11484",  # Pullover und Strick
        "Herren Tops & T-Shirts": "185100",  # Shirts und Hemden
        "Herren Shorts": "15689",  # Shorts und Bermudas
        "Herren Socken & Unterwäsche": "11507",  # nur Unterwäsche, da nur eine ID gegeben werden kann
        "Herren Stiefel": "11498",
        "Herren Elegante Schuhe": "53120",  # Business-Schuhe
        "Herren Sneaker": "15709",
        "Herren Loafer & Bootsschuhe": "24087",  # Halbschuhe
        "Herren Kopftücher": "52365",  # Hüte und Mützen
        "Herren Halstücher": "52382",  # Schals & Tücher
        "Herren Krawatten": "15662",  # Krawatten & Fliegen
        "Herren Gürtel": "2993",
        "Herren Handschuhe": "2994",  # Handschuhe und Fäustlinge
        "Herren Taschen": "52357",
        "Herren Schmuck": "10290",
        "Herren Uhren": "260325",  # Armbanduhren & Taschenuhren

        "Damen Alles": "260010",
        "Damen Pullover & Strickpullover": "63866",
        "Damen Kleider": "63861",
        "Damen Skorts": "63864",  # Röcke
        "Damen Jeans": "11554",
        "Damen Shorts": "11555",  # Shorts & Bermudas
        "Damen Bademode": "63867",
        "Damen Jacken & Mäntel": "63862",  # Jacken, Mäntel und Westen
        "Damen Anzüge & Blaze": "63865",  # Anzüge & Anzugteile
        "Damen Röcke": "63864",
        "Damen Tops & T-Shirts": "53159",  # Blusen, Tops & Shirts
        "Damen Hosen & Leggings": "169001",
        "Damen Unterwäsche & Nachtwäsche": "11514",
        "Damen Ballerinas": "45333",  # Halbschuhe & Ballerinas
        "Damen Stiefel": "53557",  # Stiefel & Stiefeletten
        "Damen Absatzschuhe": "55793",
        "Damen Hausschuhe, Pantoffeln & Slipper": "11632",  # Hausschuhe
        "Damen Sneaker": "95672",
        "Damen Bootsschuhe & Loafer": "45333",  # Halbschuhe & Ballerinas
        "Damen Sandalen": "62107",
        "Damen Taschen": "169291",
        "Damen Tücher & Schals": "45238",  # Schals & Tücher
        "Damen Kopftücher": "45238",  # Schals & Tücher
        "Damen Hüte und Mützen": "45230",
        "Damen Handschuhe": "105559",  # Handschuhe & Fäustlinge
        "Damen Schmuck": "10968",  # Modeschmuck (darf immer nur eine ID gegeben werden)
        "Damen Uhren": "260325",  # Armbanduhren & Taschenuhren
        "Damen Haarschmuck": "168998",  # Kopfschmuck & Fascinators
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


def get_single_item_details_and_validate(item_ids):
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

    try:
        set_of_single_jsons = set()

        for item_id in item_ids:
            url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"

            item_raw = requests.get(url, headers=headers, timeout=(5, 30))

            # HTTP-Fehler prüfen (4xx, 5xx)
            item_raw.raise_for_status()

            # JSON validieren: Prüft, ob Antwort valides JSON ist und in Python-Dict umformatiert werden kann
            single_json = item_raw.json()

            set_of_single_jsons.add(single_json)

        return set_of_single_jsons

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
res, piece_ids = get_summary_of_articles_json(sort_type="-", brand="Givenchy", max_price=10)
print(res)

print(piece_ids)

with open("single_item_details.json", encoding="utf-8", mode="w") as sidjson:
    sidjson.write(str(get_single_item_details_and_validate(piece_ids)))

# Zugriff auf die Treffer
if res and 'itemSummaries' in res:
    for item in res['itemSummaries']:
        print(f"Gefunden: {item['title']} - Preis: {item['price']['value']} {item['price']['currency']}")