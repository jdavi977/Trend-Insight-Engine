import "./App.css";
import { useState } from "react";
import YouTubePage from "./YouTubePage";
import AppStorePage from "./AppStorePage";
import HomePage from "./HomePage";
import InsightsPage from "./InsightsPage";

function App() {
  const [currentPage, setCurrentPage] = useState("homepage");

  return (
    <div className="app-wrap">
      <header className="site-header">
        <nav className="site-header-nav site-header-nav-left">
          <a
            href="#"
            className="site-header-link site-header-home"
            onClick={(e) => {
              e.preventDefault();
              setCurrentPage("homepage");
            }}
          >
            Home
          </a>
          <button
            type="button"
            className="site-header-link"
            onClick={() => setCurrentPage("homepage")}
          >
            Categories
          </button>
          <button
            type="button"
            className="site-header-link"
            onClick={() => setCurrentPage("youtube")}
          >
            Top Videos
          </button>
          <button
            type="button"
            className="site-header-link"
            onClick={() => setCurrentPage("insights")}
          >
            Insights
          </button>
          <button
            type="button"
            className="site-header-link"
            onClick={() => setCurrentPage("appstore")}
          >
            App Store
          </button>
          <button type="button" className="site-header-link">
            Contact
          </button>
        </nav>
        <div className="site-header-logo">
          <span className="site-header-logo-shapes" aria-hidden="true">
            <span className="site-header-logo-shape site-header-logo-shape--sq" />
            <span className="site-header-logo-shape site-header-logo-shape--circle" />
            <span className="site-header-logo-shape site-header-logo-shape--tri" />
          </span>
          <span className="site-header-logo-text">Trend Insight</span>
        </div>
      </header>

      <main className="site-main">
        {currentPage === "youtube" && <YouTubePage />}
        {currentPage === "appstore" && <AppStorePage />}
        {currentPage === "homepage" && <HomePage />}
        {currentPage === "insights" && <InsightsPage />}
      </main>

      {(currentPage === "homepage" || currentPage === "insights") && (
        <footer className="site-footer">
          <div className="site-footer-logo">Trend Insight</div>
          <div className="site-footer-links">
            <div className="site-footer-col">
              <div className="site-footer-col-title">Explore</div>
              <a href="#" className="site-footer-link" onClick={(e) => { e.preventDefault(); setCurrentPage("homepage"); }}>Home</a>
              <a href="#" className="site-footer-link" onClick={(e) => { e.preventDefault(); setCurrentPage("homepage"); }}>Categories</a>
              <a href="#" className="site-footer-link" onClick={(e) => { e.preventDefault(); setCurrentPage("insights"); }}>Insights</a>
            </div>
            <div className="site-footer-col">
              <div className="site-footer-col-title">Community</div>
              <a href="#" className="site-footer-link">Contact</a>
              <a href="#" className="site-footer-link">FAQ</a>
              <a href="#" className="site-footer-link">Support</a>
            </div>
            <div className="site-footer-col">
              <div className="site-footer-col-title">Resources</div>
              <a href="#" className="site-footer-link">Blog</a>
              <a href="#" className="site-footer-link">Weekly Updates</a>
              <a href="#" className="site-footer-link">Terms</a>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}

export default App;
