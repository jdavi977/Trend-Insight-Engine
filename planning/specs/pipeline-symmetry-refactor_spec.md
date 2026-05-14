# Pipeline Symmetry Refactor

**Date:** 2026-05-13
**Scope:** Make YouTube and App Store run through identical pipeline stages with no source-specific abstractions

---

## Decisions

| Decision | Choice |
|---|---|
| Title assignment | Always set manually from metadata API after `extract_insights`; never from LLM echo |
| Preprocessing shape | Align App Store rows to carry `{Id, Title, rating, vote_count, Content}` — matching YouTube's `{Id, Title, Likes, Content}` |
| `appstore_rows_for_llm` | Delete it; field mapping happens inline in `_appstore_clean` and manual service |
| `source` string | Unify to `"app_store"` everywhere |
| Metadata fetching | Both manual services fetch unconditionally (not gated on RAG flags) |
| App Store prompt | Add input-shape description block matching `YOUTUBE_PROMPT_TEMPLATE` style |

---

## Changes by File

### `app/config/promptTemplates.py`

**1. Remove `"title"` from `youtubePromptOutput`.**
The LLM should not be responsible for echoing the title. It will be set manually post-extraction.

Before:
```
{
  "source": "youtube",
  "title": "Title"
  "problems": [...]
}
```

After:
```
{
  "source": "youtube",
  "problems": [...]
}
```

**2. Add input-shape block to `APPSTORE_PROMPT_TEMPLATE`.**
Match the style already used in `YOUTUBE_PROMPT_TEMPLATE`.

```python
APPSTORE_PROMPT_TEMPLATE = """
{intro}

You will receive a JSON array of App Store reviews, each with:
- "Title": name of the app
- "rating": star rating (1–5)
- "vote_count": number of helpful votes
- "Content": the review text

Your task:
...
```

---

### `app/preprocessing/reviewPipeline.py`

**Delete `appstore_rows_for_llm`.**
This function is the root of the divergence — it strips rows down to `{Votes, Content}` and hides `Id` and `Title` from the LLM. Callers will do inline field mapping instead.

`clean()` and the private helpers are unchanged.

---

### `app/services/appstore_service.py`

**Replace `appstore_rows_for_llm` call with inline mapping** (matching `youtube_service.py`'s pattern):

```python
# Before
from app.preprocessing.reviewPipeline import appstore_rows_for_llm
cleaned_data = appstore_rows_for_llm(all_items, default.keywords)

# After
from app.preprocessing.reviewPipeline import clean
rows = [{**item, "Content": item["content"]} for item in all_items]
cleaned_data = clean(rows, **APPSTORE_PREPROCESS)
```

`result.title = app_name` is already set post-extraction. No change needed there.

---

### `app/services/youtube_service.py`

**Remove RAG guard around `get_video_metadata`.**

```python
# Before
meta = {}
if RAG_READ_ENABLED or RAG_WRITE_ENABLED:
    meta = get_video_metadata(id)

# After
meta = get_video_metadata(id)
```

Title and thumbnail are always part of the response, not just a RAG side-effect.

---

### `app/jobs/automaticAppStore.py`

**1. Fix `source` string.**
```python
# Before
source="appstore",
# After
source="app_store",
```

**2. Replace `_appstore_clean` to do inline mapping** (matching `_youtube_clean`):

```python
# Before
def _appstore_clean(raw: list, keywords: list) -> list:
    return appstore_rows_for_llm(raw, keywords)

# After
def _appstore_clean(raw: list, keywords: list) -> list:
    rows = [{**item, "Content": item["content"]} for item in raw]
    kw = tuple(keywords) if keywords else None
    return clean(rows, **{**APPSTORE_PREPROCESS, "keyword_filter": kw})
```

`_appstore_post_extract` already sets `result.title = item.get("Title")`. No change needed.

---

### `app/jobs/automaticYoutube.py`

**Set `result.title` explicitly in `_youtube_post_extract`**, now that the LLM no longer echoes it:

```python
# Before
def _youtube_post_extract(result, item):
    if RAG_WRITE_ENABLED:
        source_url = f"https://www.youtube.com/watch?v={item['Id']}"
        embed_and_store(result, source_url)

# After
def _youtube_post_extract(result, item):
    result.title = item.get("Title")
    if RAG_WRITE_ENABLED:
        source_url = f"https://www.youtube.com/watch?v={item['Id']}"
        embed_and_store(result, source_url)
```

---

## Symmetric pipeline after refactor

Both sources will follow this identical shape through the pipeline:

```
ingestion  →  [{Id, Title, <engagement>, <text_field>}]
                          ↓ inline field mapping
clean()    →  [{Id, Title, <engagement>, Content}]
                          ↓ extract_insights()
LLMExtraction (title=None)
                          ↓ post_extract / service layer
result.title = <metadata api value>
                          ↓ embed_and_store / response
```

### Row shapes sent to LLM

| Field    | YouTube          | App Store          |
|----------|------------------|--------------------|
| `Id`     | video id         | app id             |
| `Title`  | video title      | app name           |
| Engagement | `Likes`        | `vote_count`       |
| Extra    | —                | `rating`           |
| `Content`| comment text     | review text        |

---

## What does NOT change

- `clean()` internals and `APPSTORE_PREPROCESS` / `YOUTUBE_PREPROCESS` configs
- `LLMExtraction`, `YoutubeProblemItem`, `AppStoreProblemItem` schemas
- RAG read path (`enrich_problems`) — manual services only, unchanged
- `SourceAdapter` and `run_automatic_pipeline` — no changes needed
- Supabase persistence logic
