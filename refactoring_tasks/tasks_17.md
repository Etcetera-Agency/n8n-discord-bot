# Task 17 — Logging consistency

Summary
- Use `config.logger.setup_logging()` everywhere; remove ad-hoc loggers.

Steps
- Ensure `setup_logging()` initializes once (e.g., in `main.py`).
- Replace module-level loggers with imports from `config.logger` where needed.
- Add structured context where beneficial.

Acceptance Criteria
- Single, consistent logging format; no duplicate initialization.

Validation
- Run locally; inspect log output consistency. Run `pytest -q`.

Testing Note
- Tests remain fixture-driven using `payload_examples.txt` and `responses`.

