# Task: Clean Up Excessive Survey Logging

This task focuses on reviewing the codebase, particularly the files involved in the survey flow, and removing or adjusting excessive logging statements to reduce noise and improve clarity of logs.

**Important Considerations:**

*   Ensure that critical errors and important flow changes are still logged appropriately.
*   Avoid removing logging that is necessary for debugging or monitoring the core functionality.
*   Focus on removing verbose or redundant logging that doesn't provide significant value.

**Affected Files:**

*   `discord_bot/commands/survey.py`
*   `services/survey.py`
*   `services/webhook.py`
*   `discord_bot/views/` (Survey-related views/modals)
*   Potentially other files if excessive logging is found there.

**Steps:**

1.  **Review Logging in Survey Files:** Read through the code in `discord_bot/commands/survey.py`, `services/survey.py`, `services/webhook.py`, and survey-related files in `discord_bot/views/`.
2.  **Identify Excessive Logs:** Look for `logger.debug`, `logger.info`, or even `logger.warning` calls that are too frequent, redundant, or provide minimal useful information for diagnosing issues or understanding the flow.
3.  **Remove or Adjust Logging:**
    *   Remove logging statements that are clearly excessive or unnecessary.
    *   For statements that might be occasionally useful, consider changing their level (e.g., from `info` to `debug`) or adding conditional checks if the logging is only needed in specific scenarios.
    *   Ensure that error logging (`logger.error`, `logger.exception`) remains in place for critical failures.
4.  **Verify Logging Setup:** Briefly review `config/logger.py` to understand how logging is configured and ensure the changes align with the intended logging strategy.