"""CLI: one-time interactive Telegram login that prints a StringSession for .env.

Run locally (never inside Docker): uv run python -m app.tg_session
Prompts for phone + code on first login, then prints the TG_SESSION value to paste into .env.
"""

import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession

from app import config


async def main():
    api_id = int(config.TG_API_ID or input("TG api_id: "))
    api_hash = config.TG_API_HASH or input("TG api_hash: ")

    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        print("\nAdd this to your .env:\n")
        print(f"TG_SESSION={client.session.save()}")


if __name__ == "__main__":
    asyncio.run(main())
