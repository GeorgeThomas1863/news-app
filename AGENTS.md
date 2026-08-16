# Repository Guidelines

## Project Structure & Module Organization

This repository contains a FastAPI API and React application. Backend code lives in `backend/app/`; endpoints are in `app/routes/`, pipeline stages in `app/pipeline/`, and tests in `backend/tests/`. In `frontend/`, place pages in `src/views/`, reusable UI in `src/components/`, and styles in `src/css/`. Root files include `docker-compose.yml` and the project docs (`README.md`, `CLAUDE.md`).

## HARD RULES

- DO NOT touch git. The user controls all git commits. You must NEVER commit anything
- Avoid reviewing or reading the environment files in this app. 

## Build, Test, and Development Commands

- `cd backend && uv sync`: install Python 3.13 dependencies.
- `cd backend && uv run pytest`: run the backend test suite.
- `cd backend && uv run python -m app.main`: start FastAPI with reload, normally on port 8000.
- `cd frontend && npm install`: install locked frontend dependencies; use `npm ci` in CI.
- `cd frontend && npm run dev`: start Vite, normally on port 5173, proxying `/api` to FastAPI.
- `cd frontend && npm run build`: create the production bundle in `frontend/dist/`.
- `docker compose up -d --build`: build and run MongoDB, backend, and frontend together.

## Coding Style & Naming Conventions

Follow the existing style: four-space indentation and `snake_case` for Python; two-space indentation, semicolons, and double quotes for JavaScript/JSX. Use `PascalCase` for React components and files (for example, `StoryCard.jsx`), `camelCase` for JavaScript functions, and `test_<behavior>` for pytest functions. No formatter or linter is configured, so match adjacent code.

## Testing Guidelines

Pytest and `pytest-asyncio` are configured in `backend/pyproject.toml`; async tests run automatically. Add tests under `backend/tests/test_*.py`, using fixtures from `conftest.py`. Cover success, edge, and failure paths. Tests require MongoDB on `localhost:27017`. Frontend tests run with vitest (`npm run test` in `frontend/`); for visual changes also run `npm run build` and manually verify affected views.

## Commit & Pull Request Guidelines

History uses short, lowercase summaries, but is not yet consistent enough to define a strict convention. Prefer concise imperative subjects such as `fix story ranking decay`. Keep each commit scoped. Pull requests should explain the change and verification performed, link relevant issues, call out configuration or schema changes, and include screenshots for visible UI updates.

## Security & Configuration

Create `.env` at the repo root (variable names in `README.md`) and keep credentials out of version control. Configure sources and thresholds in `backend/app/config.py`; update scoring behavior in `backend/app/prompts.py`. Use `SECURE_COOKIES=true` behind HTTPS in production.
