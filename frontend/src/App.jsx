import "./App.css";
import { useState } from "react";
import YouTubePage from "./YouTubePage";
import AppStorePage from "./AppStorePage";
import HomePage from "./HomePage";

function App() {
  const [currentPage, setCurrentPage] = useState("homepage");

  return (
    <div>
      <nav className="page-nav">
        <button
          className={`nav-button ${currentPage === "homepage" ? "active" : ""}`}
          onClick={() => setCurrentPage("homepage")}
        >
          Home
        </button>
        <button
          className={`nav-button ${currentPage === "youtube" ? "active" : ""}`}
          onClick={() => setCurrentPage("youtube")}
        >
          YouTube
        </button>
        <button
          className={`nav-button ${currentPage === "appstore" ? "active" : ""}`}
          onClick={() => setCurrentPage("appstore")}
        >
          App Store
        </button>
      </nav>
      {currentPage === "youtube" && <YouTubePage />}
      {currentPage === "appstore" && <AppStorePage />}
      {currentPage === "homepage" && <HomePage />}
    </div>
  );
}

export default App;
