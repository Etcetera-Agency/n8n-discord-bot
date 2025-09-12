# Task 20 — CI: lint/format/test

Summary
- Add GitHub Actions for lint (ruff/flake8), format (black), and pytest on 3.10–3.12 with pip cache.

Steps
- Add `.github/workflows/ci.yml` with matrix Python versions.
- Install deps, run linters, run tests.

Acceptance Criteria
- CI runs on PRs and `main`; all jobs pass.

Validation
- Open a PR to trigger CI; all steps green.

Testing Note
- Ensure tests read from `payload_examples.txt` and `responses` fixtures.

