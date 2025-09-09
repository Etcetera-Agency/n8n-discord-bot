# Task 01: Notion connector

## Goal
Implement a reusable async wrapper around the Notion REST API. The existing
workflow only **queries** databases and **updates** properties on existing
pages; it never creates new ones. The connector should expose helpers that
replace n8n's Notion nodes.

## Supported operations
1. **Team Directory lookups**
   - find by employee name
   - find by Discord channel ID
   - update a page with Discord user ID and channel ID
2. **Workload database**
   - fetch a user’s workload page by name
   - update a specific day field with planned hours
3. **Profile statistics**
   - fetch a profile-stats page by name
   - update remaining Upwork connects

All operations share the same auth headers and return normalized results.

## Expected inputs and outputs
### Query Team Directory by channel ID
Request sent to `/v1/databases/{TD_DB}/query`:
```json
{
  "filter": {
    "property": "Discord channel ID",
    "rich_text": {"contains": "1234567890"}
  }
}
```
Example Notion response:
```json
{
  "results": [
    {
      "id": "PAGE_ID",
      "url": "https://www.notion.so/Roman-Lernichenko-b02bf04c43e4404ca4e21707ae8b61cc",
      "properties": {
        "Name": {"title": [{"plain_text": "Roman Lernichenko"}]},
        "Discord ID": {"rich_text": []},
        "Discord channel ID": {"rich_text": []},
        "ToDo": {
          "rich_text": [
            {"plain_text": "Todo - Roman Lernichenko", "href": "https://www.notion.so/11cc3573e5108104a0f1d579c3f9a648"},
            {"plain_text": " https://www.notion.so/11cc3573e5108104a0f1d579c3f9a648"}
          ]
        }
      }
    }
  ]
}
```
Normalized output passed to handlers:
```json
{
  "status": "ok",
  "results": [
    {
      "id": "PAGE_ID",
      "url": "https://www.notion.so/Roman-Lernichenko-b02bf04c43e4404ca4e21707ae8b61cc",
      "name": "Roman Lernichenko",
      "discord_id": "",
      "channel_id": "",
      "to_do": "https://www.notion.so/11cc3573e5108104a0f1d579c3f9a648"
    }
  ]
}
```

### Update Team Directory page with IDs
Request sent to `/v1/pages/PAGE_ID`:
```json
{
  "properties": {
    "Discord ID": {"rich_text": [{"text": {"content": "321"}}]},
    "Discord channel ID": {"rich_text": [{"text": {"content": "1234567890"}}]}
  }
}
```
Normalized success response:
```json
{ "status": "ok" }
```

The same `query_database` and `update_page` helpers are reused for workload and
profile-stats lookups and updates.

## Pseudocode
```
def base_headers():
    token = os.environ["NOTION_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

async def query_database(database_id, filter):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    async with aiohttp.post(url, headers=base_headers(), json={"filter": filter}) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise NotionError(data)
        return normalize_query(data)

async def update_page(page_id, properties):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    async with aiohttp.patch(url, headers=base_headers(), json={"properties": properties}) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise NotionError(data)
        return {"status": "ok"}
```

`normalize_query` should extract the page `id`, `url`, and needed properties
(`Discord ID`, `Discord channel ID`, `To Do`, etc.).

## Testing
- Unit tests should mock HTTP calls for `query_database` and `update_page`,
  asserting headers, endpoints, and response normalization.
- End-to-end tests should mock Notion's API to verify registration, workload,
  connects, and other handlers work without n8n.

- All tests must log inputs, steps, and outputs to a file for later review.
