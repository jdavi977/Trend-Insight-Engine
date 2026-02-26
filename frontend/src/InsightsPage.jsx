import { useState, useEffect } from "react";
import "./InsightsPage.css";

const CATEGORY_LABELS = {
  20: "Games",
  28: "Science & Tech",
  26: "How-to & Style",
};

function getAllVideoEntries(weeklyData) {
  const all = (weeklyData || []).flat();
  const byKey = Object.groupBy(all, (item) => item.key);
  return Object.entries(byKey).map(([key, items]) => ({
    key,
    title: items[0].title,
    category: items[0].category,
    categoryLabel: CATEGORY_LABELS[items[0].category] || "Other",
    items,
  }));
}

function formatDate() {
  return new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function InsightsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weeklyData, setWeeklyData] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);

  useEffect(() => {
    const getData = async () => {
      try {
        const response = await fetch("http://localhost:8000/get/homePage");
        if (!response.ok)
          throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setWeeklyData(data);
      } catch (err) {
        setError(err.message || "Failed to load insights");
      } finally {
        setLoading(false);
      }
    };
    getData();
  }, []);

  const allEntries = getAllVideoEntries(weeklyData);
  const filteredEntries =
    selectedCategory == null
      ? allEntries
      : allEntries.filter((e) => e.category === selectedCategory);

  return (
    <div className="insights-page">
      <section className="insights-browse">
        <h2 className="insights-browse-title">Browse by Category</h2>
        <p className="insights-browse-desc">
          Quickly access relevant content based on specific categories such as
          technology, business, and entertainment. Choose a category to get
          started and explore curated insights.
        </p>
        <div className="insights-browse-pills">
          <button
            type="button"
            className={`insights-pill ${selectedCategory === null ? "active" : ""}`}
            onClick={() => setSelectedCategory(null)}
          >
            All
          </button>
          {Object.entries(CATEGORY_LABELS).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`insights-pill ${selectedCategory === Number(id) ? "active" : ""}`}
              onClick={() => setSelectedCategory(Number(id))}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      <section className="insights-all">
        <h2 className="insights-all-title">Videos</h2>
        <p className="insights-all-sub">
          Filter videos by category to find what you want fastest.
        </p>

        {loading && (
          <div className="insights-loading">
            <div className="insights-loading-spinner" />
            <p>Loading insights…</p>
          </div>
        )}

        {error && (
          <div className="insights-error" role="alert">
            <p>{error}</p>
          </div>
        )}

        {!loading && !error && filteredEntries.length === 0 && (
          <p className="insights-empty">
            No insights yet. Check back after the next run.
          </p>
        )}

        {!loading && !error && filteredEntries.length > 0 && (
          <div className="insights-rows">
            {filteredEntries.map((entry) => {
              const problems = entry.items
                .map((i) => i.problems?.problem)
                .filter(Boolean);
              return (
                <div key={entry.key} className="insights-row">
                  <div className="insights-row-title">
                    <h3 className="insights-list-title">{entry.title}</h3>
                    <p className="insights-list-date">{formatDate()}</p>
                  </div>
                  <article className="insights-row-detail">
                    <div className="insights-detail-thumb" />
                    <div className="insights-detail-body">
                      <h4 className="insights-detail-heading">
                        Common Issues Highlighted
                      </h4>
                      <ul className="insights-detail-bullets">
                        {problems.length > 0 ? (
                          problems.map((text, idx) => <li key={idx}>{text}</li>)
                        ) : (
                          <li>No issues extracted for this video.</li>
                        )}
                      </ul>
                    </div>
                  </article>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

export default InsightsPage;
