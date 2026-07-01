import time
import sqlite3
from drbo_scraper import scrape_and_hydrate_drbo

# Map of standard DRBO book IDs to their max chapters to safely throttle scraping
# This includes the primary narrative historical blocks to aggressively fill your 1-24 hour matrix slots
TARGET_BOOKS = {
    1: 50,   # Genesis
    2: 40,   # Exodus
    3: 27,   # Leviticus
    4: 36,   # Numbers
    5: 34,   # Deuteronomy
    6: 24,   # Joshua
    7: 21,   # Judges
    8: 4,    # Ruth
    9: 31,   # 1 Kings (1 Samuel)
    10: 24,  # 2 Kings (2 Samuel)
    11: 22,  # 3 Kings (1 Kings)
    12: 25,  # 4 Kings (2 Kings)
    19: 150, # Psalms (Massive source for minute markers!)
    # --- New Testament Blocks ---
    55: 28,  # St. Matthew
    56: 16,  # St. Mark
    57: 24,  # St. Luke
    58: 21,  # St. John
    59: 28,  # Acts of the Apostles
}

def fill_master_database():
    print("🚀 Commencing Full DRBO Relational Hydration Campaign...")
    print("Database targets acquired. Processing book segments...")
    
    start_time = time.time()
    total_chapters_processed = 0
    
    for book_id, max_chapters in TARGET_BOOKS.items():
        print(f"\n📚 Processing Book ID [{book_id}] ── Target Chapters: 1 to {min(max_chapters, 24)}")
        
        # We only need chapters up to 24 because your clock interface bounds hours at 24!
        # This saves massive download time and keeps the database focused purely on clock matches.
        chapters_to_scrape = min(max_chapters, 24)
        if book_id == 19:  
            # Psalms is an exception where high verse counts happen early, but we still respect the hour ceiling
            chapters_to_scrape = 24 
            
        for chapter in range(1, chapters_to_scrape + 1):
            try:
                scrape_and_hydrate_drbo(book_id, chapter)
                total_chapters_processed += 1
                
                # Polite server throttling interval
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ Skipped execution item [Book {book_id}, Ch {chapter}]: {e}")
                continue

    elapsed = time.time() - start_time
    print("\n========================================================")
    print(f"🎉 Success! Relational database hydration complete.")
    print(f"Total Chapters Processed: {total_chapters_processed}")
    print(f"Execution Duration: {elapsed/60:.2f} minutes.")
    print("========================================================")

if __name__ == "__main__":
    fill_master_database()
