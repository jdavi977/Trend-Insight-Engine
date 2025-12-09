import { useState } from "react";

function AppStorePage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [analytics, setAnalytics] = useState();
  const [error, setError] = useState("");

  const APP_STORE_REGEX =
    /^https?:\/\/(www\.)?apps\.apple\.com\/[a-z]{2}\/app\/[A-Za-z0-9\-]+\/id\d+$/;

  const analyze = async () => {
    setError("");
    setAnalytics("");
    setLoading(true);

    if (!APP_STORE_REGEX.test(url)) {
      setError("Invalid App Store link");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/analyze/appStore", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ appStoreURL: url }),
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

  const problems = analytics?.Problems || analytics?.["Problems:"] || [];

  return (
    <div className="app-shell">
      <div className="app-header">
        <h1>Trend Insight Engine</h1>
        <p className="app-subtitle">
          Analyze App Store reviews to discover insights and trends
        </p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="input-row">
        <input
          type="text"
          id="appstore-link"
          placeholder="Paste your App Store link here..."
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
        </div>
      )}

      {analytics && problems.length === 0 && (
        <div className="analytics-card">
          <p className="empty-state">No problems found in the reviews.</p>
        </div>
      )}
    </div>
  );
}

export default AppStorePage;

