import datetime
import math
import sqlite3
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from data_engine import get_clock_display_data, fetch_weather_and_tides, DB_PATH, get_display_settings, save_display_settings
from drbo_scraper import DRBO_BOOK_MAP

# --- PAGE SETTINGS ---
st.set_page_config(page_title="Custom Bible Clock System", layout="wide", initial_sidebar_state="collapsed")

# Hardcoded Station Targets (Plymouth, MA Coordinates)
LAT, LON = 41.9584, -70.6673

st_autorefresh(interval=60000, key="clock_ticker_heartbeat")

now = datetime.datetime.now()
search_24h = now.strftime("%H:%M")
display_12hr_str = now.strftime("%I:%M %p")

schedule = get_display_settings()

def get_display_mode(hour: int, day_start: int, night_start: int, sleep_start: int, sleep_end: int) -> str:
    # Sleep and Night windows can wrap past midnight (e.g. sleep 23:00-05:00).
    def in_window(h, start, end):
        return start <= h < end if start <= end else (h >= start or h < end)

    if in_window(hour, sleep_start, sleep_end):
        return "sleep"
    if in_window(hour, night_start, day_start):
        return "night"
    return "day"

display_mode = get_display_mode(now.hour, schedule["day_start"], schedule["night_start"], schedule["sleep_start"], schedule["sleep_end"])

THEMES = {
    "day":   {"bg": "#FFFFFF", "clock": "#1B263B", "title": "#415A77", "body_text": "#2C3E50", "hero": "#0D1B2A", "citation": "#415A77",
              "text_secondary": "#5C7089", "text_muted": "#8B99A8", "border": "rgba(27,38,59,0.15)", "border_strong": "rgba(27,38,59,0.35)"},
    "night": {"bg": "#0D1117", "clock": "#8B98A5", "title": "#5C6B7A", "body_text": "#8B98A5", "hero": "#C9D1D9", "citation": "#5C6B7A",
              "text_secondary": "#6E7B87", "text_muted": "#4A555F", "border": "rgba(139,152,165,0.15)", "border_strong": "rgba(139,152,165,0.35)"},
    "sleep": {"bg": "#000000", "clock": "#4A3018", "title": "#000000", "body_text": "#000000", "hero": "#000000", "citation": "#000000",
              "text_secondary": "#000000", "text_muted": "#000000", "border": "#000000", "border_strong": "#000000"},
}
theme = THEMES[display_mode]

# --- STATION INSTRUMENT PANEL: gauge rendering (translates STATION_INSTRUMENT_PANEL_SPEC.md) ---
GAUGE_TICK_ANGLES = [-165, -110, -55, 0, 55, 110, 165]

def render_gauge(min_val, max_val, value, dial_label, value_text, status_text, theme, format_value, size=132):
    try:
        fraction = max(0.0, min(1.0, (float(value) - min_val) / (max_val - min_val)))
    except (TypeError, ValueError, ZeroDivisionError):
        fraction = 0.5
    needle_deg = -165 + fraction * 330
    tick_values = [min_val + i * (max_val - min_val) / 6 for i in range(7)]

    ticks_svg, labels_svg = "", ""
    for i, angle in enumerate(GAUGE_TICK_ANGLES):
        ticks_svg += f'<line x1="80" y1="14" x2="80" y2="24" stroke="{theme["border_strong"]}" stroke-width="2" transform="rotate({angle} 80 80)"/>'
        rad = math.radians(angle)
        lx, ly = 80 + 50 * math.sin(rad), 80 - 50 * math.cos(rad)
        color = theme["body_text"] if angle == 0 else theme["text_secondary"]
        weight = "font-weight:700;" if angle == 0 else ""
        labels_svg += f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="9" text-anchor="middle" dominant-baseline="middle" fill="{color}" style="{weight}">{format_value(tick_values[i])}</text>'

    svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 160 160">
      <circle cx="80" cy="80" r="66" fill="none" stroke="{theme["border"]}" stroke-width="1"/>
      <circle cx="80" cy="80" r="58" fill="none" stroke="{theme["border"]}" stroke-width="8"/>
      {ticks_svg}{labels_svg}
      <text x="80" y="104" font-size="8" font-style="italic" text-anchor="middle" fill="{theme["text_muted"]}">{dial_label}</text>
      <line x1="80" y1="80" x2="80" y2="26" stroke="{theme["body_text"]}" stroke-width="2" transform="rotate({needle_deg:.1f} 80 80)"/>
      <circle cx="80" cy="80" r="4" fill="{theme["body_text"]}"/>
    </svg>'''

    return f'''<div style="text-align:center;">{svg}
      <div style="font-size:15px;font-weight:500;color:{theme["body_text"]};margin-top:2px;">{value_text}</div>
      <div style="font-size:12px;color:{theme["text_muted"]};">{status_text}</div>
    </div>'''

def render_tide_gauge(needle_deg, status_text, next_label, theme, size=132):
    left_nums = [(1, -30), (2, -60), (3, -90), (4, -120), (5, -150)]
    right_nums = [(5, 30), (4, 60), (3, 90), (2, 120), (1, 150)]
    labels_svg = ""
    for num, angle in left_nums + right_nums:
        rad = math.radians(angle)
        lx, ly = 80 + 50 * math.sin(rad), 80 - 50 * math.cos(rad)
        labels_svg += f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="9" text-anchor="middle" dominant-baseline="middle" fill="{theme["text_secondary"]}">{num}</text>'

    svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 160 160">
      <circle cx="80" cy="80" r="66" fill="none" stroke="{theme["border"]}" stroke-width="1"/>
      <circle cx="80" cy="80" r="58" fill="none" stroke="{theme["border"]}" stroke-width="8"/>
      {labels_svg}
      <text x="80" y="22" font-size="9" font-weight="700" text-anchor="middle" fill="{theme["body_text"]}">High tide</text>
      <text x="80" y="140" font-size="9" text-anchor="middle" fill="{theme["text_secondary"]}">Low tide</text>
      <line x1="80" y1="80" x2="80" y2="26" stroke="{theme["body_text"]}" stroke-width="2" transform="rotate({needle_deg:.1f} 80 80)"/>
      <circle cx="80" cy="80" r="4" fill="{theme["body_text"]}"/>
    </svg>'''

    return f'''<div style="text-align:center;">{svg}
      <div style="font-size:15px;font-weight:500;color:{theme["body_text"]};margin-top:2px;">{status_text}</div>
      <div style="font-size:12px;color:{theme["text_muted"]};">{next_label}</div>
    </div>'''

def render_center_hub(temp_f_str, temp_c_str, theme, size=92):
    return f'''<div style="width:{size}px;height:{size}px;border-radius:50%;border:2px solid {theme["border_strong"]};
      display:flex;flex-direction:column;align-items:center;justify-content:center;background:{theme["bg"]};margin:0 auto;">
      <div style="font-size:14px;">🌡️</div>
      <div style="font-size:20px;font-weight:700;color:{theme["body_text"]};line-height:1.1;">{temp_f_str}</div>
      <div style="font-size:11px;color:{theme["text_muted"]};">{temp_c_str}</div>
    </div>'''

def render_instrument_panel(env_payload, temp_str, alt_temp_str, now, theme, hub_size=92):
    pressure_val = env_payload.get("pressure", "--")
    pressure_text = f"{pressure_val:.0f} hPa" if isinstance(pressure_val, (int, float)) else "-- hPa"
    trend_text = {"rising": "↑ Rising", "falling": "↓ Falling", "steady": "→ Steady"}.get(env_payload.get("pressure_trend"), "No trend data")
    barometer = render_gauge(950, 1070, pressure_val if isinstance(pressure_val, (int, float)) else 1010,
                              "BAROMETER", pressure_text, trend_text, theme, lambda v: f"{v:.0f}")

    humidity_val = env_payload.get("humidity", "--")
    humidity_text = f"{humidity_val}%" if isinstance(humidity_val, (int, float)) else "--%"
    hygrometer = render_gauge(0, 100, humidity_val if isinstance(humidity_val, (int, float)) else 50,
                               "HYGROMETER", humidity_text, "Relative humidity", theme, lambda v: f"{v:.0f}")

    temp_val = env_payload.get("temperature", "--")
    thermometer = render_gauge(-20, 120, temp_val if isinstance(temp_val, (int, float)) else 70,
                                "THERMOMETER", temp_str, alt_temp_str, theme, lambda v: f"{v:.0f}")

    tide_clock = render_tide_gauge(env_payload.get("tide_needle_deg", 0), env_payload.get("tide_status", "Unknown"),
                                    env_payload.get("tide_next_label", ""), theme)

    hub = render_center_hub(temp_str, alt_temp_str, theme, size=hub_size)

    return f'''<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;white-space:nowrap;gap:8px;">
      <div style="font-size:12px;font-weight:bold;color:{theme["title"]};text-transform:uppercase;letter-spacing:0.5px;">⚓ Station Instrument Panel</div>
      <div style="font-size:12px;color:{theme["text_muted"]};flex-shrink:0;">{now.strftime("%A, %B %-d")}</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr {hub_size}px 1fr;grid-template-rows:auto {hub_size}px auto;align-items:center;justify-items:center;">
      <div style="grid-column:1;grid-row:1;">{barometer}</div>
      <div style="grid-column:3;grid-row:1;">{hygrometer}</div>
      <div style="grid-column:2;grid-row:2;">{hub}</div>
      <div style="grid-column:1;grid-row:3;">{thermometer}</div>
      <div style="grid-column:3;grid-row:3;">{tide_clock}</div>
    </div>'''

# Execute consolidated queries
scripture_payload = get_clock_display_data(search_24h)
env_payload = fetch_weather_and_tides(LAT, LON)

# Numeric conversions
try:
    f_temp = float(env_payload.get("temperature", 0))
    c_temp = (f_temp - 32) * 5 / 9
    temp_str = f"{f_temp:.1f}°F"
    alt_temp_str = f"{c_temp:.1f}°C"
except Exception:
    temp_str, alt_temp_str = "--°F", "--°C"

# --- SIDEBAR CONTROL ENGINE ---
with st.sidebar:
    st.markdown("## 🧭 Navigation Deck")
    app_mode = st.radio("Select Active Workspace View Mode:", options=["🕒 Minimalist Wall Clock", "⚙️ Master Curation Matrix", "📚 Verse Catalog & Search"], key="main_navigation_rail")

    with st.expander("🌗 Display Schedule"):
        st.caption(f"Currently in **{display_mode.upper()}** mode.")
        cfg_day_start = st.number_input("Day starts at (hour, 0-23)", min_value=0, max_value=23, value=schedule["day_start"], key="cfg_day_start")
        cfg_night_start = st.number_input("Night starts at (hour, 0-23)", min_value=0, max_value=23, value=schedule["night_start"], key="cfg_night_start")
        cfg_sleep_start = st.number_input("Sleep starts at (hour, 0-23)", min_value=0, max_value=23, value=schedule["sleep_start"], key="cfg_sleep_start")
        cfg_sleep_end = st.number_input("Sleep ends at (hour, 0-23)", min_value=0, max_value=23, value=schedule["sleep_end"], key="cfg_sleep_end")
        if st.button("💾 Save Schedule", use_container_width=True):
            save_display_settings(cfg_day_start, cfg_night_start, cfg_sleep_start, cfg_sleep_end)
            st.rerun()

# --- UI VISUAL STYLING SHEET (day/night/sleep themed) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {theme['bg']}; }}
    .clock-face {{ font-size: 130px; font-weight: 800; color: {theme['clock']}; font-family: 'Courier New', monospace; text-align: center; margin-top: -15px; }}
    .meta-title {{ font-size: 16px; font-weight: bold; color: {theme['title']}; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }}
    .meta-body {{ font-size: 15px; font-family: 'Georgia', serif; line-height: 1.5; color: {theme['body_text']}; }}
    .scripture-hero {{ font-size: 38px; font-family: 'Georgia', serif; line-height: 1.6; color: {theme['hero']}; font-style: italic; }}
    .citation-banner {{ font-size: 22px; font-weight: bold; color: {theme['citation']}; margin-bottom: 5px; }}

    [data-testid="stHeader"] {{ background: transparent; }}
    footer {{ visibility: hidden !important; }}
    [data-testid="stAppDeployButton"] {{ display: none !important; }}
    </style>
""", unsafe_allow_html=True)

if app_mode == "🕒 Minimalist Wall Clock":
    if display_mode == "sleep":
        # Nothing but a dim clock face - a tablet on a nightstand shouldn't light up the room.
        st.markdown(f"<div class='clock-face' style='margin-top: 35vh;'>{now.strftime('%I:%M')}</div>", unsafe_allow_html=True)
    else:
        col_left_context, col_right_clock_face = st.columns([1, 2])

        with col_left_context:
            with st.container(border=True):
                st.markdown(f"<div class='meta-title'>📖 {scripture_payload['book']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='meta-body'>{scripture_payload['book_desc']}</div>", unsafe_allow_html=True)

            with st.container(border=True):
                st.markdown(f"<div class='meta-title'>📍 Chapter {scripture_payload['chapter']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='meta-body'>{scripture_payload['chapter_summary']}</div>", unsafe_allow_html=True)

            # Station Instrument Panel: four brass-style gauges (Barometer, Hygrometer,
            # Thermometer, Tide Clock) with a center temperature hub - see STATION_INSTRUMENT_PANEL_SPEC.md
            with st.container(border=True):
                st.markdown(render_instrument_panel(env_payload, temp_str, alt_temp_str, now, theme), unsafe_allow_html=True)

        with col_right_clock_face:
            with st.container(border=True):
                st.markdown(f"<div class='clock-face'>{now.strftime('%I:%M')}</div>", unsafe_allow_html=True)

            with st.container(border=True):
                st.markdown(f"<div class='citation-banner'>{scripture_payload['icon']} {scripture_payload['book']} {scripture_payload['chapter']}:{scripture_payload['verse']}</div>", unsafe_allow_html=True)
                st.divider()
                st.markdown(f"<div class='scripture-hero'>\"{scripture_payload['text']}\"</div>", unsafe_allow_html=True)

            if scripture_payload['footnote']:
                with st.container(border=True):
                    st.markdown("<div class='meta-title'>📝 Verse Commentary Annotations</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='meta-body'>{scripture_payload['footnote']}</div>", unsafe_allow_html=True)

elif app_mode == "⚙️ Master Curation Matrix":
    # --- MASTER CURATION CONFIGURATION MATRIX ---
    st.markdown("## ⚙️ Scripture & System Configuration Engine")
    st.info(f"Active Target Window ── **Standard:** `{display_12hr_str}` | **24-Hour Tracking Token:** `{search_24h}`")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM verses_library WHERE time_key = ?", (search_24h,))
    all_available_options = cursor.fetchall()
    
    if not all_available_options:
        st.warning("No database rows indexed for this time block. Set DEV_MODE = False in hydrate_all_books.py to populate production tables.")
    else:
        cursor.execute("SELECT * FROM curation_rules WHERE time_key = ?", (search_24h,))
        rules_map = {f"{r['book_name']}_{r['chapter']}:{r['verse']}": r["rule_state"] for r in cursor.fetchall()}
        
        for idx, item in enumerate(all_available_options):
            verse_id_key = f"{item['book_name']}_{item['chapter']}:{item['verse']}"
            current_status = rules_map.get(verse_id_key, "Show")
            
            with st.container(border=True):
                col_meta_details, col_verse_text, col_status_actions = st.columns([1, 2, 1])
                with col_meta_details:
                    st.markdown(f"**{item['book_name']}**")
                    st.caption(f"Chapter {item['chapter']}, Verse {item['verse']}")
                    if current_status == "Preferred": st.success("⭐ In Favorites Pool")
                    elif current_status == "Block": st.error("🚫 Blocked")
                    else: st.info("🔹 Active Pool")
                        
                with col_verse_text:
                    st.markdown(f"*{item['english_text']}*")
                    
                with col_status_actions:
                    if current_status != "Preferred":
                        if st.button("📌 Pin to Favorites", key=f"pref_{idx}_{verse_id_key}", use_container_width=True):
                            cursor.execute("INSERT OR REPLACE INTO curation_rules (time_key, book_name, chapter, verse, rule_state) VALUES (?, ?, ?, ?, 'Preferred')", (search_24h, item["book_name"], item["chapter"], item["verse"]))
                            conn.commit(); st.rerun()
                    if current_status == "Preferred":
                        if st.button("↩️ Unpin", key=f"rem_{idx}_{verse_id_key}", use_container_width=True):
                            cursor.execute("DELETE FROM curation_rules WHERE time_key=? AND book_name=? AND chapter=? AND verse=?", (search_24h, item["book_name"], item["chapter"], item["verse"]))
                            conn.commit(); st.rerun()
                    if current_status != "Block":
                        if st.button("❌ Block", key=f"block_{idx}_{verse_id_key}", use_container_width=True):
                            cursor.execute("INSERT OR REPLACE INTO curation_rules (time_key, book_name, chapter, verse, rule_state) VALUES (?, ?, ?, ?, 'Block')", (search_24h, item["book_name"], item["chapter"], item["verse"]))
                            conn.commit(); st.rerun()
    conn.close()

else:
    # --- VERSE CATALOG & SEARCH ---
    st.markdown("## 📚 Verse Catalog & Search")
    st.caption("Browse the full library. Pin a verse to any placeholder time slot, or add it to the fallback rotation shown when a minute has no natural match.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT book_name FROM verses_library")
    available_books = {r["book_name"] for r in cursor.fetchall()}
    book_order = [name for _, name in sorted(DRBO_BOOK_MAP.items()) if name in available_books]

    col_book, col_chapter, col_verse, col_text = st.columns([2, 1, 1, 3])
    with col_book:
        book_filter = st.selectbox("Book", options=["Any"] + book_order, key="catalog_book_filter")
    with col_chapter:
        chapter_filter = st.number_input("Chapter", min_value=0, value=0, key="catalog_chapter_filter")
    with col_verse:
        verse_filter = st.number_input("Verse", min_value=0, value=0, key="catalog_verse_filter")
    with col_text:
        text_filter = st.text_input("Search Text", key="catalog_text_filter")

    where_clauses, params = [], []
    if book_filter != "Any":
        where_clauses.append("book_name = ?")
        params.append(book_filter)
    if chapter_filter:
        where_clauses.append("chapter = ?")
        params.append(int(chapter_filter))
    if verse_filter:
        where_clauses.append("verse = ?")
        params.append(int(verse_filter))
    if text_filter:
        where_clauses.append("english_text LIKE ?")
        params.append(f"%{text_filter}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    cursor.execute(f"SELECT * FROM verses_library {where_sql} ORDER BY book_name, chapter, verse LIMIT 50", params)
    results = cursor.fetchall()

    if not results:
        st.warning("No verses match this search. Try loosening a filter, or hydrate more of the Bible first.")
    else:
        if len(results) == 50:
            st.caption("Showing first 50 matches — refine your search for more precise results.")

        cursor.execute("SELECT * FROM curation_rules WHERE rule_state IN ('Preferred', 'Fallback')")
        pinned_counts, fallback_set = {}, set()
        for r in cursor.fetchall():
            vkey = f"{r['book_name']}_{r['chapter']}:{r['verse']}"
            if r["rule_state"] == "Preferred":
                pinned_counts[vkey] = pinned_counts.get(vkey, 0) + 1
            else:
                fallback_set.add(vkey)

        for idx, item in enumerate(results):
            verse_id_key = f"{item['book_name']}_{item['chapter']}:{item['verse']}"

            with st.container(border=True):
                col_meta_details, col_verse_text, col_actions = st.columns([1, 2, 1.4])
                with col_meta_details:
                    st.markdown(f"**{item['book_name']}**")
                    st.caption(f"Chapter {item['chapter']}, Verse {item['verse']}")
                    pin_count = pinned_counts.get(verse_id_key, 0)
                    if pin_count:
                        st.success(f"📌 Pinned to {pin_count} slot(s)")
                    if verse_id_key in fallback_set:
                        st.info("📜 In Fallback Catalog")

                with col_verse_text:
                    st.markdown(f"*{item['english_text']}*")

                with col_actions:
                    chosen_time = st.time_input("Target slot", value=datetime.time(0, 0), step=60, key=f"catalog_time_{idx}_{verse_id_key}")
                    if st.button("📌 Pin to this time slot", key=f"catalog_pin_{idx}_{verse_id_key}", use_container_width=True):
                        pin_key = chosen_time.strftime("%H:%M")
                        cursor.execute("INSERT OR REPLACE INTO curation_rules (time_key, book_name, chapter, verse, rule_state) VALUES (?, ?, ?, ?, 'Preferred')",
                                       (pin_key, item["book_name"], item["chapter"], item["verse"]))
                        conn.commit(); st.rerun()

                    if verse_id_key in fallback_set:
                        if st.button("↩️ Remove from Fallback", key=f"catalog_unfallback_{idx}_{verse_id_key}", use_container_width=True):
                            cursor.execute("DELETE FROM curation_rules WHERE time_key='ANY' AND book_name=? AND chapter=? AND verse=?",
                                           (item["book_name"], item["chapter"], item["verse"]))
                            conn.commit(); st.rerun()
                    else:
                        if st.button("⭐ Add to Fallback Catalog", key=f"catalog_fallback_{idx}_{verse_id_key}", use_container_width=True):
                            cursor.execute("INSERT OR REPLACE INTO curation_rules (time_key, book_name, chapter, verse, rule_state) VALUES ('ANY', ?, ?, ?, 'Fallback')",
                                           (item["book_name"], item["chapter"], item["verse"]))
                            conn.commit(); st.rerun()
    conn.close()