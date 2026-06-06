import "./App.css";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import YouTubePage from "./YouTubePage";
import AppStorePage from "./AppStorePage";
import HomePage from "./HomePage";
import InsightsPage from "./InsightsPage";
import HomeV2 from "./HomeV2";
import NewRun from "./NewRun";
import RunResult from "./RunResult";
import MyRuns from "./MyRuns";

// v2 nav only points at the new run-lifecycle pages. Navigation is real
// client-side routing via react-router-dom (ADR 2026-06-01 / issue #58) —
// replacing the slice-1 `currentPage` state switch. The legacy v1 pages
// (HomePage, InsightsPage, YouTubePage, AppStorePage) stay mounted on
// /legacy/* routes but are unlinked from nav — removal is slice 3 (spec §9.1).
const NAV_ITEMS = [
  {
    to: "/",
    label: "Home",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 11l9-8 9 8v9a2 2 0 0 1-2 2h-4v-7h-6v7H5a2 2 0 0 1-2-2z"/>
      </svg>
    ),
  },
  {
    to: "/runs/new",
    label: "New Run",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>
      </svg>
    ),
  },
  {
    to: "/runs/mine",
    label: "My Runs",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 6h16M4 12h16M4 18h10"/>
      </svg>
    ),
  },
];

// Legacy pages addressed paths via string keys ("insights", "youtube", …);
// adapt that to /legacy/* routes so the unlinked pages keep working until
// slice-3 removal.
function LegacyHomePage() {
  const navigate = useNavigate();
  return <HomePage onNavigate={(page) => navigate(`/legacy/${page}`)} />;
}

function App() {
  return (
    <div className="app-layout">

      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">T</div>
          <div className="brand-name">Trend</div>
        </div>

        <nav className="nav" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
            >
              <span className="ico">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="site-main">
        <Routes>
          <Route path="/" element={<HomeV2 />} />
          <Route path="/runs/new" element={<NewRun />} />
          {/* Static `/runs/mine` outranks `/runs/:id` in react-router's match
              ranking, so My Runs resolves before the dynamic run route. */}
          <Route path="/runs/mine" element={<MyRuns />} />
          <Route path="/runs/:id" element={<RunResult />} />
          {/* Legacy v1 pages — unlinked from nav, mounted until slice 3 removal. */}
          <Route path="/legacy/home" element={<LegacyHomePage />} />
          <Route path="/legacy/homepage" element={<LegacyHomePage />} />
          <Route path="/legacy/insights" element={<InsightsPage />} />
          <Route path="/legacy/youtube" element={<YouTubePage />} />
          <Route path="/legacy/appstore" element={<AppStorePage />} />
        </Routes>
      </main>

    </div>
  );
}

export default App;
