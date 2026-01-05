# Trend Insight Engine

A full-stack application that extracts structured product insights from user-generated content (YouTube comments and App Store reviews) using LLM-powered analysis. Transforms raw feedback into actionable insights by identifying recurring problems, feature requests, and unmet needs with severity and frequency metrics.

---

## Project Overview

Product teams and indie developers often struggle to identify patterns in user feedback scattered across multiple platforms. Manually analyzing hundreds of comments and reviews is time-consuming and error-prone. Trend Insight Engine automates this process by ingesting user feedback from YouTube videos and App Store listings, cleaning and filtering the data, then using LLMs to extract and cluster recurring themes into structured insights with engagement metrics.

---

## Key Features

- **Multi-Source Data Ingestion**: Fetches comments from YouTube Data API v3 (sorted by relevance and time) and reviews from iTunes RSS feeds (most recent and most helpful)
- **Engagement-Based Filtering**: Filters content by engagement metrics (YouTube comments with ≥50 likes, App Store reviews with >5 votes) to prioritize high-signal feedback
- **Text Preprocessing Pipeline**: Removes emojis, filters by domain-specific keywords, eliminates duplicates, and normalizes text for analysis
- **LLM-Powered Insight Extraction**: Uses OpenAI API with structured prompts to identify, cluster, and categorize problems (feature requests, complaints, usability issues, performance, pricing)
- **Structured JSON Output**: Returns normalized insights with severity (1-5), frequency (1-5), engagement scores (total likes, average ratings), and example excerpts
- **React Frontend**: Clean, responsive UI for submitting URLs and viewing extracted insights with problem categorization and metrics
- **RESTful API**: FastAPI backend with Pydantic request validation, CORS middleware, and URL format validation

---

## Architecture

The system follows a modular pipeline architecture with clear separation of concerns:

**Frontend (React + Vite)**: Single-page application with separate views for YouTube and App Store analysis. Components handle URL input, API communication via Fetch, and display of structured insights.

**Backend (FastAPI)**: REST API with three main endpoints (`/analyze/youtube`, `/analyze/appStore`, `/data/send`). Routes delegate to pipeline scripts that orchestrate the data flow.

**Data Pipeline**: 
1. **Ingestion Layer** (`ingestion/`): YouTube Data API v3 client and iTunes RSS scraper fetch raw comments/reviews
2. **Preprocessing Layer** (`preprocessing/`): Filters by engagement, removes emojis/duplicates, applies keyword filtering
3. **LLM Layer** (`llm/`): Sends cleaned data to OpenAI API with structured prompts for insight extraction
4. **Output**: Returns JSON string with clustered problems, types, and metrics

**Storage**: Local file system for manual data saves (optional). Supabase client available for future database integration.

---

## Tech Stack

### Backend
- **FastAPI** (Python) - REST API framework with async support
- **Pydantic** - Request/response validation and data modeling
- **Uvicorn** - ASGI server for production deployment
- **python-dotenv** - Environment variable management
- **google-api-python-client** - YouTube Data API v3 integration
- **openai** - OpenAI API client for LLM inference
- **requests** - HTTP client for iTunes RSS feed scraping

### Frontend
- **React 19** - UI library with hooks-based state management
- **Vite** - Build tool and dev server
- **Fetch API** - HTTP client for backend communication

### Data & APIs
- **YouTube Data API v3** - Comment retrieval (relevance and time-sorted)
- **iTunes RSS Feed** - App Store review scraping (paginated)
- **OpenAI API** - LLM for structured insight extraction

### Infrastructure
- **Local File System** - JSON file storage for manual saves
- **Supabase** (optional) - Database client available for future persistence

---

## Implementation Highlights

- **Modular Pipeline Architecture**: Clean separation between ingestion, preprocessing, and LLM layers enables easy extension to new data sources (e.g., Reddit, Twitter)
- **Domain-Specific Keyword Filtering**: Configurable keyword lists (YouTube, App Store, game-specific) filter noise and focus on relevant feedback
- **Structured LLM Prompting**: Carefully designed system prompts enforce consistent JSON schema output with explicit formatting rules and examples
- **Engagement-Based Signal Quality**: Filters low-engagement content (likes/votes thresholds) to prioritize high-signal feedback before LLM analysis
- **URL Validation**: Regex-based validation for YouTube (supports watch, shorts, youtu.be) and App Store URLs before API calls to fail fast
- **Defensive Data Parsing**: Handles missing fields and malformed responses from external APIs with graceful degradation

---

## Setup & Running Locally

### Prerequisites
- Python 3.11+ 
- Node.js 18+ and npm
- API keys:
  - YouTube Data API v3 key ([Get one here](https://console.cloud.google.com/apis/credentials))
  - OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend/app
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install fastapi uvicorn[standard] pydantic python-dotenv google-api-python-client openai requests supabase
```

4. Create `.env` file in `backend/app/`:
```bash
YOUTUBE_API=your_youtube_api_key_here
OPENAI_KEY=your_openai_api_key_here
LOG_LEVEL=INFO  # Optional: DEBUG, INFO, WARNING, ERROR
```

5. Run the server:
```bash
uvicorn main:app --reload --port 8000
```

API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run development server:
```bash
npm run dev
```

Frontend will typically run on `http://localhost:5173` (Vite default)

**Note**: Backend CORS is configured for `http://localhost:5173`. If your frontend runs on a different port, update `allow_origins` in `backend/app/main.py`.

### Testing the Application

1. Open `http://localhost:5173` in your browser
2. Navigate to YouTube or App Store tab
3. Paste a valid URL:
   - YouTube: `https://www.youtube.com/watch?v=VIDEO_ID` or `https://youtu.be/VIDEO_ID`
   - App Store: `https://apps.apple.com/us/app/app-name/id123456789`
4. Click "Analyze" and wait for insights to load
5. View extracted problems with severity, frequency, and engagement metrics

---

## License

MIT License - see [LICENSE](LICENSE) file for details.
