# Database Schema Documentation

## Survey Steps Tracking Table

### DDL Schema
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

### Weekly Query Pattern (Kyiv TZ)
```sql
-- week_start computed in app code (Monday 00:00 Kyiv)
SELECT DISTINCT ON (step_name) 
    step_name, 
    completed, 
    updated 
FROM n8n_survey_steps_missed 
WHERE session_id = :session_id 
    AND updated >= :week_start 
ORDER BY step_name, updated DESC;
```

## Step Names Enum
Valid `step_name` values:
- `workload_today`
- `workload_nextweek` 
- `connects_thisweek`
- `day_off_nextweek`
- `day_off_thisweek`

## Usage Patterns

### Upsert Operation
```sql
INSERT INTO n8n_survey_steps_missed (session_id, step_name, completed, updated)
VALUES (:session_id, :step_name, :completed, NOW())
ON CONFLICT (session_id, step_name) 
DO UPDATE SET 
    completed = EXCLUDED.completed,
    updated = EXCLUDED.updated;
```

### Weekly Status Check
1. Compute `week_start = Monday 00:00 (Europe/Kyiv)`
2. Query latest weekly records per `step_name` for `session_id = channelId`
3. A step is **pending** if:
   - No record exists this week, OR
   - Latest record has `completed=false`
4. Exclude steps completed **today** from today's list

## Test Fixtures

### Sample Data
```sql
-- Test user session
INSERT INTO n8n_survey_steps_missed (session_id, step_name, completed, updated) VALUES
('1362738788505485414', 'workload_today', true, '2024-01-15 10:30:00+02'),
('1362738788505485414', 'workload_nextweek', false, '2024-01-15 11:00:00+02'),
('1362738788505485414', 'connects_thisweek', true, '2024-01-16 14:20:00+02');
```

### Week Boundary Test Cases
```sql
-- Monday 00:00 boundary test
INSERT INTO n8n_survey_steps_missed (session_id, step_name, completed, updated) VALUES
('test_channel', 'workload_today', true, '2024-01-14 23:59:59+02'),  -- Previous week
('test_channel', 'workload_today', false, '2024-01-15 00:00:00+02'); -- Current week start
```