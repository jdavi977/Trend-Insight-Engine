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
        <nav className="site-header-nav">
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
            onClick={() => setCurrentPage("insights")}
          >
            Insights
          </button>
          <button
            type="button"
            className="site-header-link"
            onClick={() => setCurrentPage("youtube")}
          >
            Youtube
          </button>
          <button
            type="button"
            className="site-header-link"
            onClick={() => setCurrentPage("appstore")}
          >
            App Store
          </button>
        </nav>
      </header>

      <main className="site-main">
        {currentPage === "youtube" && <YouTubePage />}
        {currentPage === "appstore" && <AppStorePage />}
        {currentPage === "homepage" && <HomePage />}
        {currentPage === "insights" && <InsightsPage />}
      </main>

      {(currentPage === "homepage" || currentPage === "insights") && (
        <footer className="site-footer">
          <div className="site-footer-logo">Trend Insight Engine</div>
          <div className="site-footer-links">
            <div className="site-footer-col">
              <div className="site-footer-col-title">Explore</div>
              <a
                href="#"
                className="site-footer-link"
                onClick={(e) => {
                  e.preventDefault();
                  setCurrentPage("insights");
                }}
              >
                Insights
              </a>
              <a
                href="#"
                className="site-footer-link"
                onClick={(e) => {
                  e.preventDefault();
                  setCurrentPage("youtube");
                }}
              >
                Youtube
              </a>
              <a
                href="#"
                className="site-footer-link"
                onClick={(e) => {
                  e.preventDefault();
                  setCurrentPage("appstore");
                }}
              >
                App Store
              </a>
            </div>
            <div className="site-footer-col">
              <div className="site-footer-col-title">Community</div>
              <a
                href="https://github.com/jdavi977/Trend-Insight-Engine"
                target="_blank"
                className="site-footer-link"
              >
                Github
              </a>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
}

export default App;
