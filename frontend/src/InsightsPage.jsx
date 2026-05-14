import { useState, useEffect } from "react";
import "./InsightsPage.css";

const CATEGORY_LABELS = {
  20: "Games",
  28: "Science & Tech",
  26: "How-to & Style",
};

const GENRE_LABELS = {
  6014: "Games",
  6005: "Social Networking",
  6002: "Utilities",
};

function parseThumbnail(raw) {
  if (!raw) return null;
  if (typeof raw === "object") return raw;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function getAllVideoEntries(weeklyData) {
  const all = (weeklyData || []).flat();
  const byKey = Object.groupBy(all, (item) => item.key);
  return Object.entries(byKey).map(([key, items]) => ({
    key,
    title: items[0].title,
    category: items[0].category,
    categoryLabel: CATEGORY_LABELS[items[0].category] || "Other",
    thumbnail: parseThumbnail(items[0].thumbnail),
    items,
  }));
}

function getAllAppEntries(appStoreData) {
  const all = (appStoreData || []).flat();
  const byAppId = Object.groupBy(all, (item) => item.app_id);
  return Object.entries(byAppId).map(([app_id, items]) => ({
    app_id,
    title: items[0].title,
    genre_id: items[0].genre_id,
    genreLabel: GENRE_LABELS[items[0].genre_id] || "Other",
    thumbnail: items[0].thumbnail,
    country: items[0].country || "us",
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
  const [source, setSource] = useState("youtube");

  const [ytLoading, setYtLoading] = useState(true);
  const [ytError, setYtError] = useState(null);
  const [weeklyData, setWeeklyData] = useState([]);

  const [asLoading, setAsLoading] = useState(true);
  const [asError, setAsError] = useState(null);
  const [appStoreData, setAppStoreData] = useState([]);

  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedGenre, setSelectedGenre] = useState(null);

  useEffect(() => {
    const fetchYouTube = async () => {
      try {
        const response = await fetch(
          `${import.meta.env.VITE_API_BASE}/get/homePage`
        );
        if (!response.ok)
          throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setWeeklyData(data);
      } catch (err) {
        setYtError(err.message || "Failed to load YouTube insights");
      } finally {
        setYtLoading(false);
      }
    };

    const fetchAppStore = async () => {
      try {
        const response = await fetch(
          `${import.meta.env.VITE_API_BASE}/get/homePageAppStore`
        );
        if (!response.ok)
          throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        setAppStoreData(data);
      } catch (err) {
        setAsError(err.message || "Failed to load App Store insights");
      } finally {
        setAsLoading(false);
      }
    };

    fetchYouTube();
    fetchAppStore();
  }, []);

  const allEntries = getAllVideoEntries(weeklyData);
  const filteredEntries =
    selectedCategory == null
      ? allEntries
      : allEntries.filter((e) => e.category === selectedCategory);

  const allAppEntries = getAllAppEntries(appStoreData);
  const filteredAppEntries =
    selectedGenre == null
      ? allAppEntries
      : allAppEntries.filter((e) => e.genre_id === selectedGenre);

  return (
    <div className="insights-page">
      <div className="insights-source-toggle">
        <button
          type="button"
          className={`insights-source-button ${source === "youtube" ? "active" : ""}`}
          onClick={() => setSource("youtube")}
        >
          YouTube
        </button>
        <button
          type="button"
          className={`insights-source-button ${source === "appstore" ? "active" : ""}`}
          onClick={() => setSource("appstore")}
        >
          App Store
        </button>
      </div>

      {source === "youtube" ? (
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
      ) : (
        <section className="insights-browse">
          <h2 className="insights-browse-title">Browse by Genre</h2>
          <p className="insights-browse-desc">
            Explore App Store insights filtered by genre. Choose a genre to see
            the most common issues users report.
          </p>
          <div className="insights-browse-pills">
            <button
              type="button"
              className={`insights-pill ${selectedGenre === null ? "active" : ""}`}
              onClick={() => setSelectedGenre(null)}
            >
              All
            </button>
            {Object.entries(GENRE_LABELS).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={`insights-pill ${selectedGenre === Number(id) ? "active" : ""}`}
                onClick={() => setSelectedGenre(Number(id))}
              >
                {label}
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="insights-all">
        <h2 className="insights-all-title">
          {source === "youtube" ? "Videos" : "Apps"}
        </h2>
        <p className="insights-all-sub">
          {source === "youtube"
            ? "Filter videos by category to find what you want fastest."
            : "Filter apps by genre to find what you want fastest."}
        </p>

        {source === "youtube" && ytLoading && (
          <div className="insights-loading">
            <div className="insights-loading-spinner" />
            <p>Loading insights…</p>
          </div>
        )}

        {source === "youtube" && ytError && (
          <div className="insights-error" role="alert">
            <p>{ytError}</p>
          </div>
        )}

        {source === "youtube" && !ytLoading && !ytError && filteredEntries.length === 0 && (
          <p className="insights-empty">
            No insights yet. Check back after the next run.
          </p>
        )}

        {source === "youtube" && !ytLoading && !ytError && filteredEntries.length > 0 && (
          <div className="insights-rows">
            {filteredEntries.map((entry) => {
              const problems = entry.items
                .map((i) => i.problems?.problem)
                .filter(Boolean);
              return (
                <div key={entry.key} className="insights-row">
                  <div className="insights-row-title">
                    <a
                      href={`https://www.youtube.com/watch?v=${entry.key}`}
                      target="_blank"
                    >
                      {entry.thumbnail?.url ? (
                        <img
                          className="insights-detail-thumb"
                          src={entry.thumbnail.url}
                          width={entry.thumbnail.width}
                          height={entry.thumbnail.height}
                          alt={entry.title}
                          loading="lazy"
                        />
                      ) : (
                        <div className="insights-detail-thumb insights-detail-thumb--empty" />
                      )}
                    </a>
                    <h3 className="insights-list-title">{entry.title}</h3>
                    <p className="insights-list-date">{formatDate()}</p>
                  </div>
                  <article className="insights-row-detail">
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

        {source === "appstore" && asLoading && (
          <div className="insights-loading">
            <div className="insights-loading-spinner" />
            <p>Loading insights…</p>
          </div>
        )}

        {source === "appstore" && asError && (
          <div className="insights-error" role="alert">
            <p>{asError}</p>
          </div>
        )}

        {source === "appstore" && !asLoading && !asError && filteredAppEntries.length === 0 && (
          <p className="insights-empty">
            No insights yet. Check back after the next run.
          </p>
        )}

        {source === "appstore" && !asLoading && !asError && filteredAppEntries.length > 0 && (
          <div className="insights-rows">
            {filteredAppEntries.map((entry) => {
              const problems = entry.items
                .map((i) => i.problems)
                .filter(Boolean);
              return (
                <div key={entry.app_id} className="insights-row">
                  <div className="insights-row-title">
                    <a
                      href={`https://apps.apple.com/${entry.country}/app/id${entry.app_id}`}
                      target="_blank"
                    >
                      {entry.thumbnail ? (
                        <img
                          className="insights-detail-thumb"
                          src={entry.thumbnail}
                          alt={entry.title}
                          loading="lazy"
                        />
                      ) : (
                        <div className="insights-detail-thumb insights-detail-thumb--empty" />
                      )}
                    </a>
                    <h3 className="insights-list-title">{entry.title}</h3>
                    <p className="insights-list-date">{entry.genreLabel}</p>
                  </div>
                  <article className="insights-row-detail">
                    <div className="insights-detail-body">
                      <h4 className="insights-detail-heading">
                        Common Issues Highlighted
                      </h4>
                      <ul className="insights-detail-bullets">
                        {problems.length > 0 ? (
                          problems.map((p, idx) => (
                            <li key={idx}>
                              {p.problem}
                              {p.average_rating != null && (
                                <span className="insights-rating-badge">
                                  ★ {Number(p.average_rating).toFixed(1)}
                                </span>
                              )}
                            </li>
                          ))
                        ) : (
                          <li>No issues extracted for this app.</li>
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
