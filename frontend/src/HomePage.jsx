import { useState, useEffect } from "react";
const GAME_CATEGORY_ID = 20;
const SCIENCE_TECH_ID = 28;
const HOWTO_STYLE_CATEGORY = 26;

function HomePage() {
  const [loading, setLoading] = useState(true);
  const [weeklyData, setWeeklyData] = useState([]);

  function createCategory(id) {
    const category = weeklyData.flatMap((nestedArray) =>
      nestedArray.filter((item) => item.category === id),
    );

    const idGrouping = Object.groupBy(category, (item) => item.key);
    return idGrouping;
  }

  useEffect(() => {
    const getData = async () => {
      try {
        const response = await fetch("http://localhost:8000/get/homePage");

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setWeeklyData(data);
      } catch (error) {
        setLoading(false);
        console.log("error");
      } finally {
        setLoading(false);
      }
    };

    getData();
  }, []);

  const gameIdGrouping = createCategory(GAME_CATEGORY_ID);
  const scitechIdGrouping = createCategory(SCIENCE_TECH_ID);
  const howstyleIdGrouping = createCategory(HOWTO_STYLE_CATEGORY);

  return (
    <div>
      <p>Weekly Youtube Insights</p>
      {!loading && gameIdGrouping && (
        <div className="analytics-card">
          <div className="card-header">
            <h2>Game Category</h2>
          </div>
          <ul className="problems-list">
            {Object.entries(gameIdGrouping).map(([key, objects]) => (
              <li key={key}>
                <h3>{objects[0].title}</h3>
                {objects.map((problem, index) => (
                  <li key={index} className="problem-item">
                    <div>{problem.problems.problem}</div>
                    <div className="problem-meta">
                      <span className="pill">{problem.problems.type}</span>
                      <span className="pill">
                        👍 {problem.problems.total_likes} likes
                      </span>
                      <span className="pill">
                        Severity: {problem.problems.severity}/5
                      </span>
                      <span className="pill">
                        Frequency: {problem.problems.frequency}/5
                      </span>
                    </div>
                  </li>
                ))}
              </li>
            ))}
          </ul>
        </div>
      )}
      {!loading && scitechIdGrouping && (
        <div className="analytics-card">
          <div className="card-header">
            <h2>Game Category</h2>
          </div>
          <ul className="problems-list">
            {Object.entries(scitechIdGrouping).map(([key, objects]) => (
              <li key={key}>
                <h3>{objects[0].title}</h3>
                {objects.map((problem, index) => (
                  <li key={index} className="problem-item">
                    <div>{problem.problems.problem}</div>
                    <div className="problem-meta">
                      <span className="pill">{problem.problems.type}</span>
                      <span className="pill">
                        👍 {problem.problems.total_likes} likes
                      </span>
                      <span className="pill">
                        Severity: {problem.problems.severity}/5
                      </span>
                      <span className="pill">
                        Frequency: {problem.problems.frequency}/5
                      </span>
                    </div>
                  </li>
                ))}
              </li>
            ))}
          </ul>
        </div>
      )}
      {!loading && howstyleIdGrouping && (
        <div className="analytics-card">
          <div className="card-header">
            <h2>Game Category</h2>
          </div>
          <ul className="problems-list">
            {Object.entries(howstyleIdGrouping).map(([key, objects]) => (
              <li key={key}>
                <h3>{objects[0].title}</h3>
                {objects.map((problem, index) => (
                  <li key={index} className="problem-item">
                    <div>{problem.problems.problem}</div>
                    <div className="problem-meta">
                      <span className="pill">{problem.problems.type}</span>
                      <span className="pill">
                        👍 {problem.problems.total_likes} likes
                      </span>
                      <span className="pill">
                        Severity: {problem.problems.severity}/5
                      </span>
                      <span className="pill">
                        Frequency: {problem.problems.frequency}/5
                      </span>
                    </div>
                  </li>
                ))}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default HomePage;
