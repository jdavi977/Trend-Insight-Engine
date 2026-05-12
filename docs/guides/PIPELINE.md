# Automated Weekly Pipeline

The weekly pipeline fetches trending YouTube videos and top App Store apps, runs them through the full analysis pipeline, and stores structured insights in Supabase. These results power the Home and Insights pages.

---

## Schedule

Both pipelines run via GitHub Actions every Sunday morning (UTC):

| Pipeline | Workflow file | Schedule |
|----------|--------------|---------|
| YouTube | `.github/workflows/weekly-youtube.yml` | Sun, Wed, Fri at 08:00 UTC |
| App Store | `.github/workflows/weekly-appstore.yml` | Sun, Wed, Fri at 08:30 UTC |

Environment secrets (`YOUTUBE_API`, `OPENAI_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `RAG_READ_ENABLED`, `RAG_WRITE_ENABLED`) must be configured in the repository settings under **Settings → Secrets and variables → Actions**.

---

## What Gets Processed

**YouTube** — 3 categories, 5 videos each (15 total per run):

| Category | ID |
|----------|----|
| Games | 20 |
| Science & Tech | 28 |
| How-to & Style | 26 |

**App Store** — 3 genres, 5 apps each (15 total per run):

| Genre | ID |
|-------|----|
| Games | 6014 |
| Social Networking | 6005 |
| Utilities | 6002 |

---

## Pipeline Flow (Per Item)

Both YouTube and App Store jobs share the same core pipeline, implemented in `app/jobs/automaticPipeline.py`:

```
For each video / app:

  1. check_existing()
     └─ Already in database for this week? → bump date, skip to next item
        New item? → continue

  2. ingest()
     └─ YouTube: fetch up to 100 comments (relevance order)
        App Store: paginate iTunes RSS (up to 10 pages)

  3. clean()
     └─ Engagement filter → normalize → strip emojis → keyword filter → dedup
        (same preprocessing as manual analysis)

  4. system_prompt()   [RAG read: only if RAG_READ_ENABLED=true]
     └─ retrieve_similar(item["Title"]) — embed title, query pgvector
        returns top-k past insights → injected into genre system prompt

  5. extract_insights()
     └─ gpt-4o with genre-specific system prompt + RAG context
        Returns validated list of ProblemItems (severity, frequency, type)

  6. post_extract()   [only if RAG_WRITE_ENABLED=true]
     └─ embed_and_store() — embed each problem, upsert to insights table

  7. persist_row()
     └─ Upsert to automatic_table (YouTube) or automatic_apple_table (App Store)
        with title, thumbnail, category/genre, problems JSON
```

The `SourceAdapter` dataclass in `automaticPipeline.py` is what makes steps 1–6 source-agnostic. Each job (YouTube or App Store) constructs an adapter that binds source-specific implementations of `ingest`, `check_existing`, `build_row`, etc.

---

## Running Manually

To populate the database outside of the scheduled run:

```bash
# Activate virtual environment first
source venv/bin/activate

# YouTube (all 3 categories)
python app/jobs/automaticYoutube.py

# App Store (all 3 genres)
python app/jobs/automaticAppStore.py
```

Both scripts require a fully configured `.env` file. Set `RAG_WRITE_ENABLED=true` if you also want embeddings written to the `insights` table.

---

## Cron Setup (Self-Hosted Alternative)

If you're not using GitHub Actions, use your system crontab or a task scheduler.

```bash
crontab -e
```

```cron
# Weekly pipeline — every Sunday
0 8  * * 0  cd /path/to/Trend-Insight-Engine && source venv/bin/activate && python app/jobs/automaticYoutube.py  >> /var/log/tie-youtube.log 2>&1
30 8 * * 0  cd /path/to/Trend-Insight-Engine && source venv/bin/activate && python app/jobs/automaticAppStore.py >> /var/log/tie-appstore.log 2>&1
```

Ensure the `.env` file is present and the virtual environment is activated in the cron context. Cron jobs do not inherit your shell environment.

---

## Backfill Script

Use the backfill script to retroactively embed all historical problems that were stored before `RAG_WRITE_ENABLED` was turned on:

```bash
RAG_WRITE_ENABLED=true python -m ops.scripts.backfill_embeddings
```

- Reads all rows from both `automatic_table` and `automatic_apple_table`
- Embeds each problem and upserts into the `insights` table
- **Idempotent** — safe to re-run; deterministic IDs (SHA256 of source URL + problem text) prevent duplicates

Run this once after deploying RAG to catch up on historical data, or again if you add new rows via manual pipeline runs.

---

## Storage Schema

**`automatic_table`** (YouTube):

| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT (PK) | Video ID |
| `date` | TEXT | ISO date when last processed |
| `category` | INTEGER | YouTube category ID |
| `title` | TEXT | Video title |
| `thumbnail` | JSON | `{url, width, height}` |
| `problems` | JSON | Array of `{problem, type, total_likes, severity, frequency}` |

**`automatic_apple_table`** (App Store):

| Column | Type | Description |
|--------|------|-------------|
| `app_id` | INTEGER (PK) | App Store app ID |
| `app_title` | TEXT | App name |
| `genre_id` | INTEGER | Apple genre ID |
| `country` | TEXT | Country code (`us`) |
| `date` | TEXT | ISO date when last processed |
| `thumbnail` | TEXT | App icon URL |
| `problems` | JSON | Array of `{problem, type, average_rating, severity, frequency, example_reviews}` |

Both tables are queried by the frontend via `GET /get/homePage` and `GET /get/homePageAppStore`, which filter by the most recent Sunday's date using `getSundayDate()`.

---

## Troubleshooting

**Home page shows no data** — The pipeline hasn't run yet, or it ran but no problems were extracted. Run `automaticYoutube.py` manually and check the console for errors.

**Duplicate entries** — Not possible; both `automatic_table` and `automatic_apple_table` use the video/app ID as a primary key. Re-runs update the existing row.

**RAG embeddings missing** — `RAG_WRITE_ENABLED` was `false` during the pipeline run. Run the backfill script.

**Cron not running** — Confirm the working directory, virtual environment path, and `.env` location are all correct in the cron command. Test by running the command directly in your shell first.
