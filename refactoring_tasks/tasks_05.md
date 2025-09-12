# Task 05 — Fix survey continuation

Summary
- Use `survey_manager` as the single source of truth. Index survey state by channel ID consistently.

Steps
- Remove any direct `SURVEYS` dict logic from services; do not key by `userId`.
- Replace lookups with channelId-based access via `survey_manager.get_survey(channel_id)`.
- Ensure continuation (`survey == "continue"`) is handled in Discord handlers using `survey_manager` (not inside router/service).

Acceptance Criteria
- Continuation works when n8n returns `{"survey": "continue"}`.
- No KeyError on user-based SURVEYS; state retrieved via `survey_manager`.

Validation
- Manual: run a survey flow end-to-end.
- Tests for continuation pass: `pytest -q tests/test_survey_start.py` and related.

Testing Note
- Tests must load payloads from `payload_examples.txt` and sample responses from `responses`.

Behavior Constraints
- Do not change Discord behavior: user-visible messages, mentions, reactions, component IDs/layout, ephemeral/public status, and message edit/delete timing must remain identical.
