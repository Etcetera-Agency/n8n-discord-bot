# Project Overview

This project is a Discord bot that originally offloads business logic to an n8n workflow through a webhook. Payload formats are described in `payload_examples.txt`, while `responses` and `README.md` demonstrate expected outputs and overall architecture. The goal is to migrate that logic into the bot codebase with minimal disruption.

## Key Components
- `services/webhook.py`: current entry point that sends payloads to n8n.
- `n8n-workflow.json`: defines existing workflow logic to be ported.
- `payload_examples.txt`: examples of command and survey payloads.
- `responses`: sample responses produced by the workflow.
- `README.md`: describes features such as session management, surveys, and command types.

## Task Guidelines
- Keep changes to existing modules minimal; treat `services/webhook.py` as the socket for new functionality.
- Each task file in this directory represents a self‑contained step in migrating n8n logic into Python code.
- Every task must include pseudocode, require unit tests, and specify end‑to‑end test updates.
- New code should follow the asynchronous style used in existing services.
- When implementing tasks, ensure database writes formerly handled in n8n are performed directly by the bot.
- All tests must log their inputs, step-by-step actions, and outputs to a file so users can review what was executed.

## Running calendar connector tests
1. Install dependencies: `pip install -r requirements.txt` (includes `aiohttp`, `google-auth`, `databases[sqlite]`, and `pytest-asyncio`).
2. Execute the tests: `pytest tests/test_calendar_connector.py`.

These tests automatically read example payloads from `payload_examples.txt` and sample API responses from `responses`, and they log inputs, steps, and outputs to temporary files for review.
