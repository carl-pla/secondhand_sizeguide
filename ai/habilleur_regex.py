"""
Regex-basierte Vorextrak tion für kritische Habilleur-Maße
"""
import re


def extract_measurements_habilleur(beschreibung: str) -> dict:
    """
    Extrahiert kritische Maße aus der Beschreibung mit Regex BEVOR das LLM sie sieht.
    
    Dies ist ein Pre-Processing-Schritt, um sicherzustellen, dass wichtige Maße
    nicht vom LLM übersehen werden.
    
    Returns:
        Dict mit extrahierten Maßen: {"schulterbreite": 44, "aermellaenge": 61, ...}
    """
    measurements = {}
    
    # Pattern für "X cm + Y cm" → X + Y
    def parse_measurement_with_addition(text):
        """Parse 'X cm + Y cm' → X + Y"""
        match = re.search(r'(\d+)\s*cm\s*\+\s*(\d+)\s*cm', text)
        if match:
            return int(match.group(1)) + int(match.group(2))
        match = re.search(r'(\d+)\s*cm', text)
        if match:
            return int(match.group(1))
        return None
    
    # 1. SCHULTERBREITE
    # Deutsch: "Schulterbreite (gemessen...): 44 cm"
    # Französisch: "Largeur épaule: 44 cm"
    # Englisch: "shoulder width: 44 cm"
    pattern = r'(?:Schulterbreite|Largeur\s*épaule|shoulder\s*width)\s*(?:\([^)]*\))?\s*[\s:]*(\d+)\s*cm'
    match = re.search(pattern, beschreibung, re.IGNORECASE)
    if match:
        measurements["schulterbreite"] = int(match.group(1))
    
    # 2. ÄRMELLÄNGE (mit Addition!)
    # Deutsch: "Ärmellänge: 58 cm + 3 cm"
    # Französisch: "Longueur manche: 63cm +3 cm"
    # Englisch: "sleeve length: 58 cm + 3 cm"
    pattern = r'(?:Ärmellänge|Armlaenge|Longueur\s*manche|sleeve\s*length)[\s:]*(\d+\s*cm(?:\s*\+\s*\d+\s*cm)?)'
    match = re.search(pattern, beschreibung, re.IGNORECASE)
    if match:
        value = parse_measurement_with_addition(match.group(1))
        if value:
            measurements["aermellaenge"] = value
    
    # 3. JACKENLÄNGE
    # Deutsch: "Jackenlänge: 72 cm"
    # Französisch: "Longueur veste: 74cm"
    # Englisch: "jacket length: 72 cm"
    pattern = r'(?:Jackenlänge|Jacken\s*Länge|Longueur\s*veste|jacket\s*length)[\s:]*(\d+)\s*cm'
    match = re.search(pattern, beschreibung, re.IGNORECASE)
    if match:
        measurements["jackenlaenge"] = int(match.group(1))
    
    # 4. ACHSELBREITE
    # Deutsch: "Achselbreite: 52 cm"
    # Französisch: "Largeur aisselle: 53cm"
    # Englisch: "armpit width / chest width: 52 cm"
    pattern = r'(?:Achselbreite|Largeur\s*aisselle|armpit\s*width|chest\s*width)[\s:]*(\d+)\s*cm'
    match = re.search(pattern, beschreibung, re.IGNORECASE)
    if match:
        measurements["achselbreite"] = int(match.group(1))
    
    # 5. TAILLENWEITE (JACKE)
    # Deutsch: "Taillenweite: 52 cm"
    # Französisch: "Largeur taille: 50cm" (ERSTES Vorkommen)
    # Finde die Jacket-Sektion und nimm die ERSTE Taillenweite darin
    jacket_section = re.search(
        r'(?:Schulterbreite|Largeur\s*épaule)(.*?)(?:Hosenmaße|Mesure du pantalon|Hauteur de fourche)',
        beschreibung, re.IGNORECASE | re.DOTALL
    )
    if jacket_section:
        section_text = jacket_section.group(1)
        pattern = r'(?:Taillenweite|Largeur\s+taille)[\s:]*(\d+)\s*cm'
        match = re.search(pattern, section_text, re.IGNORECASE)
        if match:
            measurements["jacke_taillenweite"] = int(match.group(1))
    
    # 6. TAILLENWEITE (HOSE)
    # Deutsch: "Taillenweite: 44 cm + 3 cm" (in Hosenmaße)
    # Französisch: "Largeur au niveau de la taille: 45cm"
    trouser_section = re.search(
        r'(?:Hosenmaße|Mesure du pantalon|Hauteur de fourche)(.*?)(?=$)',
        beschreibung, re.IGNORECASE | re.DOTALL
    )
    if trouser_section:
        section_text = trouser_section.group(1)
        # Suche entweder nach "Largeur au niveau" oder nach dem zweiten "Taillenweite"
        pattern = r'(?:Largeur\s+au\s+niveau\s+de\s+la\s+taille|Taillenweite)[\s:]*(\d+\s*cm(?:\s*\+\s*\d+\s*cm)?)'
        match = re.search(pattern, section_text, re.IGNORECASE)
        if match:
            value = parse_measurement_with_addition(match.group(1))
            if value:
                measurements["hose_taillenweite"] = value
    
    # 7. GABELHÖHE
    # Deutsch: "Gabelhöhe: 29 cm"
    # Französisch: "Hauteur de fourche: 28cm"
    # Englisch: "rise / inseam: 29 cm"
    pattern = r'(?:Gabelhöhe|Hauteur\s*de\s*fourche|Schritthoehe|rise|inseam)[\s:]*(\d+)\s*cm'
    match = re.search(pattern, beschreibung, re.IGNORECASE)
    if match:
        measurements["gabelhoehe"] = int(match.group(1))
    
    # 8. BEINÖFFNUNG
    # Deutsch: "Beinöffnung: 24 cm"
    # Französisch: "Ouverture de jambe: 22cm"
    # Englisch: "leg opening: 24 cm"
    pattern = r'(?:Beinöffnung|Ouverture\s*de\s*jambe|leg\s*opening)[\s:]*(\d+)\s*cm'
    match = re.search(pattern, beschreibung, re.IGNORECASE)
    if match:
        measurements["beinoeffnung"] = int(match.group(1))
    
    # 9. HOSENLÄNGE (mit Addition!)
    # Deutsch: "Hosenlänge: 98 cm + 10 cm"
    # Französisch: "Longueur du pantalon: 98 cm +7cm"
    # Englisch: "trouser length: 98 cm + 10 cm"
    pattern = r'(?:Hosenlänge|Longueur\s*du\s*pantalon|trouser\s*length)[\s:]*(\d+\s*cm(?:\s*\+\s*\d+\s*cm)?)'
    match = re.search(pattern, beschreibung, re.IGNORECASE)
    if match:
        value = parse_measurement_with_addition(match.group(1))
        if value:
            measurements["hosenlaenge"] = value
    
    return measurements


if __name__ == "__main__":
    # Test
    test_desc = """
    Maße der Jacke:
    Schulterbreite (gemessen über die Rückseite der Jacke, Naht zu Naht): 44 cm
    Ärmellänge: 58 cm + 3 cm zur Erweiterung
    Jackenlänge: 72 cm
    Achselbreite: 52 cm
    Taillenweite: 52 cm
    
    Hosenmaße:
    Taillenweite: 44 cm + 3 cm
    Gabelhöhe: 29 cm
    Beinöffnung: 24 cm
    Hosenlänge: 98 cm + 10 cm
    """
    
    result = extract_measurements_habilleur(test_desc)
    print("Extracted measurements:")
    for key, value in result.items():
        print(f"  {key}: {value}")
