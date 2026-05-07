import json
from pathlib import Path
import sys, os
import subprocess
import httpx # type: ignore 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st # type: ignore 
from database.users import registriere_user 
from database.users import deaktiviere_user

# Fügt den Projekt-Hauptordner zum Pfad hinzu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.config_defaults import (
    VINTED_GROESSEN, VINTED_KATEGORIEN, HABILLEUR_GROESSEN, HABILLEUR_KATEGORIEN, HABILLEUR_MASSE_BEISPIEL,
    EBAY_GROESSEN, EBAY_MATERIALS, OLLAMA_MODELLE, STIL_OPTIONEN, ZUSTAND_RANG, CONFIG_FILE, ERGEBNISSE_FILE, ZUSTAND_OPTIONEN,
    speichere_config, lade_config, CATEGORY_IDS_EBAY, CONDITION_IDS_EBAY, EBAY_FARBEN
)


# ─────────────────────────────────────────────
#  SEITEN-KONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MatchFit",
    page_icon="docs/logo_matchfit.png", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
#  STYLING
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Playfair+Display:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
}
h1, h2, h3 { font-family: 'Playfair Display', serif; }

.stApp { background: #0f0e0c; color: #e8e4dc; }

section[data-testid="stSidebar"] {
    background: #1a1815;
    border-right: 1px solid #2e2b26;
}

.metric-card {
    background: #1a1815;
    border: 1px solid #2e2b26;
    border-radius: 4px;
    padding: 1.2rem;
    margin-bottom: 0.8rem;
}
.metric-label { color: #8a8478; font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; }
.metric-value { color: #e8c97e; font-size: 1.6rem; font-weight: 500; margin-top: 0.2rem; }

.artikel-card {
    background: #1a1815;
    border: 1px solid #2e2b26;
    border-left: 3px solid #e8c97e;
    border-radius: 4px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}
.artikel-card:hover { border-left-color: #f0d896; }
.artikel-titel { font-family: 'Playfair Display', serif; font-size: 1.1rem; color: #e8e4dc; }
.artikel-preis { color: #e8c97e; font-size: 0.9rem; margin: 0.3rem 0; }
.artikel-bewertung { color: #8a8478; font-size: 0.75rem; }
.badge {
    display: inline-block;
    background: #2e2b26;
    color: #e8c97e;
    padding: 2px 10px;
    border-radius: 2px;
    font-size: 0.7rem;
    margin: 2px;
    letter-spacing: 0.05em;
}
.masse-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 0.8rem;
}
.masse-item {
    background: #0f0e0c;
    padding: 8px;
    border-radius: 3px;
    text-align: center;
}
.masse-key { color: #8a8478; font-size: 0.65rem; text-transform: uppercase; }
.masse-val { color: #e8e4dc; font-size: 0.9rem; margin-top: 2px; }

.status-ok { color: #7ec8a0; }
.status-warn { color: #e8c97e; }
.status-err { color: #e87e7e; }

div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] select,
textarea {
    background: #1a1815 !important;
    border: 1px solid #2e2b26 !important;
    color: #e8e4dc !important;
    border-radius: 3px !important;
    font-family: 'DM Mono', monospace !important;
}
.stSlider > div > div { background: #2e2b26; }
.stButton > button {
    background: #e8c97e;
    color: #0f0e0c;
    border: none;
    border-radius: 3px;
    font-family: 'DM Mono', monospace;
    font-weight: 500;
    letter-spacing: 0.05em;
    padding: 0.5rem 1.5rem;
}
.stButton > button:hover { background: #f0d896; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  STATE
# ─────────────────────────────────────────────
if "config" not in st.session_state:
    st.session_state.config = lade_config()

# Jede Änderung direkt in session_state schreiben:
config = st.session_state.config

# ─────────────────────────────────────────────
#  SIDEBAR – NAVIGATION
# ─────────────────────────────────────────────
with st.sidebar:

    # Pfad zum Logo (sehr sauber lesbar)
    logo_path ="docs/logo_matchfit.png"

    st.image(logo_path, width=180)
    st.markdown(
        "<h1 style='text-align:center; margin-top:-10px; margin-right: 60px; '>MatchFit</h1>",
        unsafe_allow_html=True
    )
    st.divider()
    seite = st.radio(
        "",
        ["🛍️  Vinted", "👔  Habilleur", "🛒  eBay", "🦿 Ollama", "🔍  Suche starten", "📋  Ergebnisse", "📧  Newsletter"],
        label_visibility="collapsed"
    )
    st.markdown("---")

    # Ollama Status
    try:
        ollama_base_url = config["ollama_url"].rstrip("/").rsplit("/api", 1)[0]
        httpx.get(ollama_base_url, timeout=2)
        st.markdown('<span class="status-ok">● Ollama online</span>', unsafe_allow_html=True)
    except:
        st.markdown('<span class="status-err">● Ollama offline</span>', unsafe_allow_html=True)

    


# ═══════════════════════════════════════════════
#  SEITE: VINTED
# ═══════════════════════════════════════════════
if "Vinted" in seite:
    st.markdown("# ⚙️ Vinted Einstellungen")
    st.markdown("Konfiguriere deine Vinted-Präferenzen.")
    st.markdown("---")

    # Setze Quelle auf Vinted
    st.session_state.config["quelle"] = "vinted"
    
    # Konvertiere Größe zu Vinted-Format falls nötig
    aktuelle_groesse = st.session_state.config.get("groesse", "M / 38")
    if " / " not in str(aktuelle_groesse):  # Habilleur-Format "M" → "M / 38"
        # Versuche eine Vinted-Größe zu finden, die mit dem Buchstaben beginnt
        for vinted_size in VINTED_GROESSEN.keys():
            if vinted_size.startswith(str(aktuelle_groesse)):
                aktuelle_groesse = vinted_size
                break
        else:
            aktuelle_groesse = "M / 38"  # Fallback
    if aktuelle_groesse not in VINTED_GROESSEN.keys():
        aktuelle_groesse = "M / 38"
    st.session_state.config["groesse"] = aktuelle_groesse

    tab1, tab2, tab3 = st.tabs(["👗  Größe, Kategorie & Stil", "📐  Maße", "🔍  Suche"])

    # ── TAB 1: Stil & Größe ──
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.config["groesse"] = st.selectbox(
                "Kleidungsgröße (Vinted)",
                list(VINTED_GROESSEN.keys()),
                index=list(VINTED_GROESSEN.keys()).index(st.session_state.config["groesse"])
            )
            st.session_state.config["kategorie"] = st.selectbox(
                "Kategorie (Vinted)",
                list(VINTED_KATEGORIEN.keys()),
                index=list(VINTED_KATEGORIEN.keys()).index(
                    st.session_state.config.get("kategorie", "Herren Jacken & Mäntel") if st.session_state.config.get("kategorie") in VINTED_KATEGORIEN.keys() else "Herren Jacken & Mäntel"
                )
            )
            st.session_state.config["stile"] = st.multiselect(
                "Bevorzugte Stile (Suchbegriffe)",
                STIL_OPTIONEN,                
                default=st.session_state.config.get("stile", ["Vintage"])
            )
            
        with col2:
            st.session_state.config["max_preis"] = st.slider(
                "Maximaler Preis (€)", 5, 200,
                st.session_state.config.get("max_preis", 50), step=5
            )
            st.session_state.config["min_zustand"] = st.selectbox(
                "Mindest-Zustand",
                ZUSTAND_RANG,
                index=ZUSTAND_OPTIONEN.index(
                    st.session_state.config.get("min_zustand", "Gut")
                )
            )

    # ── TAB 2: Maße ──
    with tab2:
        st.markdown("Trage deine Maße ein – das LLM vergleicht sie mit den Angaben in der Beschreibung.")
        masse = st.session_state.config.get("eigene_masse", {})
        col1, col2 = st.columns(2)
        with col1:
            masse["brust"]            = st.number_input("Brustumfang (cm)",             60, 130, masse.get("brust", 88))
            masse["taille"]           = st.number_input("Taillenumfang (cm)",          50, 120, masse.get("taille", 70))
            masse["huefte"]           = st.number_input("Hüftumfang (cm)",             70, 140, masse.get("huefte", 96))
            masse["schulter"]         = st.number_input("Schulterbreite (cm)",         30, 60,  masse.get("schulter", 38))
            masse["gabelhoehe"]       = st.number_input("Gabelhöhe/Rise (cm)",         20, 40,  masse.get("gabelhoehe", 28))
        with col2:
            masse["laenge_oberteil"]  = st.number_input("Bevorzugte Länge Top/Jacke (cm)", 40, 100, masse.get("laenge_oberteil", 60))
            masse["laenge_hosen"]     = st.number_input("Bevorzugte Länge Hose (cm)",      80, 120, masse.get("laenge_hosen", 100))
            masse["innennaht"]        = st.number_input("Innennaht / Schrittlänge (cm)",   60, 100, masse.get("innennaht", 78))
            masse["aermellaenge"]     = st.number_input("Ärmellänge (cm)",                 50, 75,  masse.get("aermellaenge", 62))
            masse["beinoeffnung"]     = st.number_input("Beinöffnung/Hosenbein (cm)", 18, 32,  masse.get("beinoeffnung", 24))
        
        st.session_state.config["eigene_masse"] = masse

    # ── TAB 3: Suche ──
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            user_email = st.text_input("E-Mail (optional)", value=st.session_state.config.get("user_email", ""))
            if user_email:
                st.session_state.config["user_email"] = user_email
        with col2:
            max_artikel = st.session_state.config.get("max_artikel_pro_suche", 20)
            # wir wollen nicht sehr hohe Suchanzahlen erlauben, weil das sehr lange dauert (bei eBay durch get-request schneller)
            if max_artikel > 60:
                max_artikel = 60
            st.session_state.config["max_artikel_pro_suche"] = st.slider(
                "Artikel pro Suchbegriff", 1, 60,
                st.session_state.config.get("max_artikel_pro_suche", 5)
            )
            
        st.markdown("**Anti-Ban Pausen (Sekunden)**")
        col1, col2 = st.columns(2)
        with col1:
            p_art = st.slider(
                "Pause zwischen Artikeln", 1, 15,
                tuple(st.session_state.config.get("pause_zwischen_artikeln", [4, 7]))
            )
            st.session_state.config["pause_zwischen_artikeln"] = list(p_art)
        with col2:
            p_such = st.slider(
                "Pause zwischen Suchen", 3, 30,
                tuple(st.session_state.config.get("pause_zwischen_suchen", [6, 10]))
            )
            st.session_state.config["pause_zwischen_suchen"] = list(p_such)


    if st.button("💾  Einstellungen speichern"):
        speichere_config(st.session_state.config)
        st.success(f"✓ Gespeichert in `{CONFIG_FILE}`")
        st.json(st.session_state.config)  # zur Kontrolle


# ═══════════════════════════════════════════════
#  SEITE: HABILLEUR
# ═══════════════════════════════════════════════
elif "Habilleur" in seite:
    st.markdown("# ⚙️ Habilleur Jean Einstellungen")
    st.markdown("Finde perfekt sitzende Second-Hand Anzüge, Jacken und Mäntel von Habilleur Jean.")
    st.markdown("---")
    
    # Setze Quelle auf Habilleur
    st.session_state.config["quelle"] = "habilleur"
    
    # Konvertiere Größe vom Vinted-Format falls nötig
    aktuelle_groesse = st.session_state.config.get("groesse", "M")
    if " / " in str(aktuelle_groesse):  # Vinted-Format "M / 38" → "M"
        aktuelle_groesse = aktuelle_groesse.split(" / ")[0].strip()
    if aktuelle_groesse not in HABILLEUR_GROESSEN.keys():  # Fallback auf Default
        aktuelle_groesse = "M"
    st.session_state.config["groesse"] = aktuelle_groesse

    # Tabs
    tab1, tab2, tab3 = st.tabs(["👗  Größe & Kategorie", "📐  Maße", "🔍  Suche"])

    # ── TAB 1: Größe & Kategorie ──
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.config["groesse"] = st.selectbox(
                "Größe (Habilleur)",
                list(HABILLEUR_GROESSEN.keys()),
                index=list(HABILLEUR_GROESSEN.keys()).index(st.session_state.config["groesse"])
            )
            st.session_state.config["kategorie"] = st.selectbox(
                "Kategorie (Habilleur)",
                list(HABILLEUR_KATEGORIEN.keys()),
                index=list(HABILLEUR_KATEGORIEN.keys()).index(
                    st.session_state.config.get("kategorie", "Anzug") if st.session_state.config.get("kategorie") in HABILLEUR_KATEGORIEN.keys() else "Anzug"
                )
            )
        with col2:
            st.session_state.config["max_preis"] = st.slider(
                "Maximaler Preis (€)", 50, 350,
                st.session_state.config.get("max_preis", 200), step=10
            )

    # ── TAB 2: Maße ──
    with tab2:
        st.markdown("**Maße der Habilleur Jean Kleidungsstücke** (Größe M)")
        st.markdown("Passe diese Maße an, um passende Artikel zu finden.")
        
        masse = st.session_state.config.get("habilleur_masse", HABILLEUR_MASSE_BEISPIEL.copy())
        
        st.markdown("##### 👔 Jackenmaße")
        col1, col2, col3 = st.columns(3)
        with col1:
            masse["schulterbreite"] = st.number_input(
                "Schulterbreite (cm)", 40, 55,
                int(masse.get("schulterbreite", 46))
            )
            masse["aermellange"] = st.number_input(
                "Ärmellänge (cm)", 60, 75,
                int(masse.get("aermellange", 68))
            )
        with col2:
            masse["jackenlaenge"] = st.number_input(
                "Jackenlänge (cm)", 65, 85,
                int(masse.get("jackenlaenge", 75))
            )
            masse["achselbreite"] = st.number_input(
                "Achselbreite (cm)", 48, 65,
                int(masse.get("achselbreite", 55))
            )
        with col3:
            masse["jacke_taillenweite"] = st.number_input(
                "Taillenweite Jacke (cm)", 45, 65,
                int(masse.get("jacke_taillenweite", 52))
            )
        
        st.markdown("##### 👖 Hosenmaße")
        col1, col2, col3 = st.columns(3)
        with col1:
            masse["hose_taillenweite"] = st.number_input(
                "Taillenweite Hose (cm)", 40, 60,
                int(masse.get("hose_taillenweite", 50))
            )
            masse["gabelhoehe"] = st.number_input(
                "Gabelhöhe (cm)", 25, 35,
                int(masse.get("gabelhoehe", 30))
            )
        with col2:
            masse["beinoeffnung"] = st.number_input(
                "Beinöffnung (cm)", 20, 32,
                int(masse.get("beinoeffnung", 26))
            )
            masse["hosenlaenge"] = st.number_input(
                "Hosenlänge (cm)", 95, 120,
                int(masse.get("hosenlaenge", 110))
            )
        
        st.markdown("##### 🧥 Mantelmaße")
        col1, col2, col3 = st.columns(3)
        with col1:
            masse["mantel_schulterbreite"] = st.number_input(
                "Mantel Schulterbreite (cm)", 42, 58,
                int(masse.get("mantel_schulterbreite", 48))
            )
            masse["mantel_aermellange"] = st.number_input(
                "Mantel Ärmellänge (cm)", 55, 70,
                int(masse.get("mantel_aermellange", 62))
            )
        with col2:
            masse["mantel_gesamtlaenge"] = st.number_input(
                "Mantel Gesamtlänge (cm)", 70, 95,
                int(masse.get("mantel_gesamtlaenge", 80))
            )
            masse["mantel_achselbreite"] = st.number_input(
                "Mantel Achselbreite (cm)", 50, 68,
                int(masse.get("mantel_achselbreite", 57))
            )
        with col3:
            masse["mantel_taillenweite"] = st.number_input(
                "Mantel Taillenweite (cm)", 48, 70,
                int(masse.get("mantel_taillenweite", 54))
            )
        
        st.session_state.config["habilleur_masse"] = masse

    # ── TAB 3: Suche ──
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            user_email = st.text_input("E-Mail (optional)", value=st.session_state.config.get("user_email", ""))
            
            if user_email:
                st.session_state.config["user_email"] = user_email
        with col2:
            max_artikel = st.session_state.config.get("max_artikel_pro_suche", 20)
            if max_artikel > 100:
                max_artikel = 100
            st.session_state.config["max_artikel_pro_suche"] = st.slider(
                "Max. Artikel pro Kategorie", 1, 100,
                max_artikel, step=1
            )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾  Habilleur Einstellungen speichern"):
            speichere_config(st.session_state.config)
            st.success("✓ Habilleur Konfiguration gespeichert")
# ═══════════════════════════════════════════════
#  SEITE: eBay
# ═══════════════════════════════════════════════
elif "eBay" in seite:
    st.markdown("# ⚙️ eBay Einstellungen")
    st.markdown("Konfiguriere deine eBay-Sucheinstellungen.")
    st.markdown("---")

    # Setze Quelle auf eBay
    st.session_state.config["quelle"] = "ebay"

    aktuelle_groesse = st.session_state.config.get("groesse", "M")
    if " / " in str(aktuelle_groesse):  # Vinted-Format "M / 38" → "M"
        aktuelle_groesse = aktuelle_groesse.split(" / ")[0].strip()
    if aktuelle_groesse not in EBAY_GROESSEN:  # Fallback auf Default
        aktuelle_groesse = "M"
    st.session_state.config["groesse"] = aktuelle_groesse

    tab1, tab2, tab3 = st.tabs(["👗  Größe & Kategorie", "📐  Maße", "🔍  Suche"])

    # ── TAB 1: Stil & Größe ──
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.config["groesse"] = st.selectbox(
                "Kleidungsgröße (eBay)",
                EBAY_GROESSEN,
                index=EBAY_GROESSEN.index(st.session_state.config["groesse"])
            )
            st.session_state.config["kategorie"] = st.selectbox(
                "Kategorie (eBay)",
                list(CATEGORY_IDS_EBAY.keys()),
                index=list(CATEGORY_IDS_EBAY.keys()).index(
                    st.session_state.config.get("kategorie", "Herren Jacken, Mäntel und Westen") if st.session_state.config.get(
                        "kategorie") in CATEGORY_IDS_EBAY.keys() else "Herren Jacken, Mäntel und Westen"
                ))
            st.session_state.config["min_zustand"] = st.selectbox(
                "Mindest-Zustand",
                CONDITION_IDS_EBAY,
                index=list(CONDITION_IDS_EBAY.keys()).index(
                    st.session_state.config.get("min_zustand", "Gut")
                ))
            st.session_state.config["farbe"] = st.selectbox(
                "Gewünschte Farbe des Artikels (leer lassen für keine Präferenz)",
                EBAY_FARBEN,
                index=EBAY_FARBEN.index(st.session_state.config.get("farbe", ""))
            )

        with col2:
            st.session_state.config["max_preis"] = st.slider(
                "Maximaler Preis (€)", 5, 200,
                st.session_state.config.get("max_preis", 50), step=5
            )
            st.session_state.config["suchbegriffe"] = st.text_input(
                "Suchbegriffe eingeben",
                value=st.session_state.config.get("suchbegriffe", ""),
                placeholder="z. B. Stile"
            )
            st.session_state.config["marke"] = st.text_input(
                "Gewünschte Marke des Artikels (Achtung: Eingabe ist case-sensitive)",
                value=st.session_state.config.get("marke", ""),
                placeholder="z. B. Adidas",
            )
            st.session_state.config["material"] = st.selectbox(
                "Gewünschtes Material des Artikels (leer lassen für keine Präferenz)",
                EBAY_MATERIALS,
                index=EBAY_MATERIALS.index(st.session_state.config.get("material", ""))
            )

    # ── TAB 2: Maße ──
    with tab2:
        st.markdown("Trage deine Maße ein – das LLM vergleicht sie mit den Angaben in der Beschreibung.")
        masse = st.session_state.config.get("ebay_masse", HABILLEUR_MASSE_BEISPIEL.copy())

        st.markdown("##### 👔 Jackenmaße")
        col1, col2, col3 = st.columns(3)
        with col1:
            masse["schulterbreite"] = st.number_input(
                "Schulterbreite (cm)", 40, 55,
                int(masse.get("schulterbreite", 46))
            )
            masse["aermellange"] = st.number_input(
                "Ärmellänge (cm)", 60, 75,
                int(masse.get("aermellange", 68))
            )
        with col2:
            masse["jackenlaenge"] = st.number_input(
                "Jackenlänge (cm)", 65, 85,
                int(masse.get("jackenlaenge", 75))
            )
            masse["achselbreite"] = st.number_input(
                "Achselbreite (cm)", 48, 65,
                int(masse.get("achselbreite", 55))
            )
        with col3:
            masse["jacke_taillenweite"] = st.number_input(
                "Taillenweite Jacke (cm)", 45, 65,
                int(masse.get("jacke_taillenweite", 52))
            )

        st.markdown("##### 👖 Hosenmaße")
        col1, col2, col3 = st.columns(3)
        with col1:
            masse["hose_taillenweite"] = st.number_input(
                "Taillenweite Hose (cm)", 40, 60,
                int(masse.get("hose_taillenweite", 50))
            )
            masse["gabelhoehe"] = st.number_input(
                "Gabelhöhe (cm)", 25, 35,
                int(masse.get("gabelhoehe", 30))
            )
        with col2:
            masse["beinoeffnung"] = st.number_input(
                "Beinöffnung (cm)", 20, 32,
                int(masse.get("beinoeffnung", 26))
            )
            masse["hosenlaenge"] = st.number_input(
                "Hosenlänge (cm)", 95, 120,
                int(masse.get("hosenlaenge", 110))
            )

        st.markdown("##### 🧥 Mantelmaße")
        col1, col2, col3 = st.columns(3)
        with col1:
            masse["mantel_schulterbreite"] = st.number_input(
                "Mantel Schulterbreite (cm)", 42, 58,
                int(masse.get("mantel_schulterbreite", 48))
            )
            masse["mantel_aermellange"] = st.number_input(
                "Mantel Ärmellänge (cm)", 55, 70,
                int(masse.get("mantel_aermellange", 62))
            )
        with col2:
            masse["mantel_gesamtlaenge"] = st.number_input(
                "Mantel Gesamtlänge (cm)", 70, 95,
                int(masse.get("mantel_gesamtlaenge", 80))
            )
            masse["mantel_achselbreite"] = st.number_input(
                "Mantel Achselbreite (cm)", 50, 68,
                int(masse.get("mantel_achselbreite", 57))
            )
        with col3:
            masse["mantel_taillenweite"] = st.number_input(
                "Mantel Taillenweite (cm)", 48, 70,
                int(masse.get("mantel_taillenweite", 54))
            )

        st.session_state.config["habilleur_masse"] = masse


    # ── TAB 3: Suche ──
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            email_input = st.text_input(
                "Deine Email-Adresse",
                placeholder="maxmusterfrau@gmail.com",
            )
            if email_input:
                st.session_state.config["user_email"] = email_input
                st.session_state["user_email"] = email_input

        with col2:
            st.session_state.config["max_artikel_pro_suche"] = st.slider(
                "Artikelanzahl pro Suche", 1, 200,
                st.session_state.config.get("max_artikel_pro_suche", 5)
            )

    st.markdown("---")

    if st.button("💾  Einstellungen speichern"):
        speichere_config(st.session_state.config)
        st.success(f"✓ Gespeichert in `{CONFIG_FILE}`")
        st.json(st.session_state.config)  # zur Kontrolle


# ═══════════════════════════════════════════════
#  SEITE: Ollama
# ═══════════════════════════════════════════════
elif "Ollama" in seite:
    st.markdown("# Ollama-Konfiguration")

    st.session_state.config["ollama_url"] = st.text_input(
        "Ollama API URL",
        st.session_state.config.get("ollama_url", "http://localhost:11434/api/generate")
    )

    st.session_state.config["ollama_modell"] = st.selectbox(
        "Modell",
        OLLAMA_MODELLE,
        index=OLLAMA_MODELLE.index(st.session_state.config.get("ollama_modell", "llama3.2:3b"))
        if st.session_state.config.get("ollama_modell") in OLLAMA_MODELLE else 0
    )
    st.caption("Modell muss mit `ollama pull <modell>` heruntergeladen sein.")

    st.markdown("---")

    if st.button("💾  Einstellungen speichern"):
        speichere_config(st.session_state.config)
        st.success(f"✓ Gespeichert in `{CONFIG_FILE}`")
        st.json(st.session_state.config)  # zur Kontrolle


# ═══════════════════════════════════════════════
#  SEITE: SUCHE STARTEN
# ═══════════════════════════════════════════════
elif "Suche" in seite:
    st.markdown("# 🔍 Suche starten")

    quelle = st.session_state.config.get("quelle", "vinted")
    user_email = st.session_state.config.get("user_email") or st.session_state.get("user_email", "anonym")

    if user_email and user_email != "anonym":
        st.caption(f"🔗 Suche wird gespeichert für: **{user_email}**")
    else:
        st.warning("⚠️ Keine Email hinterlegt – Suche wird als 'anonym' gespeichert.")

    min_empfehlung = st.slider("Mindest-Bewertung für Empfehlung", 1, 10,
                               st.session_state.config.get("min_empfehlung", 6))
    st.session_state.config["min_empfehlung"] = min_empfehlung

    st.markdown("---")

    if quelle == "vinted":
        # ─────────────────────────────────────────────
        #  VINTED SUCHE
        # ─────────────────────────────────────────────
        st.markdown("### ⚙️ Vinted Konfiguration")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Größe</div><div class="metric-value">{config["groesse"]}</div></div>',
                unsafe_allow_html=True)
        with col2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Max. Preis</div><div class="metric-value">{config["max_preis"]} €</div></div>',
                unsafe_allow_html=True)
        with col3:
            anzahl = config["max_artikel_pro_suche"] * min(config.get("max_suchen", 2), len(config["stile"]))
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Max. Artikel</div><div class="metric-value">~{anzahl}</div></div>',
                unsafe_allow_html=True)

        st.markdown("**Aktive Suchbegriffe für Vinted (Stile):**")
        for s in config["stile"][:config.get("max_suchen", 2)]:
            st.markdown(f'<span class="badge">{s}</span>', unsafe_allow_html=True)

    elif quelle == "habilleur":
        # ─────────────────────────────────────────────
        #  HABILLEUR SUCHE
        # ─────────────────────────────────────────────
        st.markdown("### 🛍️ Habilleur Jean Konfiguration")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Größe</div><div class="metric-value">{config["groesse"]}</div></div>',
                unsafe_allow_html=True)
        with col2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Kategorie</div><div class="metric-value">{config["kategorie"]}</div></div>',
                unsafe_allow_html=True)
        with col3:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Max. Preis</div><div class="metric-value">{config["max_preis"]} €</div></div>',
                unsafe_allow_html=True)

    elif quelle == "ebay":
        # ─────────────────────────────────────────────
        #  EBAY SUCHE
        # ─────────────────────────────────────────────
        st.markdown("### ⚙️ eBay Einstellungen")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Größe</div><div class="metric-value">{config["groesse"]}</div></div>',
                unsafe_allow_html=True)
        with col2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Kategorie</div><div class="metric-value">{config["kategorie"]}</div></div>',
                unsafe_allow_html=True)
        with col3:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Max. Preis</div><div class="metric-value">{config["max_preis"]} €</div></div>',
                unsafe_allow_html=True)


    st.markdown("---")

    if st.button(f"🚀  {quelle.upper()}-Suche starten"):
        speichere_config(st.session_state.config)
        st.info(f"✓ Gespeichert in `{CONFIG_FILE}`\n\n**Quelle:** {quelle.upper()}")

        projekt_pfad = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

        with st.spinner("Vorgang läuft... (kann einige Minuten dauern)"):
            result = subprocess.run(
                [sys.executable, "main.py", "--config", str(CONFIG_FILE)],  # Nutzt Python aus dem venv
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=projekt_pfad
            )

        if result.returncode == 0:
            st.success("✅ Fertig!")
            if result.stdout:
                st.code(result.stdout[-3000:])
            else:
                st.info("(Keine Ausgabe erfasst)")
        else:
            st.error("❌ Fehler!")
            if result.stderr:
                st.code(result.stderr[-1000:])
            else:
                st.code(f"Return Code: {result.returncode}\n(Keine Fehlerausgabe erfasst)")


# ═══════════════════════════════════════════════
#  SEITE: ERGEBNISSE
# ═══════════════════════════════════════════════
elif "Ergebnisse" in seite:
    st.markdown("# Ergebnisse")
    quelle = st.session_state.config.get("quelle", "vinted")

    if not ERGEBNISSE_FILE.exists():
        st.warning("Noch keine Ergebnisse. Starte zuerst eine Suche.")
    else:
        with open(ERGEBNISSE_FILE, "r", encoding="utf-8") as f:
            ergebnisse = json.load(f)

        # Filter
        col1, col2, col3 = st.columns(3)
        with col1:
            nur_empfohlen = st.checkbox("Nur empfohlene Artikel", value=True)

        with col2:
            min_bewertung = st.slider("Mindest-Bewertung (Ergebnisanzeige)", 1, 10, 6)

        with col3:
            sortierung = st.selectbox("Sortierung", ["Bewertung ↓", "Preis ↑", "Preis ↓"])

        gefiltert = [
            item for item in ergebnisse
            if (not nur_empfohlen or item.get("empfohlen"))
            and ( (item.get("bewertung") or 0) >= min_bewertung )
        ]

        if sortierung == "Bewertung ↓":
            gefiltert.sort(key=lambda x: x.get("bewertung") or 0, reverse=True)
        elif sortierung == "Preis ↑":
            gefiltert.sort(key=lambda x: float(''.join(filter(str.isdigit, x.get("preis","0"))) or 0))
        else:
            gefiltert.sort(key=lambda x: float(''.join(filter(str.isdigit, x.get("preis","0"))) or 0), reverse=True)

        st.markdown(f"**{len(gefiltert)} Artikel** von {len(ergebnisse)} gesamt")
        st.markdown("---")

        for filter_item in gefiltert:
            bewertung = filter_item.get("bewertung", "?")
            sterne = "⭐" * int(bewertung // 2) if isinstance(bewertung, (int, float)) else ""

            masse = filter_item.get("masse", {})
            masse_html = ""

            if quelle == "vinted":
                masse_felder = [
                    ("brust_cm", "Brust"), ("taille_cm", "Taille"), ("huefte_cm", "Hüfte"),
                    ("schulter_cm", "Schulter"), ("laenge_oberteil_cm", "Länge Top"), ("laenge_hosen_cm", "Länge Hose"),
                    ("innennaht_cm", "Innennaht"), ("aermellaenge_cm", "Ärmellänge"), ("gabelhoehe_cm", "Gabelhöhe"), ("beinoeffnung_cm", "Beinöffnung")
                ]

            elif ( quelle == "habilleur" ) or ( quelle == "ebay"):
                masse_felder = [
                    ("schulterbreite", "Schulterbreite"),
                    ("aermellaenge", "Ärmellänge"),
                    ("jackenlaenge", "Jackenlänge"),
                    ("achselbreite", "Achselbreite"),
                    ("jacke_taillenweite", "Jacke Taillenweite"),
                    ("hose_taillenweite", "Hose Taillenweite"),
                    ("gabelhoehe", "Gabelhöhe"),
                    ("beinoeffnung", "Beinöffnung"),
                    ("hosenlaenge", "Hosenlänge"),
                    ("mantel_schulterbreite", "Mantel Schulterbreite"),
                    ("mantel_gesamtlaenge", "Mantel Gesamtlänge"),
                    ("mantel_aermellaenge", "Mantel Ärmellänge"),
                    ("mantel_achselbreite", "Mantel Achselbreite"),
                    ("mantel_taillenweite", "Mantel Taillenweite"),
                ]

            else:
                masse_felder = []
                print("Es ist bei der Suchauswahl ein Fehler aufgetreten.")


            # Prüfe sicherheitshalber, ob 'masse' überhaupt existiert, bevor wir .get() nutzen
            if masse is not None:
                masse_items = [(label, masse.get(key)) for key, label in masse_felder if masse.get(key)]
            else:
                masse_items = []
            if masse_items:
                items_html = "".join([
                    f'<div class="masse-item"><div class="masse-key">{label}</div><div class="masse-val">{val} cm</div></div>'
                    for label, val in masse_items
                ])
                masse_html = f'<div class="masse-grid">{items_html}</div>'

            passform = ""
            if filter_item.get("passform_hinweise"):
                passform = " · ".join(filter_item["passform_hinweise"])

            badges = ""
            if filter_item.get("zustand"):
                badges += f'<span class="badge">{filter_item["zustand"]}</span>'
            if filter_item.get("material"):
                badges += f'<span class="badge">{filter_item["material"]}</span>'
            if ( filter_item.get("passt_stil") ) and ( quelle == "vinted"):
                badges += '<span class="badge">✓ Stil passt</span>'

            st.markdown(f"""
<div class="artikel-card">
  <div class="artikel-titel">{filter_item.get('titel','–')}</div>
  <div class="artikel-preis">{filter_item.get('preis','–')} &nbsp;·&nbsp; {sterne} {bewertung}/10</div>
  <div style="margin: 0.5rem 0">{badges}</div>
  {masse_html}
  <div style="margin-top:0.8rem; color:#8a8478; font-size:0.8rem">{filter_item.get('begruendung','')}</div>
  {f'<div style="color:#e8c97e; font-size:0.75rem; margin-top:0.4rem">📐 {passform}</div>' if passform else ''}
  <div style="margin-top:0.6rem"><a href="{filter_item.get('url','#')}" target="_blank" style="color:#e8c97e; font-size:0.75rem; text-decoration:none">→ Auf Marktplatz ansehen</a></div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
#  SEITE: Newsletter
# ═══════════════════════════════════════════════
elif "Newsletter" in seite:
    st.markdown("# Newsletter abonnieren")
    st.markdown("Erhalte personalisierte Empfehlungen direkt per Email.")
    st.markdown("---")

    email = st.text_input("Deine Email-Adresse")

    st.markdown("**Deine Präferenzen** (aus den Einstellungen):")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Größe</div><div class="metric-value">{config["groesse"]}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Max. Preis</div><div class="metric-value">{config["max_preis"]}€</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Stile für Vinted</div><div class="metric-value">{", ".join(config.get("stile", []))}</div></div>', unsafe_allow_html=True)

    st.caption("💡 Passe deine Präferenzen unter Einstellungen an, bevor du dich registrierst.")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📧  Jetzt anmelden"):
            if not email:
                st.error("Bitte Email eingeben.")
            else:
                try:
                    result = registriere_user(email, st.session_state.config)
                    if "error" in result:
                        st.error(result["error"])
                    elif result["status"] == "neu":
                        st.session_state["user_email"] = email 
                        st.success(f"✅ Angemeldet! Du erhältst Empfehlungen an {email}")
                    else:
                        st.info(f"✓ Präferenzen für {email} aktualisiert.")
                except Exception as e:
                    st.error(f"Fehler: {e}")

    with col2:
        if st.button("🚫  Abmelden"):
            if not email:
                st.error("Bitte Email eingeben.")
            else:
                try:
                    deaktiviere_user(email)
                    st.success(f"✓ {email} vom Newsletter abgemeldet.")
                except Exception as e:
                    st.error(f"Fehler: {e}")

    # Registrierte User anzeigen (Admin-Ansicht)
    st.markdown("---")
    st.markdown("### Registrierte User")
    try:
        from database.users import lade_alle_user
        users = lade_alle_user()
        if users:
            st.caption(f"{len(users)} aktive Abonnenten")
            for u in users:
                st.markdown(f"- **{u['email']}** | {u['groesse']} | max {u['max_preis']}€ | {', '.join(u.get('stile', []))}")
        else:
            st.info("Noch keine Abonnenten.")
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")