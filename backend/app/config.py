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

# --- sources (moves to UI settings in a later version) ---
RSS_FEEDS = [
    # {"name": "Example Feed", "url": "https://example.com/feed"},
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
STORIES_PER_TOPIC = 5
MIN_TEXT_LENGTH = 40

# --- models ---
EMBED_MODEL = "voyage-4-lite"
FILTER_MODEL = "claude-haiku-4-5"
SCORING_MODEL = "claude-sonnet-5"

# --- auth ---
JWT_EXPIRY_HOURS = 24
AUTH_COOKIE_NAME = "news_token"
