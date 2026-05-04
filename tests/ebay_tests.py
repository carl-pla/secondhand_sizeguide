# ─────────────────────────────────────────────────────────────────────────────
# Allgemeine Imports
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock

# ─────────────────────────────────────────────────────────────────────────────
# Zu testende Funktionen importieren
# ─────────────────────────────────────────────────────────────────────────────

from src_ebay.ebay_helper import clean_description, extract_important_data
from src_ebay.get_new_token import get_new_token
from src_ebay.ebay_ids import old_token
from src_ebay.get_request import get_summary_of_articles_json, fetch_one_item, get_detailed_items_async


# ─────────────────────────────────────────────────────────────────────────────
# Reales Beispiel-JSON als Dictionary einlesen
# ─────────────────────────────────────────────────────────────────────────────

path_to_mock_json = os.path.join(os.path.dirname(__file__), "mock_item_ebay.json")

with open(path_to_mock_json, "r", encoding="utf-8") as mock_json:
    base_item = json.load(mock_json)

# ═════════════════════════════════════════════════════════════════════════════
# Tests: clean_description (ebay_helper.py)
# ═════════════════════════════════════════════════════════════════════════════

def test_clean_description_example():
    result = clean_description(base_item["description"])

    assert "Schone Freizeithose." in result
    assert "Nichtraucherhaushalt." in result
    assert "</p>" not in result
    assert "<br>" not in result

def test_clean_description_empty():
    result = clean_description("")

    assert result == ""

# ═════════════════════════════════════════════════════════════════════════════
# Tests: extract_important_data (ebay_helper.py)
# ═════════════════════════════════════════════════════════════════════════════

def test_extract_important_data_example():
    result = extract_important_data(base_item)

    assert result["marketplace"]        == "ebay"
    assert result["itemId"]             == "v1|388630721336|0"
    assert result["url"]                == "https://www.ebay.de/itm/388630721336"
    assert result["title"]              == "Bermuda Gr. 48"
    assert result["price"]              == "3.00 €"
    assert result["condition"]          == "Gebraucht - Gut"
    assert result["conditionId"]        == "3000"
    assert result["localizedAspects"]   == base_item["localizedAspects"]
    assert result["shortDescription"]   == base_item["shortDescription"]
    assert result["brand"]              == "markenlos"
    assert result["color"]              == "Blau"
    assert result["size"]               == "48"
    assert result["material"]           == "Baumwolle"
    assert isinstance(result["description"], str)


def test_extract_important_data_empty():
    result = extract_important_data({})

    assert result["itemId"]             == "Unbekannt"
    assert result["title"]              == "Unbekannt"
    assert result["price"]              == "Unbekannt €"
    assert result["brand"]              == "Unbekannt"
    assert result["localizedAspects"]   == []
    assert result["shortDescription"]   == "Unbekannt"
    assert result["description"]        == ""
    assert result["marketplace"]        == "ebay"

# ═════════════════════════════════════════════════════════════════════════════
# Tests: get_new_token (get_new_token.py)
# ═════════════════════════════════════════════════════════════════════════════

def test_get_new_token():
    result = get_new_token()
    assert isinstance(result, str)
    assert result.startswith("v^1.1#i^1#") # Token startet immer mit dieser Zeichenkette

# ═════════════════════════════════════════════════════════════════════════════
# Tests: get_summary_of_articles_json (get_request.py)
# ═════════════════════════════════════════════════════════════════════════════

def test_get_summary_of_articles_json_invalid_token():
    result = get_summary_of_articles_json(user_token=old_token)
    
    assert result == None

def test_get_summary_of_articles_json_valid_token():
    valid_token = get_new_token()

    result = get_summary_of_articles_json(user_token=valid_token)

    assert isinstance(result, set)
    assert all(item_id.startswith("v1") for item_id in result)  # alle Item-IDs starten mit "v1"
    assert all("|" in item_id for item_id in result)            # alle Item-IDs enthalten mindestens einmal "|"

# ═════════════════════════════════════════════════════════════════════════════
# Tests: fetch_one_item (get_new_token.py)
# ═════════════════════════════════════════════════════════════════════════════

def test_fetch_one_item_valid():
    mock_response = MagicMock()
    mock_response.json.return_value = base_item

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = asyncio.run(fetch_one_item(mock_client, "v1|388630721336|0"))

    assert result["itemId"]      == "v1|388630721336|0"
    assert result["marketplace"] == "ebay"
    assert isinstance(result["description"], str)

def test_fetch_one_item():
    mock_response = MagicMock()
    mock_response.json.return_value = {}

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = asyncio.run(fetch_one_item(mock_client, ""))

    assert result["itemId"]             == "Unbekannt"
    assert result["title"]              == "Unbekannt"
    assert result["price"]              == "Unbekannt €"
    assert result["brand"]              == "Unbekannt"
    assert result["localizedAspects"]   == []
    assert result["shortDescription"]   == "Unbekannt"
    assert result["description"]        == ""
    assert result["marketplace"]        == "ebay"

# ═════════════════════════════════════════════════════════════════════════════
# Tests: get_detailed_items_async (get_new_token.py)
# ═════════════════════════════════════════════════════════════════════════════

def test_get_detailed_items_async_empty_set():
    result = asyncio.run(get_detailed_items_async({}, get_new_token()))

    assert result == None

def test_get_detailed_items_async_():
    result = asyncio.run(get_detailed_items_async({"v1|389850879696|657119538592", "v1|236666629262|0", "v1|356858283565|0"}, get_new_token()))

    assert isinstance(result, list)
    assert len(result) == 3
    assert None not in result
    assert all(item["price"][-1] == "€" for item in result)



if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])