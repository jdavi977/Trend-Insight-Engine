import "./App.css";
import { useState } from "react";

function App() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const analyze = async () => {
    setLoading(true);

    // TODO: Create a function to check pasted link first
    // try to send link to fastAPI
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
    </>
  );
}

export default App;
