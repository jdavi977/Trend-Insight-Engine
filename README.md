# Trend Insight Engine

A full-stack application that extracts structured product insights from user-generated content (YouTube comments and App Store reviews) using LLM-powered analysis. Transforms raw feedback into actionable insights by identifying recurring problems, feature requests, and unmet needs with severity and frequency metrics.

---

## Project Overview

Product teams and indie developers often struggle to identify patterns in user feedback scattered across multiple platforms. Manually analyzing hundreds of comments and reviews is time-consuming and error-prone. Trend Insight Engine automates this process by ingesting user feedback from YouTube videos and App Store listings, cleaning and filtering the data, then using LLMs to extract and cluster recurring themes into structured insights with engagement metrics.

Weekly trending insights are automatically generated from YouTube's most popular videos across three categories (Games, Science & Tech, How-to & Style), stored in Supabase, and surfaced on the Home and Insights pages.

---

## Key Features

- **Multi-Source Data Ingestion**: Fetches comments from YouTube Data API v3 (sorted by relevance) and reviews from iTunes RSS feeds (most recent and most helpful)
- **Automated Weekly YouTube Pipeline**: Fetches the most popular YouTube videos across three categories and runs the full analysis pipeline, storing results in Supabase
- **Engagement-Based Filtering**: Filters content by engagement metrics (YouTube comments with ≥50 likes, App Store reviews with >5 votes) to prioritize high-signal feedback
- **Text Preprocessing Pipeline**: Removes emojis, filters by domain-specific keywords, eliminates duplicates, and normalizes text for analysis
- **LLM-Powered Insight Extraction**: Uses OpenAI API with structured prompts to identify, cluster, and categorize problems (feature requests, complaints, usability issues, performance, pricing)
- **Structured JSON Output**: Returns normalized insights with severity (1–5), frequency (1–5), total likes, and problem type
- **React Frontend**: Four-page SPA — Home (weekly top videos), Insights (all weekly videos with category filtering), YouTube (manual analysis), and App Store (manual analysis)
- **RESTful API**: FastAPI backend with Pydantic request validation, CORS middleware, and URL format validation
- **Supabase Integration**: Persists automated weekly insights and serves them to the frontend via the `/get/homePage` endpoint

---

## Architecture

The system follows a modular pipeline architecture with clear separation of concerns:

**Frontend (React + Vite)**: Single-page application with four views — Home, Insights, YouTube, and App Store. Components handle URL input, API communication via Fetch, and display of structured insights.

**Backend (FastAPI)**: REST API with four main endpoints (`/analyze/youtube`, `/analyze/appStore`, `/get/homePage`, `/data/send`). Routes delegate to pipeline scripts that orchestrate the data flow.

**Data Pipeline**:
1. **Ingestion Layer** (`ingestion/`): YouTube Data API v3 client and iTunes RSS scraper fetch raw comments/reviews; also fetches most popular videos by category ID
2. **Preprocessing Layer** (`preprocessing/`): Filters by engagement, removes emojis/duplicates, applies keyword filtering, validates URLs
3. **LLM Layer** (`llm/`): Sends cleaned data to OpenAI API with structured prompts for insight extraction; validates LLM output schema
4. **Output**: Returns JSON with clustered problems, types, and metrics

**Config Layer** (`config/`): Centralized keyword lists, LLM system/output prompts, regex patterns, API settings, and category IDs.

**Utilities Layer** (`utilities/`): Text cleaning helpers, YouTube API response helpers, and date utilities for weekly bucketing.

**Schemas Layer** (`schemas/`): Pydantic models for LLM insight output validation.

**Storage**: Supabase (`automatic_table`) stores automated weekly insights keyed by YouTube video ID, date, and category. A local file-system save is also available via `/data/send`.

---

## Tech Stack

### Backend
- **FastAPI** (Python) — REST API framework
- **Pydantic** — Request/response validation and data modeling
- **Uvicorn** — ASGI server
- **python-dotenv** — Environment variable management
- **google-api-python-client** — YouTube Data API v3 integration
- **openai** — OpenAI API client for LLM inference
- **requests** — HTTP client for iTunes RSS feed scraping
- **supabase** — Supabase Python client for database reads/writes

### Frontend
- **React 19** — UI library with hooks-based state management
- **Vite** — Build tool and dev server
- **Fetch API** — HTTP client for backend communication

### Data & APIs
- **YouTube Data API v3** — Comment retrieval and most-popular video discovery
- **iTunes RSS Feed** — App Store review scraping (paginated)
- **OpenAI API** — LLM for structured insight extraction

### Storage
- **Supabase** — Primary persistence for automated weekly YouTube insights

---

## Setup & Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- API keys:
  - YouTube Data API v3 key ([Get one here](https://console.cloud.google.com/apis/credentials))
  - OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
  - Supabase project URL and service role key ([Get one here](https://supabase.com))

### Backend Setup

1. From the project root, create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install fastapi "uvicorn[standard]" pydantic python-dotenv google-api-python-client openai requests supabase
```

3. Create a `.env` file in the project root:
```bash
YOUTUBE_API=your_youtube_api_key_here
OPENAI_KEY=your_openai_api_key_here
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
LOG_LEVEL=INFO  # Optional: DEBUG, INFO, WARNING, ERROR
```

4. Run the server from the project root:
```bash
uvicorn app.main:app --reload --port 8000
```

API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

Frontend will typically run on `http://localhost:5173` (Vite default).

**Note**: Backend CORS is configured for `http://localhost:5173`. If your frontend runs on a different port, update `allow_origins` in `app/main.py`.

### Testing the Application

**Manual analysis (YouTube or App Store):**
1. Open `http://localhost:5173` in your browser
2. Navigate to the YouTube or App Store tab
3. Paste a valid URL:
   - YouTube: `https://www.youtube.com/watch?v=VIDEO_ID` or `https://youtu.be/VIDEO_ID`
   - App Store: `https://apps.apple.com/us/app/app-name/id123456789`
4. Click "Analyze" and wait for insights to load
5. View extracted problems with severity, frequency, and engagement metrics

**Weekly home page (requires Supabase + automated pipeline data):**
1. Run `app/jobs/automaticYoutube.py` to populate Supabase with weekly data
2. The Home and Insights pages will display this week's top videos and their extracted issues

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analyze/youtube` | Analyze a YouTube video by URL |
| `POST` | `/analyze/appStore` | Analyze an App Store listing by URL |
| `GET` | `/get/homePage` | Fetch this week's automated YouTube insights from Supabase |
| `POST` | `/data/send` | Save arbitrary JSON data to the local file system |

---

## License

MIT License - see [LICENSE](LICENSE) file for details.
