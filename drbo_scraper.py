import re
import sqlite3
import requests
from bs4 import BeautifulSoup

# Global DRBO identification dictionary to prevent layout structural parsing failures
DRBO_BOOK_MAP = {
    1: "Genesis", 2: "Exodus", 3: "Leviticus", 4: "Numbers", 5: "Deuteronomy",
    6: "Joshua", 7: "Judges", 8: "Ruth", 9: "1 Kings", 10: "2 Kings",
    11: "3 Kings", 12: "4 Kings", 19: "Psalms", 55: "St. Matthew",
    56: "St. Mark", 57: "St. Luke", 58: "St. John", 59: "Acts"
}

def init_database():
    """Creates the bible_clock.db file and initializes tables."""
    conn = sqlite3.connect("bible_clock.db")
    cursor = conn.cursor()
    
    # Core verses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verses_library (
            time_key TEXT, 
            book_name TEXT, 
            chapter INTEGER, 
            verse INTEGER, 
            english_text TEXT, 
            latin_text TEXT
        )""")
        
    # Footnotes / Commentary annotations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verse_footnotes (
            book_name TEXT, 
            chapter INTEGER, 
            verse INTEGER, 
            footnote_text TEXT
        )""")
        
    # Structural Book descriptions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_metadata (
            book_name TEXT PRIMARY KEY, 
            book_description TEXT
        )""")
        
    # Chapter summary headers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chapter_headers (
            book_name TEXT, 
            chapter INTEGER, 
            chapter_summary TEXT, 
            PRIMARY KEY (book_name, chapter)
        )""")
        
    # Dynamic user overrides, display counters, and states table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS curation_rules (
            time_key TEXT, 
            book_name TEXT, 
            chapter INTEGER, 
            verse INTEGER, 
            rule_state TEXT, 
            display_count INTEGER DEFAULT 0,
            PRIMARY KEY (time_key, book_name, chapter, verse)
        )""")
        
    conn.commit()
    conn.close()

def scrape_and_hydrate_drbo(book_id: int, chapter_num: int):
    """Parses a target chapter from drbo.org and saves it to SQLite."""
    url = f"https://drbo.org/lvb/chapter/{book_id:02d}{chapter_num:03d}.htm"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: 
            print(f"⚠️ Page missing/inaccessible: {url}")
            return
    except Exception as e:
        print(f"Connection failed to {url}: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    conn = sqlite3.connect("bible_clock.db")
    cursor = conn.cursor()

    # Dynamic Lookup using our trusted global book register index map
    book_name = DRBO_BOOK_MAP.get(book_id, f"Book_{book_id}")

    # Capture Chapter Summary / Description
    header_div = soup.find('div', class_='chapdesc') or soup.find('p', class_='sub')
    if header_div:
        cursor.execute("INSERT OR REPLACE INTO chapter_headers VALUES (?, ?, ?)", 
                       (book_name, chapter_num, header_div.text.strip()))

    # Capture Verses and Footnotes
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        text_block = p.get_text().strip()
        
        # Check if line is an annotation footnote block
        if text_block.startswith("[") and "]" in text_block:
            try:
                verse_num = int(text_block.split("]")[0].replace("[", "").strip())
                cursor.execute("INSERT INTO verse_footnotes (book_name, chapter, verse, footnote_text) VALUES (?, ?, ?, ?)",
                               (book_name, chapter_num, verse_num, text_block))
            except ValueError: 
                continue
            
        # Handle standard text verse lines
        else:
            verse_tag = p.find('b')
            if verse_tag and verse_tag.text.strip().isdigit():
                verse_num = int(verse_tag.text.strip())
                
                # Match strict clock bounds (Chapter 1-24, Verse 1-59)
                if (1 <= chapter_num <= 24) and (1 <= verse_num <= 59):
                    time_key = f"{chapter_num:02d}:{verse_num:02d}"
                    english_txt = text_block.replace(str(verse_num), "", 1).strip()
                    
                    cursor.execute("INSERT INTO verses_library (time_key, book_name, chapter, verse, english_text, latin_text) VALUES (?, ?, ?, ?, ?, ?)",
                                   (time_key, book_name, chapter_num, verse_num, english_txt, ""))

    conn.commit()
    conn.close()
    print(f"Successfully loaded {book_name} Chapter {chapter_num} into SQLite framework.")

if __name__ == "__main__":
    init_database()