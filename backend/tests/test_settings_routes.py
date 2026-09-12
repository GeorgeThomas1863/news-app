from contextlib import asynccontextmanager

import bcrypt
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import auth, config
from app.routes import settings as settings_routes

TEST_PASSWORD = "correct-horse-battery"


@pytest_asyncio.fixture
async def client(test_db, monkeypatch):
    pw_hash = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
    monkeypatch.setattr(config, "PW_HASH", pw_hash)
    monkeypatch.setattr(config, "JWT_SECRET", "test-secret-thats-at-least-32-bytes-long!")
    monkeypatch.setattr(config, "SECURE_COOKIES", False)

    app = FastAPI()
    app.include_router(auth.router, prefix="/api")
    app.include_router(settings_routes.router, prefix="/api")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        await test_client.post("/api/auth/login", json={"password": TEST_PASSWORD})
        yield test_client


async def test_get_settings_requires_auth(client):
    client.cookies.clear()

    response = await client.get("/api/settings")

    assert response.status_code == 401


async def test_get_settings_returns_effective_and_allowed(client):
    response = await client.get("/api/settings")

    assert response.status_code == 200
    body = response.json()
    assert "filter_model" in body
    assert "scoring_model" in body
    assert "sources" in body
    assert body["allowed_models"]["anthropic"][0]["value"] == "claude-fable-5"


async def test_put_settings_updates_model(client):
    response = await client.put("/api/settings", json={"filter_model": "claude-haiku-4-5"})

    assert response.status_code == 200
    assert response.json()["success"] is True

    check = await client.get("/api/settings")
    assert check.json()["filter_model"] == "claude-haiku-4-5"
    assert check.json()["sources"]["filter_model"] == "db"


async def test_put_settings_rejects_unknown_model(client):
    response = await client.put("/api/settings", json={"filter_model": "totally-fake-model"})

    assert response.status_code == 400


async def test_put_settings_reset_to_null(client):
    await client.put("/api/settings", json={"filter_model": "claude-haiku-4-5"})
    response = await client.put("/api/settings", json={"filter_model": None})

    assert response.status_code == 200
    check = await client.get("/api/settings")
    assert check.json()["sources"]["filter_model"] != "db"
