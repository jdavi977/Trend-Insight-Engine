/* Sticky site header — brand, primary nav, "Start a run" CTA.
 *
 * Ported from the v2.2 prototype chrome.jsx. Nav is Home / New Run / My Runs;
 * the v1 YouTube, App Store and Insights tabs left with the legacy pages.
 *
 * The prototype drove the active tab from an `currentPage` prop; here NavLink
 * derives it from the route (ADR 2026-06-01 / issue #58), so /runs/:id and
 * /runs/new both light up "New Run" via the `/runs` prefix without the shell
 * tracking any state. Hover / active styling lives in App.css.
 */
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { PrimaryButton, LogoMark } from "./atoms";

export default function SiteHeader({ myRunsCount = 0 }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  // A run being watched or read is still part of the "New Run" journey, so the
  // dynamic /runs/:id route keeps that tab lit — but not /runs/mine, which is
  // its own tab.
  const runFlowActive = pathname.startsWith("/runs") && pathname !== "/runs/mine";

  return (
    <header className="tie-header">
      <NavLink to="/" className="tie-brand">
        <LogoMark size={9} />
        <span>Trend Insight Engine</span>
      </NavLink>

      <nav className="tie-nav" aria-label="Primary">
        <NavLink to="/" end className={({ isActive }) => `tie-nav-link${isActive ? " active" : ""}`}>
          Home
        </NavLink>
        <NavLink to="/runs/new" className={`tie-nav-link${runFlowActive ? " active" : ""}`}>
          New Run
        </NavLink>
        <NavLink to="/runs/mine" className={({ isActive }) => `tie-nav-link${isActive ? " active" : ""}`}>
          My Runs
          {myRunsCount > 0 && <span className="tie-nav-badge">{myRunsCount}</span>}
        </NavLink>
        {/* Not a link inside a link: a button navigating on click keeps the
            markup valid while matching the prototype's CTA treatment. */}
        <PrimaryButton className="tie-header-cta" size="sm" onClick={() => navigate("/runs/new")}>
          Start a run
        </PrimaryButton>
      </nav>
    </header>
  );
}
