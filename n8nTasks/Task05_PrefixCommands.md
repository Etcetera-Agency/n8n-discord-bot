# Task 05: Prefix command router

## Goal
Handle the limited set of `!`-prefixed commands locally so the dispatcher can invoke the matching handler without n8n.

### Input Variants
Prefix messages from Discord are parsed into payloads like those in `payload_examples.txt`. The workflow defines only two prefix commands:
- `!register <display name>`
- `!unregister`

Each payload contains common fields (`userId`, `channelId`, `sessionId`, `author`, `channelName`, `timestamp`) and a `result` block holding command‑specific data.

### Output Variants
Handlers return localized strings following templates defined in Tasks 03–10. The router wraps these into:
```json
{ "output": "…" }
```
for standalone commands, or
```json
{ "output": "…", "survey": "continue|end" }
```
when called as part of a survey.

## Steps
1. Implement a parser that checks `payload["message"]` for `!register` or `!unregister`.
2. For `!register`, extract the display name and store it in `payload["result"]["text"]`.
3. For `!unregister`, leave `payload["result"]` empty.
4. Forward the normalized payload to `router.dispatch` so the appropriate handler executes.

## Pseudocode
```python
def parse_prefix(message: str) -> Optional[dict]:
    if message.startswith("!register"):
        name = message.removeprefix("!register").strip()
        return {"command": "register", "result": {"text": name}}
    if message.startswith("!unregister"):
        return {"command": "unregister", "result": {}}
    return None  # not a prefix command
```

## Tests
- Unit: feed sample messages (`"!register Alice"`, `"!unregister"`) and assert that the parser returns the expected command and
  extracted arguments.
- End-to-end: issue `!register` and `!unregister` through Discord and verify handlers return the templates described in Tasks 03
  and 04.
- All tests must log inputs, steps, and outputs to a file for later review.