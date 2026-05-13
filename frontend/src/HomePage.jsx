import { useState, useEffect } from "react";
import "./HomePage.css";

const CATEGORIES_YT = [
  {
    id: 20,
    name: "Games",
    catId: "id 20",
    count: "5 videos",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 4h12l2 4-8 12L4 8z"/>
      </svg>
    ),
  },
  {
    id: 28,
    name: "Science & Tech",
    catId: "id 28",
    count: "5 videos",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3"/><path d="M3 12h2M19 12h2M12 3v2M12 19v2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>
      </svg>
    ),
  },
  {
    id: 26,
    name: "How-to & Style",
    catId: "id 26",
    count: "5 videos",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 4h16v6a8 8 0 1 1-16 0z"/><path d="M9 14v6M15 14v6M7 20h10"/>
      </svg>
    ),
  },
];

const CATEGORIES_APP = [
  {
    id: 6014,
    name: "Games",
    catId: "id 6014",
    count: "5 apps",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="7" width="18" height="11" rx="3"/><path d="M8 11v3M6 12.5h4M15 12h.01M18 14h.01"/>
      </svg>
    ),
  },
  {
    id: 6005,
    name: "Social Networking",
    catId: "id 6005",
    count: "5 apps",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="8" cy="8" r="3"/><circle cx="16" cy="16" r="3"/><path d="M10.5 9.5l3 5"/>
      </svg>
    ),
  },
  {
    id: 6002,
    name: "Utilities",
    catId: "id 6002",
    count: "5 apps",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 3 4 14h7l-1 7 10-11h-7z"/>
      </svg>
    ),
  },
];

const CAT_LABEL = { 20: "Games", 28: "Sci & Tech", 26: "How-to" };
const SEV_CLASS = { 5: "s5", 4: "s4", 3: "s3", 2: "s2", 1: "s1" };

function parseThumbnail(raw) {
  if (!raw) return null;
  if (typeof raw === "object") return raw;
  try { return JSON.parse(raw); } catch { return null; }
}

function getTopVideoEntries(weeklyData) {
  const all = weeklyData.flat();
  const byKey = Object.groupBy(all, (item) => item.key);
  return Object.entries(byKey)
    .slice(0, 3)
    .map(([key, items]) => ({
      key,
      title: items[0].title,
      category: items[0].category,
      thumbnail: parseThumbnail(items[0].thumbnail),
      items,
    }));
}

function HomePage({ onNavigate }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weeklyData, setWeeklyData] = useState([]);
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState("youtube");
  const [urlValue, setUrlValue] = useState("");

  useEffect(() => {
    const getData = async () => {
      try {
        const [homeRes, statsRes] = await Promise.all([
          fetch("http://localhost:8000/get/homePage"),
          fetch("http://localhost:8000/get/homePageStats"),
        ]);
        if (!homeRes.ok) throw new Error(`HTTP error! status: ${homeRes.status}`);
        const data = await homeRes.json();
        setWeeklyData(data);
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats(statsData);
        }
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
    <div className="hp">

      {/* ── Hero ── */}
      <section className="hp-hero">
        <h1 className="hp-title">
          Turn YouTube comments and App Store reviews into{" "}
          <em>actionable product insights</em>.
        </h1>
        <p className="hp-sub">
          Paste a video or app URL. The engine fetches user feedback, filters
          noise, and uses an LLM to surface recurring problems — ranked by
          severity and frequency.
        </p>
      </section>

      {/* ── Pipeline status ── */}
      <section className="hp-sec">
        <div className="hp-sec-head">
          <div className="hp-sec-head-l">
            <h2>Total processed</h2>
            <p className="hp-sec-sub">Automated pipeline runs Sun / Wed / Fri at 08:00 UTC via GitHub Actions.</p>
          </div>
        </div>
        <div className="hp-pipeline">
          <div className="hp-pipe-cell">
            <span className="hp-pipe-label">Items analyzed</span>
            <span className="hp-pipe-value">
              {stats
                ? <>{stats.items_analyzed.total}<span className="hp-unit"> · {stats.items_analyzed.youtube} YT + {stats.items_analyzed.appstore} apps</span></>
                : <span className="hp-unit">—</span>}
            </span>
          </div>
          <div className="hp-pipe-cell">
            <span className="hp-pipe-label">Problems extracted</span>
            <span className="hp-pipe-value">{stats ? stats.problems_extracted : "—"}</span>
          </div>
          <div className="hp-pipe-cell">
            <span className="hp-pipe-label">Insights indexed</span>
            <span className="hp-pipe-value">{stats ? stats.insights_indexed : "—"}</span>
          </div>
          <div className="hp-pipe-cell">
            <span className="hp-pipe-label">Pipeline status</span>
            <span className="hp-pipe-value">
              <span className="hp-ok"><span className="hp-ok-dot" />Healthy</span>
            </span>
          </div>
        </div>
      </section>

      {/* ── Covered categories ── */}
      <section className="hp-sec">
        <div className="hp-sec-head">
          <div className="hp-sec-head-l">
            <h2>Covered categories</h2>
            <p className="hp-sec-sub">5 items per category per run.</p>
          </div>
        </div>
        <div className="hp-cats">

          <div className="hp-cat-group">
            <div className="hp-cat-group-head">
              <span className="hp-src-badge">
                <span className="hp-src-mark yt">YT</span>
                YouTube
              </span>
              <span className="hp-src-count">Data API v3</span>
            </div>
            <div className="hp-cat-list">
              {CATEGORIES_YT.map((cat) => (
                <button key={cat.id} className="hp-cat-row">
                  <span className="hp-cat-glyph">{cat.icon}</span>
                  <span>
                    <div className="hp-cat-name">{cat.name}</div>
                    <span className="hp-cat-id">{cat.catId}</span>
                  </span>
                  <span className="hp-cat-meta">{cat.count}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="hp-cat-group">
            <div className="hp-cat-group-head">
              <span className="hp-src-badge">
                <span className="hp-src-mark app">AS</span>
                App Store
              </span>
              <span className="hp-src-count">iTunes RSS · US</span>
            </div>
            <div className="hp-cat-list">
              {CATEGORIES_APP.map((cat) => (
                <button key={cat.id} className="hp-cat-row">
                  <span className="hp-cat-glyph">{cat.icon}</span>
                  <span>
                    <div className="hp-cat-name">{cat.name}</div>
                    <span className="hp-cat-id">{cat.catId}</span>
                  </span>
                  <span className="hp-cat-meta">{cat.count}</span>
                </button>
              ))}
            </div>
          </div>

        </div>
      </section>

      {/* ── Top picks this week ── */}
      <section className="hp-sec">
        <div className="hp-sec-head">
          <div className="hp-sec-head-l">
            <h2>Top picks this week</h2>
            <p className="hp-sec-sub">Pre-analyzed by the Sunday pipeline run.</p>
          </div>
          <button className="hp-sec-link" onClick={() => onNavigate?.("insights")}>
            View all insights →
          </button>
        </div>

        {loading && (
          <div className="hp-loading">
            <div className="hp-spinner" />
            <p>Loading insights…</p>
          </div>
        )}

        {error && (
          <div className="hp-error" role="alert">
            <p>{error}</p>
          </div>
        )}

        {!loading && !error && topVideos.length === 0 && (
          <p className="hp-empty">No insights yet. Check back after the next run.</p>
        )}

        {!loading && !error && topVideos.length > 0 && (
          <div className="hp-topvids">
            {topVideos.map(({ key, title, category, thumbnail, items }) => (
              <article key={key} className="hp-topvid">
                <div className="hp-topvid-thumb">
                  <span className="hp-src-stamp">
                    <span className="hp-src-mark yt">YT</span>
                    {CAT_LABEL[category] ?? `Cat ${category}`}
                  </span>
                  {thumbnail?.url ? (
                    <img src={thumbnail.url} alt={title} loading="lazy" />
                  ) : (
                    <span className="hp-thumb-placeholder">video thumbnail</span>
                  )}
                </div>
                <div className="hp-topvid-body">
                  <span className="hp-topvid-cat">YouTube · Category {category}</span>
                  <h3 className="hp-topvid-title">{title}</h3>
                  <ul className="hp-topvid-problems">
                    {items.slice(0, 3).map((item, idx) => {
                      const sev = item.problems?.severity ?? 0;
                      const freq = item.problems?.frequency ?? 0;
                      return (
                        <li key={idx} className="hp-topvid-problem">
                          <span className={`hp-sev ${SEV_CLASS[sev] ?? ""}`}>
                            S{sev}·F{freq}
                          </span>
                          <span>{item.problems?.problem}</span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* ── How it works ── */}
      <section className="hp-sec">
        <div className="hp-sec-head">
          <div className="hp-sec-head-l">
            <h2>How the pipeline works</h2>
            <p className="hp-sec-sub">Same flow for manual and automated runs.</p>
          </div>
        </div>
        <div className="hp-how">
          <article className="hp-how-step">
            <h3>Ingest</h3>
            <p>Fetch up to 100 YouTube comments (relevance order) or paginate the iTunes RSS feed for App Store reviews.</p>
          </article>
          <article className="hp-how-step">
            <h3>Clean</h3>
            <p>Engagement filter, normalize, strip emojis, keyword filter, and dedupe — same preprocessing across both sources.</p>
          </article>
          <article className="hp-how-step">
            <h3>Extract</h3>
            <p>gpt-4o produces a validated list of problems with type, severity (1–5), and frequency (1–5). Embedded with text-embedding-3-small for RAG.</p>
          </article>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="hp-footer">
        <div className="hp-footer-brand">
          <div className="hp-brand-mark">T</div>
          <span><b>Trend Insight Engine</b> · MIT licensed</span>
        </div>
        <div className="hp-footer-links">
          <a
            href="https://github.com/jdavi977/Trend-Insight-Engine"
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.09 3.29 9.4 7.86 10.93.58.1.8-.25.8-.56v-2.1c-3.2.7-3.87-1.37-3.87-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.18-3.08-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.18 1.17.92-.26 1.91-.39 2.9-.39.98 0 1.97.13 2.9.39 2.2-1.48 3.18-1.17 3.18-1.17.62 1.59.23 2.76.11 3.05.73.8 1.17 1.82 1.17 3.08 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.06.78 2.13v3.16c0 .31.21.67.81.56C20.22 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5Z"/>
            </svg>
            jdavi977/Trend-Insight-Engine
          </a>
        </div>
      </footer>

    </div>
  );
}

export default HomePage;
