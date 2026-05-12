# App Store API

## `POST /analyze/appStore`

Ingests reviews from an iOS App Store app page, runs them through the cleaning pipeline, extracts structured product insights via LLM, and returns the result with optional RAG context from prior analyses.

### Request

```json
{
  "appStoreURL": "https://apps.apple.com/us/app/<app-name>/id<app_id>"
}
```

| Field         | Type   | Required | Description                     |
|---------------|--------|----------|---------------------------------|
| `appStoreURL` | string | yes      | Full App Store product page URL |

The URL is validated before processing — it must be a recognisable `apps.apple.com` URL containing an app ID.

### Response `200 OK`

```json
{
  "source": "app_store",
  "title": "App Title or null",
  "problems": [
    {
      "problem": "Description of the issue",
      "type": "Usability | Bug | Feature Request | ...",
      "average_rating": 2.3,
      "severity": 4,
      "frequency": 3,
      "example_reviews": [
        "The login screen crashes every time I open it.",
        "Can't sign in — app freezes on launch."
      ]
    }
  ],
  "retrieved_context": [
    {
      "problem": "Prior insight problem text",
      "type": "Bug",
      "severity": 3,
      "frequency": 2,
      "source": "app_store",
      "source_url": "https://apps.apple.com/us/app/example/id123456",
      "title": "Releated app title",
      "extracted_at": "2026-04-28T09:15:00",
      "similarity": 0.79
    }
  ]
}
```

| Field               | Type                    | Description                                             |
|---------------------|-------------------------|---------------------------------------------------------|
| `source`            | `"app_store"`           | Always `"app_store"` for this endpoint                  |
| `title`             | string \| null          | App name; currently always `null` for this source       |
| `problems`          | array                   | One or more extracted problem items (see below)         |
| `retrieved_context` | array of RetrievedInsight | Similar insights from past analyses; empty if RAG read is disabled |

#### Problem item fields

| Field             | Type          | Constraints    | Description                                                  |
|-------------------|---------------|----------------|--------------------------------------------------------------|
| `problem`         | string        | min 5 chars    | Short description of the problem                             |
| `type`            | string        | min 2 chars    | Problem category (e.g. Bug, Usability)                       |
| `average_rating`  | float         | 0–5            | Average star rating of reviews that mention this problem     |
| `severity`        | int           | 1–5            | How severe the problem is                                    |
| `frequency`       | int           | 1–5            | How often the problem is mentioned                           |
| `example_reviews` | array[string] | min 1 item     | Representative review snippets from the source data          |

#### RetrievedInsight fields

See [youtube.md — RetrievedInsight fields](youtube.md#retrievedinsight-fields). The schema is identical across sources.

Returns `null` (empty body) if the LLM extracts no problems from the reviews.

### Errors

| Status | Condition                                       |
|--------|-------------------------------------------------|
| 400    | `appStoreURL` fails URL validation              |
| 422    | Request body is missing or malformed            |

See [errors.md](errors.md) for the response envelope.
