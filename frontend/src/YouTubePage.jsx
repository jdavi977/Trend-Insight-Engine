import { useState } from "react";

function YouTubePage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [analytics, setAnalytics] = useState();
  const [error, setError] = useState("");

  const YOUTUBE_REGEX =
    /^https?:\/\/((www\.)?youtube\.com\/watch\?v=|youtu\.be\/)[A-Za-z0-9_-]{11}$/;

  const analyze = async () => {
    setError("");
    setAnalytics("");
    setLoading(true);

    if (!YOUTUBE_REGEX.test(url)) {
      setError("Invalid YouTube link");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/analyze/youtube", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ youtubeURL: url }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      const parsedData = typeof data === "string" ? JSON.parse(data) : data;

      setAnalytics(parsedData);
      setLoading(false);
    } catch (error) {
      setError("Failed to analyze. Please try again.");
      setLoading(false);
      console.error("Error", error);
    }
  };

  const save = async () => {
    try {
      const payload = {
        data: analytics,
      };
      const response = await fetch("http://localhost:8000/data/send", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      setError("Failed to send data. Please try again.");
      setLoading(false);
      console.error("Error", error);
    }
  };

  const problems = analytics?.problems || analytics?.["problems:"] || [];
  console.log(problems);
  console.log(problems.length);

  return (
    <div className="app-shell">
      <div className="app-header">
        <h1>Trend Insight Engine</h1>
        <p className="app-subtitle">
          Analyze YouTube comments to discover insights and trends
        </p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="input-row">
        -
        <input
          type="text"
          id="youtube-link"
          placeholder="Paste your YouTube link here..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !loading && analyze()}
          required
        />
        <button onClick={analyze} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>
      {analytics && problems.length > 0 && (
        <div className="analytics-card">
          <div className="card-header">
            <h2>Insights</h2>
            <span className="pill">
              {problems.length} {problems.length === 1 ? "Problem" : "Problems"}
            </span>
          </div>
          <ul className="problems-list">
            {problems.map((problem, index) => (
              <li key={index} className="problem-item">
                <h3 className="problem-title">{problem.problem}</h3>
                <div className="problem-meta">
                  <span className="pill">{problem.type}</span>
                  <span className="pill">👍 {problem.total_likes} likes</span>
                  <span className="pill">Severity: {problem.severity}/5</span>
                  <span className="pill">Frequency: {problem.frequency}/5</span>
                </div>
              </li>
            ))}
          </ul>
          <div className="card-header">
            <button onClick={save}>Save Data</button>
          </div>
        </div>
      )}

      {analytics && problems.length === 0 && (
        <div className="analytics-card">
          <p className="empty-state">No problems found in the comments.</p>
        </div>
      )}
    </div>
  );
}

export default YouTubePage;
