from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import auth, config

TEST_PASSWORD = "correct-horse-battery"


@pytest.fixture
def client(monkeypatch):
    pw_hash = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
    monkeypatch.setattr(config, "PW_HASH", pw_hash)
    monkeypatch.setattr(config, "JWT_SECRET", "test-secret-thats-at-least-32-bytes-long!")
    monkeypatch.setattr(config, "SECURE_COOKIES", False)

    app = FastAPI()
    app.include_router(auth.router, prefix="/api")

    @app.get("/api/protected")
    def protected(_=Depends(auth.require_auth)):
        return {"ok": True}

    return TestClient(app)


def test_login_correct_password_sets_httponly_cookie(client):
    response = client.post("/api/auth/login", json={"password": TEST_PASSWORD})

    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"]
    assert config.AUTH_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie


def test_login_wrong_password_returns_401_without_cookie(client):
    response = client.post("/api/auth/login", json={"password": "wrong"})

    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_login_missing_password_field_returns_422(client):
    response = client.post("/api/auth/login", json={})

    assert response.status_code == 422


def test_check_with_valid_cookie_returns_200(client):
    client.post("/api/auth/login", json={"password": TEST_PASSWORD})

    response = client.get("/api/auth/check")

    assert response.status_code == 200


def test_check_without_cookie_returns_401(client):
    response = client.get("/api/auth/check")

    assert response.status_code == 401


def test_check_with_garbage_token_returns_401(client):
    client.cookies.set(config.AUTH_COOKIE_NAME, "not-a-jwt")

    response = client.get("/api/auth/check")

    assert response.status_code == 401


def test_check_with_expired_token_returns_401(client):
    expired = jwt.encode(
        {"exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        config.JWT_SECRET,
        algorithm="HS256",
    )
    client.cookies.set(config.AUTH_COOKIE_NAME, expired)

    response = client.get("/api/auth/check")

    assert response.status_code == 401


def test_logout_clears_cookie_so_check_fails(client):
    client.post("/api/auth/login", json={"password": TEST_PASSWORD})

    logout = client.post("/api/auth/logout")
    response = client.get("/api/auth/check")

    assert logout.status_code == 200
    assert response.status_code == 401


def test_require_auth_blocks_protected_route_without_cookie(client):
    response = client.get("/api/protected")

    assert response.status_code == 401


def test_require_auth_passes_protected_route_with_cookie(client):
    client.post("/api/auth/login", json={"password": TEST_PASSWORD})

    response = client.get("/api/protected")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
