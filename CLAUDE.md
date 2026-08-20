# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

News intelligence app: Telegram/RSS ingestion → embedding clustering → Claude scoring →
password-gated React UI. Style/naming: `AGENTS.md`. Setup + env vars: `README.md`.

## Hard rules

- **Never touch git.** The user owns all commits.
- **Never read `.env` / `env.example`.** Variable names are in README.md (Configuration).

## Commands

```sh
cd backend
uv sync
uv run pytest                             # needs Mongo — see below
uv run pytest tests/test_routes.py::test_login_success -x   # single test
uv run python -m app.main                 # reload server on BACKEND_PORT

cd frontend
npm run test                              # vitest (jsdom) — api.js, SourcesModal, score, time
npm run dev                               # Vite on FRONTEND_PORT, proxies /api
npm run build

docker compose up -d --build              # mongo + backend + nginx frontend
```

Ports come from the repo-root `.env`: locally FRONTEND_PORT=2000, BACKEND_PORT=2001
(code defaults 5173/8000).

## Tests and MongoDB

`conftest.py` picks the test instance: `TEST_MONGO_URI` → `localhost:27017` (if
reachable and no auth wall) → auto-spawned scratch `mongod` on **27018** (binary from
PATH or `C:\Program Files\MongoDB\Server`). Whole-suite connection/auth failures mean
all three fell through — set `TEST_MONGO_URI` or check the Windows MongoDB service.

Fixtures: `test_db` drops `news_app_test` before and after each test;
`reset_pipeline_flags` (autouse) resets runner module state. `asyncio_mode = "auto"`.

## Architecture — what spans multiple files

- **One process runs API + pipeline**: `main.py` lifespan connects Mongo and Telethon
  (`app.state.tg_client`), then loops `runner.run_pipeline` every 15 min. Stages:
  ingest (TG/RSS) → clean/dedupe → embed (Voyage) → group (cosine vs active stories;
  Haiku verdict on borderline) → importance filter (Haiku) → score (Sonnet);
  `runner.py` orchestrates, one module per stage.
- **`dirty` flag = the retry mechanism.** New items set `dirty: true`; cleared only on
  successful filter/score. `pipeline/llm.py: call_json` returns **None** on API failure
  or malformed JSON (one retry) — callers skip, never raise, story retried next cycle.
  A story stuck unscored → grep logs for `llm call failed` / `no valid json`.
- **Sources live in the `sources` collection, not config.py.** Seeded from config
  once, only while the collection is empty — after that, config edits do nothing;
  manage via `/api/sources` CRUD or Mongo. Pipeline reads only `enabled: true` docs.
- **Ranking is read-time only** (`ranking.py`:
  `score * 0.5 ** (hours_since_latest_item / DECAY_HALF_LIFE_HOURS)`);
  `routes/stories.py` bounds the query by `RANKING_WINDOW_HALF_LIVES`. Only
  `status: "scored"` stories are returned; others 404.
- **Module-level state**: `db.py` global collection handles (bound by `init_db`);
  `runner.py` `_lock` (concurrent run → 409), `_paused`, `_stop_requested`. Pause/stop
  is in-memory and the default is **stopped** — every boot waits for Resume; stop
  aborts at the next stage checkpoint.
- **Telegram is optional**: without TG env vars `tg_client` is None → RSS-only, TG
  source endpoints 503. TG vars are required at startup only if
  `config.TELEGRAM_CHANNELS` is non-empty.
- **Frontend**: `src/api.js` is the single fetch wrapper; a 401 dispatches the
  `auth-expired` window event → App.jsx bounces to Login. No state library.

## Gotchas

- **Datetimes must stay UTC-aware** — Mongo client is `tz_aware=True` because decay
  math mixes stored values with `datetime.now(timezone.utc)`; naive datetimes raise or
  mis-rank.
- **`sources` unique indexes are partial** (`url`/rss, `channel`/telegram). Plain
  unique indexes caused false 409s on the other type's nulls — don't "simplify" back.
- **Grouping write order is deliberate crash-safety** (`attach_item_to_story`): story
  doc before `raw.story_id`, so a crash re-groups instead of losing the item;
  `item_count` transiently over-counts and is recounted at scoring.
  `reap_orphan_stories` deletes pending shells with zero linked items.
- **Ingestion misbehaving? Check `pipeline_runs` first** (`GET /api/pipeline/status`):
  per-run stage counts and source/stage-tagged `errors[]`.
- **Conventions**: DB calls in routes try/except → 503; queries return data or None;
  operations return `{success, message}`.
