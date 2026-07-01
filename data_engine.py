import sqlite3
import requests

def fetch_weather(lat: float, lon: float):
    """Fetches meteorological observations directly from Open-Meteo."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&temperature_unit=fahrenheit&windspeed_unit=mph"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get('current_weather', {})
    except Exception: 
        pass
    return {"temperature": "--", "windspeed": "--"}

def get_clock_display_data(time_key: str):
    """
    Executes relational query operations to build the 6-zone interface.
    Applies display_count sorting to ensure fair distribution across choices.
    """
    conn = sqlite3.connect("bible_clock.db")
    conn.row_factory = sqlite3.Row # Allows column indexing by string header key names
    cursor = conn.cursor()

    # 1. Identify active configuration constraints
    cursor.execute("SELECT * FROM curation_rules WHERE time_key = ?", (time_key,))
    user_rules = cursor.fetchall()
    
    preferred_rules = [r for r in user_rules if r["rule_state"] == "Preferred"]
    blocked_rules = [f"{r['book_name']}_{r['chapter']}:{r['verse']}" for r in user_rules if r["rule_state"] == "Block"]
    
    target_verse = None
    origin_marker = "✝" 

    # 2. Evaluate state rotation priority arrays
    if preferred_rules:
        # FAIR DISTRIBUTION LOOP: Select the favored record display item shown the least
        preferred_rules = sorted(preferred_rules, key=lambda x: x["display_count"])
        selected_rule = preferred_rules[0]
        
        cursor.execute("SELECT * FROM verses_library WHERE book_name=? AND chapter=? AND verse=?",
                       (selected_rule["book_name"], selected_rule["chapter"], selected_rule["verse"]))
        target_verse = cursor.fetchone()
        
        # Increment counter records
        cursor.execute("UPDATE curation_rules SET display_count = display_count + 1 WHERE time_key=? AND book_name=? AND chapter=? AND verse=?",
                       (time_key, selected_rule["book_name"], selected_rule["chapter"], selected_rule["verse"]))
        conn.commit()
        origin_marker = "⭐"

    if not target_verse:
        # Run standard active lookup matching pools
        cursor.execute("SELECT * FROM verses_library WHERE time_key = ?", (time_key,))
        all_matches = cursor.fetchall()
        
        # Filter exclusions
        valid_pool = [m for m in all_matches if f"{m['book_name']}_{m['chapter']}:{m['verse']}" not in blocked_rules]
        
        if valid_pool:
            for item in valid_pool:
                cursor.execute("INSERT OR IGNORE INTO curation_rules (time_key, book_name, chapter, verse, rule_state) VALUES (?, ?, ?, ?, 'Show')",
                               (time_key, item["book_name"], item["chapter"], item["verse"]))
            conn.commit()
            
            # Sort standard options by least displayed to achieve fair distribution
            cursor.execute("SELECT * FROM curation_rules WHERE time_key = ? AND rule_state = 'Show'", (time_key,))
            active_shows = cursor.fetchall()
            active_shows = sorted(active_shows, key=lambda x: x["display_count"])
            
            selected_show = active_shows[0]
            cursor.execute("SELECT * FROM verses_library WHERE book_name=? AND chapter=? AND verse=?",
                           (selected_show["book_name"], selected_show["chapter"], selected_show["verse"]))
            target_verse = cursor.fetchone()
            
            cursor.execute("UPDATE curation_rules SET display_count = display_count + 1 WHERE time_key=? AND book_name=? AND chapter=? AND verse=?",
                           (time_key, selected_show["book_name"], selected_show["chapter"], selected_show["verse"]))
            conn.commit()
        
    # Safe Fallback Framework
    if not target_verse:
        target_verse = {"book_name": "The Book Of Psalms", "chapter": 23, "verse": 1, "english_text": "The Lord is my shepherd, I shall not want."}
        origin_marker = "𓆟"

    # 3. COMPILING STRUCTURAL RELATIONAL METADATA VIA SQL JOINS
    cursor.execute("SELECT book_description FROM book_metadata WHERE book_name = ?", (target_verse["book_name"],))
    desc_row = cursor.fetchone()
    
    cursor.execute("SELECT chapter_summary FROM chapter_headers WHERE book_name = ? AND chapter = ?", 
                   (target_verse["book_name"], target_verse["chapter"]))
    summary_row = cursor.fetchone()
    
    cursor.execute("SELECT footnote_text FROM verse_footnotes WHERE book_name = ? AND chapter = ? AND verse = ?", 
                   (target_verse["book_name"], target_verse["chapter"], target_verse["verse"]))
    note_row = cursor.fetchone()

    payload = {
        "book": target_verse["book_name"],
        "chapter": target_verse["chapter"],
        "verse": target_verse["verse"],
        "text": target_verse["english_text"],
        "icon": origin_marker,
        "book_desc": desc_row["book_description"] if desc_row else "Introductory notes parsing...",
        "chapter_summary": summary_row["chapter_summary"] if summary_row else "Summary parameters loading...",
        "footnote": note_row["footnote_text"] if note_row else ""
    }
    
    conn.close()
    return payload