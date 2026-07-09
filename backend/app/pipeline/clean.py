import hashlib
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

from app import config


class _TagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self):
        return "".join(self.parts)


def clean_text(text):
    stripper = _TagStripper()
    stripper.feed(text)
    stripped = stripper.get_text()
    return re.sub(r"\s+", " ", stripped).strip()


def content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_clean_item(source_type, source_name, url, title, text, published_at):
    cleaned = clean_text(text)
    if len(cleaned) < config.MIN_TEXT_LENGTH:
        return None

    return {
        "source_type": source_type,
        "source_name": source_name,
        "url": url,
        "title": title,
        "text": cleaned,
        "published_at": published_at,
        "ingested_at": datetime.now(timezone.utc),
        "content_hash": content_hash(cleaned),
        "embedding": None,
        "story_id": None,
    }
