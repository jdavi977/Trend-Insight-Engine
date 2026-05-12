# YouTube API

## `POST /analyze/youtube`

Ingests comments from a YouTube video, runs them through the cleaning pipeline, extracts structured product insights via LLM, and returns the result with optional RAG context from prior analyses.

### Request

```json
{
  "youtubeURL": "https://www.youtube.com/watch?v=<video_id>"
}
```

| Field        | Type   | Required | Description                    |
|--------------|--------|----------|--------------------------------|
| `youtubeURL` | string | yes      | Full YouTube video URL         |

The URL is validated before processing — it must be a recognisable YouTube video link (e.g. `youtube.com/watch?v=...` or `youtu.be/...`).

### Response `200 OK`

```json
{
  "source": "youtube",
  "title": "Video Title or null",
  "problems": [
    {
      "problem": "Description of the issue",
      "type": "Bug | Usability | Feature Request | ...",
      "total_likes": 142,
      "severity": 3,
      "frequency": 4
    }
  ],
  "retrieved_context": [
    {
      "problem": "Prior insight problem text",
      "type": "Bug",
      "severity": 2,
      "frequency": 3,
      "source": "youtube",
      "source_url": "https://www.youtube.com/watch?v=abc",
      "title": "Related video title",
      "extracted_at": "2026-05-05T12:00:00",
      "similarity": 0.87
    }
  ]
}
```

| Field               | Type                    | Description                                             |
|---------------------|-------------------------|---------------------------------------------------------|
| `source`            | `"youtube"`             | Always `"youtube"` for this endpoint                   |
| `title`             | string \| null          | Video title; populated when RAG is enabled              |
| `problems`          | array                   | One or more extracted problem items (see below)         |
| `retrieved_context` | array of RetrievedInsight | Similar insights from past analyses; empty if RAG read is disabled |

#### Problem item fields

| Field         | Type   | Constraints | Description                              |
|---------------|--------|-------------|------------------------------------------|
| `problem`     | string | min 5 chars | Short description of the problem         |
| `type`        | string | min 2 chars | Problem category (e.g. Bug, Usability)   |
| `total_likes` | int    | ≥ 0         | Total likes across comments mentioning this problem |
| `severity`    | int    | 1–5         | How severe the problem is                |
| `frequency`   | int    | 1–5         | How often the problem is mentioned       |

#### RetrievedInsight fields

| Field          | Type                       | Description                              |
|----------------|----------------------------|------------------------------------------|
| `problem`      | string                     | Problem text from the prior insight       |
| `type`         | string                     | Problem category                         |
| `severity`     | int (1–5)                  |                                          |
| `frequency`    | int (1–5)                  |                                          |
| `source`       | `"youtube"` \| `"app_store"` | Origin of the prior insight             |
| `source_url`   | string                     | URL that produced the prior insight       |
| `title`        | string \| null             | Title of the source video/app            |
| `extracted_at` | string (ISO 8601)          | When the prior insight was extracted      |
| `similarity`   | float                      | Cosine similarity score (0–1); only returned when ≥ `RAG_MIN_SIMILARITY` (0.35) |

Returns `null` (empty body) if the LLM extracts no problems from the comments.

### Errors

| Status | Condition                                      |
|--------|------------------------------------------------|
| 400    | `youtubeURL` fails URL validation              |
| 422    | Request body is missing or malformed           |

See [errors.md](errors.md) for the response envelope.
