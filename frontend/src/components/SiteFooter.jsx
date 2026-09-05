/* Site footer — what the product is, and the run links again.
 *
 * Ported from the v2.2 prototype chrome.jsx. The blurb carries the framing the
 * whole product rests on ("decision support — not a verdict", PRD §7.6), so it
 * stays on every page rather than only the result.
 */
import { Link } from "react-router-dom";
import { LogoMark } from "./atoms";

const REPO_URL = "https://github.com/jdavi977/Trend-Insight-Engine";

export default function SiteFooter() {
  return (
    <footer className="tie-footer">
      <div className="tie-footer-blurb">
        <div style={{ display: "flex", alignItems: "center", gap: ".6rem", color: "var(--tie-fg-1)", fontWeight: 600, fontSize: "1rem" }}>
          <LogoMark />
          <span>Trend Insight Engine</span>
        </div>
        <div style={{ fontSize: ".88rem", color: "var(--tie-fg-3)", lineHeight: 1.55, textWrap: "pretty" }}>
          A first pass on public complaint surfaces for an idea. Decision support — not a verdict.
        </div>
      </div>

      <div className="tie-footer-cols">
        <div className="tie-footer-col">
          <div className="tie-footer-col-title">Run</div>
          <Link className="tie-footer-link" to="/runs/new">Start a run</Link>
          <Link className="tie-footer-link" to="/">Recent runs</Link>
          <Link className="tie-footer-link" to="/runs/mine">My runs</Link>
        </div>
        <div className="tie-footer-col">
          <div className="tie-footer-col-title">About</div>
          <a className="tie-footer-link" href={REPO_URL} target="_blank" rel="noreferrer">
            GitHub
          </a>
          <a className="tie-footer-link" href={`${REPO_URL}#readme`} target="_blank" rel="noreferrer">
            How it works
          </a>
        </div>
      </div>
    </footer>
  );
}
