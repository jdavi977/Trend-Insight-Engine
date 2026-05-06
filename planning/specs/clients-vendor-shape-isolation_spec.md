# Clients Own Vendor Shape: Ingestion Deals in Domain Rows

## Problem

The [clients/ wrapper-layer ADR](../decisions/2026-05-01-clients-wrapper-layer.md) promises that `clients/` is the single seam for each external SDK and the single mock point per vendor. Today the *transport* lives in clients but the *response shape* leaks one layer up into ingestion — so the seam is leaky and the ADR's "single mock point" guarantee is false.

- **YouTube vendor JSON walked in ingestion.** [app/ingestion/youtubeComments.py:26-32](app/ingestion/youtubeComments.py#L26-L32) reaches into `item["snippet"]["topLevelComment"]["snippet"]["likeCount" | "textDisplay"]`. The YouTube Data API v3 schema lives in ingestion, not in [app/clients/youtube.py](app/clients/youtube.py).
- **YouTube thumbnail picking is also vendor-shape.** [app/ingestion/youtubeComments.py:36-51](app/ingestion/youtubeComments.py#L36-L51) walks `item["snippet"]["thumbnails"]` size keys (`maxres` → `default`) — same leak, different endpoint.
- **iTunes RSS shape walked in ingestion.** [app/ingestion/appStoreReviews.py:13-26](app/ingestion/appStoreReviews.py#L13-L26) parses `data['feed']['entry']`, `review["im:rating"]["label"]`, `review["im:voteCount"]["label"]`, `review["title"]["label"]`, `review["content"]["label"]`. The Atom-style `im:*` keys are vendor knowledge.
- **The "single mock point" guarantee is broken.** Both [tests/clients/test_youtube_client.py](tests/clients/test_youtube_client.py) AND [tests/ingestion/test_youtubeComments.py:34-48](tests/ingestion/test_youtubeComments.py#L34-L48) carry YouTube-API-shaped fixtures (`{"snippet": {"topLevelComment": {"snippet": {...}}}}`). Same for App Store: [tests/ingestion/test_appStoreReviews.py:27-33](tests/ingestion/test_appStoreReviews.py#L27-L33) builds `im:rating`/`im:voteCount` fixtures that should only exist in client tests.
- **Latent breakage on rename.** When YouTube renames `topLevelComment` or Apple deprecates `im:rating` (likely — see [iTunes RSS deprecation ADR](../decisions/2026-05-05-itunes-rss-top-apps-deprecation.md)), two layers and two test files change. `list_top_apps` in [app/clients/appstore.py:31-39](app/clients/appstore.py#L31-L39) and `getVideoCategories` in [app/clients/youtube.py:41-57](app/clients/youtube.py#L41-L57) already follow the right pattern — comments and reviews are the outliers.

## Solution

Push the dict-walking down. `clients/` returns plain domain rows; `ingestion/` becomes a thin orchestration layer (URL parsing, pagination, batching, retry) that doesn't know vendor JSON keys.

```python
# app/clients/youtube.py
def list_comment_threads(video_id, order, max_results) -> list[dict]:
    """Returns [{"Likes": int, "Text": str}, ...] — domain rows, not vendor JSON."""

def list_most_popular(category_id, max_results) -> list[dict]:
    """Returns [{"Id": str, "Title": str, "Thumbnail": dict | None}, ...]."""

# app/clients/appstore.py
def list_reviews(app_id, sort_by, page, timeout=10) -> list[dict]:
    """Returns [{"rating": str, "title": str, "content": str, "vote_count": str}, ...].
    Returns [] when the page has no entries or fewer than 2 (current sentinel)."""
```

Behind those interfaces:
1. Vendor SDK / HTTP call (unchanged).
2. The dict-walk that's currently in ingestion.
3. Return rows shaped for the domain — caller-facing keys, no `im:*` or `snippet.topLevelComment.snippet`.

After this change, `getYoutubeComments` is a `for row in list_comment_threads(...): rows.append({"Id": id, "Title": title, **row})`-style loop, and `getAppReviews` is a paginate-until-empty loop over `list_reviews`. Neither knows vendor key names.

## Caller Changes

| File | Before | After |
|------|--------|-------|
| [app/clients/youtube.py](app/clients/youtube.py) | `list_comment_threads` returns raw `items` | returns `[{"Likes", "Text"}, ...]` |
| [app/clients/youtube.py](app/clients/youtube.py) | `list_most_popular` returns raw `items` | returns `[{"Id", "Title", "Thumbnail"}, ...]`; thumbnail-priority logic moves here |
| [app/clients/appstore.py](app/clients/appstore.py) | `fetch_reviews_page` returns full `response.json()` | new `list_reviews` returns `[{rating, title, content, vote_count}, ...]`; `fetch_reviews_page` either deleted or kept private |
| [app/ingestion/youtubeComments.py](app/ingestion/youtubeComments.py) | walks `snippet.topLevelComment.snippet` and `thumbnails.{maxres,...}` | enriches client rows with `Id`/`Title` only |
| [app/ingestion/appStoreReviews.py](app/ingestion/appStoreReviews.py) | walks `feed/entry/im:*` and decides break condition from raw shape | paginates `list_reviews`; break condition is "client returned `[]` or `len < 2`" |

Pagination break condition (`len(entry) <= 1`) is currently driven by raw shape inspection at [app/ingestion/appStoreReviews.py:17](app/ingestion/appStoreReviews.py#L17). Two options:

- **(a)** Have `list_reviews` return `[]` when the underlying entry count is `≤ 1`. Ingestion stops on empty list. Cleaner; matches the spirit of the seam.
- **(b)** Have `list_reviews` return whatever rows it parsed and ingestion stops on `len(rows) < 2`. Leaks the "page-has-pagination-marker" semantic into ingestion.

Recommendation: (a). The "first entry is feed metadata, not a review" quirk is iTunes RSS knowledge, so it lives in the client.

## Benefits

- **Locality.** When YouTube renames `topLevelComment` or Apple deprecates `im:rating`, one file changes — the client. (Ties directly to the [clients ADR](../decisions/2026-05-01-clients-wrapper-layer.md) consequence "A single place to change SDK versions".)
- **Leverage.** Restores the ADR's promised mock seam: `clients/` is the only layer with vendor knowledge, so client tests are the only place vendor-shape fixtures live.
- **Test simplification.** [tests/ingestion/test_youtubeComments.py](tests/ingestion/test_youtubeComments.py) and [tests/ingestion/test_appStoreReviews.py](tests/ingestion/test_appStoreReviews.py) drop their `topLevelComment` / `im:rating` fixtures and use simple domain dicts.
- **Symmetry.** `getVideoCategories` ([app/clients/youtube.py:41-57](app/clients/youtube.py#L41-L57)) and `list_top_apps` ([app/clients/appstore.py:15-40](app/clients/appstore.py#L15-L40)) already do this. Comments/reviews catch up.

## Test Plan

Vendor fixtures move to client tests; ingestion tests use domain dicts.

**Client tests (where vendor JSON now lives):**
- [tests/clients/test_youtube_client.py](tests/clients/test_youtube_client.py) — add cases for `list_comment_threads`: builds the YouTube `commentThreads` mock, asserts it returns `[{"Likes", "Text"}, ...]`.
- [tests/clients/test_youtube_client.py](tests/clients/test_youtube_client.py) — add cases for `list_most_popular`: covers `maxres` happy path, fallback through priority list, no-thumbnails returns `None`. (These are the cases currently in ingestion tests at lines 78-146.)
- [tests/clients/test_appstore_client.py](tests/clients/test_appstore_client.py) — add `list_reviews`: `im:*`-shaped fixture in → domain rows out. Cover the `len(entry) <= 1` → `[]` rule and the empty-feed → `[]` rule.

**Ingestion tests (now vendor-agnostic):**
- [tests/ingestion/test_youtubeComments.py](tests/ingestion/test_youtubeComments.py) — `getYoutubeComments` test patches `list_comment_threads` to return `[{"Likes": 12, "Text": "great vid"}, ...]`. Asserts enrichment with `Id`/`Title`. No `topLevelComment` in this file after the change.
- [tests/ingestion/test_appStoreReviews.py](tests/ingestion/test_appStoreReviews.py) — `getAppReviews` test patches `list_reviews` to return `[{"rating": ..., "title": ..., ...}, ...]`. The `_entry` / `_rss_page` helpers (lines 23-33) are deleted. Pagination break is asserted via `list_reviews` returning `[]`.

Out of scope: testing the live SDK / HTTP call.

## Sequencing (two PRs)

### PR 1 — YouTube
- Move dict-walk for `list_comment_threads` and `list_most_popular` (including `_pick_largest_thumbnail`) into [app/clients/youtube.py](app/clients/youtube.py).
- Update [app/ingestion/youtubeComments.py](app/ingestion/youtubeComments.py) callers.
- Move thumbnail-priority + `topLevelComment` fixtures from [tests/ingestion/test_youtubeComments.py](tests/ingestion/test_youtubeComments.py) into [tests/clients/test_youtube_client.py](tests/clients/test_youtube_client.py).
- Rewrite the ingestion tests against domain rows.

### PR 2 — App Store
- Add `list_reviews` to [app/clients/appstore.py](app/clients/appstore.py) (decide whether `fetch_reviews_page` stays as a private helper or is deleted).
- Update [app/ingestion/appStoreReviews.py](app/ingestion/appStoreReviews.py) to paginate over `list_reviews`; stop on `[]`.
- Move `im:rating`/`im:voteCount` fixtures from [tests/ingestion/test_appStoreReviews.py](tests/ingestion/test_appStoreReviews.py) into [tests/clients/test_appstore_client.py](tests/clients/test_appstore_client.py).
- Rewrite the ingestion tests against domain rows.

PRs are independent — either can ship first. Splitting by vendor keeps each diff scoped to one client + its ingestion module + its two test files.

## Acceptance

- `grep -rn "topLevelComment" app/` returns no matches.
- `grep -rn "im:rating\|im:voteCount\|im:image" app/` returns no matches outside [app/clients/](app/clients/).
- `grep -rn "topLevelComment\|im:rating\|im:voteCount" tests/ingestion/` returns no matches.
- [app/ingestion/youtubeComments.py](app/ingestion/youtubeComments.py) does not reference `snippet`, `thumbnails`, or `topLevelComment`.
- [app/ingestion/appStoreReviews.py](app/ingestion/appStoreReviews.py) does not reference `feed`, `entry`, or any `im:*` key.
- All existing ingestion behaviors preserved: pagination break condition, thumbnail priority, comment ordering.
- Tests green.

## Deferred

- Typing the client return rows as Pydantic models (`YoutubeCommentRow`, `AppStoreReviewRow`). The dict→model upgrade is a separate seam-tightening pass; this spec only relocates the parsing.
- Retry/backoff inside the clients (separate concern; lives in `clients/` whenever it's added).
- Replacing iTunes RSS — tracked in [2026-05-05-itunes-rss-top-apps-deprecation.md](../decisions/2026-05-05-itunes-rss-top-apps-deprecation.md). This spec makes that future swap easier (one file, not two).
