# Task 11 — Centralize strings/i18n

Summary
- Keep user-facing strings in `config/strings.py` and add light interpolation helpers.

Steps
- Audit inline f-strings in commands/views; move static text to `Strings` with placeholders.
- Add helper for interpolation if needed (e.g., `Strings.format(template, **kwargs)`).
- Replace usage sites to call `Strings` constants/helpers.

Acceptance Criteria
- No duplicated literal strings for user messages in handlers.
- All messages defined in `config/strings.py`.

Validation
- Grep: `rg -n "Помилка|Дякую|Вибрано|Select" discord_bot` and migrate.
- Run: `pytest -q`.

Testing Note
- Keep tests reading fixture data from `payload_examples.txt` and `responses`.

