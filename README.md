# news-app

Personal news intelligence pipeline: ingests Telegram channels + RSS feeds, clusters
items into stories with embeddings + Claude, scores importance, and shows top stories
by topic behind a password-gated web UI. Full design: [SPEC.md](SPEC.md).

## Stack

FastAPI (Python 3.13, uv) · MongoDB · React + Vite · Anthropic (Haiku filter / Sonnet scoring) · Voyage AI embeddings · Docker

## Dev

```sh
# backend (needs local MongoDB on 27017 for tests)
cd backend
uv sync
uv run pytest
uv run python -m app.main              # serves on BACKEND_PORT (default 8000)

# frontend (proxies /api to the backend on BACKEND_PORT)
cd frontend
npm install
npm run dev                            # serves on FRONTEND_PORT (default 5173)
```

## Configuration

- Secrets: copy `env.example` → `.env` at the repo root and fill it in
  (`PW_HASH` via `uv run python -m app.hash_pw`, `TG_SESSION` via `uv run python -m app.tg_session`).
- Behavior (sources, topics, thresholds, intervals, models): `backend/app/config.py`.
- Scoring rubric: `backend/app/prompts.py` (`SCORING_SYSTEM_PROMPT`).

## Deploy

```sh
docker compose up -d --build
```

Frontend listens on host port `FRONTEND_PORT` (default 8080) — put the VPS reverse proxy /
TLS in front of it and set `SECURE_COOKIES=true` in `.env`. Mongo is not exposed outside
the compose network.
