import { useState, useEffect } from "react";
import "./HomePage.css";

const CATEGORIES = [
  {
    id: 20,
    label: "Games",
    slug: "games",
    icon: "🎮",
    accent: "var(--category-games)",
  },
  {
    id: 28,
    label: "Science & Tech",
    slug: "scitech",
    icon: "🔬",
    accent: "var(--category-scitech)",
  },
  {
    id: 26,
    label: "How-to & Style",
    slug: "howstyle",
    icon: "✨",
    accent: "var(--category-howstyle)",
  },
];

function createCategoryGrouping(weeklyData, categoryId) {
  const category = weeklyData.flatMap((nestedArray) =>
    nestedArray.filter((item) => item.category === categoryId),
  );
  return Object.groupBy(category, (item) => item.key);
}

function HomePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weeklyData, setWeeklyData] = useState([]);

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

  return (
    <div className="homepage">
      <header className="homepage-hero">
        <h1 className="homepage-title">Weekly YouTube Insights</h1>
        <p className="homepage-subtitle">
          Top themes and problems from trending videos, by category
        </p>
      </header>

      {loading && (
        <div className="homepage-loading" aria-hidden="true">
          <div className="homepage-loading-spinner" />
          <p>Loading insights…</p>
        </div>
      )}

      {error && (
        <div className="homepage-error" role="alert">
          <span className="homepage-error-icon" aria-hidden="true">
            ⚠️
          </span>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="category-grid">
          {CATEGORIES.map((cat) => {
            const grouping = createCategoryGrouping(weeklyData, cat.id);
            const hasData = grouping && Object.keys(grouping).length > 0;
            return (
              <section
                key={cat.id}
                className="category-column"
                aria-labelledby={`category-heading-${cat.slug}`}
                style={{ "--accent": cat.accent }}
              >
                <h2
                  id={`category-heading-${cat.slug}`}
                  className="category-column-title"
                >
                  <span className="category-column-icon" aria-hidden="true">
                    {cat.icon}
                  </span>
                  {cat.label}
                </h2>

                {!hasData && (
                  <div className="category-empty">
                    <p>No insights yet. Check back after the next run.</p>
                  </div>
                )}

                {hasData && (
                  <ul className="category-video-list">
                    {Object.entries(grouping).map(([key, objects]) => (
                      <li key={key} className="video-group">
                        <h3 className="video-group-title">
                          {objects[0].title}
                        </h3>
                        <ul className="problems-list">
                          {objects.map((problem, index) => (
                            <li
                              key={`${key}-${index}`}
                              className="problem-item"
                            >
                              <p className="problem-text">
                                {problem.problems.problem}
                              </p>
                              <div className="problem-meta">
                                <span className="pill type">
                                  {problem.problems.type}
                                </span>
                                <span className="pill">
                                  👍 {problem.problems.total_likes} likes
                                </span>
                                <span className="pill pill-metric">
                                  Severity {problem.problems.severity}/5
                                </span>
                                <span className="pill pill-metric">
                                  Frequency {problem.problems.frequency}/5
                                </span>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default HomePage;
