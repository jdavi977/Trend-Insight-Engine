# Data Sources

## YouTube

### Weekly categories

The automated pipeline covers three YouTube categories:

| Category | YouTube category ID |
|----------|-------------------|
| Games | 20 |
| Science & Tech | 28 |
| How-to & Style | 26 |

For each category, the pipeline fetches the **top 5 trending videos** and analyzes up to **100 comments** per video (sorted by relevance).

### Manual analysis

Any public YouTube video URL works — category is detected automatically from the video's metadata. The manual path fetches up to **100 comments** sorted by relevance.

### Quota limits

YouTube Data API v3 has a daily quota of **10,000 units** (shared across all requests on your API key). Each video's comment fetch costs roughly 1–3 units. The weekly pipeline for 3 categories × 5 videos = ~15 comment fetches, well within quota. Heavy manual usage on the same key could approach the limit.

---

## App Store

### Weekly categories

The automated pipeline covers three App Store genres (US store):

| Genre | iTunes genre ID |
|-------|----------------|
| Games | 6014 |
| Social Networking | 6005 |
| Utilities | 6002 |

For each genre, the pipeline fetches the **top 5 apps** from the iTunes RSS feed and scrapes **10 pages of reviews** (most recent) per app.

### Manual analysis

Any US App Store URL works. The manual path fetches **2 pages of reviews** (most recent) to keep response times fast.

> Only the US App Store (`apps.apple.com/us/...`) is supported. The `id` numeric suffix in the URL is used to identify the app.

### Quota limits

The iTunes RSS feed and App Store review scraper have no enforced API key quota, but Apple rate-limits aggressive requests. The pipeline runs weekly and stays well within normal usage patterns.

---

## Refresh cadence

The Home and Insights pages show data from the most recent pipeline run. Pipeline scripts are:

```
app/jobs/automaticYoutube.py   # YouTube pipeline
app/jobs/automaticAppStore.py  # App Store pipeline
```

Run these manually or schedule them weekly via cron. The pipeline skips any video or app it has already processed this week (deduplication is keyed on video ID / app ID + date).

---

## RAG / historical context

After each pipeline run (and each manual analysis, if `RAG_WRITE_ENABLED=true`), insights are embedded and stored in Supabase with `pgvector`. Future analyses retrieve similar past insights with a similarity threshold of **0.35**. Up to **5 prior results** are surfaced as retrieved context on each result page.
