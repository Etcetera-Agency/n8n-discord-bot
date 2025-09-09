# End-to-End Survey Testing Guide

This document describes how to write and run end-to-end tests for the survey flow of the Discord bot. The tests begin **after the user presses the guide button** in the Discord channel.

## 1. Environment and Tools
- Discord interactions are simulated directly in the tests; no live server or channel is required.
- Bot handlers are imported and invoked within the test process.
- Testing framework: Jest or Playwright for message exchange, and `pytest` for Python assertions.
- HTTP mocking library such as `nock`/`msw` to emulate external services (e.g., Notion).
- Example payloads: load from `payload_examples.txt`.
- Sample API responses: load from the `responses/` directory.

## 2. Scenario Files
Store scenarios under `tests/e2e/surveys/<scenario-name>/`:
- `dbSetup.json` – initial database state.
- `notionResponses.json` – mocked responses from Notion or other services.
- `steps.json` – ordered list of user/bot interactions. Each step describes:
  - `user`: message or button pressed.
  - `bot`: expected bot reply.
  - `dbExpected`: expected database state after the step.
  - `notionMock`: expected request/response from the mock service.

## 3. Initialization
Before running a scenario:
1. Reset the test database using `dbSetup.json`.
2. Configure mock services with `notionResponses.json`.
3. Load the initial guide payload from `payload_examples.txt`.
4. Simulate the **guide button press** by invoking the bot's handler with the loaded payload.

## 4. Executing Steps
For each entry in `steps.json`:
1. Provide the user's input to the bot handler (simulating a Discord message).
2. Wait for the bot's reply and assert it matches `bot`.
3. Verify the database matches `dbExpected`.
4. Ensure the mock service interactions match `notionMock`.

## 5. Coverage
Create scenarios that cover:
- Valid, invalid, and cancelled user inputs.
- All survey branches and repeated steps.
- Successful completion and early termination.

## 6. Adding New Scenarios
1. Copy an existing scenario folder.
2. Update `dbSetup.json`, `notionResponses.json`, and `steps.json`.
3. Append new guide payloads to `payload_examples.txt` as needed.
4. Run `pytest tests/e2e` to execute the scenario.

## 7. Manual Execution
Tests run entirely locally and can be executed without external services or CI.

## 8. Logging and Debugging
- Store logs for each scenario in `tests/e2e/logs/<scenario-name>/`.
- On failure, capture the last simulated Discord messages and mock service history for troubleshooting.
