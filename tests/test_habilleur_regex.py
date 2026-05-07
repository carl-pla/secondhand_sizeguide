"""
=== TEST HABILLEUR REGEX ===

Tests für die Regex-basierte Maß-Extraktion aus Habilleur Jean Beschreibungen.
Die extract_measurements_habilleur() Funktion wird mit verschiedenen 
Input-Formaten (Deutsch, Französisch, Englisch) getestet.
"""

import pytest
from ai.habilleur_regex import extract_measurements_habilleur


class TestExtractMeasurementsHabilleurBasics:
    """Grundlegende Tests für Maß-Extraktion."""
    
    def test_extract_all_measures_deutsch(self, habilleur_beschreibung_deutsch):
        """Test: Alle Maße aus deutscher Beschreibung extrahieren."""
        result = extract_measurements_habilleur(habilleur_beschreibung_deutsch)
        
        # Alle Maße sollten vorhanden sein
        assert "schulterbreite" in result
        assert "aermellaenge" in result
        assert "jackenlaenge" in result
        assert "achselbreite" in result
        assert "jacke_taillenweite" in result
        assert "hose_taillenweite" in result
        assert "gabelhoehe" in result
        assert "beinoeffnung" in result
        assert "hosenlaenge" in result
        
        # Werte überprüfen
        assert result["schulterbreite"] == 44
        assert result["jackenlaenge"] == 72
        assert result["achselbreite"] == 52
        assert result["gabelhoehe"] == 29
        assert result["beinoeffnung"] == 24
    
    def test_extract_with_addition_deutsch(self, habilleur_beschreibung_deutsch):
        """Test: Maße mit Addition (X cm + Y cm) werden richtig verrechnet."""
        result = extract_measurements_habilleur(habilleur_beschreibung_deutsch)
        
        # Ärmellänge: 58 cm + 3 cm = 61 cm
        assert result["aermellaenge"] == 61
        
        # Taillenweite Hose: 44 cm + 3 cm = 47 cm
        assert result["hose_taillenweite"] == 47
        
        # Hosenlänge: 98 cm + 10 cm = 108 cm
        assert result["hosenlaenge"] == 108
    
    def test_extract_french_descriptions(self, habilleur_beschreibung_franzoesisch):
        """Test: Französische Beschreibungen werden erkannt."""
        result = extract_measurements_habilleur(habilleur_beschreibung_franzoesisch)
        
        # Französische Bezeichnungen müssen erkannt werden
        assert "schulterbreite" in result  # Largeur épaule
        assert "aermellaenge" in result    # Longueur manche
        assert "jackenlaenge" in result    # Longueur veste
        assert "achselbreite" in result    # Largeur aisselle
        assert "gabelhoehe" in result      # Hauteur de fourche
        assert "beinoeffnung" in result    # Ouverture de jambe
        
        # Werte validieren
        assert result["schulterbreite"] == 44
        assert result["jackenlaenge"] == 72
        assert result["gabelhoehe"] == 28
        assert result["beinoeffnung"] == 22
        
        # Addition für Französisch: 63 + 3 = 66
        assert result["aermellaenge"] == 66
        # Addition: 98 + 7 = 105
        assert result["hosenlaenge"] == 105
    
    def test_extract_english_descriptions(self, habilleur_beschreibung_englisch):
        """Test: Englische Beschreibungen werden erkannt."""
        result = extract_measurements_habilleur(habilleur_beschreibung_englisch)
        
        # Englische Bezeichnungen
        assert "schulterbreite" in result  # shoulder width
        assert "aermellaenge" in result    # sleeve length
        assert "jackenlaenge" in result    # jacket length
        assert "achselbreite" in result    # armpit width
        assert "gabelhoehe" in result      # rise
        assert "beinoeffnung" in result    # leg opening
        
        # Werte validieren
        assert result["schulterbreite"] == 46
        assert result["jackenlaenge"] == 74
        assert result["achselbreite"] == 54
        assert result["gabelhoehe"] == 30


class TestExtractMeasurementsHabilleurAddition:
    """Tests für Addition von Maßen (X cm + Y cm → X+Y)."""
    
    def test_addition_simple(self):
        """Test: Einfache Addition wird erkannt."""
        desc = "Ärmellänge: 60 cm + 2 cm"
        result = extract_measurements_habilleur(desc)
        assert result["aermellaenge"] == 62
    
    def test_addition_with_spaces(self):
        """Test: Addition mit verschiedenen Abstände."""
        desc = "Hosenlänge: 98 cm+5cm"
        result = extract_measurements_habilleur(desc)
        assert result["hosenlaenge"] == 103
    
    def test_addition_large_numbers(self):
        """Test: Addition mit größeren Zahlen."""
        desc = "Hosenlänge: 108 cm + 12 cm"
        result = extract_measurements_habilleur(desc)
        assert result["hosenlaenge"] == 120
    
    def test_no_addition_single_value(self):
        """Test: Einzelne Werte ohne Addition."""
        desc = "Schulterbreite: 44 cm"
        result = extract_measurements_habilleur(desc)
        assert result["schulterbreite"] == 44


class TestExtractMeasurementsHabilleurIncompleteness:
    """Tests für unvollständige Beschreibungen."""
    
    def test_partial_measures(self, habilleur_beschreibung_unvollstaendig):
        """Test: Nur vorhandene Maße werden extrahiert."""
        result = extract_measurements_habilleur(habilleur_beschreibung_unvollstaendig)
        
        # Vorhandene Maße
        assert result["schulterbreite"] == 44
        assert result["aermellaenge"] == 61  # 58 + 3
        assert result["gabelhoehe"] == 29
        
        # Fehlende Maße sollten NICHT in result sein
        assert "jackenlaenge" not in result
        assert "achselbreite" not in result
        assert "beinoeffnung" not in result
    
    def test_empty_description(self):
        """Test: Leere Beschreibung."""
        result = extract_measurements_habilleur("")
        assert result == {}
    
    def test_description_without_measures(self):
        """Test: Text ohne Maße."""
        desc = "Schöner Anzug, Vintage Zustand, kaum getragen."
        result = extract_measurements_habilleur(desc)
        assert result == {}


class TestExtractMeasurementsHabilleurCaseInsensitivity:
    """Tests für case-insensitive Matching."""
    
    def test_uppercase_labels(self):
        """Test: Labels in Großbuchstaben."""
        desc = "SCHULTERBREITE: 44 cm"
        result = extract_measurements_habilleur(desc)
        assert result["schulterbreite"] == 44
    
    def test_mixed_case_labels(self):
        """Test: Labels mit Mischung aus Groß-/Kleinbuchstaben."""
        desc = "SchulterBreite: 46 cm"
        result = extract_measurements_habilleur(desc)
        assert result["schulterbreite"] == 46
    
    def test_alternative_spellings(self):
        """Test: Alternative Schreibweisen (z.B. Armlaenge statt Ärmellänge)."""
        desc = "Armlaenge: 62 cm"
        result = extract_measurements_habilleur(desc)
        assert result["aermellaenge"] == 62


class TestExtractMeasurementsHabilleurJacketVsTrousers:
    """Tests für Unterscheidung zwischen Jacken- und Hosenmaßen."""
    
    def test_jacket_section_taillenweite(self):
        """Test: Erste Taillenweite (Jacke) wird vor Hosensektion extrahiert."""
        desc = """
        Maße der Jacke:
        Schulterbreite: 44 cm
        Taillenweite: 50 cm
        
        Hosenmaße:
        Taillenweite: 48 cm
        Gabelhöhe: 30 cm
        """
        result = extract_measurements_habilleur(desc)
        
        # Jacke Taillenweite (erste)
        assert result["jacke_taillenweite"] == 50
        # Hose Taillenweite (zweite)
        assert result["hose_taillenweite"] == 48
    
    def test_trouser_section_detection(self):
        """Test: Hosensektion wird richtig erkannt."""
        desc = """
        Jackenlänge: 75 cm
        
        Hosenmaße:
        Hosenlänge: 110 cm
        Gabelhöhe: 30 cm
        """
        result = extract_measurements_habilleur(desc)
        
        assert result["hosenlaenge"] == 110
        assert result["gabelhoehe"] == 30


class TestExtractMeasurementsHabilleurRealWorldExamples:
    """Tests mit realistischen Beispielen."""
    
    def test_habilleur_article(self, habilleur_artikel):
        """Test: Realer Habilleur-Artikel."""
        result = extract_measurements_habilleur(habilleur_artikel["beschreibung"])
        
        # Alle wichtigen Maße sollten vorhanden sein
        assert result["schulterbreite"] == 46
        assert result["aermellaenge"] == 67  # 65 + 2
        assert result["jackenlaenge"] == 75
        assert result["achselbreite"] == 55
        assert result["gabelhoehe"] == 30
        assert result["hosenlaenge"] == 110  # 108 + 2
    
    def test_complete_anzug_description(self):
        """Test: Komplette Anzugbeschreibung mit allen Maßen."""
        desc = """
        Habilleur Jean Anzug Größe M
        
        Maße der Jacke:
        Schulterbreite: 44 cm
        Ärmellänge: 58 cm + 3 cm
        Jackenlänge: 72 cm
        Achselbreite: 52 cm
        Taillenweite: 50 cm
        
        Hosenmaße:
        Taillenweite: 48 cm + 1 cm
        Gabelhöhe: 29 cm
        Beinöffnung: 24 cm
        Hosenlänge: 98 cm + 8 cm
        """
        result = extract_measurements_habilleur(desc)
        
        # Jacke
        assert result["schulterbreite"] == 44
        assert result["aermellaenge"] == 61
        assert result["jackenlaenge"] == 72
        assert result["achselbreite"] == 52
        assert result["jacke_taillenweite"] == 50
        
        # Hose
        assert result["hose_taillenweite"] == 49
        assert result["gabelhoehe"] == 29
        assert result["beinoeffnung"] == 24
        assert result["hosenlaenge"] == 106


class TestExtractMeasurementsHabilleurEdgeCases:
    """Tests für Edge Cases und Fehlerbehandlung."""
    
    def test_malformed_measurement(self):
        """Test: Falsch formatierte Maße werden ignoriert."""
        desc = "Schulterbreite: abc cm"
        result = extract_measurements_habilleur(desc)
        assert "schulterbreite" not in result
    
    def test_measurement_without_unit(self):
        """Test: Maße ohne Einheit werden erkannt."""
        desc = "Schulterbreite: 44 cm"
        result = extract_measurements_habilleur(desc)
        assert result["schulterbreite"] == 44
    
    def test_extra_whitespace(self):
        """Test: Extra Whitespace wird korrekt behandelt."""
        desc = "Schulterbreite   :   44   cm"
        result = extract_measurements_habilleur(desc)
        assert result["schulterbreite"] == 44
    
    def test_special_characters_in_description(self):
        """Test: Spezialzeichen in der Beschreibung behindern nicht."""
        desc = "Schulterbreite (gemessen): 44 cm | Ärmellänge: 60 cm"
        result = extract_measurements_habilleur(desc)
        assert result["schulterbreite"] == 44
        # Ärmellänge ohne Addition
        assert result["aermellaenge"] == 60

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])