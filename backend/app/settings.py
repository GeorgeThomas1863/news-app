import logging
import os

from app import config, db

log = logging.getLogger(__name__)

SETTINGS_DOC_ID = "app"

ALLOWED_MODELS = {
    "anthropic": [
        {"value": "claude-fable-5", "label": "Fable 5"},
        {"value": "claude-opus-5", "label": "Opus 5"},
        {"value": "claude-sonnet-5", "label": "Sonnet 5"},
        {"value": "claude-sonnet-4-6", "label": "Sonnet 4.6"},
        {"value": "claude-haiku-4-5", "label": "Haiku 4.5"},
    ],
    "openai": [
        {"value": "gpt-5.6-sol", "label": "GPT-5.6 Sol"},
        {"value": "gpt-5.6-terra", "label": "GPT-5.6 Terra"},
        {"value": "gpt-5.6-luna", "label": "GPT-5.6 Luna"},
        {"value": "gpt-5.5", "label": "GPT-5.5"},
    ],
}

# sentinel distinguishing "field omitted" from "field explicitly set to None" in update_models
_UNSET = object()


async def get_effective_models():
    """Resolve filter_model / scoring_model: Mongo settings doc > env var > config default."""
    stored = await load_settings_doc()

    filter_model, filter_source = resolve_model_field(
        stored.get("filter_model"), "FILTER_MODEL", config.FILTER_MODEL
    )
    scoring_model, scoring_source = resolve_model_field(
        stored.get("scoring_model"), "SCORING_MODEL", config.SCORING_MODEL
    )

    return {
        "filter_model": filter_model,
        "scoring_model": scoring_model,
        "sources": {"filter_model": filter_source, "scoring_model": scoring_source},
    }


async def update_models(filter_model=_UNSET, scoring_model=_UNSET):
    """Set/reset/leave filter_model and scoring_model in the settings doc.

    Each of filter_model/scoring_model: a valid model string sets it, None resets
    (unsets) it, and omitting the argument entirely leaves it untouched.
    """
    set_fields = {}
    unset_fields = {}

    error = collect_field_write(filter_model, "filter_model", set_fields, unset_fields)
    if error:
        return error
    error = collect_field_write(scoring_model, "scoring_model", set_fields, unset_fields)
    if error:
        return error

    if not set_fields and not unset_fields:
        return {"success": True, "message": "No changes"}

    await write_settings_doc(set_fields, unset_fields)
    return {"success": True, "message": "Settings updated"}


def collect_field_write(value, field_name, set_fields, unset_fields):
    """Validate one incoming field and route it into set_fields/unset_fields. Returns an
    error dict on invalid input, else None."""
    if value is _UNSET:
        return None
    if value is None:
        unset_fields[field_name] = ""
        return None
    if not is_allowed_model(value):
        return {"success": False, "message": f"Unknown model: {value}"}
    set_fields[field_name] = value
    return None


def is_allowed_model(value):
    for models in ALLOWED_MODELS.values():
        for entry in models:
            if entry["value"] == value:
                return True
    return False


def resolve_model_field(stored_value, env_var_name, config_default):
    """db value (if allowed) > env var (if set) > config default."""
    if stored_value is not None:
        if is_allowed_model(stored_value):
            return stored_value, "db"
        log.warning("resolve_model_field: stored value %r not in allowlist, ignoring", stored_value)

    env_value = os.environ.get(env_var_name)
    if env_value:
        return env_value, "env"

    return config_default, "default"


async def load_settings_doc():
    try:
        doc = await db.settings.find_one({"_id": SETTINGS_DOC_ID})
    except Exception:
        log.exception("load_settings_doc: failed to read settings")
        raise
    return doc or {}


async def write_settings_doc(set_fields, unset_fields):
    update = {}
    if set_fields:
        update["$set"] = set_fields
    if unset_fields:
        update["$unset"] = unset_fields

    try:
        await db.settings.update_one({"_id": SETTINGS_DOC_ID}, update, upsert=True)
    except Exception:
        log.exception("write_settings_doc: failed to write settings")
        raise
