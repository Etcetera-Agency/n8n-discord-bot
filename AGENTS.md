# Repository Guidelines

## Project Structure & Module Organization

- `main.py` (entry), `bot.py` (Discord setup), `config/` (env, constants, logger), `services/` (webhook, survey, session, Notion), `discord_bot/` (commands, views), `web/` (HTTP server), `tests/` (unit/e2e), `assets/` (images), `n8n-workflow.json` (import for n8n).
- Test fixtures live alongside tests. Sample inputs: `payload_examples.txt`. Sample outputs: `responses` (UTF‑8 text file with JSON samples).

## Build, Test, and Development Commands

- Python: 3.10 (Docker uses `python:3.10-slim`). Local dev is pinned via `.python-version`.
- Install: `pip install -r requirements.txt`
- Run locally: `python main.py`
- Lint: `ruff check` (auto-fix safe issues: `ruff check --fix`)
- Tests: `pytest -q` (async tests use `pytest-asyncio`). Run a file: `pytest tests/test_router.py -q`.
- Docker (optional): `docker build -t n8n-discord-bot .` then `docker run -p 3000:3000 --env-file .env n8n-discord-bot`.

## Running Tests (Quick Start)

- Use Python 3.10 venv:
  - Create once: `python3.10 -m venv .venv && .venv/bin/pip install -r requirements.txt`
  - Activate: `source .venv/bin/activate`
- Lint first: `ruff check` (apply safe fixes: `ruff check --fix`)
- Run all tests: `pytest -q`
- Run a single file: `pytest tests/test_router.py -q`
- If the venv points to the wrong Python, recreate it:
  - `rm -rf .venv && python3.10 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Docker alternative (no local Python needed):
  - `docker run --rm -v "$PWD":/app -w /app python:3.10-slim bash -lc "pip install -r requirements.txt && pytest -q"`

### Install Ruff (if not installed)
- Via pip (inside venv): `pip install ruff`
- Via Homebrew (macOS): `brew install ruff`

## Coding Style & Naming Conventions

- Python, PEP 8, 4‑space indentation. Use type hints where practical.
- Naming: `snake_case` for files/functions/vars, `PascalCase` for classes, constants in `UPPER_SNAKE_CASE`.
- Keep modules focused; place Discord UI under `discord_bot/views/`, handlers under `discord_bot/commands/`, integrations under `services/`.

## Testing Guidelines

- Framework: `pytest` with `pytest-asyncio` for async coroutines.
- Naming: files `tests/test_*.py`, tests `def test_*()`.
- Required: load example payloads and responses from repo files — do not hardcode.
  - Payloads: `Path('payload_examples.txt').read_text(encoding='utf-8')`
  - Responses: `Path('responses').read_text(encoding='utf-8')`
- Prefer pure functions and mock network/Discord I/O. Keep tests deterministic.

## Commit & Pull Request Guidelines

- Commits: concise, imperative subject (≤72 chars), meaningful body when needed. Group related changes.
- PRs: clear description, linked issues, test evidence (e.g., command output), and note config changes. Update docs if behavior changes.

## Security & Configuration Tips

- Copy `.env.example` to `.env`; never commit secrets. Important keys: `DISCORD_TOKEN`, `NOTION_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_B64`, DB settings.
- Validate inputs at boundaries; log with `config/logger.py`; avoid leaking tokens in logs.
