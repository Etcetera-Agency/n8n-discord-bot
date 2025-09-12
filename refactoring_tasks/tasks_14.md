# Task 14 — Explicit survey models

Summary
- Introduce dataclasses for survey steps/results to replace ad-hoc dicts.

Steps
- Add `SurveyStep` and `SurveyResult` (e.g., in `services/survey_models.py`).
- Update `survey_manager` to use these types for storage and transitions.
- Adapt handlers to construct/consume these models.

Acceptance Criteria
- Survey flow uses typed models; no implicit dict structure assumptions.

Validation
- Type-check locally if using annotations; run `pytest -q`.

Testing Note
- Tests should keep loading fixtures from `payload_examples.txt` and `responses`.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
