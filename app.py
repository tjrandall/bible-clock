import datetime
import sqlite3
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Import SQL-linked routines
from data_engine import get_clock_display_data, fetch_weather

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Custom Bible Clock System", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

if "weather_station_coords" not in st.session_state:
    st.session_state.weather_station_coords = {"name": "Lower Plymouth, MA", "lat": 41.6715, "lon": -70.5642}

# --- 60-SECOND BACKGROUND TICKLOOP HEARTBEAT ---
st_autorefresh(interval=60000, key="clock_ticker_heartbeat")

# Fetch clock system times
now = datetime.datetime.now()
search_24h = now.strftime("%H:%M")   
display_12hr_str = now.strftime("%I:%M %p")  

# Execute multi-table extraction query
scripture_payload = get_clock_display_data(search_24h)
weather_payload = fetch_weather(st.session_state.weather_station_coords["lat"], st.session_state.weather_station_coords["lon"])

# Process complex metrics conversions
try:
    f_temp = float(weather_payload.get("temperature", 0))
    c_temp = (f_temp - 32) * 5 / 9
    temperature_string = f"{f_temp:.1f}°F ({c_temp:.1f}°C)"
except Exception:
    temperature_string = "--°F (--°C)"


# --- VISUAL PRESENTATION STYLESHEET (CSS) ---
st.markdown("""
    <style>
    .clock-face { font-size: 130px; font-weight: 800; color: #1B263B; font-family: 'Courier New', monospace; text-align: center; margin-top: -15px; }
    .meta-title { font-size: 16px; font-weight: bold; color: #415A77; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
    .meta-body { font-size: 15px; font-family: 'Georgia', serif; line-height: 1.5; color: #2C3E50; }
    .scripture-hero { font-size: 38px; font-family: 'Georgia', serif; line-height: 1.6; color: #0D1B2A; font-style: italic; }
    .citation-banner { font-size: 22px; font-weight: bold; color: #415A77; margin-bottom: 5px; }
    header, footer {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# UNIFIED INTERFACE GRAPHICS LAYOUT MATRIX (MOCKUP REPLICATION)
# ==============================================================================
col_left_context, col_right_clock_face = st.columns([1, 2])

with col_left_context:
    # Zone 1: Book Description Context Frame
    with st.container(border=True):
        st.markdown(f"<div class='meta-title'>📖 {scripture_payload['book']} Context Summary</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta-body'>{scripture_payload['book_desc']}</div>", unsafe_allow_html=True)
    
    # Zone 2: Chapter Summary Header Frame
    with st.container(border=True):
        st.markdown(f"<div class='meta-title'>📍 Chapter {scripture_payload['chapter']} Header Overview</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta-body'>{scripture_payload['chapter_summary']}</div>", unsafe_allow_html=True)
        
    # Zone 3: Consolidated Meteorological Conditions Frame
    with st.container(border=True):
        st.markdown("<div class='meta-title'>🌤️ Weather</div>", unsafe_allow_html=True)
        st.metric(label="Temperature", value=temperature_string)
        st.caption(f"Surface Winds: {weather_payload.get('windspeed', '--')} MPH ── Station: {st.session_state.weather_station_coords['name']}")

with col_right_clock_face:
    # Zone 4: Hero Digital Clock Display Screen
    with st.container(border=True):
        st.markdown(f"<div class='clock-face'>{now.strftime('%I:%M')}</div>", unsafe_allow_html=True)
        
    # Zone 5: Hero Scripture Core Text Output Card
    with st.container(border=True):
        st.markdown(
            f"<div class='citation-banner'>{scripture_payload['icon']} {scripture_payload['book']} {scripture_payload['chapter']}:{scripture_payload['verse']}</div>", 
            unsafe_allow_html=True
        )
        st.divider()
        st.markdown(f"<div class='scripture-hero'>\"{scripture_payload['text']}\"</div>", unsafe_allow_html=True)
        
    # Zone 6: Specific Verse Commentary Footnote Overlay Frame
    if scripture_payload['footnote']:
        with st.container(border=True):
            st.markdown("<div class='meta-title'>📝 Verse Commentary Annotations</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='meta-body'>{scripture_payload['footnote']}</div>", unsafe_allow_html=True)