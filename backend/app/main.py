import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from telethon import TelegramClient
from telethon.sessions import StringSession

from app import auth, config, db
from app.pipeline import runner
from app.routes import pipeline as pipeline_routes
from app.routes import stories as stories_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_required_env()
    await db.init_db()
    app.state.tg_client = await connect_telegram()
    scheduler = asyncio.create_task(run_pipeline_on_schedule(app))

    yield

    scheduler.cancel()
    with suppress(asyncio.CancelledError):
        await scheduler
    if app.state.tg_client is not None:
        await app.state.tg_client.disconnect()
    await db.close_db()


def validate_required_env():
    required = {
        "PW_HASH": config.PW_HASH,
        "JWT_SECRET": config.JWT_SECRET,
        "ANTHROPIC_API_KEY": config.ANTHROPIC_API_KEY,
        "VOYAGE_API_KEY": config.VOYAGE_API_KEY,
    }
    if config.TELEGRAM_CHANNELS:
        required.update(
            {
                "TG_API_ID": config.TG_API_ID,
                "TG_API_HASH": config.TG_API_HASH,
                "TG_SESSION": config.TG_SESSION,
            }
        )

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"missing required environment variables: {', '.join(missing)}")


async def connect_telegram():
    if not config.TELEGRAM_CHANNELS:
        log.info("no telegram channels configured; telegram client not started")
        return None

    client = TelegramClient(
        StringSession(config.TG_SESSION), int(config.TG_API_ID), config.TG_API_HASH
    )
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError(
            "TG_SESSION is not authorized — mint a new one with: python -m app.tg_session"
        )
    log.info("telegram client connected")
    return client


async def run_pipeline_on_schedule(app: FastAPI):
    while True:
        if runner.is_paused():
            await asyncio.sleep(config.POLL_INTERVAL_MINUTES * 60)
            continue
        try:
            await runner.run_pipeline(app.state.tg_client, trigger="schedule")
        except Exception:
            log.exception("scheduled pipeline run crashed")
        await asyncio.sleep(config.POLL_INTERVAL_MINUTES * 60)


app = FastAPI(title="news-app", lifespan=lifespan)
app.include_router(auth.router, prefix="/api")
app.include_router(stories_routes.router, prefix="/api")
app.include_router(pipeline_routes.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", port=config.BACKEND_PORT, reload=True)
