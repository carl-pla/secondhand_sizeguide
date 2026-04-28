import html2text

def clean_description(html_content):
    """
    Konvertiert HTML-Text in einfachen Markdown-Text ohne Brackets.

    :param html_content: Artikelbeschreibung in HTML-Format
    :return: Artikelbeschreibung in Markdown-Format
    """
    # Falls Beschreibung nicht gefunden wird
    if not html_content:
        return ""

    converter = html2text.HTML2Text()

    converter.ignore_links = True  # Links entfernen
    converter.ignore_images = True  # Bilder-URLs entfernen
    converter.bypass_tables = False  # Tabellen in Text umwandeln

    # Umwandlung
    markdown_text = converter.handle(html_content)
    markdown_text = markdown_text.replace("\n", " ")

    return markdown_text.strip()


def extract_important_data(single_json):
    """
    Extrahiert nur die für den Prompt benötigten Daten über einen einzelnen Artikel.

    :param single_json: dict mit detaillierten Informationen über einen Artikel
    :return: dict mit nur relevanten Informationen über den Artikel.
    """
    raw_aspects = {aspect['name']: aspect['value'] for aspect in single_json.get("localizedAspects", [])}

    clean_item = {
        "marketplace": "ebay",
        "itemId": single_json.get("itemId", "Unbekannt"),
        "title": single_json.get("title", "Unbekannt"),
        "price": single_json.get("price", {}).get("value" + ", €", "Unbekannt"),
        "condition": single_json.get("condition", "Unbekannt"),

        "brand": raw_aspects.get("Marke", "Unbekannt"),
        "color": raw_aspects.get("Farbe", "Unbekannt"),
        "size": raw_aspects.get("Größe", "Unbekannt"),
        "material": raw_aspects.get("Material", "Unbekannt"),
        "description": clean_description(single_json.get("description", ""))
        # description wird als HTML zurückgegeben, muss noch für LLM zu Markdown konvertiert werden
    }

    return clean_item