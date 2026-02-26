import { useState, useEffect } from "react";
import "./HomePage.css";

const CATEGORIES = [
  {
    id: 20,
    label: "Games",
    slug: "games",
    icon: "./assets/Pictures/Games.png",
    description:
      "Explore top gaming videos and discover trending player issues and feedback.",
  },
  {
    id: 28,
    label: "Science & Tech",
    slug: "scitech",
    icon: "./assets/Pictures/SciTech.png",
    description:
      "See what's popular in tech and the challenges viewers are talking about.",
  },
  {
    id: 26,
    label: "How-to & Style",
    slug: "howstyle",
    icon: "./assets/Pictures/beauty.png",
    description:
      "Track lifestyle and how-to topics and frequent audience problems.",
  },
];

// function createCategoryGrouping(weeklyData, categoryId) {
//   const category = weeklyData.flatMap((nestedArray) =>
//     nestedArray.filter((item) => item.category === categoryId),
//   );
//   return Object.groupBy(category, (item) => item.key);
// }

function getTopVideoEntries(weeklyData) {
  const all = weeklyData.flat();
  const byKey = Object.groupBy(all, (item) => item.key);
  return Object.entries(byKey)
    .slice(0, 3)
    .map(([key, items]) => ({
      key,
      title: items[0].title,
      category: items[0].category,
      items,
    }));
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

  const topVideos = getTopVideoEntries(weeklyData || []);

  return (
    <div className="homepage">
      <section className="hero">
        <h1 className="hero-title">Weekly YouTube Insights.</h1>
        <p className="hero-subtitle">Popular videos, real user issues.</p>
      </section>

      <section className="intro">
        <p className="intro-lead">
          Get insights from the most popular YouTube videos across three
          trending categories.
        </p>
        <p className="intro-sub">
          Uncover what common user issues appear each week.
        </p>
      </section>

      <section className="category-cards" id="categories">
        <div className="category-cards-inner">
          {CATEGORIES.map((cat) => (
            <article key={cat.id} className="category-card">
              <div>
                <img className="resized-image" src={cat.icon} />
              </div>
              <h2 className="category-card-title">{cat.label}</h2>
              <p className="category-card-desc">{cat.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="top-videos" id="top-videos">
        <h2 className="top-videos-title">Top Videos by Category</h2>
        <p className="top-videos-subtitle">
          This week&apos;s most popular picks
        </p>

        {loading && (
          <div className="homepage-loading">
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

        {!loading && !error && topVideos.length === 0 && (
          <p className="top-videos-empty">
            No insights yet. Check back after the next run.
          </p>
        )}

        {!loading && !error && topVideos.length > 0 && (
          <div className="top-videos-grid">
            {topVideos.map(({ key, title, items }) => (
              <article key={key} className="top-video-card">
                <a
                  href={`https://www.youtube.com/watch?v=${key}`}
                  target="_blank"
                >
                  <div className="top-video-card-thumb" />
                  <h3 className="top-video-card-title">{title}</h3>
                </a>
                <p className="top-video-card-meta">
                  {new Date().toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </p>
                <ul className="top-video-card-insights">
                  {items.slice(0, 3).map((item, idx) => (
                    <li key={idx} className="top-video-card-insight">
                      {item.problems?.problem}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default HomePage;

/*
 * TODO:
 * Add thumbnails
 * Show Top videos for other categories
 */
