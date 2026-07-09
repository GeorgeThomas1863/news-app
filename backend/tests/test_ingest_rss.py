from datetime import timezone

from app.pipeline import ingest_rss

FEED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>Story one</title>
      <link>https://example.com/one</link>
      <description>Summary of story one</description>
      <pubDate>Tue, 07 Jul 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Story two</title>
      <link>https://example.com/two</link>
      <description>Summary of story two</description>
      <pubDate>Tue, 07 Jul 2026 11:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def fake_fetch(xml):
    async def fetch(url):
        return xml

    return fetch


async def test_first_poll_snapshots_seen_urls_and_returns_nothing(test_db, monkeypatch):
    monkeypatch.setattr(ingest_rss, "fetch_feed_text", fake_fetch(FEED_XML))

    items = await ingest_rss.fetch_new_feed_entries("Example Feed", "https://example.com/feed")

    assert items == []
    state = await test_db.source_state.find_one(
        {"source_type": "rss", "source_name": "Example Feed"}
    )
    assert set(state["initial_seen_urls"]) == {
        "https://example.com/one",
        "https://example.com/two",
    }


async def test_subsequent_poll_returns_only_unseen_entries(test_db, monkeypatch):
    monkeypatch.setattr(ingest_rss, "fetch_feed_text", fake_fetch(FEED_XML))
    await test_db.source_state.insert_one(
        {
            "source_type": "rss",
            "source_name": "Example Feed",
            "initial_seen_urls": ["https://example.com/one"],
        }
    )

    items = await ingest_rss.fetch_new_feed_entries("Example Feed", "https://example.com/feed")

    assert len(items) == 1
    item = items[0]
    assert item["source_type"] == "rss"
    assert item["source_name"] == "Example Feed"
    assert item["url"] == "https://example.com/two"
    assert item["title"] == "Story two"
    assert item["text"] == "Summary of story two"
    assert item["published_at"].tzinfo == timezone.utc
    assert item["published_at"].hour == 11


async def test_entry_already_in_raw_collection_is_skipped(test_db, monkeypatch):
    monkeypatch.setattr(ingest_rss, "fetch_feed_text", fake_fetch(FEED_XML))
    await test_db.source_state.insert_one(
        {
            "source_type": "rss",
            "source_name": "Example Feed",
            "initial_seen_urls": ["https://example.com/one"],
        }
    )
    await test_db.raw.insert_one({"url": "https://example.com/two", "content_hash": "x"})

    items = await ingest_rss.fetch_new_feed_entries("Example Feed", "https://example.com/feed")

    assert items == []


async def test_entry_content_preferred_over_summary(test_db, monkeypatch):
    xml = FEED_XML.replace(
        "<description>Summary of story two</description>",
        "<description>Summary of story two</description>"
        '<content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/">'
        "Full body of story two</content:encoded>",
    )
    monkeypatch.setattr(ingest_rss, "fetch_feed_text", fake_fetch(xml))
    await test_db.source_state.insert_one(
        {
            "source_type": "rss",
            "source_name": "Example Feed",
            "initial_seen_urls": ["https://example.com/one"],
        }
    )

    items = await ingest_rss.fetch_new_feed_entries("Example Feed", "https://example.com/feed")

    assert items[0]["text"] == "Full body of story two"
