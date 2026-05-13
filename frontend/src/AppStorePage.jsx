import { useState } from "react";
import RecurrenceTag from "./components/RecurrenceTag";
import RetrievedContextAccordion from "./components/RetrievedContextAccordion";
import "./AppStorePage.css";

const APP_STORE_REGEX =
  /^https?:\/\/(www\.)?apps\.apple\.com\/[a-z]{2}\/app\/[A-Za-z0-9\-]+\/id\d+$/;

const EXAMPLES = [
  { label: "Notion",   url: "https://apps.apple.com/us/app/notion-notes-docs-ai/id1232780281" },
  { label: "Linear",   url: "https://apps.apple.com/us/app/linear-plan-build-software/id1383692638" },
  { label: "Figma",    url: "https://apps.apple.com/us/app/figma/id1152747299" },
  { label: "Things 3", url: "https://apps.apple.com/us/app/things-3/id904237743" },
];

const TYPE_TAG = {
  complaint:       "tag-red",
  bug:             "tag-red",
  issue:           "tag-red",
  problem:         "tag-red",
  performance:     "tag-red",
  praise:          "tag-green",
  positive:        "tag-green",
  strength:        "tag-green",
  pricing:         "tag-amber",
  usability:       "tag-amber",
  ux:              "tag-amber",
  "feature request":"tag-blue",
  feature:         "tag-blue",
};

function tagClass(type = "") {
  return TYPE_TAG[type.toLowerCase()] ?? "tag-blue";
}

function problemSimilarInsights(p) {
  const raw = p?.similar_insights;
  return Array.isArray(raw) ? raw : [];
}

function sevClass(sev) {
  if (sev >= 4) return "high";
  if (sev >= 3) return "med";
  return "low";
}

function SevBar({ severity }) {
  const cls = sevClass(severity);
  return (
    <span className={`sev-bar ${cls}`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`seg${i <= severity ? " on" : ""}`} />
      ))}
    </span>
  );
}

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l3 7 7 .5-5.5 4.5 2 7L12 17l-6.5 4 2-7L2 9.5 9 9z" />
    </svg>
  );
}

function InsightCard({ problem }) {
  const tc = tagClass(problem.type);
  const quote = problem.example_reviews?.[0] ?? "";
  const quote2 = problem.example_reviews?.[1] ?? "";
  const similar = problemSimilarInsights(problem);

  return (
    <article className="insight-card">
      <div className="insight-head">
        <span className={`tag ${tc}`}>
          <span className="dot" />
          {problem.type}
        </span>
        <RecurrenceTag recurrence={problem.recurrence} />
        {problem.average_rating != null && (
          <span className="review-avg">
            <StarIcon />
            {Number(problem.average_rating).toFixed(1)} avg
          </span>
        )}
      </div>

      <h3 className="insight-title">{problem.problem}</h3>

      {quote && (
        <blockquote className="insight-quote">
          {quote}
          {quote2 && <cite>{quote2}</cite>}
        </blockquote>
      )}

      <RetrievedContextAccordion items={similar} className="retrieved-accordion--nested" />

      <div className="insight-foot">
        <span>
          <b>Severity {problem.severity}/5</b> · Freq {problem.frequency}/5
        </span>
        <span className="right">
          <SevBar severity={problem.severity} />
          <b>{problem.severity}/5</b>
        </span>
      </div>
    </article>
  );
}

function AppStorePage() {
  const [url, setUrl]           = useState("");
  const [loading, setLoading]   = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [error, setError]       = useState("");
  const [activeType, setActiveType] = useState("All");
  const [view, setView]         = useState("cards");
  const [analyzedUrl, setAnalyzedUrl] = useState("");

  const analyze = async () => {
    setError("");
    setAnalytics(null);
    setLoading(true);
    setActiveType("All");
    setView("cards");
    setAnalyzedUrl(url);

    if (!APP_STORE_REGEX.test(url)) {
      setError("Invalid App Store link. Expected format: https://apps.apple.com/us/app/app-name/id123");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE}/analyze/appStore`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ appStoreURL: url }),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data = await response.json();
      setAnalytics(typeof data === "string" ? JSON.parse(data) : data);
    } catch (err) {
      setError("Failed to analyze. Please try again.");
      console.error("Error", err);
    } finally {
      setLoading(false);
    }
  };

  const problems = analytics?.problems ?? analytics?.["problems:"] ?? [];
  const thumbnail = analytics?.thumbnail ?? null;

  const types = ["All", ...new Set(problems.map((p) => p.type).filter(Boolean))];
  const visible = activeType === "All"
    ? problems
    : problems.filter((p) => p.type === activeType);

  return (
    <div className="appstore-page">
      {/* Page header */}
      <header style={{ marginBottom: "var(--s-6)" }}>
        <h1 style={{ margin: "0 0 6px", fontSize: 26, fontWeight: 500, color: "var(--ink-1)", letterSpacing: "-0.01em" }}>
          App store analysis
        </h1>
        <p style={{ margin: 0, color: "var(--ink-2)", fontSize: 14 }}>
          Paste an App Store URL. The agent pulls reviews, clusters them into themes, and surfaces what users actually love and hate.
        </p>
      </header>

      {/* URL input */}
      <div className="url-row">
        <label className="url-field">
          <svg className="lead" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="7" /><path d="m16 16 5 5" />
          </svg>
          <input
            type="url"
            value={url}
            placeholder="Paste an App Store URL or search by app name"
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && analyze()}
          />
        </label>
        <button className="btn-analyze" onClick={analyze} disabled={loading}>
          {loading ? "Analyzing…" : "Analyze"}
        </button>
      </div>

      {/* Example chips */}
      <div className="examples-row">
        <span className="lab">Try:</span>
        {EXAMPLES.map((ex) => (
          <button key={ex.label} className="chip" onClick={() => setUrl(ex.url)}>
            {ex.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && <div className="as-error">{error}</div>}

      {/* Loading */}
      {loading && (
        <div className="as-loading">
          <div className="spinner" />
          Pulling and analyzing reviews…
        </div>
      )}

      {/* Results */}
      {!loading && analytics && (
        <>
          {/* App header card */}
          <div className="as-app-card">
            <div className="as-app-card-left">
              {thumbnail && (
                <img src={thumbnail} alt={analytics.title ?? "App icon"} className="as-app-icon" />
              )}
              <div className="as-app-info">
                {analytics.title && <h2 className="as-app-name">{analytics.title}</h2>}
                {analytics.seller && <p className="as-app-seller">by {analytics.seller}</p>}
                <div className="as-app-tags">
                  {analytics.genre && <span className="as-badge">{analytics.genre}</span>}
                  {analytics.age_rating && <span className="as-badge">{analytics.age_rating}</span>}
                </div>
              </div>
            </div>
            {analyzedUrl && (
              <a href={analyzedUrl} target="_blank" rel="noreferrer" className="as-open-btn">
                Open in store ↗
              </a>
            )}
          </div>

          {/* Stats row */}
          {(analytics.average_rating != null || analytics.rating_count != null) && (
            <div className="as-stats-row">
              {analytics.average_rating != null && (
                <div className="as-stat">
                  <span className="as-stat-value">
                    {Number(analytics.average_rating).toFixed(1)}
                    <StarIcon />
                  </span>
                  <span className="as-stat-label">Average rating</span>
                </div>
              )}
              {analytics.rating_count != null && (
                <div className="as-stat">
                  <span className="as-stat-value">{analytics.rating_count.toLocaleString()}</span>
                  <span className="as-stat-label">Total ratings</span>
                </div>
              )}
            </div>
          )}

          {/* Section heading */}
          <div className="section-h">
            <div>
              <h2>Extracted themes</h2>
              <div className="sub">
                {problems.length} insight{problems.length !== 1 ? "s" : ""} surfaced
              </div>
            </div>
            <div className="as-view-toggle">
              {["cards", "json"].map((v) => (
                <button
                  key={v}
                  className={view === v ? "on" : ""}
                  onClick={() => setView(v)}
                >
                  {v.charAt(0).toUpperCase() + v.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Cards view */}
          {view === "cards" && (
            <>
              {types.length > 1 && (
                <div className="theme-chips">
                  {types.map((t) => {
                    const cnt = t === "All" ? problems.length : problems.filter((p) => p.type === t).length;
                    return (
                      <button
                        key={t}
                        className={`filter-chip${activeType === t ? " active" : ""}`}
                        onClick={() => setActiveType(t)}
                      >
                        {t} <span className="count">{cnt}</span>
                      </button>
                    );
                  })}
                </div>
              )}
              {visible.length > 0 ? (
                <div className="results-grid">
                  {visible.map((problem, i) => (
                    <InsightCard key={i} problem={problem} />
                  ))}
                </div>
              ) : (
                <div className="as-empty">No insights found for this filter.</div>
              )}
            </>
          )}

          {/* JSON view */}
          {view === "json" && (
            <div className="as-json-wrap">
              <pre>{JSON.stringify(problems, null, 2)}</pre>
            </div>
          )}
        </>
      )}

      {!loading && !analytics && !error && (
        <div className="as-empty">Enter an App Store URL above to get started.</div>
      )}
    </div>
  );
}

export default AppStorePage;
