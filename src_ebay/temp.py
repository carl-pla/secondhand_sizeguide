import requests
from get_new_token import get_new_token
import html2text

def get_articles_json():
    """
    Holt json mit Artikeln und zugehörigen Daten über Browse API.

    :return: json mit Artikeln und zugehörigen Daten
    """
    user_token = get_new_token()
    url = f"https://api.ebay.com/buy/browse/v1/item/v1|406708990037|0"

    # Achtung: Holt nicht die lange Artikelbeschreibung, die manchmal genauere Maße enthält. FIX!!!

    headers = {
        "Authorization": f"Bearer {user_token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
    }

    try:

        articles_raw = requests.get(url, headers=headers, timeout=(5, 30))

        # HTTP-Fehler prüfen (4xx, 5xx)
        articles_raw.raise_for_status()

        # JSON validieren: Prüft, ob Antwort valides JSON ist und in Python-Dict umformatiert werden kann
        data = articles_raw.json()

        # Zugriff auf die verfügbaren Größen in der Antwort (zum Debuggen oder für dynamische Menüs)
        if 'aspectDistributions' in data:
            print("\n--- Verfügbare Filterwerte (Aspects) ---")
            for aspect in data['aspectDistributions']:
                # Klarnamen der Merkmale ausgeben
                print(f"Merkmal: {aspect['localizedAspectName']} (ID: {aspect.get('aspectId', 'N/A')})")
                # Die ersten 3 verfügbaren Werte anzeigen
                for value in aspect['aspectValues'][:3]:
                    print(f"  - Wert: {value['localizedValue']} ({value['matchCount']} Treffer)")

        return data

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
res = get_articles_json()
text = str(res)

print(text)
# Zugriff auf die Treffer
if res and 'itemSummaries' in res:
    for item in res['itemSummaries']:
        print(f"Gefunden: {item['title']} - Preis: {item['price']['value']} {item['price']['currency']}")

def clean_description(html_content):
    # Initialisiere den Konverter
    converter = html2text.HTML2Text()

    # Konfiguration (wichtig für Datenanalyse)
    converter.ignore_links = True  # Links brauchen wir nicht für TF-IDF
    converter.ignore_images = True  # Bilder-URLs stören nur
    converter.bypass_tables = False  # Tabellen in Text umwandeln (oft wichtig bei Maßen)

    # Umwandlung
    markdown_text = converter.handle(html_content)

    return markdown_text.strip()

print(clean_description("""<div style="font-family: Helvetica,Verdana,sans-serif">
<ul style="list-style-type: none; padding: 0;">
<li><p><b>Marke:</b> Givenchy</p></li><li><p><b>Art:</b> T-shirt</p></li><li><p><b>Größe:</b> 80 - cm</p></li><li><p><b>Farbe:</b> Weiß, Orange</p></li><li><p><b>Material:</b> Baumwolle, Elasthan</p></li><li><p><b>Muster:</b> Print</p></li><li><p><b>Damen/Herren/Kinder :</b> Jungen</p></li><li><p><b>Zustand:</b> Akzeptabel</p></li>
</ul>
<h3>Zustandsinformationen</h3><ul style="list-style-type: none; padding: 0;">
<li><p><b>Fleck:</b> Vorderseite</p></li>
</ul>

<h3>Über Sellpy</h3>
<p>
Sellpy ist der Nr.1 Second Online Shop und Verkaufsservice. Wir verkaufen pre-loved Kleidung und andere Artikel
von Privatpersonen, nachdem wir sie auf Zustand, Qualität und Echtheit geprüft haben. Da wir im Auftrag von
privaten Verkäufern handeln, können wir keine Preisvorschläge akzeptieren. Der Versand der Waren erfolgt von
unseren Lagern in Polen und Schweden in 24 EU-Länder. Jeder angebotene Artikel ist ein Einzelstück und daher
nicht in anderen Größen, Farben o.ä. verfügbar. Wir bieten immer ein 30-tägiges Rückgaberecht an.
</p>
<h3>Zustand</h3>
<p>
Die Artikel werden in gebrauchtem Zustand verkauft. Wenn nicht anders angegeben, gehört zu einem Artikel nur,
was auf dem Bild erkennbar ist. Alle Artikel werden von uns in ihrem Zustand bewertet und beschrieben. Wir
können leider keine zusätzlichen Anfragen zu den Artikeln beantworten, da sich alle in einem Lager befinden.
</p>
<h3>Defekt</h3>
<p>
Sollte ein Artikel nicht fehlerfrei sein (z.B. Fleck oder Loch), wird dies deutlich in der Beschreibung
aufgeführt. Der Artikel kann deshalb nicht aufgrund des Defekts reklamiert werden.
</p>
<h3>Bezahlung</h3>
<p>
Wir bieten Zahlungen über PayPal, Visa, Mastercard, American Express oder Apple Pay an. Außerdem bieten wir
flexible Zahlungsmöglichkeiten über Klarna an, wie zum Beispiel Sofort bezahlen, Später bezahlen oder In Raten
zahlen.
</p>
<h3>Lieferung</h3>
<p>
Sobald die Zahlung bei uns eingegangen ist, wird die Ware sorgfältig verpackt und versendet. Wir bieten
Kombiversand für unsere Artikel an. Das heißt, für Artikel in einer Bestellung bezahlst du nur einmalig
Versandkosten. Sobald eine Bestellung getätigt und bezahlt wurde, können wir nachträglich keinen Kombiversand
anrechnen. Bitte beachte, dass Zustellung in eine Packstation nicht möglich ist.
</p>
<h3>Rückgabe &amp; Reklamation</h3>
<p>
Wir bieten ein Rückgaberecht von 30 Tagen. Du kannst eine Rücksendung einfach in deinem eBay-Konto unter
„Einzelheiten zum Kauf aufrufen” neben dem Artikel beauftragen. Klicke auf „Artikel zurückgeben” und wähle einen
Grund für die Rücksendung aus und schicke den Artikel an uns zurück. Bei Reklamationen melden wir uns an
Werktagen innerhalb von 24h bei dir.
</p>
<h4>ACHTUNG: Immer polnische Rücksendeadresse nutzen!</h4>
<p>Bitte nutze mit <b>jedem</b> Versanddienstleister folgende Rücksendeadresse:</p>
<p>
Sellhelp AB / Sellpy<br />
ul. Szkolna 96<br />
62-023 Robakowo<br />
Poland
</p>
<p>
<b>⚠️ Wichtig</b>: Schicke deine Rücksendungen niemals an die Adresse des Versandlabels deiner Bestellung. Dort
werden sie nicht angenommen und gehen kostenpflichtig an dich zurück.
</p>

</div>"""))
