import { useState } from "react";
import RetrievedContextAccordion from "./components/RetrievedContextAccordion";
import "./YouTubePage.css";

const YOUTUBE_REGEX =
  /^https?:\/\/((www\.)?youtube\.com\/watch\?v=|youtu\.be\/)[A-Za-z0-9_-]{11}$/;

const EXAMPLES = [
  { label: "Cursor vs Copilot",      url: "https://www.youtube.com/watch?v=gqUQbjsYZLQ" },
  { label: "Linear app deep dive",   url: "https://www.youtube.com/watch?v=gqUQbjsYZLQ" },
  { label: "Notion for developers",  url: "https://www.youtube.com/watch?v=oTahLEX3NXo" },
];

const TYPE_META = {
  complaint:       { label: "Complaint",       cls: "red"   },
  feature_request: { label: "Feature request", cls: "blue"  },
  usability:       { label: "Usability",       cls: "amber" },
  strength:        { label: "Strength",        cls: "green" },
};

function SeverityBar({ value }) {
  const level = value >= 4 ? "high" : value >= 3 ? "med" : "low";
  return (
    <span className={`yt-sev-bar ${level}`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`yt-sev-seg${i <= value ? " on" : ""}`} />
      ))}
    </span>
  );
}

function TypeTag({ type }) {
  const meta = TYPE_META[type?.toLowerCase()] ?? { label: type, cls: "blue" };
  return (
    <span className={`yt-tag ${meta.cls}`}>
      <span className="yt-tag-dot" />
      {meta.label}
    </span>
  );
}

function InsightCard({ problem }) {
  return (
    <article className="yt-insight">
      <div className="yt-insight-head">
        <TypeTag type={problem.type} />
      </div>
      <p className="yt-insight-title">{problem.problem}</p>
      <div className="yt-insight-foot">
        <span>{problem.total_likes.toLocaleString()} likes · freq {problem.frequency}/5</span>
        <span className="yt-insight-foot-right">
          <SeverityBar value={problem.severity} />
          <b>{problem.severity}/5</b>
        </span>
      </div>
    </article>
  );
}

function InsightTable({ problems }) {
  return (
    <div className="yt-table-wrap">
      <table className="yt-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Problem</th>
            <th>Likes</th>
            <th>Severity</th>
            <th>Frequency</th>
          </tr>
        </thead>
        <tbody>
          {problems.map((p, i) => (
            <tr key={i}>
              <td><TypeTag type={p.type} /></td>
              <td>{p.problem}</td>
              <td>{p.total_likes.toLocaleString()}</td>
              <td>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <SeverityBar value={p.severity} />
                  <span style={{ fontSize: 12, color: "var(--ink-2)" }}>{p.severity}/5</span>
                </span>
              </td>
              <td>{p.frequency}/5</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function extractVideoId(url) {
  const m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  return m ? m[1] : null;
}

function fmt(n) {
  if (n == null) return null;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toLocaleString();
}

function fmtDate(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

function likeRatio(likes, views) {
  if (!likes || !views) return null;
  return `${((likes / views) * 100).toFixed(1)}%`;
}

function YouTubePage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [analytics, setAnalytics] = useState();
  const [error, setError] = useState("");
  const [view, setView] = useState("cards");
  const [videoId, setVideoId] = useState(null);

  const isValidUrl = YOUTUBE_REGEX.test(url);

  const analyze = async () => {
    setError("");
    setAnalytics(undefined);
    setVideoId(null);
    setLoading(true);

    if (!isValidUrl) {
      setError("Invalid YouTube link — paste a full youtube.com/watch?v= or youtu.be/ URL.");
      setLoading(false);
      return;
    }

    setVideoId(extractVideoId(url));

    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE}/analyze/youtube`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ youtubeURL: url }),
      });

      if (!response.ok) throw new Error(`Server error ${response.status}`);

      const data = await response.json();
      setAnalytics(typeof data === "string" ? JSON.parse(data) : data);
    } catch (err) {
      setError("Failed to analyze. Please try again.");
      console.error("Analyze error:", err);
    } finally {
      setLoading(false);
    }
  };

  const problems = analytics?.problems || analytics?.["problems:"] || [];
  const retrievedContext = analytics?.retrieved_context || [];

  return (
    <div className="yt-page">
      <h1 className="yt-page-title">Video analysis</h1>
      <p className="yt-page-sub">
        Paste a YouTube URL — the engine reads the comments and extracts structured insights.
      </p>

      {/* URL input */}
      <div className="yt-url-row">
        <label className="yt-url-field">
          <svg className="yt-url-lead" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 1 0-5.66-5.66l-1 1"/>
            <path d="M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 1 0 5.66 5.66l1-1"/>
          </svg>
          <input
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && analyze()}
          />
          {isValidUrl && (
            <span className="yt-url-valid">
              <span className="yt-url-valid-dot" />
              Valid URL
            </span>
          )}
        </label>
        <button className="yt-btn-primary" onClick={analyze} disabled={loading}>
          {loading ? "Analyzing…" : "Analyze"}
        </button>
      </div>

      {/* Example chips */}
      <div className="yt-examples">
        <span className="yt-examples-label">Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.url}
            type="button"
            className="yt-chip"
            onClick={() => setUrl(ex.url)}
          >
            {ex.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && <div className="yt-error">{error}</div>}

      {/* Loading */}
      {loading && (
        <div className="yt-loading">
          <div className="yt-spinner" />
          Analyzing comments…
        </div>
      )}

      {/* Results */}
      {analytics && !loading && (
        <>
          {/* Video meta card */}
          {(videoId || analytics.title) && (
            <div className="yt-vid-card">
              {videoId && (
                <a
                  className="yt-vid-thumb"
                  href={`https://www.youtube.com/watch?v=${videoId}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <img
                    src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`}
                    alt={analytics.title || "YouTube video thumbnail"}
                  />
                  <span className="yt-vid-play"><span className="yt-vid-play-glyph" /></span>
                  {analytics.duration && (
                    <span className="yt-vid-duration">{analytics.duration}</span>
                  )}
                </a>
              )}
              <div className="yt-vid-info">
                {(analytics.channel_name || analytics.subscriber_count != null || analytics.published_at) && (
                  <p className="yt-vid-meta">
                    {analytics.channel_name && <span>{analytics.channel_name}</span>}
                    {analytics.subscriber_count != null && <span>{fmt(analytics.subscriber_count)} subscribers</span>}
                    {analytics.published_at && <span>{fmtDate(analytics.published_at)}</span>}
                  </p>
                )}
                {analytics.title && (
                  <p className="yt-vid-title">{analytics.title}</p>
                )}
                {(analytics.view_count != null || analytics.like_count != null || analytics.comment_count != null) && (
                  <p className="yt-vid-stats">
                    {analytics.view_count != null && <span>{fmt(analytics.view_count)} views</span>}
                    {analytics.like_count != null && <span>{fmt(analytics.like_count)} likes</span>}
                    {analytics.comment_count != null && <span>{analytics.comment_count.toLocaleString()} comments</span>}
                    {likeRatio(analytics.like_count, analytics.view_count) && (
                      <span>{likeRatio(analytics.like_count, analytics.view_count)} like ratio</span>
                    )}
                  </p>
                )}
              </div>
            </div>
          )}

          {problems.length === 0 ? (
            <p className="yt-empty">No insights found in the comments.</p>
          ) : (
            <>
              {/* Section heading + view toggle */}
              <div className="yt-section-h">
                <div>
                  <h2>Extracted insights</h2>
                  <p className="yt-section-sub">
                    {problems.length} insight{problems.length !== 1 ? "s" : ""} from comment analysis
                  </p>
                </div>
                <div className="yt-view-toggle">
                  {["cards", "table", "json"].map((v) => (
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
                <div className="yt-results-grid">
                  {problems.map((p, i) => (
                    <InsightCard key={i} problem={p} />
                  ))}
                </div>
              )}

              {/* Table view */}
              {view === "table" && <InsightTable problems={problems} />}

              {/* JSON view */}
              {view === "json" && (
                <div className="yt-json-wrap">
                  <pre>{JSON.stringify(problems, null, 2)}</pre>
                </div>
              )}

            </>
          )}

          {/* RAG context */}
          <RetrievedContextAccordion items={retrievedContext} />
        </>
      )}

      {!loading && !analytics && !error && (
        <div className="yt-empty">Enter a YouTube URL above to get started.</div>
      )}
    </div>
  );
}

export default YouTubePage;
