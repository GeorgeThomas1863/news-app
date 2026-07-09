from datetime import datetime, timezone
from types import SimpleNamespace

from app.pipeline import ingest_telegram


class FakeTelegramClient:
    def __init__(self, latest=None, new_messages=None):
        self.latest = latest
        self.new_messages = new_messages or []
        self.iter_calls = []

    async def get_messages(self, channel):
        if self.latest is None:
            return []
        return [self.latest]

    def iter_messages(self, channel, min_id=0, reverse=False):
        self.iter_calls.append({"channel": channel, "min_id": min_id, "reverse": reverse})

        async def generate():
            for message in self.new_messages:
                yield message

        return generate()


def make_message(msg_id, text, date=None):
    return SimpleNamespace(
        id=msg_id,
        raw_text=text,
        date=date or datetime(2026, 7, 8, 10, 0, 0, tzinfo=timezone.utc),
    )


async def test_first_poll_records_bookmark_and_returns_nothing(test_db):
    tg_client = FakeTelegramClient(latest=make_message(100, "latest post"))

    items = await ingest_telegram.fetch_new_channel_messages(tg_client, "somechannel")

    assert items == []
    state = await test_db.source_state.find_one(
        {"source_type": "telegram", "source_name": "somechannel"}
    )
    assert state["last_message_id"] == 100


async def test_first_poll_of_empty_channel_records_zero(test_db):
    tg_client = FakeTelegramClient(latest=None)

    items = await ingest_telegram.fetch_new_channel_messages(tg_client, "emptychannel")

    assert items == []
    state = await test_db.source_state.find_one(
        {"source_type": "telegram", "source_name": "emptychannel"}
    )
    assert state["last_message_id"] == 0


async def test_subsequent_poll_returns_new_messages_after_bookmark(test_db):
    await ingest_telegram.set_bookmark("somechannel", 100)
    published = datetime(2026, 7, 8, 11, 30, 0, tzinfo=timezone.utc)
    tg_client = FakeTelegramClient(
        new_messages=[
            make_message(101, "first new post", published),
            make_message(102, None),
            make_message(103, "second new post"),
        ]
    )

    items = await ingest_telegram.fetch_new_channel_messages(tg_client, "somechannel")

    assert tg_client.iter_calls == [{"channel": "somechannel", "min_id": 100, "reverse": True}]
    assert len(items) == 2
    assert items[0] == {
        "source_type": "telegram",
        "source_name": "somechannel",
        "url": "https://t.me/somechannel/101",
        "title": None,
        "text": "first new post",
        "published_at": published,
        "message_id": 101,
    }
    assert items[1]["message_id"] == 103


async def test_set_bookmark_upserts(test_db):
    await ingest_telegram.set_bookmark("somechannel", 100)
    await ingest_telegram.set_bookmark("somechannel", 250)

    state = await test_db.source_state.find_one(
        {"source_type": "telegram", "source_name": "somechannel"}
    )
    assert state["last_message_id"] == 250
    count = await test_db.source_state.count_documents({"source_name": "somechannel"})
    assert count == 1
