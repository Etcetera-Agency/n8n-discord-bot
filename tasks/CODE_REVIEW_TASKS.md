# Code Review Tasks for n8n to Python Migration

## Overview
Comprehensive code review checklist tailored specifically for the Discord bot migration from n8n workflow to deterministic Python implementation.

## Template & Response Accuracy Review

### Task: Ukrainian Text Preservation
- [ ] **Verify exact Ukrainian text** from n8n Set/Respond nodes preserved
- [ ] **Check newline handling** - ensure `\n` not escaped to `\\n`
- [ ] **Validate template variables** - all placeholders properly substituted
- [ ] **Test special characters** - Ukrainian characters render correctly
- [ ] **Verify response encoding** - UTF-8 encoding maintained throughout
- [ ] **Check text formatting** - spacing, punctuation, capitalization exact

### Task: Response Schema Compliance
- [ ] **Non-survey commands** return `{"output": "string"}` only
- [ ] **Survey commands** return `{"output": "string", "survey": "continue|end|cancel"}`
- [ ] **Survey end** includes `{"output": "string", "survey": "end", "url": "string"}`
- [ ] **Check channel** includes `{"output": "string", "steps": ["string"]}`
- [ ] **JSON serialization** produces valid JSON without extra fields
- [ ] **Response headers** include proper Content-Type: application/json

### Task: Template Variable Substitution
- [ ] **User names** from Notion Team Directory properly inserted
- [ ] **Channel names** without # prefix in responses
- [ ] **Time formatting** as HH:MM in Ukrainian timezone
- [ ] **Date formatting** as YYYY-MM-DD consistently
- [ ] **Ukrainian weekdays** - Понеділок, Вівторок, Середа, Четвер, П'ятниця, Субота, Неділя
- [ ] **Numeric formatting** - hours, connects, capacity properly formatted

## Database Integration Review

### Task: PostgreSQL Schema Compliance
- [ ] **Table structure** matches exact DDL from `docs/db.md`
- [ ] **Column names** exactly: `id`, `session_id`, `step_name`, `completed`, `updated`
- [ ] **Data types** match: SERIAL, VARCHAR(255), VARCHAR(50), BOOLEAN, TIMESTAMPTZ
- [ ] **Indexes** created: `idx_missed_session_updated`, `idx_missed_step`
- [ ] **Constraints** properly enforced
- [ ] **Default values** applied correctly (updated = now())

### Task: Query Implementation Accuracy
- [ ] **Weekly query** uses exact SQL pattern from schema
- [ ] **DISTINCT ON** clause properly implemented
- [ ] **ORDER BY** includes step_name, updated DESC
- [ ] **WHERE clause** filters by session_id and updated >= week_start
- [ ] **Timezone handling** in WHERE clause uses Europe/Kyiv
- [ ] **Parameter binding** prevents SQL injection

### Task: Upsert Logic Verification
- [ ] **ON CONFLICT** uses correct columns (session_id, step_name)
- [ ] **DO UPDATE SET** updates completed and updated fields
- [ ] **Transaction handling** ensures atomicity
- [ ] **Error handling** for constraint violations
- [ ] **Retry logic** for deadlocks and connection issues
- [ ] **Audit logging** for all database changes

## External API Integration Review

### Task: Notion API Compliance
- [ ] **Property names** exact: `Discord ID|rich_text`, `Discord channel ID|rich_text`
- [ ] **Database IDs** match n8n configuration
- [ ] **Filter conditions** replicate n8n logic exactly
- [ ] **Update operations** use correct property types
- [ ] **Error handling** for API rate limits
- [ ] **Authentication** using correct credentials

### Task: Google Calendar Integration
- [ ] **All-day events** created with correct time range (00:00:00 to 23:59:59)
- [ ] **Event summaries** match format: "Day off: {user_name}", "Vacation: {user_name}"
- [ ] **Date formatting** in YYYY-MM-DD HH:MM:SS format
- [ ] **Calendar ID** matches n8n configuration
- [ ] **Error handling** for calendar API failures
- [ ] **Authentication** using correct OAuth2 credentials

### Task: HTTP Service Integration
- [ ] **Connects endpoint** URL matches: `https://tech2.etcetera.kiev.ua/set-db-connects`
- [ ] **Request payload** includes name and connects parameters
- [ ] **HTTP method** POST with correct headers
- [ ] **Error handling** for HTTP failures (fatal vs non-fatal)
- [ ] **Timeout configuration** appropriate for external service
- [ ] **Retry logic** for transient failures

## Business Logic Accuracy Review

### Task: Registration Logic Verification
- [ ] **Public channel check** uses exact hardcoded list from n8n
- [ ] **19-digit regex** validation: `^\\d{19}$`
- [ ] **User search** by Name|title contains logic
- [ ] **Channel search** by Discord channel ID|rich_text contains
- [ ] **Update logic** preserves user ID during unregistration
- [ ] **Error messages** match n8n Set node outputs exactly

### Task: Survey Flow Logic
- [ ] **Week calculation** Monday 00:00 Europe/Kyiv timezone
- [ ] **Pending step detection** excludes completed today
- [ ] **Step enumeration** includes all 5 steps exactly
- [ ] **Status routing** deterministic (no LLM)
- [ ] **Step completion** marks correct step_name
- [ ] **Survey end** includes user's to-do URL

### Task: Workload Logic Verification
- [ ] **Zero hours validation** - 0 is valid and completes step
- [ ] **Day field mapping** to Ukrainian weekday names
- [ ] **Week total calculation** Monday through current/target day
- [ ] **Capacity handling** updates when provided
- [ ] **Database lookups** by user name exact match
- [ ] **Response formatting** matches multi-line template exactly

## Error Handling & Edge Cases Review

### Task: Error Response Consistency
- [ ] **Notion API errors** return "Спробуй трохи піздніше. Я тут пораюсь по хаті."
- [ ] **Generic errors** return "Some error"
- [ ] **User not found** appropriate Ukrainian message
- [ ] **Validation errors** clear Ukrainian messages
- [ ] **HTTP 500 errors** don't expose internal details
- [ ] **Logging** captures sufficient detail for debugging

### Task: Edge Case Handling
- [ ] **Empty/null inputs** handled gracefully
- [ ] **Invalid step names** rejected with clear errors
- [ ] **Timezone edge cases** Monday 00:00 boundary correct
- [ ] **Daylight saving transitions** handled correctly
- [ ] **Concurrent access** doesn't cause data corruption
- [ ] **Rate limiting** prevents API abuse

## Performance & Scalability Review

### Task: Database Performance
- [ ] **Connection pooling** configured appropriately
- [ ] **Query optimization** uses indexes effectively
- [ ] **Transaction scope** minimized for performance
- [ ] **Batch operations** where applicable
- [ ] **Connection limits** don't exceed database capacity
- [ ] **Query timeouts** prevent hanging requests

### Task: External API Performance
- [ ] **HTTP timeouts** configured appropriately
- [ ] **Connection reuse** for HTTP clients
- [ ] **Rate limiting** respects API limits
- [ ] **Caching** where appropriate and safe
- [ ] **Circuit breakers** for failing services
- [ ] **Async operations** where beneficial

## Security Review

### Task: Input Validation
- [ ] **SQL injection** prevention through parameterized queries
- [ ] **XSS prevention** in response data
- [ ] **Input sanitization** for all user inputs
- [ ] **Command injection** prevention
- [ ] **Path traversal** prevention
- [ ] **Data validation** at service boundaries

### Task: Authentication & Authorization
- [ ] **API credentials** stored securely
- [ ] **Environment variables** for sensitive data
- [ ] **Access controls** for database operations
- [ ] **Webhook authentication** validates Discord requests
- [ ] **Rate limiting** prevents abuse
- [ ] **Audit logging** for security events

## Testing Coverage Review

### Task: Unit Test Coverage
- [ ] **90% code coverage** for new modules achieved
- [ ] **Edge cases** covered in tests
- [ ] **Error conditions** tested
- [ ] **Mock usage** appropriate and complete
- [ ] **Test data** realistic and comprehensive
- [ ] **Assertion quality** validates correct behavior

### Task: Integration Test Coverage
- [ ] **End-to-end flows** tested
- [ ] **External API mocking** comprehensive
- [ ] **Database integration** tested with real DB
- [ ] **Error scenarios** tested
- [ ] **Performance tests** validate acceptable response times
- [ ] **Load tests** validate scalability

## Documentation Review

### Task: Code Documentation
- [ ] **Docstrings** for all public methods
- [ ] **Type hints** comprehensive and accurate
- [ ] **Comments** explain complex business logic
- [ ] **README** updated with migration details
- [ ] **API documentation** for webhook endpoints
- [ ] **Configuration documentation** complete

### Task: Operational Documentation
- [ ] **Deployment procedures** documented
- [ ] **Environment setup** instructions clear
- [ ] **Monitoring setup** documented
- [ ] **Troubleshooting guides** available
- [ ] **Rollback procedures** documented
- [ ] **Performance tuning** guidelines provided