# Discord Bot n8n to Python Migration Plan

## Overview
This document outlines the complete migration of the Discord bot from n8n workflow to a deterministic Python implementation with a thin HTTP entrypoint at `services/webhook.py`.

## Task Files Structure

### Core Planning Files
- `README_refactor_plan.md` - This file, overview of all tasks
- `slash_commands_refactor_plan.md` - Command routing and handler architecture
- `tasks_surveyfix.md` - Survey flow and weekly logic implementation
- `tasks_update_survey.md` - Survey step completion and DB operations
- `CODE_REVIEW_TASKS.md` - Code review checklist for migration
- `tasks_CODE_REVIEW.md` - Execution-focused review checklist

### Documentation
- `docs/db.md` - Database schema, indices, and SQL fixtures
- `response_templates.md` - Extracted templates and response examples

### Command Implementation Files
- `commands/register.md` - User registration to channel
- `commands/unregister.md` - User unregistration from channel
- `commands/check_channel.md` - Weekly pending survey steps check
- `commands/workload_today.md` - Today's workload logging
- `commands/workload_nextweek.md` - Next week workload planning
- `commands/day_off_thisweek.md` - This week day-off requests
- `commands/day_off_nextweek.md` - Next week day-off requests
- `commands/connects_thisweek.md` - Weekly connects reporting
- `commands/vacation.md` - Vacation period requests
- `commands/survey.md` - Survey meta-handler
- `commands/mention.md` - Bot mention responses
- `commands/default.md` - Default/fallback responses

## Execution Order

### Phase 1: Setup & Infrastructure
- [ ] Set up project dependencies (`pytest`, `pytest-mock`, database drivers)
- [ ] Create configuration loader with environment variable support
- [ ] Implement client abstractions (`clients/notion.py`, `clients/gcal.py`, `clients/postgres.py`, `clients/http.py`)
- [ ] Set up database schema and migrations

### Phase 2: Core Services
- [ ] Implement `services/survey.py` with timezone-aware week calculations
- [ ] Create router and thin `services/webhook.py` entrypoint
- [ ] Implement normalized success/error response schemas

### Phase 3: Command Handlers
- [ ] Implement registration commands (`register`, `unregister`)
- [ ] Implement survey status commands (`check_channel`)
- [ ] Implement workload commands (`workload_today`, `workload_nextweek`)
- [ ] Implement day-off commands (`day_off_thisweek`, `day_off_nextweek`)
- [ ] Implement connects and vacation commands
- [ ] Implement survey meta-handler and fallback responses

### Phase 4: Testing & Validation
- [ ] Write comprehensive unit tests for all handlers
- [ ] Implement integration tests with mocked external services
- [ ] Validate byte-for-byte equivalence with n8n templates
- [ ] Set up CI/lint hooks with 90% coverage gate

## Key Technical Requirements

### Timezone Handling
- **Timezone**: Europe/Kyiv
- **Week Start**: Monday 00:00 local time
- Use `zoneinfo` for timezone calculations

### Response Schema
- Non-survey commands: `{ "output": "string" }`
- Survey commands: `{ "output": "string", "survey": "continue|end|cancel" }`
- Survey end: `{ "output": "string", "survey": "end", "url": "<to_do_URL>" }`

### Database Operations
- Use upsert operations for survey step tracking
- Maintain exact property names from n8n (e.g., `Discord channel ID|rich_text`)
- Implement proper session management with `session_id = channelId`

### External Integrations
- **Notion**: Team Directory, Workload DB, Profile Stats DB
- **Google Calendar**: Day-off and vacation event creation
- **HTTP**: Connects reporting to external service
- **PostgreSQL**: Survey step tracking

## Testing Strategy
- Mock all external clients
- Test week boundary conditions (Monday 00:00 Kyiv)
- Validate exact template matching
- Test error handling and edge cases
- Ensure 90% code coverage for new modules

## Success Criteria
- [ ] Byte-for-byte equivalence with n8n output (ignoring dynamic values)
- [ ] All external integrations properly mocked and tested
- [ ] No runtime LLM dependencies - fully deterministic
- [ ] 90% test coverage
- [ ] All Ukrainian response templates preserved exactly
- [ ] Proper newline handling (no escaping of `\n`)