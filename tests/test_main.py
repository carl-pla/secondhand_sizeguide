"""
=== MATCHFIT – PYTEST SUITE ===
Abgedeckte Module:
  - main.py           → Validierungslogik (Pflichtfelder, Quellen)

"""

# ══════════════════════════════════════════════════════════════════
#  MAIN – Validierungslogik (ohne echtes Scraping)
# ══════════════════════════════════════════════════════════════════

import json
import pytest 
from unittest.mock import MagicMock, patch

from ai.ollama import analysiere_artikel
from database.scraping_sessions import speichere_in_mongo
from main import main


class TestMainValidierung:
    """
    Testet die Pflichtfeld-Validierung in main.py, ohne Playwright zu starten.
    main() gibt bei fehlenden Pflichtfeldern None zurück.
    """

    @pytest.mark.asyncio
    async def test_fehlende_groesse_bricht_ab(self, basis_config):
        """Ohne Größe darf der Scraper nicht starten."""
        basis_config["groesse"] = ""
        with patch("httpx.get"):  # Ollama-Check überspringen
            from main import main
            result = await main(basis_config)
        assert result is None

    @pytest.mark.asyncio
    async def test_fehlendes_modell_bricht_ab(self, basis_config):
        """Ohne Ollama-Modell darf der Scraper nicht starten."""
        basis_config["ollama_modell"] = ""
        with patch("httpx.get"):
            result = await main(basis_config)
        assert result is None

    @pytest.mark.asyncio
    async def test_fehlende_kategorie_bricht_ab(self, basis_config):
        """Ohne Kategorie darf der Scraper nicht starten."""
        basis_config["kategorie"] = ""
        with patch("httpx.get"):
            result = await main(basis_config)
        assert result is None

    @pytest.mark.asyncio
    async def test_ungueltige_quelle_bricht_ab(self, basis_config):
        """Quelle darf nur 'vinted' oder 'habilleur' sein."""
        basis_config["quelle"] = "ebay"
        with patch("httpx.get"):
            from main import main
            result = await main(basis_config)
        assert result is None

    @pytest.mark.asyncio
    async def test_ollama_nicht_erreichbar_bricht_ab(self, basis_config):
        """Wenn Ollama offline ist, soll main() sauber abbrechen."""
        with patch("httpx.get", side_effect=Exception("Connection refused")):
            from main import main
            result = await main(basis_config)
        assert result is None


# ══════════════════════════════════════════════════════════════════
#  INTEGRATIONS-TEST – Ollama → Analyse → Speicherung
# ══════════════════════════════════════════════════════════════════

class TestIntegration:

    @patch("database.scrapping_sessions.pymongo.MongoClient")
    def test_vollstaendiger_analyse_und_speicher_flow(
        self, mock_client_class, basis_artikel, basis_config, ollama_antwort_gut
    ):
        """
        End-to-end: Artikel analysieren → empfohlen → in DB speichern.
        Testet das Zusammenspiel von analysiere_artikel() und speichere_in_mongo().
        """
        mock_col = MagicMock()
        mock_client_class.return_value.__getitem__.return_value.__getitem__.return_value = mock_col

        # 1. Analyse
        with patch("ai.ollama.frage_ollama", return_value=ollama_antwort_gut):
            analysiert = analysiere_artikel(basis_artikel, basis_config)

        assert analysiert["empfohlen"] is True

        # 2. Speicherung
        speichere_in_mongo([analysiert], basis_config, "test@example.com")

        mock_col.insert_one.assert_called_once()
        session = mock_col.insert_one.call_args[0][0]
        assert session["anzahl_empfohlen"] == 1
        assert session["empfehlungen"][0]["titel"] == basis_artikel["titel"]
