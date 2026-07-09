from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app import config

router = APIRouter()


class LoginBody(BaseModel):
    password: str


@router.post("/auth/login")
def login(body: LoginBody, response: Response):
    if not verify_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    set_auth_cookie(response, mint_token())
    return {"success": True}


@router.get("/auth/check")
def check(request: Request):
    require_auth(request)
    return {"authenticated": True}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(config.AUTH_COOKIE_NAME)
    return {"success": True}


def require_auth(request: Request):
    token = request.cookies.get(config.AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Not authenticated")


def verify_password(password):
    if not config.PW_HASH:
        return False
    try:
        return bcrypt.checkpw(password.encode(), config.PW_HASH.encode())
    except ValueError:
        return False


def mint_token():
    expires = datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXPIRY_HOURS)
    return jwt.encode({"exp": expires}, config.JWT_SECRET, algorithm="HS256")


def set_auth_cookie(response, token):
    response.set_cookie(
        key=config.AUTH_COOKIE_NAME,
        value=token,
        max_age=config.JWT_EXPIRY_HOURS * 3600,
        httponly=True,
        samesite="strict",
        secure=config.SECURE_COOKIES,
    )
