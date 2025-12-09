import "./App.css";
import { useState } from "react";
import YouTubePage from "./YouTubePage";
import AppStorePage from "./AppStorePage";

function App() {
  const [currentPage, setCurrentPage] = useState("youtube");

  return (
    <div>
      <nav className="page-nav">
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
    </div>
  );
}

export default App;
