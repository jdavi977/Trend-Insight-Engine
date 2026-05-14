# Preprocessing Pipeline Optimisation

**Date:** 2026-05-13
**Scope:** Three targeted improvements to `reviewPipeline.py` — pre-compiled regex, minimum content length filter, and collapsing five list passes into one.

---

## Why

The current `clean()` function makes **five separate passes** over the row list, re-compiles keyword regex patterns on every call inside the inner loop, and has no floor on content length — short noise strings (`"ok"`, `"bad"`) pass through and reach the LLM, burning tokens for zero insight.

These three changes address correctness, token cost, and code clarity. None require new dependencies.

---

## Decisions

| Decision | Choice |
|---|---|
| Regex compilation | Pre-compile keyword patterns once inside `clean()`, before the row loop |
| Min-length semantics | Applied to **post-normalize** content (after lowercase + emoji strip), so length reflects signal not formatting |
| Min-length default | `20` characters — filters `"ok"`, `"great app"`, `"love it"` but keeps real sentences |
| Pipeline shape | Collapse five private helpers into a single `for` loop inside `clean()` |
| Private helpers | Keep `_filter_engagement`, `_normalise_content`, `_strip_emojis`, `_apply_keyword_filter`, `_dedup` as **deleted** — their logic moves inline |
| Dedup strategy | Unchanged — last-seen-wins on normalized `Content` |
| Public API | `clean()` signature gets one new optional param: `min_length: int = 20`. All existing callers work without changes. |

---

## Changes by File

### `app/preprocessing/reviewPipeline.py`

**Replace the five-pass implementation with a single-pass loop.**

Before (current shape):
```python
def clean(rows, *, engagement_field, threshold, keyword_filter=None):
    after_threshold = _filter_engagement(rows, engagement_field, threshold)
    normalised = _normalise_content(after_threshold)
    after_emoji = _strip_emojis(normalised)
    after_keywords = _apply_keyword_filter(after_emoji, keyword_filter)
    return _dedup(after_keywords)
```

After:
```python
def clean(
    rows: list[dict],
    *,
    engagement_field: str,
    threshold: int | float,
    keyword_filter: Optional[tuple[str, ...]] = None,
    min_length: int = 20,
) -> list[dict]:
    patterns = (
        [re.compile(r"\b" + re.escape(kw) + r"\b") for kw in keyword_filter]
        if keyword_filter
        else None
    )

    seen: dict[str, dict] = {}
    for row in rows:
        # 1. Engagement filter
        try:
            score = float(row.get(engagement_field, 0) or 0)
        except (ValueError, TypeError):
            score = 0.0
        if score < threshold:
            continue

        # 2. Normalise
        content = EMOJI_REGEX.sub("", row["Content"].lower().strip())

        # 3. Min-length
        if len(content) < min_length:
            continue

        # 4. Keyword filter (pre-compiled patterns, short-circuit on first match)
        if patterns and not any(p.search(content) for p in patterns):
            continue

        # 5. Dedup — last-seen wins
        seen[content] = {**row, "Content": content}

    return list(seen.values())
```

**Delete all five private helpers** — their logic is now inline:
- `_filter_engagement`
- `_normalise_content`
- `_strip_emojis`
- `_apply_keyword_filter`
- `_dedup`

---

## What does NOT change

- `APPSTORE_PREPROCESS` and `YOUTUBE_PREPROCESS` config dicts — no `min_length` key needed; the default of `20` applies to both
- All call sites in `appstore_service.py`, `youtube_service.py`, `automaticAppStore.py`, `automaticYoutube.py` — signature is backwards-compatible
- `EMOJI_REGEX` import from `app/config/regex.py`
- Row shapes entering and leaving `clean()` — same contract as before

---

## Callers (no changes required)

| File | Call site | Impact |
|---|---|---|
| `app/services/youtube_service.py` | `clean(rows, **YOUTUBE_PREPROCESS)` | None — `min_length` defaults to 20 |
| `app/services/appstore_service.py` | `clean(rows, **APPSTORE_PREPROCESS)` | None |
| `app/jobs/automaticYoutube.py` | `clean(rows, **YOUTUBE_PREPROCESS, ...)` | None |
| `app/jobs/automaticAppStore.py` | `clean(rows, **{...APPSTORE_PREPROCESS, "keyword_filter": kw})` | None |

---

## Test coverage

These tests live in `tests/preprocessing/test_reviewPipeline.py` (already called out in `app/CONTEXT.md` as a pre-refactor safety net).

Add or update cases for:

| Case | What to assert |
|---|---|
| Row with content `"ok"` (2 chars) | Dropped when `min_length=20` |
| Row with content `"ok"` and `min_length=2` | Kept |
| Keyword patterns pre-compiled | `re.compile` called once regardless of row count (patch `re.compile` and assert call count) |
| Duplicate rows with different casing | Collapsed to one after normalisation |
| Engagement below threshold | Dropped before normalisation (assert `Content` not mutated on dropped rows) |

---

## What this does NOT solve (future work)

- **Language filtering** — non-English reviews still pass through to the LLM
- **Semantic / fuzzy dedup** — rephrased duplicates (`"app crashes"` vs `"keeps crashing"`) still reach the LLM
- **Engagement percentile thresholds** — absolute thresholds (`>= 50 likes`) don't adapt to volume variance across different channels/apps
