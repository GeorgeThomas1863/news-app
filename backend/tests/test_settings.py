from app import config, settings


async def test_default_when_nothing_set(test_db, monkeypatch):
    monkeypatch.delenv("FILTER_MODEL", raising=False)
    monkeypatch.delenv("SCORING_MODEL", raising=False)
    monkeypatch.setattr(config, "FILTER_MODEL", "gpt-5.6-luna")
    monkeypatch.setattr(config, "SCORING_MODEL", "gpt-5.6-sol")

    result = await settings.get_effective_models()

    assert result["filter_model"] == "gpt-5.6-luna"
    assert result["scoring_model"] == "gpt-5.6-sol"
    assert result["sources"] == {"filter_model": "default", "scoring_model": "default"}


async def test_env_beats_default(test_db, monkeypatch):
    monkeypatch.setenv("FILTER_MODEL", "gpt-5.6-terra")
    monkeypatch.setattr(config, "FILTER_MODEL", "gpt-5.6-terra")

    result = await settings.get_effective_models()

    assert result["filter_model"] == "gpt-5.6-terra"
    assert result["sources"]["filter_model"] == "env"


async def test_db_beats_env_and_default(test_db, monkeypatch):
    monkeypatch.setenv("FILTER_MODEL", "gpt-5.6-terra")
    monkeypatch.setattr(config, "FILTER_MODEL", "gpt-5.6-terra")

    write_result = await settings.update_models(filter_model="claude-haiku-4-5")
    assert write_result["success"] is True

    result = await settings.get_effective_models()

    assert result["filter_model"] == "claude-haiku-4-5"
    assert result["sources"]["filter_model"] == "db"


async def test_stored_value_outside_allowlist_falls_through(test_db):
    await test_db.settings.update_one(
        {"_id": "app"}, {"$set": {"filter_model": "not-a-real-model"}}, upsert=True
    )

    result = await settings.get_effective_models()

    assert result["filter_model"] == config.FILTER_MODEL
    assert result["sources"]["filter_model"] in ("env", "default")


async def test_update_models_rejects_unknown_model(test_db):
    result = await settings.update_models(filter_model="not-a-real-model")

    assert result["success"] is False


async def test_update_models_reset_to_null(test_db):
    await settings.update_models(filter_model="claude-haiku-4-5")
    result = await settings.update_models(filter_model=None)

    assert result["success"] is True
    doc = await test_db.settings.find_one({"_id": "app"})
    assert doc is None or "filter_model" not in doc


async def test_update_models_omitted_field_left_untouched(test_db):
    await settings.update_models(filter_model="claude-haiku-4-5")
    result = await settings.update_models(scoring_model="claude-sonnet-5")

    assert result["success"] is True
    effective = await settings.get_effective_models()
    assert effective["filter_model"] == "claude-haiku-4-5"
    assert effective["scoring_model"] == "claude-sonnet-5"
