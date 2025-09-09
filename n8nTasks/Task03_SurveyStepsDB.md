# Task 03: Survey steps tracking database

## Goal
Store survey progress so the bot can skip completed steps and query missed ones without n8n.

## Supported operations
1. **Upsert step status**
   - insert or update a row keyed by `(session_id, step_name)`
2. **Fetch last week’s statuses**
   - return the most recent record per step for a session
3. **Determine pending steps**
   - given expected step names, return those not completed for the current week

## Schema
The `n8n_survey_steps_missed` table already exists in production, so no migration is
required if it is present. The DDL below is provided only for reference in case a
fresh environment needs to recreate the table.

```sql
CREATE TABLE IF NOT EXISTS n8n_survey_steps_missed (
    id         SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    step_name  VARCHAR(50)  NOT NULL,
    completed  BOOLEAN      NOT NULL,
    updated    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_missed_session_updated ON n8n_survey_steps_missed (session_id, updated DESC);
CREATE INDEX IF NOT EXISTS idx_missed_step            ON n8n_survey_steps_missed (step_name);
```

## Expected inputs and outputs
### Upsert
```json
{
  "session_id": "CHAN123_USER456",
  "step_name": "workload_today",
  "completed": true
}
```
Normalized response:
```json
{ "status": "ok" }
```

### Fetch weekly steps (Kyiv TZ)
Request parameters: `session_id`, `week_start`
SQL pattern:
```sql
SELECT DISTINCT ON (step_name)
    step_name,
    completed,
    updated
FROM n8n_survey_steps_missed
WHERE session_id = :session_id
  AND updated >= :week_start
ORDER BY step_name, updated DESC;
```
Example output:
```json
[
  {"step_name": "workload_today", "completed": true, "updated": "2024-02-05T10:00:00+02:00"},
  {"step_name": "connects_thisweek", "completed": false, "updated": "2024-02-06T11:00:00+02:00"}
]
```

## Pseudocode
```
async def upsert_step(session_id, step_name, completed):
    await db.execute(
        """INSERT INTO n8n_survey_steps_missed (session_id, step_name, completed, updated)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (session_id, step_name) DO UPDATE SET
                completed = EXCLUDED.completed,
                updated = EXCLUDED.updated""",
        session_id, step_name, completed,
    )

async def fetch_week(session_id, week_start):
    rows = await db.fetch(
        "SELECT DISTINCT ON (step_name) step_name, completed, updated \n"
        "FROM n8n_survey_steps_missed \n"
        "WHERE session_id=$1 AND updated >= $2 \n"
        "ORDER BY step_name, updated DESC",
        session_id, week_start,
    )
    return [dict(r) for r in rows]

async def pending_steps(session_id, week_start, all_steps):
    records = await fetch_week(session_id, week_start)
    done = {r["step_name"] for r in records if r["completed"]}
    return [s for s in all_steps if s not in done]
```

## Testing
- Unit tests should run against a temporary database and cover insert, update, and week-query cases with example payloads.
- End-to-end tests should verify survey steps are persisted and retrieved when navigating the survey.
- All tests must log inputs, steps, and outputs to a file for later review.
