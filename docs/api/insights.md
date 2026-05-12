# Insights API

## `GET /insights/similar`

Performs a semantic similarity search over stored insights using the RAG vector store. Returns the top-`k` insights most similar to the query string.

### Query Parameters

| Parameter | Type   | Default | Constraints | Description                              |
|-----------|--------|---------|-------------|------------------------------------------|
| `query`   | string | —       | required, min length 1 | Natural-language search query  |
| `k`       | int    | 5       | 1–50        | Maximum number of results to return      |

Only results with a similarity score ≥ `RAG_MIN_SIMILARITY` (0.35) are returned. If fewer than `k` results meet the threshold, the actual result count will be lower.

### Response `200 OK`

```json
{
  "query": "crashes on login",
  "results": [
    {
      "problem": "App crashes immediately after tapping the login button",
      "type": "Bug",
      "severity": 5,
      "frequency": 4,
      "source": "app_store",
      "source_url": "https://apps.apple.com/us/app/example/id123456",
      "title": null,
      "extracted_at": "2026-05-01T14:30:00",
      "similarity": 0.91
    }
  ]
}
```

| Field     | Type                    | Description                              |
|-----------|-------------------------|------------------------------------------|
| `query`   | string                  | The query string as received             |
| `results` | array of RetrievedInsight | Matched insights sorted by similarity descending |

#### RetrievedInsight fields

| Field          | Type                         | Description                               |
|----------------|------------------------------|-------------------------------------------|
| `problem`      | string                       | Problem description                       |
| `type`         | string                       | Problem category                          |
| `severity`     | int (1–5)                    | Severity rating                           |
| `frequency`    | int (1–5)                    | Frequency rating                          |
| `source`       | `"youtube"` \| `"app_store"` | Data source                               |
| `source_url`   | string                       | URL of the original analysis              |
| `title`        | string \| null               | Video or app title if available           |
| `extracted_at` | string (ISO 8601)            | Timestamp when the insight was extracted  |
| `similarity`   | float (0–1)                  | Cosine similarity to the query            |

`results` is an empty array when no stored insights meet the similarity threshold.

### Errors

| Status | Condition                              |
|--------|----------------------------------------|
| 422    | `query` is missing or empty; `k` is outside 1–50 |

See [errors.md](errors.md) for the response envelope.
