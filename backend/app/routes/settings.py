import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import settings as settings_module
from app.auth import require_auth

log = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_auth)])

class SettingsUpdateIn(BaseModel):
    filter_model: str | None = None
    scoring_model: str | None = None


@router.get("/settings")
async def get_settings():
    effective = await load_effective_models()
    effective["allowed_models"] = settings_module.ALLOWED_MODELS
    return effective


@router.put("/settings")
async def update_settings(body: SettingsUpdateIn):
    result = await apply_settings_update(body)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


async def load_effective_models():
    try:
        return await settings_module.get_effective_models()
    except Exception:
        log.exception("get_settings: failed to read settings")
        raise HTTPException(status_code=503, detail="Database unavailable")


async def apply_settings_update(body):
    try:
        # only fields the client actually sent; omitted fields keep update_models' _UNSET default
        return await settings_module.update_models(**body.model_dump(exclude_unset=True))
    except Exception:
        log.exception("update_settings: failed to write settings")
        raise HTTPException(status_code=503, detail="Database unavailable")
