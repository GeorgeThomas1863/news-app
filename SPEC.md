# SPEC — Personal News Intelligence App (v1)

A self-hosted, password-gated web app that ingests news from Telegram channels and RSS feeds, clusters items into stories using embeddings + LLM judgment, scores each story's importance with Claude, and displays the top stories per topic with time-decayed ranking.

Design reference: `docs/design_plan_July2026.excalidraw`.

---

## 1. Scope

### In v1

- Sources: **Telegram channels** (via Telethon, user-account login) and **RSS feeds** (Substack feeds work here too)
- Interval-polled ingestion (15 min) + manual "refresh now" button
- Text only — media (photos/videos) ignored
- No backfill — ingestion starts from deploy time forward
- Embedding-based story clustering with Haiku verdicts on borderline matches
- Haiku importance pre-filter → Sonnet full scoring (score, topic, headline, summary in one call)
- Time-decayed ranking, computed at read time
- React frontend: topic sections with top stories, story detail view, single-password JWT auth
- Docker deployment (3 containers), self-hosted Mongo

### Explicitly out of v1 (later)

- Alerts (external or in-app)
- Twitter/X, paid news sites, Substack account-login pulls
- Source list / settings management in the UI (config file only for now)
- Volume term in the ranking formula
- Multi-user accounts

---

## 2. Architecture

Monorepo. Three containers via `docker-compose`:

| Container  | Contents |
|------------|----------|
| `backend`  | FastAPI (Python 3.12+, async). Serves the API **and** runs the ingestion/scoring pipeline in-process on a schedule. Telethon client shares the FastAPI event loop (started/stopped in the app lifespan). |
| `mongo`    | MongoDB, named volume for data persistence. Not exposed publicly. |
| `frontend` | nginx serving the built React app; proxies `/api/*` to `backend`. |

- Scheduling: a plain asyncio background task started in the FastAPI lifespan — sleep loop firing the pipeline every `POLL_INTERVAL_MINUTES`. No scheduler library.
- Pipeline runs never overlap: an `asyncio.Lock` guards the run; the manual trigger returns "already running" instead of queueing.
- TLS/domain handled outside the app (VPS reverse proxy). `SECURE_COOKIES` env flag toggles the cookie `secure` attribute (on in production, off for local HTTP dev).
- Mongo driver: PyMongo's async API (verify current recommended async driver against MongoDB docs at implementation time; Motor is being superseded).

---

## 3. Data model (Mongo)

### `raw` — one doc per ingested post/article

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `source_type` | string | `"telegram"` \| `"rss"` |
| `source_name` | string | channel handle or feed name from config |
| `url` | string | link to original (Telegram message link / article URL) |
| `title` | string \| null | RSS entry title; null for Telegram |
| `text` | string | cleaned plain text |
| `published_at` | datetime | from the source |
| `ingested_at` | datetime | |
| `content_hash` | string | SHA-256 of normalized text; exact-dupe detection |
| `embedding` | float[] | Voyage vector |
| `story_id` | ObjectId \| null | set when grouped |

Indexes: unique on `content_hash`, index on `url`, index on `story_id`.

### `stories` — one doc per clustered story

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | |
| `status` | string | `"pending"` → `"filtered"` \| `"scored"` |
| `dirty` | bool | `true` when the story is new or has gained items since its last successful filter/score; drives stage selection; cleared on success |
| `topic` | string \| null | one of the configured topics; set by scoring |
| `headline` | string \| null | Claude-generated; set by scoring |
| `summary` | string \| null | 1–2 sentences; set by scoring |
| `score` | int \| null | 0–100; set by scoring |
| `item_count` | int | denormalized count of raw docs |
| `first_item_at` | datetime | |
| `latest_item_at` | datetime | drives active window + decay |
| `scored_at` | datetime \| null | |
| `created_at` / `updated_at` | datetime | |

Indexes: `(status, latest_item_at)`.

Story lifecycle: a story is **active** (accepts new items) while `now - latest_item_at < ACTIVE_WINDOW_HOURS` (48h). Creating a story or adding items to one sets `dirty: true`. Each cycle processes dirty stories: `pending`/`filtered` → importance filter (an unimportant story can become important); `scored` → re-score. `dirty` is cleared only on successful completion, so failures (LLM error, malformed output) are retried automatically next cycle.

### `source_state` — one doc per configured source

Per-source bookmark. Telegram: last seen message id per channel (newness = id greater than bookmark). RSS: `initial_seen_urls` — snapshot of the feed's entries at first poll (the no-backfill skip-list) — plus `last_polled_at` and last error; RSS newness = URL not in `raw` and not in `initial_seen_urls`. Enables "start from now", incremental fetching, and crash recovery. Created on first poll of each source.

### `pipeline_runs` — one doc per pipeline cycle

`trigger` (`"schedule"` \| `"manual"`), `started_at`, `finished_at`, `status` (`"running"` \| `"success"` \| `"error"`), per-stage counts (`ingested`, `deduped`, `embedded`, `stories_created`, `stories_updated`, `filtered_out`, `scored`), `errors[]` (source/stage-tagged messages). Feeds the header status display; serves as audit trail.

---

## 4. Pipeline

Runs every 15 minutes and on manual trigger. Stages in order:

### 4.1 Ingest

- **Telegram (Telethon)**: for each configured channel, fetch messages with id greater than the bookmark in `source_state`. First-ever poll of a channel: record the current latest message id and fetch nothing (no backfill).
- **RSS**: fetch each feed URL (`httpx`), parse (`feedparser`), keep entries not already present in `raw` (by `url`). First-ever poll of a feed: mark its current entries as seen without ingesting them (no backfill), consistent with Telegram.
- Every source is wrapped in its own try/except — a dead feed or unreachable channel logs an error into `pipeline_runs.errors` and the cycle continues.

### 4.2 Clean + dedupe

- Strip HTML, normalize whitespace.
- Drop items shorter than `MIN_TEXT_LENGTH`.
- Compute `content_hash`; drop exact duplicates (hash or URL already in `raw`).
- Insert survivors into `raw`.

### 4.3 Embed

Batch all new items through the Voyage API. Model id in config (pick the current recommended general-purpose model from Voyage docs at implementation time). Store vectors on the `raw` docs.

### 4.4 Group into stories

For each new item, cosine similarity (computed in Python) against the embeddings of items belonging to **active** stories:

- best similarity ≥ `SIM_HIGH` (start: 0.85) → join that story
- best similarity < `SIM_LOW` (start: 0.70) → create a new singleton story
- in between → **Haiku verdict**: show the item and the candidate story (headline if scored, else sample item texts); Haiku answers same-story yes/no

Thresholds are config values expected to need tuning against real data.

### 4.5 Importance filter (Haiku)

Every dirty `pending`/`filtered` story gets a cheap gate: *"any chance this story is important?"* — deliberately permissive, its only job is discarding obvious noise before it costs a Sonnet call.

- No → `status: "filtered"`, `dirty` cleared (kept in DB, never shown, re-filtered only when new items set `dirty` again)
- Yes → `status` stays `pending`, proceeds to scoring this same cycle

### 4.6 Full scoring (Sonnet)

One structured-output call per story (JSON schema enforced, one retry on malformed output, then skip and log — the story keeps `dirty: true` and any previous score, and is retried next cycle). Input: the story's item texts + source names + timestamps. Output:

```json
{ "score": 0-100, "topic": "<one of configured topics>", "headline": "...", "summary": "..." }
```

- The system prompt lives in `backend/app/prompts.py` as an editable string — the detailed scoring method (owner's rubric) drops in later without code changes. Until then a straightforward placeholder rubric is used.
- Dirty `scored` stories (gained new items) are re-scored with the same call (score, headline, and summary stay current as a story develops). On success `dirty` is cleared.

### 4.7 Ranking (read time — not a pipeline stage)

Computed in the API layer on every read:

```
effective_score = score * 0.5 ** (hours_since_latest_item / DECAY_HALF_LIFE_HOURS)
```

Half-life default 24h. No volume term in v1 (Sonnet sees `item_count` and source breadth when scoring). Only `scored` stories are ever returned to the frontend.

---

## 5. LLM / API usage

| Use | Provider / model | Notes |
|---|---|---|
| Embeddings | Voyage AI | batched; model id in config |
| Grouping verdicts | Anthropic — Haiku (`claude-haiku-4-5`) | borderline matches only |
| Importance filter | Anthropic — Haiku (`claude-haiku-4-5`) | one call per pending story |
| Full scoring | Anthropic — Sonnet (`claude-sonnet-5`) | one structured call per story; also re-scores |

Model ids are config values. All external calls: try/except, retry with exponential backoff on transient errors, context-rich logging (source, story id, stage).

---

## 6. API

All routes under `/api`. Everything except `login` requires a valid JWT cookie (FastAPI dependency).

| Method + path | Purpose |
|---|---|
| `POST /api/auth/login` | body `{password}` → bcrypt-verify against `PW_HASH` → JWT (1-day expiry) set as httpOnly cookie |
| `POST /api/auth/logout` | clears the cookie |
| `GET  /api/auth/check` | 200 if logged in — used by the SPA on boot |
| `GET  /api/stories` | scored stories grouped by topic, ranked by effective score, top `STORIES_PER_TOPIC` (5) each |
| `GET  /api/stories?topic=X&limit=N&skip=M` | ranked list for one topic — powers "show more" |
| `GET  /api/stories/{id}` | story + all its `raw` items (for the detail view) |
| `POST /api/pipeline/run` | manual refresh; 409-style response if a run is already in flight |
| `GET  /api/pipeline/status` | latest `pipeline_runs` doc (header display) |

Auth mechanics: JWT signed with `JWT_SECRET` (HS256, `exp` = 24h), cookie flags `httpOnly`, `sameSite=strict`, `secure` per `SECURE_COOKIES`. Unauthenticated API calls get 401; the SPA redirects to the login screen.

---

## 7. Frontend (React + Vite)

Plain CSS (no UI framework), visual style ported from `nork-displayer-1950`: Roboto Condensed, blue `#2563a8` uppercase collapse headers with animated chevron, white cards with 12px radius and soft shadows, pill-style buttons.

### Views (react-router)

- **Login** — single password field (show/hide toggle), submit → `/api/auth/login`, error state on wrong password.
- **Main** — header: app title, last-pipeline-run time, "Refresh" button (`POST /api/pipeline/run`, disabled while running), logout. Body: one **collapsible topic section** per configured topic (sections with zero stories render collapsed/empty-state). Inside: story cards ranked by effective score, top 5, then a "show more" button that pulls the next batch for that topic.
- **Story detail** (`/story/:id`) — headline, score, topic, full summary, then the complete list of source items: source name, title/text snippet, timestamp, each linking to the original URL (new tab).

### Story card

Claude headline · 1–2 sentence summary · score badge (0–100) · topic · source count · time of latest item. Card links to the detail view.

### Data flow

Central fetch wrapper adds `credentials: include`, funnels 401s to the login screen. No state library — component state + a top-level auth check on boot (`/api/auth/check`).

---

## 8. Configuration

### `.env` (secrets — never committed)

```
MONGO_URI=
PW_HASH=            # bcrypt hash; generate with: python -m app.hash_pw
JWT_SECRET=
ANTHROPIC_API_KEY=
VOYAGE_API_KEY=
TG_API_ID=
TG_API_HASH=
TG_SESSION=         # Telethon StringSession — mint once with: python -m app.tg_session
SECURE_COOKIES=true
```

### `backend/app/config.py` (behavior — moves to UI settings in a later version)

```
RSS_FEEDS               # list of {name, url}
TELEGRAM_CHANNELS       # list of channel usernames
TOPICS                  # ["Geopolitics", "Ukraine", "Middle East", "Markets", "Tech", "Domestic US"]
POLL_INTERVAL_MINUTES   # 15
SIM_HIGH / SIM_LOW      # 0.85 / 0.70 starting values
ACTIVE_WINDOW_HOURS     # 48
DECAY_HALF_LIFE_HOURS   # 24
STORIES_PER_TOPIC       # 5
MIN_TEXT_LENGTH         # cleanup floor
EMBED_MODEL / FILTER_MODEL / SCORING_MODEL
```

### Telegram session

No interactive login at deploy time and no session file/volume. The app authenticates with a Telethon **StringSession** read from `.env` (`TG_SESSION`) alongside `TG_API_ID`/`TG_API_HASH`. Telegram user accounts require a one-time phone-code exchange to mint a session; that happens once on any machine — `python -m app.tg_session` prints the string (an existing valid string from another project also works) — and the result is pasted into `.env`. The deployed app never prompts.

---

## 9. Error handling & logging

- Structured logging to stdout (`docker logs`): timestamp, level, stage/source context.
- Per-source isolation in ingestion (one failure never kills a cycle); failures recorded in `pipeline_runs.errors`.
- LLM/embedding calls: retry with backoff on transient errors; malformed structured output → one retry → skip and log; skipped stories remain `pending` and are retried next cycle.
- A fully failed pipeline run marks its `pipeline_runs` doc `status: "error"` — visible in the header status.

---

## 10. Testing

**Development method: TDD.** Every unit is built test-first — write the failing test, implement to green, refactor. This applies throughout the backend.

- **pytest** on pure logic with mocked external clients: cleanup/normalization, hash dedup, grouping threshold decisions (join / new / gray-zone), story lifecycle transitions, decay math, ranking order.
- API endpoint tests via FastAPI test client (auth required/rejected, stories grouping shape, pipeline lock behavior).
- Frontend: no test suite in v1.

---

## 11. Repository layout

```
news-app/
├── SPEC.md
├── docker-compose.yml
├── .env                        # secrets (gitignored)
├── env.example                 # documented blank template (dotless name — .env* is tool-guarded; gitignored, local-only)
├── docs/                       # design files (gitignored)
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py             # FastAPI app, lifespan (scheduler + Telethon), route registration
│       ├── config.py
│       ├── prompts.py          # filter / grouping / scoring prompts (scoring rubric = owner-editable)
│       ├── auth.py             # login/logout/check + JWT dependency
│       ├── routes/             # stories, pipeline
│       ├── pipeline/           # ingest_telegram, ingest_rss, clean, embed, group, filter, score, runner
│       ├── db.py               # Mongo client + collection handles
│       ├── hash_pw.py          # CLI: bcrypt hash generator
│       └── tg_session.py       # CLI: mint Telethon StringSession (one-time, run locally)
└── frontend/
    ├── Dockerfile              # build → nginx
    ├── nginx.conf              # static + /api proxy
    └── src/                    # React app (views, components, fetch wrapper, css)
```

(Exact internal file split may be refined in the implementation plan; the structure above is the intent.)

---

## 12. Deploy (operator steps)

1. Copy `env.example` → `.env`, fill secrets; generate `PW_HASH` via `python -m app.hash_pw`; set `TG_SESSION` (mint once locally via `python -m app.tg_session` or reuse an existing string).
2. `docker compose up -d --build`.
3. Put the VPS reverse proxy / TLS in front of the `frontend` container. `SECURE_COOKIES=true` in production.
