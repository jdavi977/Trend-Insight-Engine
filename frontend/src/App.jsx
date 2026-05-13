import "./App.css";
import { useState } from "react";
import YouTubePage from "./YouTubePage";
import AppStorePage from "./AppStorePage";
import HomePage from "./HomePage";
import InsightsPage from "./InsightsPage";

const NAV_ITEMS = [
  {
    id: "homepage",
    label: "Home",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 11l9-8 9 8v9a2 2 0 0 1-2 2h-4v-7h-6v7H5a2 2 0 0 1-2-2z"/>
      </svg>
    ),
  },
  {
    id: "insights",
    label: "Insights",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 17l6-6 4 4 8-9"/><path d="M14 6h7v7"/>
      </svg>
    ),
  },
  {
    id: "youtube",
    label: "YouTube analysis",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="5" width="20" height="14" rx="3"/>
        <path d="M10 9l5 3-5 3z" fill="currentColor" stroke="none"/>
      </svg>
    ),
  },
  {
    id: "appstore",
    label: "App Store analysis",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="4" y="3" width="16" height="18" rx="3"/>
        <path d="M8 17h8"/>
        <circle cx="12" cy="9" r="2"/>
      </svg>
    ),
  },
];

function App() {
  const [currentPage, setCurrentPage] = useState("homepage");

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
        {currentPage === "youtube"   && <YouTubePage />}
        {currentPage === "appstore"  && <AppStorePage />}
        {currentPage === "homepage"  && <HomePage onNavigate={setCurrentPage} />}
        {currentPage === "insights"  && <InsightsPage />}
      </main>

    </div>
  );
}

export default App;
