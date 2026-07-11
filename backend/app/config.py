import os
from pathlib import Path

from dotenv import load_dotenv

# repo-root .env; in Docker the same vars arrive via compose env_file
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# --- secrets / environment ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "news_app")
PW_HASH = os.environ.get("PW_HASH")
JWT_SECRET = os.environ.get("JWT_SECRET")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
TG_API_ID = os.environ.get("TG_API_ID")
TG_API_HASH = os.environ.get("TG_API_HASH")
TG_SESSION = os.environ.get("TG_SESSION")
SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "false").lower() == "true"
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))

# --- sources (moves to UI settings in a later version) ---
RSS_FEEDS = [
    # all URLs live-verified 2026-07-09 through fetch_feed_text; see rss_info.txt
    # -- geopolitics / world --
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Guardian World", "url": "https://www.theguardian.com/world/rss"},
    {"name": "War on the Rocks", "url": "https://warontherocks.com/feed/"},
    {"name": "Defense One", "url": "https://www.defenseone.com/rss/all/"},
    # -- ukraine --
    {"name": "Kyiv Independent", "url": "https://kyivindependent.com/feed/rss"},
    {"name": "Ukrainska Pravda", "url": "https://www.pravda.com.ua/eng/rss/view_news/"},
    # -- middle east --
    {"name": "BBC Middle East", "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"},
    {"name": "Times of Israel", "url": "https://www.timesofisrael.com/feed/"},
    # -- markets --
    {"name": "CNBC Top News", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"name": "CNBC Markets", "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html"},
    {"name": "Financial Times", "url": "https://www.ft.com/rss/home"},
    {"name": "Economist Finance", "url": "https://www.economist.com/finance-and-economics/rss.xml"},
    # -- tech --
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    # -- domestic us --
    {"name": "Politico", "url": "https://rss.politico.com/politics-news.xml"},
    {"name": "NPR Politics", "url": "https://feeds.npr.org/1014/rss.xml"},
    {"name": "Axios", "url": "https://api.axios.com/feed/"},
    {"name": "BBC US & Canada", "url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"},
]
TELEGRAM_CHANNELS = [
    # "channelusername",
]

# --- pipeline behavior ---
TOPICS = ["Geopolitics", "Ukraine", "Middle East", "Markets", "Tech", "Domestic US"]
POLL_INTERVAL_MINUTES = 15
SIM_HIGH = 0.85
SIM_LOW = 0.70
ACTIVE_WINDOW_HOURS = 48
DECAY_HALF_LIFE_HOURS = 24
RANKING_WINDOW_HALF_LIVES = 10  # stories older than this many half-lives never outrank fresh ones
STORIES_PER_TOPIC = 5
MIN_TEXT_LENGTH = 40

# --- models ---
EMBED_MODEL = "voyage-4-lite"
FILTER_MODEL = "claude-haiku-4-5"
SCORING_MODEL = "claude-sonnet-5"

# --- auth ---
JWT_EXPIRY_HOURS = 24
AUTH_COOKIE_NAME = "news_token"
