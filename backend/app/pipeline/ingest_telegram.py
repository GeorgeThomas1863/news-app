from app import db


async def fetch_new_channel_messages(tg_client, channel):
    """Returns pre-clean item dicts newer than the channel bookmark; empty on first poll (no backfill)."""
    state = await db.source_state.find_one(
        {"source_type": "telegram", "source_name": channel}
    )
    if state is None:
        await record_initial_bookmark(tg_client, channel)
        return []

    items = []
    async for message in tg_client.iter_messages(
        channel, min_id=state["last_message_id"], reverse=True
    ):
        item = build_message_item(channel, message)
        if item is None:
            continue
        items.append(item)
    return items


async def record_initial_bookmark(tg_client, channel):
    latest = await tg_client.get_messages(channel)
    last_id = latest[0].id if latest else 0
    await set_bookmark(channel, last_id)


async def set_bookmark(channel, last_message_id):
    await db.source_state.update_one(
        {"source_type": "telegram", "source_name": channel},
        {"$set": {"last_message_id": last_message_id}},
        upsert=True,
    )


def build_message_item(channel, message):
    if not message.raw_text:
        return None

    return {
        "source_type": "telegram",
        "source_name": channel,
        "url": f"https://t.me/{channel}/{message.id}",
        "title": None,
        "text": message.raw_text,
        "published_at": message.date,
        "message_id": message.id,
    }
