import requests
from get_new_token import get_new_token

def get_articles_json(user_token=None):
    """
    Holt json mit Artikeln und zugehörigen Daten über Browse API.

    :param user_token: Der User-Token, der für GET-Request benötigt wird
    :return: json mit Artikeln und zugehörigen Daten
    """
    user_token = get_new_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE"
    }

    params = {
        "q": "lego",
        "limit": "10"
    }

    articles_raw = requests.get(url, headers=headers, params=params, timeout=30)

    if articles_raw.json()['errors'][0]['message'] == 'Invalid access token':
        user_token = get_new_token()
        articles_json = get_articles_json(user_token)

    else:
        articles_json = articles_raw.json()

    return articles_json

# timeout: maximale Wartezeit für Request, Rest ist selbsterklärend