import os
import sqlite3
import datetime
import requests

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bible_clock.db")

def get_display_settings():
    """Reads the configurable day/night/sleep schedule hours (0-23), clock face format (12/24),
    and Display Distance (Desk/Counter/Wall) from app_settings."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT setting_key, setting_value FROM app_settings")
    raw = dict(cursor.fetchall())
    conn.close()
    return {
        "day_start": int(raw.get("day_start_hour", 7)),
        "night_start": int(raw.get("night_start_hour", 19)),
        "sleep_start": int(raw.get("sleep_start_hour", 23)),
        "sleep_end": int(raw.get("sleep_end_hour", 5)),
        "clock_format": int(raw.get("clock_format_hour", 12)),
        "display_distance": raw.get("display_distance", "Desk"),
    }

def save_display_settings(day_start: int, night_start: int, sleep_start: int, sleep_end: int, clock_format: int, display_distance: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT OR REPLACE INTO app_settings (setting_key, setting_value) VALUES (?, ?)",
        [("day_start_hour", str(day_start)), ("night_start_hour", str(night_start)),
         ("sleep_start_hour", str(sleep_start)), ("sleep_end_hour", str(sleep_end)),
         ("clock_format_hour", str(clock_format)), ("display_distance", display_distance)]
    )
    conn.commit()
    conn.close()

def fetch_weather_and_tides(lat: float, lon: float):
    """
    Fetches raw weather metrics (incl. barometric pressure + trend) from Open-Meteo
    and tide-cycle position (last/next event, needle angle) from the NOAA CO-OPS API
    for Plymouth Harbor (Station 8447435). Feeds the Station Instrument Panel gauges.
    """
    payload = {
        "temperature": "--", "windspeed": "--", "humidity": "--",
        "pressure": "--", "pressure_trend": None,
        "tide_needle_deg": 0, "tide_status": "Unknown", "tide_next_label": "Tide data unavailable",
    }

    # 1. Grab Weather Metrics (timezone=auto so hourly/current timestamps are local,
    # letting the pressure-trend lookup below match hours by plain wall-clock math)
    try:
        weather_url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                       f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,surface_pressure"
                       f"&hourly=surface_pressure&timezone=auto"
                       f"&temperature_unit=fahrenheit&windspeed_unit=mph")
        w_res = requests.get(weather_url, timeout=3)
        if w_res.status_code == 200:
            w_data = w_res.json()
            current = w_data.get('current', {})
            payload["temperature"] = current.get('temperature_2m', '--')
            payload["windspeed"] = current.get('wind_speed_10m', '--')
            payload["humidity"] = current.get('relative_humidity_2m', '--')
            payload["pressure"] = current.get('surface_pressure', '--')

            hourly = w_data.get('hourly', {})
            hourly_times = hourly.get('time', [])
            hourly_pressures = hourly.get('surface_pressure', [])
            target_ts = (datetime.datetime.now() - datetime.timedelta(hours=3)).strftime("%Y-%m-%dT%H:00")
            if target_ts in hourly_times and isinstance(payload["pressure"], (int, float)):
                past_pressure = hourly_pressures[hourly_times.index(target_ts)]
                delta = payload["pressure"] - past_pressure
                payload["pressure_trend"] = "rising" if delta > 1 else "falling" if delta < -1 else "steady"
    except Exception:
        pass

    # 2. Grab NOAA Tide Predictions (Station 8447435 - Plymouth, MA). A 3-day window
    # (yesterday-tomorrow) guarantees a valid last/next event pair at any time of day.
    try:
        window_start = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
        window_end = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y%m%d")
        tide_url = (f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date={window_start}"
                   f"&end_date={window_end}&station=8447435&product=predictions&datum=MLLW"
                   f"&time_zone=lst_ldt&units=english&interval=hilo&format=json")
        t_res = requests.get(tide_url, timeout=3)
        if t_res.status_code == 200:
            predictions = t_res.json().get("predictions", [])
            now_dt = datetime.datetime.now()
            parsed = [(datetime.datetime.strptime(p["t"], "%Y-%m-%d %H:%M"), p["type"]) for p in predictions]
            past_events = [p for p in parsed if p[0] <= now_dt]
            future_events = [p for p in parsed if p[0] > now_dt]

            if past_events and future_events:
                last_time, last_type = past_events[-1]
                next_time, next_type = future_events[0]
                span = (next_time - last_time).total_seconds()
                fraction = 0.5 if span <= 0 else max(0.0, min(1.0, (now_dt - last_time).total_seconds() / span))

                if last_type == "L" and next_type == "H":
                    payload["tide_needle_deg"] = -180 + fraction * 180
                    payload["tide_status"] = "Rising"
                elif last_type == "H" and next_type == "L":
                    payload["tide_needle_deg"] = fraction * 180
                    payload["tide_status"] = "Falling"

                next_label_type = "high" if next_type == "H" else "low"
                payload["tide_next_label"] = f"Next {next_label_type} {next_time.strftime('%H:%M')}"
    except Exception:
        pass

    return payload

def get_clock_display_data(time_key_24h: str):
    """Executes relational query operations matching 12-hour and 24-hour windows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    hr, mn = map(int, time_key_24h.split(":"))
    hr_12 = hr % 12
    if hr_12 == 0: hr_12 = 12
    time_key_12h = f"{hr_12:02d}:{mn:02d}"

    cursor.execute("SELECT * FROM curation_rules WHERE time_key IN (?, ?)", (time_key_24h, time_key_12h))
    user_rules = cursor.fetchall()
    preferred_rules = [r for r in user_rules if r["rule_state"] == "Preferred"]
    blocked_rules = [f"{r['book_name']}_{r['chapter']}:{r['verse']}" for r in user_rules if r["rule_state"] == "Block"]
    
    target_verse = None
    origin_marker = "✝" 

    if preferred_rules:
        preferred_rules = sorted(preferred_rules, key=lambda x: x["display_count"])
        selected_rule = preferred_rules[0]
        cursor.execute("SELECT * FROM verses_library WHERE book_name=? AND chapter=? AND verse=?",
                       (selected_rule["book_name"], selected_rule["chapter"], selected_rule["verse"]))
        target_verse = cursor.fetchone()
        if target_verse:
            cursor.execute("UPDATE curation_rules SET display_count = display_count + 1 WHERE time_key=? AND book_name=? AND chapter=? AND verse=?",
                           (selected_rule["time_key"], selected_rule["book_name"], selected_rule["chapter"], selected_rule["verse"]))
            conn.commit()
            origin_marker = "⭐"

    if not target_verse:
        cursor.execute("SELECT * FROM verses_library WHERE time_key IN (?, ?)", (time_key_24h, time_key_12h))
        all_matches = cursor.fetchall()
        valid_pool = [m for m in all_matches if f"{m['book_name']}_{m['chapter']}:{m['verse']}" not in blocked_rules]
        
        if valid_pool:
            for item in valid_pool:
                cursor.execute("INSERT OR IGNORE INTO curation_rules (time_key, book_name, chapter, verse, rule_state) VALUES (?, ?, ?, ?, 'Show')", 
                               (item["time_key"], item["book_name"], item["chapter"], item["verse"]))
            conn.commit()
            
            cursor.execute("SELECT * FROM curation_rules WHERE time_key IN (?, ?) AND rule_state = 'Show'", (time_key_24h, time_key_12h))
            active_shows = sorted(cursor.fetchall(), key=lambda x: x["display_count"])
            
            for selected_show in active_shows:
                cursor.execute("SELECT * FROM verses_library WHERE book_name=? AND chapter=? AND verse=?",
                               (selected_show["book_name"], selected_show["chapter"], selected_show["verse"]))
                target_verse = cursor.fetchone()
                if target_verse:
                    cursor.execute("UPDATE curation_rules SET display_count = display_count + 1 WHERE time_key=? AND book_name=? AND chapter=? AND verse=?",
                                   (selected_show["time_key"], selected_show["book_name"], selected_show["chapter"], selected_show["verse"]))
                    conn.commit()
                    break
        
    # No natural or preferred match for this minute — draw from the user-curated
    # fallback catalog (rule_state='Fallback', time_key='ANY' sentinel — never a real HH:MM)
    if not target_verse:
        cursor.execute("SELECT * FROM curation_rules WHERE time_key='ANY' AND rule_state='Fallback' ORDER BY display_count ASC")
        fallback_pool = cursor.fetchall()
        for candidate in fallback_pool:
            cursor.execute("SELECT * FROM verses_library WHERE book_name=? AND chapter=? AND verse=?",
                           (candidate["book_name"], candidate["chapter"], candidate["verse"]))
            target_verse = cursor.fetchone()
            if target_verse:
                cursor.execute("UPDATE curation_rules SET display_count = display_count + 1 WHERE time_key='ANY' AND book_name=? AND chapter=? AND verse=?",
                               (candidate["book_name"], candidate["chapter"], candidate["verse"]))
                conn.commit()
                origin_marker = "📜"
                break

    if not target_verse:
        target_verse = {"book_name": "The Book Of Psalms", "chapter": 23, "verse": 1, "english_text": "The Lord is my shepherd, I shall not want."}
        origin_marker = "𓆟"

    cursor.execute("SELECT book_description FROM book_metadata WHERE book_name = ?", (target_verse["book_name"],))
    desc_row = cursor.fetchone()
    cursor.execute("SELECT chapter_summary FROM chapter_headers WHERE book_name = ? AND chapter = ?", (target_verse["book_name"], target_verse["chapter"]))
    summary_row = cursor.fetchone()
    cursor.execute("SELECT footnote_text FROM verse_footnotes WHERE book_name = ? AND chapter = ? AND verse = ?", (target_verse["book_name"], target_verse["chapter"], target_verse["verse"]))
    note_row = cursor.fetchone()

    payload = {
        "book": target_verse["book_name"], "chapter": target_verse["chapter"], "verse": target_verse["verse"], "text": target_verse["english_text"], "icon": origin_marker,
        "book_desc": desc_row["book_description"] if (desc_row and desc_row["book_description"]) else f"Historical context documentation for {target_verse['book_name']} will populate during production database hydration.",
        "chapter_summary": summary_row["chapter_summary"] if summary_row else f"Chapter {target_verse['chapter']} structural summary narration text loading...",
        "footnote": note_row["footnote_text"] if note_row else ""
    }
    conn.close()
    return payload