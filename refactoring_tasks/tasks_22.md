# Task 22 — Normalize naming

Summary
- Enforce snake_case for files; remove spaces; standardize module names.

Steps
- Review filenames; rename as needed (avoid spaces/case inconsistencies).
- Update imports to match new names.

Acceptance Criteria
- No filenames with spaces or mixed casing remain.

Validation
- Search: `rg -n "[A-Z]" --iglob "**/*.py"` for uppercase names; fix as needed.

Testing Note
- After renames, run `pytest -q`; tests still load fixtures from repo files.

