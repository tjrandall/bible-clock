import os
import sqlite3
import requests
from bs4 import BeautifulSoup

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bible_clock.db")

# Global DRBO identification dictionary containing all 73 structural books
DRBO_BOOK_MAP = {
    # --- OLD TESTAMENT ---
    1: "Genesis", 2: "Exodus", 3: "Leviticus", 4: "Numbers", 5: "Deuteronomy",
    6: "Joshua", 7: "Judges", 8: "Ruth", 9: "1 Kings", 10: "2 Kings",
    11: "3 Kings", 12: "4 Kings", 13: "1 Chronicles", 14: "2 Chronicles",
    15: "1 Esdras", 16: "2 Esdras (Nehemiah)", 17: "Tobias", 18: "Judith",
    19: "Esther", 20: "Job", 21: "Psalms", 22: "Proverbs", 23: "Ecclesiastes",
    24: "Canticle of Canticles", 25: "Wisdom", 26: "Ecclesiasticus",
    27: "Isaias", 28: "Jeremias", 29: "Lamentations", 30: "Baruch",
    31: "Ezechiel", 32: "Daniel", 33: "Osee", 34: "Joel", 35: "Amos",
    36: "Abdias", 37: "Jonas", 38: "Micheas", 39: "Nahum", 40: "Habacuc",
    41: "Sophonias", 42: "Aggeus", 43: "Zacharias", 44: "Malachias",
    45: "1 Machabees", 46: "2 Machabees",

    # --- NEW TESTAMENT ---
    47: "St. Matthew", 48: "St. Mark", 49: "St. Luke", 50: "St. John",
    51: "Acts of the Apostles", 52: "Romans", 53: "1 Corinthians", 54: "2 Corinthians",
    55: "Galatians", 56: "Ephesians", 57: "Philippians", 58: "Colossians",
    59: "1 Thessalonians", 60: "2 Thessalonians", 61: "1 Timothy", 62: "2 Timothy",
    63: "Titus", 64: "Philemon", 65: "Hebrews", 66: "St. James",
    67: "1 St. Peter", 68: "2 St. Peter", 69: "1 St. John", 70: "2 St. John",
    71: "3 St. John", 72: "St. Jude", 73: "Apocalypse (Revelation)"
}

# Short static book-level summaries (not scrapable from DRBO chapter pages)
BOOK_DESCRIPTIONS = {
    "Genesis": "Creation, the patriarchs, and the origins of Israel.",
    "Exodus": "Israel's bondage in Egypt, the Exodus, and the giving of the Law.",
    "Leviticus": "Priestly law, ritual purity, and instructions for worship.",
    "Numbers": "The census of Israel and the wilderness journey to Canaan.",
    "Deuteronomy": "Moses' final addresses restating the Law before entering Canaan.",
    "Joshua": "The conquest and division of the Promised Land.",
    "Judges": "Israel's cycles of apostasy, oppression, and deliverance by judges.",
    "Ruth": "A Moabite widow's loyalty and inclusion in Israel's lineage.",
    "1 Kings": "Samuel, Saul, and the rise of David (1 Samuel).",
    "2 Kings": "The reign of David (2 Samuel).",
    "3 Kings": "Solomon's reign and the division of the kingdom (1 Kings).",
    "4 Kings": "The kings of Israel and Judah to the Babylonian exile (2 Kings).",
    "1 Chronicles": "Genealogies and David's reign retold.",
    "2 Chronicles": "Solomon and the kings of Judah to the exile.",
    "1 Esdras": "The return from exile and rebuilding of the Temple (Ezra).",
    "2 Esdras (Nehemiah)": "Rebuilding Jerusalem's walls under Nehemiah.",
    "Tobias": "A tale of piety, trial, and divine providence in exile.",
    "Judith": "A widow's courage delivers Israel from a besieging army.",
    "Esther": "A Jewish queen saves her people from destruction in Persia.",
    "Job": "A righteous man's suffering and the mystery of divine justice.",
    "Psalms": "150 poems of praise, lament, and prayer.",
    "Proverbs": "Wisdom sayings on righteous and prudent living.",
    "Ecclesiastes": "Reflections on the vanity and meaning of life.",
    "Canticle of Canticles": "A love poem read as an allegory of divine love.",
    "Wisdom": "Meditations on divine wisdom and the fate of the just.",
    "Ecclesiasticus": "Practical wisdom and moral instruction (Sirach).",
    "Isaias": "Prophecies of judgment, comfort, and the coming Messiah.",
    "Jeremias": "A prophet's warnings to Judah before the Babylonian exile.",
    "Lamentations": "Mourning over the destruction of Jerusalem.",
    "Baruch": "A scribe's reflections in the shadow of exile.",
    "Ezechiel": "Visions of judgment and restoration during the exile.",
    "Daniel": "Faithfulness in exile and apocalyptic visions of the future.",
    "Osee": "A prophet's marriage as a picture of Israel's unfaithfulness (Hosea).",
    "Joel": "A call to repentance after locust plague, and the Day of the Lord.",
    "Amos": "Judgment on Israel's social injustice and false worship.",
    "Abdias": "Judgment against Edom for its treachery against Israel (Obadiah).",
    "Jonas": "A reluctant prophet sent to warn Nineveh (Jonah).",
    "Micheas": "Judgment and hope for Israel and Judah (Micah).",
    "Nahum": "The coming fall of Nineveh.",
    "Habacuc": "A dialogue questioning God's justice amid Babylon's rise.",
    "Sophonias": "Warning of the Day of the Lord and a remnant's hope (Zephaniah).",
    "Aggeus": "A call to rebuild the Temple after the exile (Haggai).",
    "Zacharias": "Visions encouraging Temple rebuilding and messianic hope.",
    "Malachias": "Final prophetic rebukes and promise of a coming messenger.",
    "1 Machabees": "The Jewish revolt against Hellenistic oppression.",
    "2 Machabees": "A theological retelling of the Maccabean revolt.",
    "St. Matthew": "Jesus as the promised Messiah, from birth to resurrection.",
    "St. Mark": "A fast-paced account of Jesus' ministry, death, and resurrection.",
    "St. Luke": "Jesus' life with attention to the poor, women, and outcasts.",
    "St. John": "Jesus' divinity through signs, discourses, and the Passion.",
    "Acts of the Apostles": "The early Church's growth from Jerusalem to Rome.",
    "Romans": "Paul's exposition of sin, grace, and justification by faith.",
    "1 Corinthians": "Paul addresses division and disorder in the Corinthian church.",
    "2 Corinthians": "Paul defends his apostleship and calls for reconciliation.",
    "Galatians": "Paul defends salvation by faith against legalism.",
    "Ephesians": "The unity of the Church in Christ.",
    "Philippians": "Paul's letter of joy and encouragement from prison.",
    "Colossians": "The supremacy of Christ over false teachings.",
    "1 Thessalonians": "Encouragement and teaching on Christ's return.",
    "2 Thessalonians": "Clarifying misunderstandings about the Day of the Lord.",
    "1 Timothy": "Pastoral instruction for church leadership and order.",
    "2 Timothy": "Paul's final charge to Timothy to persevere in ministry.",
    "Titus": "Instructions for organizing the church in Crete.",
    "Philemon": "Paul's appeal for the runaway slave Onesimus.",
    "Hebrews": "Christ's superiority as the great high priest.",
    "St. James": "Practical faith expressed through works and endurance.",
    "1 St. Peter": "Encouragement to persevere through suffering.",
    "2 St. Peter": "Warnings against false teachers and the coming judgment.",
    "1 St. John": "Assurance of faith through love and truth.",
    "2 St. John": "A brief warning against false teachers.",
    "3 St. John": "Commendation of hospitality shown to traveling teachers.",
    "St. Jude": "A warning against false teachers who corrupt the faith.",
    "Apocalypse (Revelation)": "Apocalyptic visions of the end times and Christ's triumph.",
}

def init_database():
    # Creates the bible_clock.db file and initializes tables.
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Core verses table
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS verses_library ("
        "time_key TEXT, "
        "book_name TEXT, "
        "chapter INTEGER, "
        "verse INTEGER, "
        "english_text TEXT, "
        "latin_text TEXT, "
        "PRIMARY KEY (book_name, chapter, verse))"
    )
        
    # Footnotes / Commentary annotations table
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS verse_footnotes ("
        "book_name TEXT, "
        "chapter INTEGER, "
        "verse INTEGER, "
        "footnote_text TEXT, "
        "PRIMARY KEY (book_name, chapter, verse, footnote_text))"
    )

    # Structural Book descriptions table
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS book_metadata ("
        "book_name TEXT PRIMARY KEY, "
        "book_description TEXT)"
    )

    # Populate static book-level descriptions (idempotent)
    cursor.executemany(
        "INSERT OR IGNORE INTO book_metadata (book_name, book_description) VALUES (?, ?)",
        list(BOOK_DESCRIPTIONS.items())
    )
        
    # Chapter summary headers table
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS chapter_headers ("
        "book_name TEXT, "
        "chapter INTEGER, "
        "chapter_summary TEXT, "
        "PRIMARY KEY (book_name, chapter))"
    )
        
    # Dynamic user overrides, display counters, and states table
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS curation_rules ("
        "time_key TEXT, "
        "book_name TEXT, "
        "chapter INTEGER, "
        "verse INTEGER, "
        "rule_state TEXT, "
        "display_count INTEGER DEFAULT 0, "
        "PRIMARY KEY (time_key, book_name, chapter, verse))"
    )

    # Key-value app configuration (e.g. day/night/sleep schedule hours)
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS app_settings ("
        "setting_key TEXT PRIMARY KEY, "
        "setting_value TEXT)"
    )

    # Seed schedule defaults (idempotent - won't clobber a user's saved settings)
    cursor.executemany(
        "INSERT OR IGNORE INTO app_settings (setting_key, setting_value) VALUES (?, ?)",
        [("day_start_hour", "7"), ("night_start_hour", "19"), ("sleep_start_hour", "23"), ("sleep_end_hour", "5")]
    )


    conn.commit()
    conn.close()

def scrape_and_hydrate_drbo(book_id: int, chapter_num: int) -> bool:
    # Parses a target chapter from drbo.org and saves it to SQLite.
    # Returns True if successful, False if missing/failed.
    
    url = f"https://drbo.org/chapter/{book_id:02d}{chapter_num:03d}.htm"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # DRBO doesn't 404 a missing chapter - it soft-redirects to /404.htm
        if response.history:
            print(f"🚫 Chapter does not exist (soft-404 redirect): Book {book_id}, Ch {chapter_num}")
            return False
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code} - Missing/Blocked: Book {book_id}, Ch {chapter_num}")
            return False
    except Exception as e:
        print(f"💥 Network Error on Book {book_id}, Ch {chapter_num}: {e}")
        return False

    soup = BeautifulSoup(response.content, 'html.parser')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Dynamic Lookup using our trusted global book register index map
    book_name = DRBO_BOOK_MAP.get(book_id, f"Book_{book_id}")

    # Capture Chapter Summary / Description
    header_p = soup.find('p', class_='desc')
    if header_p:
        cursor.execute("INSERT OR REPLACE INTO chapter_headers VALUES (?, ?, ?)",
                       (book_name, chapter_num, header_p.get_text().strip()))

    # Track if any valid clock verses were written to disk
    verses_written = False

    # Capture Verses and Footnotes
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        text_block = p.get_text().strip()

        # Check if line is an annotation footnote block
        if text_block.startswith("[") and "]" in text_block:
            try:
                verse_num = int(text_block.split("]")[0].replace("[", "").strip())
                cursor.execute("INSERT OR IGNORE INTO verse_footnotes (book_name, chapter, verse, footnote_text) VALUES (?, ?, ?, ?)",
                               (book_name, chapter_num, verse_num, text_block))
            except ValueError:
                continue

        # Standard verse paragraphs: multiple verses share one <p>, each verse
        # introduced by an <a class="vn"> anchor holding its verse number.
        else:
            verse_anchors = p.find_all('a', class_='vn')
            for anchor in verse_anchors:
                anchor_text = anchor.get_text().strip()
                if not anchor_text.isdigit():
                    continue
                verse_num = int(anchor_text)

                # Verse text = everything between this anchor and the next verse anchor
                text_parts = []
                for sibling in anchor.next_siblings:
                    if getattr(sibling, "name", None) == "a" and "vn" in (sibling.get("class") or []):
                        break
                    text_parts.append(sibling.get_text() if hasattr(sibling, "get_text") else str(sibling))
                english_txt = "".join(text_parts).strip()

                # Clock-representable verses (chapters 1-24, verses 1-59) get a time_key;
                # everything else is still stored (for search/catalog/pinning) with time_key NULL
                # so it never appears as a "natural" match on the clock.
                if (1 <= chapter_num <= 24) and (1 <= verse_num <= 59):
                    # Strategic Routing: Map Chapter 24 directly to the 00:xx Midnight block
                    if chapter_num == 24:
                        time_key = f"00:{verse_num:02d}"
                    else:
                        time_key = f"{chapter_num:02d}:{verse_num:02d}"
                else:
                    time_key = None

                cursor.execute("INSERT OR REPLACE INTO verses_library (time_key, book_name, chapter, verse, english_text, latin_text) VALUES (?, ?, ?, ?, ?, ?)",
                               (time_key, book_name, chapter_num, verse_num, english_txt, ""))
                verses_written = True

    conn.commit()
    conn.close()

    if verses_written:
        print(f"📖 Successfully loaded {book_name} Chapter {chapter_num} into SQLite framework.")
        return True
    else:
        print(f"⚠️ Processed {book_name} Chapter {chapter_num}, but no verses were found.")
        return False

if __name__ == "__main__":
    init_database()
