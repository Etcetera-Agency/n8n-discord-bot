# Task 24 — Consolidate responses dirs

Summary
- Consolidate `responses` and remove `responses_leonid` if obsolete.

Steps
- Review contents/usage of both.
- Migrate any unique fixtures from `responses_leonid` into `responses` if needed.
- Update tests to reference `responses` only.

Acceptance Criteria
- Single authoritative `responses` file; no redundant fixtures.

Validation
- Grep for `responses_leonid` references; update or remove.
- Run `pytest -q`.

Testing Note
- Absolutely no hardcoded responses; always read from `responses`.

