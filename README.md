# Trend Insight Engine

**A full-stack application that transforms user-generated content into structured product insights using LLM-powered analysis. Extract recurring problems, feature requests, and unmet needs from YouTube comments and App Store reviews to validate niches and inform product decisions.**

## Why This Matters

This project demonstrates end-to-end product engineering: from API integration and data pipelines to structured LLM outputs and frontend-backend communication. It solves a real problem—helping creators and indie developers validate product ideas by analyzing what users actually say—while showcasing technical depth in data processing, error handling, and system design.

**Product Thinking:** The application addresses a genuine need in the product development workflow: moving from intuition-based decisions to data-driven insights. By aggregating and analyzing user feedback at scale, it helps identify patterns that would be impossible to spot manually.

**Technical Depth:** The implementation covers multiple engineering concerns: external API integration (YouTube Data API, iTunes RSS), text preprocessing pipelines, defensive error handling for unreliable data sources, structured LLM prompting for consistent outputs, and a clean separation of concerns that enables extensibility.

---

## Key Features

- **YouTube Comment Ingestion**: Fetches comments via YouTube Data API v3, sorted by relevance and time
- **App Store Review Ingestion**: Retrieves reviews from iTunes RSS feed, sorted by most recent and most helpful
- **Text Cleaning Pipeline**: Removes emojis, URLs, duplicates, and filters by engagement metrics (likes/votes)
- **LLM-Powered Extraction**: Uses OpenAI API to identify and cluster recurring problems, feature requests, and unmet needs
- **Structured JSON Output**: Returns normalized insights with metrics (severity, frequency, engagement scores)
- **Simple React UI**: Clean interface for submitting URLs and viewing extracted insights

---

## Tech Stack

**Frontend:**
- React 19
- Vite
- Fetch API for backend communication

**Backend:**
- FastAPI (Python)
- Pydantic for request/response validation
- Uvicorn ASGI server

**APIs & Services:**
- YouTube Data API v3 (Google)
- iTunes RSS Feed (Apple App Store)
- OpenAI API (GPT models)

**LLM:**
- OpenAI GPT for structured extraction and clustering

---

## How It Works

```
User submits URL
    ↓
Backend validates URL format
    ↓
Ingestion Layer:
  - YouTube: Fetch comments (relevance + time sorted)
  - App Store: Fetch reviews (most recent + most helpful)
    ↓
Preprocessing:
  - Filter by engagement (likes ≥ 50, votes > 5)
  - Remove emojis, URLs, duplicates
  - Keyword filtering for relevance
    ↓
LLM Analysis:
  - Extract recurring themes
  - Cluster similar feedback
  - Calculate metrics (severity, frequency, engagement)
    ↓
Structured JSON Response:
  - Problem descriptions
  - Type classification
  - Metrics and examples
```

---

## API Endpoints

### `POST /analyze/youtube`

Analyzes YouTube video comments to extract insights.

**Request:**
```json
{
  "youtubeURL": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response:**
```json
{
  "problems": [
    {
      "problem": "Users want dark mode for better nighttime viewing",
      "type": "feature_request",
      "total_likes": 1247,
      "severity": 3,
      "frequency": 4
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request`: Invalid YouTube URL format

---

### `POST /analyze/appStore`

Analyzes App Store reviews to extract insights.

**Request:**
```json
{
  "appStoreURL": "https://apps.apple.com/us/app/example-app/id123456789"
}
```

**Response:**
```json
{
  "problems": [
    {
      "problem": "App crashes when syncing data",
      "type": "complaint",
      "average_rating": 2.3,
      "frequency": 4,
      "severity": 5,
      "example_reviews": [
        "Crashes every time I try to sync. Very frustrating.",
        "Lost all my data after the last update."
      ]
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request`: Invalid App Store URL format

---

## Getting Started (Local)

### Prerequisites

- Python 3.11+ (recommended)
- Node.js 18+ and npm
- API keys: YouTube Data API v3, OpenAI API

### Backend Setup

```bash
cd backend/app
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install fastapi uvicorn[standard] pydantic python-dotenv google-api-python-client openai requests
```

Create `.env` file in `backend/app/`:
```bash
YOUTUBE_API=your_youtube_api_key_here
OPENAI_KEY=your_openai_api_key_here
```

Run the server:
```bash
uvicorn main:app --reload --port 8000
```

API available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend typically runs on `http://localhost:5173` (Vite default)

**CORS Note:** Backend is configured to allow requests from `http://localhost:5173`. If your frontend runs on a different port, update CORS settings in `backend/app/main.py`.

---

## Environment Variables

Create a `.env` file in `backend/app/`:

```bash
# Required: YouTube Data API v3 key
YOUTUBE_API_KEY=your_youtube_api_key_here

# Required: OpenAI API key (or use GEMINI_API_KEY for alternative provider)
OPENAI_API_KEY=your_openai_api_key_here
# GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Number of App Store review pages to fetch (default: 10)
# Configure in backend/app/config/settings.py
```

---

## Output Format

The API returns structured JSON with extracted problems. Each problem includes:

- **problem**: Short description of the issue or request
- **type**: Classification (`feature_request`, `complaint`, `usability`, `performance`, `pricing`, `other`)
- **severity**: 1-5 scale (5 = most painful/impactful)
- **frequency**: 1-5 scale (5 = very common theme)
- **total_likes** (YouTube): Aggregated likes for comments in this cluster
- **average_rating** (App Store): Average star rating for reviews in this cluster
- **example_reviews** (App Store): 1-2 example review excerpts

**Example Response:**
```json
{
  "problems": [
    {
      "problem": "Users want offline mode for travel",
      "type": "feature_request",
      "average_rating": 4.1,
      "frequency": 5,
      "severity": 4,
      "example_reviews": [
        "Great app but needs offline support for travel",
        "Please add offline mode! I travel a lot."
      ]
    }
  ],
  "source": {
    "platform": "app_store",
    "url": "https://apps.apple.com/..."
  }
}
```

---

## Engineering Notes

**Pagination and Graceful Degradation:** The App Store RSS feed pagination stops gracefully when `feed.entry` is missing (no more pages or invalid app ID). The pipeline handles this without crashing, logging the stopping point and returning whatever data was successfully collected.

**Defensive Parsing and Error Handling:** All external API responses are parsed with defensive checks. Missing fields, malformed JSON, and network timeouts are handled at each layer. URL validation occurs before any API calls to fail fast on invalid input.

**Rate Limits and Timeouts:** YouTube API quota limits are respected (10,000 units/day default). App Store RSS requests include 10-second timeouts to prevent hanging. Future improvements would include exponential backoff and request queuing.

**Separation of Concerns:** The codebase is organized into distinct layers: `ingestion/` for API clients, `preprocessing/` for data cleaning, `llm/` for analysis, and `scripts/` for pipeline orchestration. This modularity makes it straightforward to add new data sources or swap LLM providers.

**Testability and Extensibility:** Each module has clear interfaces and minimal dependencies. The pipeline functions accept URLs and return structured data, making them easy to unit test. Adding a new source (e.g., Reddit) requires implementing the ingestion and cleaning modules following the existing patterns.

**Structured LLM Outputs:** Prompts are carefully designed to enforce consistent JSON schema. The system prompts include explicit formatting rules and examples to minimize parsing errors and ensure reliable structured outputs.

---

## Roadmap

- [ ] Add Reddit ingestion for subreddit analysis
- [ ] Improve clustering algorithm for better problem grouping
- [ ] Add caching layer to reduce API calls and improve performance
- [ ] Implement pagination for large datasets
- [ ] Enhanced UI with charts and visualizations
- [ ] Async job processing with background tasks
- [ ] Database storage for historical analysis
- [ ] Export insights to CSV/Excel format
- [ ] Add support for additional LLM providers (Gemini, Claude, etc.)
- [ ] Batch processing for multiple URLs
- [ ] API rate limiting and usage tracking

---

## License

MIT License - see [LICENSE](LICENSE) file for details.
