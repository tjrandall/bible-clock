import time
import sqlite3
# Import BOTH the scraper and the database initializer subroutine
from drbo_scraper import scrape_and_hydrate_drbo, init_database

# ==============================================================================
# CONFIGURATION SWITCHES
# ==============================================================================
DEV_MODE = False  # 💡 Change to True for a fast ~1min dev iteration load (3 books, chapters 1-24 only)
# ==============================================================================

def fill_master_database():
    print("🚀 Commencing DRBO Relational Hydration Campaign...")
    
    # CRITICAL: Dynamically instantiate the 5 relational table skeletons on raw database files
    print("📦 Bootstrapping database schema structure and indexes...")
    init_database()
    
    start_time = time.time()
    total_chapters_attempted = 0
    total_chapters_saved = 0
    
    # No real book runs past this many chapters (Psalms, the longest, has 150) -
    # it's just an outer safety ceiling, not the real stopping condition.
    MAX_CHAPTER_SAFETY_CAP = 200

    if DEV_MODE:
        print("🛠️  [DEV MODE ACTIVE] - Targeting the 3 largest books to maximize clock density quickly.")
        # Top 3 highest chapter counts: Psalms (21), Isaias (27), and Jeremias (28)
        book_pool = [21, 27, 28]
        chapter_ceiling = 24  # Pull all 24 clock hours for these three giants
    else:
        print("🌍 [PRODUCTION MODE ACTIVE] - Preparing complete 73-book extraction sequence.")
        book_pool = list(range(1, 74))
        chapter_ceiling = MAX_CHAPTER_SAFETY_CAP  # real stopping point is each book's actual end (see below)

    print(f"Database targets acquired. Processing {len(book_pool)} structural books...\n")

    for book_id in book_pool:
        print(f"📚 Processing Book ID [{book_id}] ── Target Chapters: 1 to {chapter_ceiling}")

        for chapter in range(1, chapter_ceiling + 1):
            try:
                total_chapters_attempted += 1

                # Check for absolute data commitment
                success = scrape_and_hydrate_drbo(book_id, chapter)

                if success:
                    total_chapters_saved += 1
                elif not DEV_MODE:
                    # DRBO ran out of real chapters for this book - move on to the next one.
                    print(f"🛑 Book {book_id} ends at chapter {chapter - 1}. Moving to next book.")
                    break

                # Polite server throttling interval to protect network integrity
                time.sleep(0.4)

            except Exception as e:
                print(f"⚠️ Skipped processing unit [Book {book_id}, Ch {chapter}]: {e}")
                continue

    elapsed = time.time() - start_time
    print("\n========================================================")
    print(f"🎉 Relational database hydration complete.")
    print(f"Total Chapters Attempted: {total_chapters_attempted}")
    print(f"Total Chapters Successfully Saved: {total_chapters_saved}")
    print(f"Execution Duration: {elapsed/60:.2f} minutes.")
    print(f"Active Flag Profile State: {'DEVELOPMENT' if DEV_MODE else 'PRODUCTION'}")
    print("========================================================")

if __name__ == "__main__":
    fill_master_database()