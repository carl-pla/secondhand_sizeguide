import base64
import requests
from ebay_ids import app_id, cert_id


def get_new_token(client_id=app_id, client_secret=cert_id):
    """
    Holt mithilfe von Client-ID und -Secret einen neuen User-Token für die Artikelsuche.

    :param client_id: Client ID von eBay Production Keyset
    :param client_secret: Client Secret von eBay Production Keyset
    :return: neuer User-Token, mit dem Browse API genutzt werden kann
    """

    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {auth_header}"
    }

    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }

    response = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers=headers,
        data=data
    )

    token = response.json()["access_token"]
    return token