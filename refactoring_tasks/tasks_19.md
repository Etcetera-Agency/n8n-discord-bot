# Task 19 — Graceful shutdown

Summary
- Trap SIGTERM/SIGINT in `main.py` and shut down Discord client and aiohttp server cleanly.

Steps
- Add signal handlers; cancel tasks and await shutdown.
- Ensure HTTP server and bot close sequences run without errors.

Acceptance Criteria
- Process exits cleanly; no hanging tasks or warnings.

Validation
- Run locally and send SIGINT (Ctrl+C) to verify graceful exit.

Testing Note
- No test hardcoding; use repo fixtures if adding tests.

