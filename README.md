# news-app

Personal news intelligence pipeline: ingests Telegram channels + RSS feeds, clusters
items into stories with embeddings + Claude, scores importance, and shows top stories
by topic behind a password-gated web UI.

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

Secrets — create `.env` at the repo root (never committed):

```
MONGO_URI=
PW_HASH=            # bcrypt hash — generate: uv run python -m app.hash_pw
JWT_SECRET=
ANTHROPIC_API_KEY=
VOYAGE_API_KEY=
TG_API_ID=
TG_API_HASH=
TG_SESSION=
SECURE_COOKIES=true # cookie `secure` flag — true behind HTTPS, false for local HTTP dev
FRONTEND_PORT=      # optional host-port overrides (defaults above)
BACKEND_PORT=
```

- `TG_*` vars are optional: without them the app runs RSS-only (they're required at
  startup only if `config.TELEGRAM_CHANNELS` is non-empty). `TG_SESSION` is a Telethon
  StringSession minted once on any machine — `uv run python -m app.tg_session` prints
  it (an existing string from another project also works). The deployed app never
  prompts for a login code.
- Behavior (seed sources, topics, thresholds, intervals, models): `backend/app/config.py`.
- Scoring rubric: `backend/app/prompts.py` (`SCORING_SYSTEM_PROMPT`).

## Deploy

```sh
docker compose up -d --build
```

Frontend listens on host port `FRONTEND_PORT` (default 8080) — put the VPS reverse proxy /
TLS in front of it and set `SECURE_COOKIES=true` in `.env`. Mongo is not exposed outside
the compose network.

## Later (explicitly not in v1)

Alerts · Twitter/X and paid/account-login sources · a volume term in the ranking
formula · multi-user accounts
