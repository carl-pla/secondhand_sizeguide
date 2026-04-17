import streamlit as st # type: ignore 
import json
from pathlib import Path
import sys, os
import subprocess
import httpx # type: ignore 

from database.users import registriere_user 
from database.users import deaktiviere_user

# Fügt den Projekt-Hauptordner zum Pfad hinzu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.config_defaults import (
    VINTED_GROESSEN, VINTED_KATEGORIEN, OLLAMA_MODELLE, STIL_OPTIONEN, ZUSTAND_RANG, CONFIG_FILE, ERGEBNISSE_FILE, ZUSTAND_OPTIONEN,
    speichere_config, lade_config
)


# ─────────────────────────────────────────────
#  SEITEN-KONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="MatchFit",
    page_icon="dashboard/logo/logo_matchfit.png",
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
    st.image("dashboard/logo/logo_matchfit.png", width=180)
    st.markdown(
        "<h1 style='text-align:center; margin-top:-10px; margin-right: 60px; '>MatchFit</h1>",
        unsafe_allow_html=True
    )
    st.divider()
    seite = st.radio(
        "",
        ["⚙️  Einstellungen", "🔍  Suche starten", "📋  Ergebnisse", "📧  Newsletter"],
        label_visibility="collapsed"
    )
    st.markdown("---")

    # Ollama Status
    try:
        httpx.get(config["ollama_url"].replace("/api/generate", ""), timeout=2)
        st.markdown('<span class="status-ok">● Ollama online</span>', unsafe_allow_html=True)
    except:
        st.markdown('<span class="status-err">● Ollama offline</span>', unsafe_allow_html=True)

    


# ═══════════════════════════════════════════════
#  SEITE: EINSTELLUNGEN
# ═══════════════════════════════════════════════
if "Einstellungen" in seite:
    st.markdown("# Einstellungen")
    st.markdown("Konfiguriere deine Präferenzen.")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["👗  Stil & Größe", "📐  Maße", "🔍  Suche", "🤖  Ollama"])

    # ── TAB 1: Stil & Größe ──
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.config["groesse"] = st.selectbox(
                "Kleidungsgröße",
                list(VINTED_GROESSEN.keys()),
                index=list(VINTED_GROESSEN.keys()).index(
                    st.session_state.config.get("groesse", "M / 38")
                )
            )
            st.session_state.config["kategorie"] = st.selectbox(
                "Kategorie",
                list(VINTED_KATEGORIEN.keys()),
                index=list(VINTED_KATEGORIEN.keys()).index(
                    st.session_state.config.get("kategorie", "Herren Jacken & Mäntel")
                )
            )
            st.session_state.config["stile"] = st.multiselect(
            "Bevorzugte Stile",
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
            email_input = st.text_input(
            "Deine Email-Adresse",
        )
        if email_input:
            st.session_state.config["user_email"] = email_input
            st.session_state["user_email"] = email_input
        
        
            

    # ── TAB 2: Maße ──
    with tab2:
        st.markdown("Trage deine Maße ein – das LLM vergleicht sie mit den Angaben in der Beschreibung.")
        masse = st.session_state.config.get("eigene_masse", {})
        col1, col2 = st.columns(2)
        with col1:
            masse["brust"]   = st.number_input("Brustumfang (cm)",   60, 130, masse.get("brust", 88))
            masse["taille"]  = st.number_input("Taillenumfang (cm)", 50, 120, masse.get("taille", 70))
            masse["huefte"]  = st.number_input("Hüftumfang (cm)",    70, 140, masse.get("huefte", 96))
        with col2:
            masse["schulter"]       = st.number_input("Schulterbreite (cm)",           30, 60,  masse.get("schulter", 38))
            masse["laenge_oberteil"]= st.number_input("Bevorzugte Länge Oberteil (cm)",40, 100, masse.get("laenge_oberteil", 60))
            masse["innennaht"]      = st.number_input("Innennaht / Schrittlänge (cm)", 60, 100, masse.get("innennaht", 78))
        st.session_state.config["eigene_masse"] = masse

    # ── TAB 3: Suche ──
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.config["max_artikel_pro_suche"] = st.slider(
                "Artikel pro Suchbegriff", 1, 60,
                st.session_state.config.get("max_artikel_pro_suche", 5)
            )
        with col2:
            stile = st.session_state.config["stile"]
            anzahl = max(2, len(stile))  # minimum 2 damit Slider nicht crasht
            st.session_state.config["max_suchen"] = st.slider(
                "Maximale Anzahl Suchbegriffe", 1, anzahl,
                min(st.session_state.config.get("max_suchen", 1), anzahl)
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

    # ── TAB 4: Ollama ──
    with tab4:
        st.session_state.config["ollama_url"] = st.text_input(
            "Ollama API URL",
            st.session_state.config.get("ollama_url", "http://ollama:11435/api/generate")
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
elif "Suche" in seite:   # ← elif statt if, und "Suche" check
    st.markdown("# Suche starten")
    user_email = st.session_state.config.get("user_email") or st.session_state.get("user_email", "anonym")
    if user_email:
        st.caption(f"🔗 Suche wird gespeichert für: **{user_email}**")
    else:
        st.warning("⚠️ Keine Email hinterlegt – Suche wird als 'anonym' gespeichert.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Größe</div><div class="metric-value">{config["groesse"]}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Max. Preis</div><div class="metric-value">{config["max_preis"]} €</div></div>', unsafe_allow_html=True)
    with col3:
        anzahl = config["max_artikel_pro_suche"] * min(config.get("max_suchen", 2), len(config["stile"]))
        st.markdown(f'<div class="metric-card"><div class="metric-label">Max. Artikel</div><div class="metric-value">~{anzahl}</div></div>', unsafe_allow_html=True)

    st.markdown("**Aktive Stile:**")
    for s in config["stile"][:config.get("max_suchen", 2)]:
        st.markdown(f'<span class="badge">{s}</span>', unsafe_allow_html=True)

    st.markdown("---")

    if st.button("🚀  Scraper starten"):
        speichere_config(st.session_state.config)
        st.info(f"✓ Gespeichert in `{CONFIG_FILE}`")

        projekt_pfad = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

        with st.spinner("Scraper läuft... (kann einige Minuten dauern)"):
            result = subprocess.run(
                ["python3", "main.py", "--config", str(CONFIG_FILE)],
                capture_output=True,
                text=True,
                cwd=projekt_pfad
            )

        if result.returncode == 0:
            st.success("✅ Fertig!")
            st.code(result.stdout[-3000:])
        else:
            st.error("❌ Fehler!")
            st.code(result.stderr[-1000:])

# ═══════════════════════════════════════════════
#  SEITE: ERGEBNISSE
# ═══════════════════════════════════════════════
elif "Ergebnisse" in seite:
    st.markdown("# Ergebnisse")

    if not ERGEBNISSE_FILE.exists():
        st.warning("Noch keine Ergebnisse. Starte zuerst eine Suche.")
    else:
        with open(ERGEBNISSE_FILE, "r") as f:
            ergebnisse = json.load(f)

        # Filter
        col1, col2, col3 = st.columns(3)
        with col1:
            nur_empfohlen = st.checkbox("Nur empfohlene Artikel", value=True)
        with col2:
            min_bewertung = st.slider("Mindest-Bewertung", 1, 10, 7)
        with col3:
            sortierung = st.selectbox("Sortierung", ["Bewertung ↓", "Preis ↑", "Preis ↓"])

        gefiltert = [
            a for a in ergebnisse
            if (not nur_empfohlen or a.get("empfohlen"))
            and (a.get("bewertung") or 0) >= min_bewertung
        ]

        if sortierung == "Bewertung ↓":
            gefiltert.sort(key=lambda x: x.get("bewertung") or 0, reverse=True)
        elif sortierung == "Preis ↑":
            gefiltert.sort(key=lambda x: float(''.join(filter(str.isdigit, x.get("preis","0"))) or 0))
        else:
            gefiltert.sort(key=lambda x: float(''.join(filter(str.isdigit, x.get("preis","0"))) or 0), reverse=True)

        st.markdown(f"**{len(gefiltert)} Artikel** von {len(ergebnisse)} gesamt")
        st.markdown("---")

        for a in gefiltert:
            bewertung = a.get("bewertung", "?")
            sterne = "⭐" * int(bewertung // 2) if isinstance(bewertung, (int, float)) else ""

            masse = a.get("masse", {})
            masse_html = ""
            masse_felder = [
                ("brust_cm", "Brust"), ("taille_cm", "Taille"), ("huefte_cm", "Hüfte"),
                ("schulter_cm", "Schulter"), ("laenge_cm", "Länge"), ("aermel_cm", "Ärmel")
            ]
            masse_items = [(label, masse.get(key)) for key, label in masse_felder if masse.get(key)]
            if masse_items:
                items_html = "".join([
                    f'<div class="masse-item"><div class="masse-key">{label}</div><div class="masse-val">{val} cm</div></div>'
                    for label, val in masse_items
                ])
                masse_html = f'<div class="masse-grid">{items_html}</div>'

            passform = ""
            if a.get("passform_hinweise"):
                passform = " · ".join(a["passform_hinweise"])

            badges = ""
            if a.get("zustand"):
                badges += f'<span class="badge">{a["zustand"]}</span>'
            if a.get("material"):
                badges += f'<span class="badge">{a["material"]}</span>'
            if a.get("passt_stil"):
                badges += '<span class="badge">✓ Stil passt</span>'

            st.markdown(f"""
<div class="artikel-card">
  <div class="artikel-titel">{a.get('titel','–')}</div>
  <div class="artikel-preis">{a.get('preis','–')} &nbsp;·&nbsp; {sterne} {bewertung}/10</div>
  <div style="margin: 0.5rem 0">{badges}</div>
  {masse_html}
  <div style="margin-top:0.8rem; color:#8a8478; font-size:0.8rem">{a.get('begruendung','')}</div>
  {f'<div style="color:#e8c97e; font-size:0.75rem; margin-top:0.4rem">📐 {passform}</div>' if passform else ''}
  <div style="margin-top:0.6rem"><a href="{a.get('url','#')}" target="_blank" style="color:#e8c97e; font-size:0.75rem; text-decoration:none">→ Auf Vinted ansehen</a></div>
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
        st.markdown(f'<div class="metric-card"><div class="metric-label">Stile</div><div class="metric-value">{", ".join(config.get("stile", []))}</div></div>', unsafe_allow_html=True)

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