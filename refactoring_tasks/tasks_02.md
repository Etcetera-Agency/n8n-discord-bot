# Task 02 — Remove config/service coupling

Summary
- Stop re-exporting services from `config`. Remove router/service exports from `config/__init__.py` and fix imports.

Steps
- Edit `config/__init__.py` to export only config, constants, logger, strings.
- Replace `from config import WebhookService` with direct imports from services (e.g., `from services.webhook import WebhookService`, or `from services.app_router import AppRouter` after the rename in Task 08).
- Ensure no circular imports remain.

Acceptance Criteria
- `config` package contains no service imports/exports.
- App runs without circular import errors.

Validation
- Grep for bad imports: `rg "from config import (WebhookService|AppRouter)"` should return nothing.
- Run: `python main.py` and `pytest -q`.

Testing Note
- New/updated tests must read fixtures from `payload_examples.txt` and `responses`.
