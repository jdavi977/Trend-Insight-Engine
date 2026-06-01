import "./App.css";
import { useState } from "react";
import YouTubePage from "./YouTubePage";
import AppStorePage from "./AppStorePage";
import HomePage from "./HomePage";
import InsightsPage from "./InsightsPage";
import HomeV2 from "./HomeV2";
import NewRun from "./NewRun";
import RunResult from "./RunResult";

// v2 nav only points at the new run-lifecycle pages (issue #53). The legacy
// pages (HomePage, InsightsPage, YouTubePage, AppStorePage) stay mounted below
// but are unlinked from nav — removal is slice 3 (spec §3, §10).
const NAV_ITEMS = [
  {
    id: "homev2",
    label: "Home",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 11l9-8 9 8v9a2 2 0 0 1-2 2h-4v-7h-6v7H5a2 2 0 0 1-2-2z"/>
      </svg>
    ),
  },
  {
    id: "newrun",
    label: "New Run",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>
      </svg>
    ),
  },
];

function App() {
  const [currentPage, setCurrentPage] = useState("homev2");
  // Set when a run is approved (or opened from a feed); the Result page reads it
  // and polls GET /runs/:id from there.
  const [activeRunId, setActiveRunId] = useState(null);

  const openRun = (runId) => {
    setActiveRunId(runId);
    setCurrentPage("runresult");
  };

  return (
    <div className="app-layout">

      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">T</div>
          <div className="brand-name">Trend</div>
        </div>

        <nav className="nav" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item${currentPage === item.id ? " active" : ""}`}
              onClick={() => setCurrentPage(item.id)}
            >
              <span className="ico">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="site-main">
        {currentPage === "homev2"    && (
          <HomeV2 onOpenRun={openRun} onNewRun={() => setCurrentPage("newrun")} />
        )}
        {currentPage === "newrun"    && <NewRun onOpenRun={openRun} />}
        {currentPage === "runresult" && (
          <RunResult runId={activeRunId} onNewRun={() => setCurrentPage("newrun")} />
        )}
        {/* Legacy v1 pages — unlinked from nav, mounted until slice 3 removal. */}
        {currentPage === "youtube"   && <YouTubePage />}
        {currentPage === "appstore"  && <AppStorePage />}
        {currentPage === "homepage"  && <HomePage onNavigate={setCurrentPage} />}
        {currentPage === "insights"  && <InsightsPage />}
      </main>

    </div>
  );
}

export default App;
