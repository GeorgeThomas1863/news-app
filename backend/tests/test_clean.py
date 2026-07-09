from datetime import datetime, timezone

from app import config
from app.pipeline import clean


def test_clean_text_strips_html_tags():
    result = clean.clean_text("<p>Hello <b>world</b></p>")
    assert result == "Hello world"


def test_clean_text_unescapes_html_entities():
    result = clean.clean_text("Tom &amp; Jerry &mdash; a &quot;classic&quot;")
    assert result == 'Tom & Jerry — a "classic"'


def test_clean_text_collapses_and_trims_whitespace():
    result = clean.clean_text("  Hello   \n\n world  \t again  ")
    assert result == "Hello world again"


def test_content_hash_stable_for_same_text_after_messy_formatting():
    cleaned_a = clean.clean_text("<p>Breaking   news</p>")
    cleaned_b = clean.clean_text("Breaking \n news  ")
    assert clean.content_hash(cleaned_a) == clean.content_hash(cleaned_b)


def test_content_hash_differs_for_different_text():
    hash_a = clean.content_hash("Breaking news")
    hash_b = clean.content_hash("Different story entirely")
    assert hash_a != hash_b


def test_build_clean_item_returns_raw_doc_shape(monkeypatch):
    monkeypatch.setattr(config, "MIN_TEXT_LENGTH", 10)
    published = datetime(2026, 7, 8, 9, 0, 0, tzinfo=timezone.utc)
    result = clean.build_clean_item(
        source_type="rss",
        source_name="Example Feed",
        url="https://example.com/a",
        title="A title",
        text="<p>A perfectly  long\n enough article body</p>",
        published_at=published,
    )
    assert result["source_type"] == "rss"
    assert result["source_name"] == "Example Feed"
    assert result["url"] == "https://example.com/a"
    assert result["title"] == "A title"
    assert result["text"] == "A perfectly long enough article body"
    assert result["published_at"] == published
    assert result["content_hash"] == clean.content_hash("A perfectly long enough article body")
    assert result["story_id"] is None
    assert result["embedding"] is None
    assert isinstance(result["ingested_at"], datetime)
    assert result["ingested_at"].tzinfo is not None


def test_build_clean_item_allows_none_title(monkeypatch):
    monkeypatch.setattr(config, "MIN_TEXT_LENGTH", 10)
    result = clean.build_clean_item(
        source_type="telegram",
        source_name="somechannel",
        url="https://t.me/somechannel/42",
        title=None,
        text="A telegram post that is long enough to keep",
        published_at=datetime(2026, 7, 8, 9, 0, 0, tzinfo=timezone.utc),
    )
    assert result["title"] is None


def test_build_clean_item_returns_none_below_min_text_length(monkeypatch):
    monkeypatch.setattr(config, "MIN_TEXT_LENGTH", 40)
    result = clean.build_clean_item(
        source_type="rss",
        source_name="Example Feed",
        url="https://example.com/a",
        title="A title",
        text="Too short",
        published_at="2026-07-08T00:00:00+00:00",
    )
    assert result is None
