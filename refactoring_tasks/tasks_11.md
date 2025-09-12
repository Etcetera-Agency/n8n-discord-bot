# Task 11 — Views safety and minimal helpers

Summary
- Preserve existing view classes and step-by-step flows. Do not merge slash and survey views. Only add tiny shared helpers where they do not change behavior.

Steps
- Audit current flow constraints (component IDs, timeouts, ephemeral responses, message edit/delete patterns).
- Add small, non-invasive helpers (e.g., constants, tiny functions) under `discord_bot/views/generic.py` or `views/components.py` to reduce copy-paste without changing external behavior.
- Keep `views/factory.py` interface and logic intact; extend cautiously only if strictly necessary.
- Remove only accidental duplicates (e.g., files with spaces in names) but avoid renaming functional modules.
- Add docstrings to views documenting expectations and interaction constraints.

Acceptance Criteria
- No renames or class merges; event handling and component IDs remain unchanged.
- All UI interactions behave exactly as before; no regressions in step-by-step conversations.
- Accidental duplicates removed; minor helpers added where safe.

Validation
- Manual: run workload/day_off flows; verify buttons/selects and message lifecycle behave the same.
- Run: `pytest -q` relevant tests.

Testing Note
- Tests must load fixtures from `payload_examples.txt` and `responses`.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
