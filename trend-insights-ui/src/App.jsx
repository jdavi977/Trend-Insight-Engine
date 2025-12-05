import "./App.css";
import React, { useState } from "react";

function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [analytics, setAnalytics] = useState();

  const analyze = async () => {
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ youtubeURL: url }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      setAnalytics(await response.json());
      setLoading = false;
    } catch (error) {
      console.error("Error", error);
    }
  };

  return (
    <>
      <h1>Trend Insight Engine</h1>
      <input
        type="text"
        id="link"
        placeholder="Paste your link here..."
        onChange={(e) => setUrl(e.target.value)}
        required
      />
      <button onClick={analyze}>{loading ? "Analying..." : "Analyze"}</button>
      {analytics}
    </>
  );
}

export default App;
