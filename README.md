# 🕒 Bible Clock Dashboard

An interactive, multi-zone digital wall clock and theological study workstation built using **Streamlit** and a local **SQLite** relational database engine. The system transforms a clock into an immersive contemplative experience by mapping every minute of the day to matching chapter-and-verse boundaries extracted from the historic Douay-Rheims translation via `drbo.org`.

---

## 🎨 Layout Matrix Architecture

The interface utilizes a responsive grid layout to partition historical text metadata, real-time meteorological inputs, and hero typography spaces into a unified 6-zone display:

```
┌──────────────────────────────────────┐┌──────────────────────────────────────┐
│  📖 BOOK CONTEXT SUMMARY              ││  🕒 HERO DIGITAL WALL CLOCK          │
│  Initial background, historical      ││                                      │
│  notes, and linguistic origins.       ││              08:44 PM                │
├──────────────────────────────────────┤└──────────────────────────────────────┘
│  📍 CHAPTER HEADER OVERVIEW          │┌──────────────────────────────────────┐
│  High-level breakdown of action      ││  ✝ CORE SCRIPTURE DISPLAY            │
│  narratives inside the block.        ││  Exodus 20:2                         │
├──────────────────────────────────────┤│  "I am the Lord thy God, who..."     │
│  🌤️ METEOROLOGICAL CONDITIONS        │└──────────────────────────────────────┘
│  Dual-unit real-time temperature     │┌──────────────────────────────────────┐
│  Fahrenheit & Celsius tracking with  ││  📝 VERSE COMMENTARY FOOTNOTES      │
│  surface wind speed monitoring.      ││  Theological textual annotations.   │
└──────────────────────────────────────┘└──────────────────────────────────────┘

```

### 🎛️ Minimalist Structural Status Icons

The dashboard relies on clean, text-free visual iconography right next to the active citation to quickly verify the structural source of the displayed text:

* **`✝` (Cross):** Identifies a standard, exact database `Chapter:Verse` structural match for the current minute.
* **`⭐` (Star):** Appears when the slot is pulling from your customized, hand-pinned favorite rotation pool.
* **`𓆟` (Jesus Fish / Ichthys):** Indicates that a time slot is running the emergency, beautiful fill-in fallback verse (*Psalms 23:1*) to maintain interface stability.

To ensure a larger variety of quotes, the system will consider chapter:verse selections for both the AM/PM version of time, as well as the 24HR version of time.  For example, it will pull chapter:verse matches for 13:28 and 1:28 PM.

---

## 🚀 Initial Installation & Setup

Follow these steps to initialize your virtual environment, construct your local relational database, and boot the interface layer.

### 1. Clone and Navigate to the Repository

```bash
git clone https://github.com/yourusername/bible-clock.git
cd bible-clock

```

### 2. Establish and Hydrate Your Virtual Environment

```bash
# Instantiate the local Python virtual environment tracking layer
python3 -m venv venv

# Activate the workspace sandbox sheet
source venv/bin/activate

# Upgrade the local installation package pip arrays
pip install --upgrade pip

# Hydrate the third-party framework dependencies (Streamlit, BeautifulSoup4, etc.)
pip install -r requirements.txt

```

### 3. Compile Your Relational Database Layer

Execute the master automation crawl script. This initializes your local `bible_clock.db` binary and maps out the target text rows, summaries, and annotations from online repositories into indexed relational tables:

```bash
python3 hydrate_all_books.py

```

*Note: Due to our explicit `.gitignore` policy, the compiled `bible_clock.db` file stays hidden from tracking arrays, keeping version control lightweight while allowing easy deployment to fresh hardware targets.*

### 4. Fire Up the Dashboard Interface

```bash
streamlit run app.py

```

Your local system will immediately spin up the Streamlit server and launch a fresh browser window housing the live dashboard interface.

---

## ⚙️ Core System Administration & Management

The clock features two distinct workspace modes separated via top-level navigation tabs:

### 🕒 Minimalist Wall Clock (Kiosk Mode)

Designed for dedicated smart displays, tablets, or wall-mounted monitors. This view strips away all configuration controls, development sidebars, and header options to reveal a clean, high-contrast, distraction-free dashboard.

### ⚙️ Master Curation Matrix

Your operational control deck. It automatically pulls the active time coordinates, searches the database for all 12-hour and 24-hour alternate matching verses simultaneously, and lets you manage text visibility:

* **📌 Pin to Favorites Pool:** Add multiple verses to a single time slot. The engine uses a **Fair-Distribution Rotation Algorithm**, checking relative display histories (`display_count`) to ensure every favorite verse gets an even share of screen time.
* **❌ Block Entire Minute Slot:** Instantly bans problematic or truncated single-line items from ever rendering on the display panel.
* **🗺️ Meteorological Preset Targets:** Switch your active weather calculation source on the fly between different regional station coordinates (e.g., Downtown Plymouth vs. South Station).

---

## 🛠️ Relational Database Schema Architecture

The internal storage layer runs completely inside a localized **SQLite** instance (`bible_clock.db`), eliminating external server dependencies. The relational tables cross-reference seamlessly via SQL indexes:

```
  ┌───────────────────────┐             ┌───────────────────────┐
  │    verses_library     │             │    verse_footnotes    │
  ├───────────────────────┤             ├───────────────────────┤
  │ time_key (INDEX)      │             │ book_name             │
  │ book_name             │────────────►│ chapter               │
  │ chapter               │             │ verse                 │
  │ verse                 │             │ footnote_text         │
  │ english_text          │             └───────────────────────┘
  │ latin_text            │
  └───────────────────────┘             ┌───────────────────────┐
              │                         │    chapter_headers    │
              │                         ├───────────────────────┤
              └────────────────────────►│ book_name             │
              │                         │ chapter               │
              │                         │ chapter_summary       │
              │                         └───────────────────────┘
              ▼
  ┌───────────────────────┐             ┌───────────────────────┐
  │     book_metadata     │             │    curation_rules     │
  ├───────────────────────┤             ├───────────────────────┤
  │ book_name (PK)        │             │ time_key (PK)         │
  │ book_description      │             │ book_name (PK)        │
  └───────────────────────┘             │ chapter (PK)          │
                                        │ verse (PK)            │
                                        │ rule_state            │
                                        │ display_count         │
                                        └───────────────────────┘

```

---

## 🗺️ Future Enhancements / TODO

- Extend the ⚙️ **Master Curation Matrix** screen to pin a favorite to an arbitrary chosen time slot (like the 📚 Verse Catalog & Search screen already does), instead of only the current literal minute.

---

## 📝 License

This project is licensed under the MIT License - see the `LICENSE` file for details. All scripture and commentary text pulled via the scraping utilities reside entirely within the Public Domain.
