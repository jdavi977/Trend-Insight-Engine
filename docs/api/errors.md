# Error Reference

## Response Envelope

All error responses use the same JSON envelope:

```json
{
  "detail": "<human-readable message>"
}
```

Validation errors (`422`) use an array instead of a string:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "youtubeURL"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

The `loc` array identifies the path to the invalid field (e.g. `["body", "fieldName"]`).

---

## Error Codes

### `400 Bad Request`

The request was well-formed but failed domain validation before any processing occurred.

| Endpoint              | `detail` message   | Cause                                                              |
|-----------------------|--------------------|--------------------------------------------------------------------|
| `POST /analyze/youtube`   | `"Invalid link"` | `youtubeURL` is not a recognisable YouTube URL                     |
| `POST /analyze/appStore`  | `"Invalid link"` | `appStoreURL` is not a recognisable `apps.apple.com` URL          |

---

### `422 Unprocessable Entity`

The request body failed Pydantic validation. The `detail` field is an array of validation error objects.

Common causes:

| Cause                                    | Example `loc`             |
|------------------------------------------|---------------------------|
| Required field missing                   | `["body", "youtubeURL"]`  |
| Field type mismatch                      | `["body", "k"]`           |
| String too short (min_length violated)   | `["query", "query"]`      |
| Integer out of range                     | `["query", "k"]`          |

---

### `503 Service Unavailable`

A downstream dependency (Supabase) failed to respond. Retrying after a short delay is appropriate.

| Endpoint              | `detail` message                              | Cause                                      |
|-----------------------|-----------------------------------------------|--------------------------------------------|
| `GET /get/homePage`       | `"Failed to fetch game data from supabase"`   | Supabase query for Gaming category failed  |
| `GET /get/homePage`       | `"Failed to fetch scitech data from supabase"` | Supabase query for Science & Tech failed  |
| `GET /get/homePage`       | `"Failed to fetch style data from supabase"`  | Supabase query for How-to & Style failed   |
| `GET /get/homePageAppStore` | `"Failed to fetch game data from supabase"` | Supabase query for Games genre failed      |
| `GET /get/homePageAppStore` | `"Failed to fetch scitech data from supabase"` | Supabase query for Social genre failed  |
| `GET /get/homePageAppStore` | `"Failed to fetch style data from supabase"` | Supabase query for Utilities genre failed |

Each category is fetched independently; the first failure short-circuits and returns 503.
