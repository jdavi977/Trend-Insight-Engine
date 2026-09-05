import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import "./App.css";
import SiteHeader from "./components/SiteHeader";
import SiteFooter from "./components/SiteFooter";
import HomeV2 from "./HomeV2";
import NewRun from "./NewRun";
import RunResult from "./RunResult";
import MyRuns from "./MyRuns";
import { getMyRunIds } from "./runStorage";

/* App shell for the v2.2 design: sticky header, page area, footer.
 *
 * Replaces the slice-1 fixed sidebar. Routing is unchanged — real client-side
 * routing via react-router-dom (ADR 2026-06-01 / issue #58); only the chrome
 * around <Routes> moved.
 */
function App() {
  const { pathname } = useLocation();

  // The header's "My Runs" badge counts the run ids this browser remembers.
  // New Run writes that list at submit time, so it is read straight through on
  // render (the shell only re-renders on navigation) rather than mirrored into
  // state that would then need syncing.
  const myRunsCount = getMyRunIds().length;

  // Each page is its own document; land at the top of it, not wherever the
  // previous page was scrolled to.
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [pathname]);

  return (
    <div className="tie-app-shell">
      <SiteHeader myRunsCount={myRunsCount} />

      <main className="tie-main">
        <Routes>
          <Route path="/" element={<HomeV2 />} />
          <Route path="/runs/new" element={<NewRun />} />
          {/* Static `/runs/mine` outranks `/runs/:id` in react-router's match
              ranking, so My Runs resolves before the dynamic run route. */}
          <Route path="/runs/mine" element={<MyRuns />} />
          <Route path="/runs/:id" element={<RunResult />} />
        </Routes>
      </main>

      <SiteFooter />
    </div>
  );
}

export default App;
