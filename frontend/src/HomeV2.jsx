/* Home V2 — public feed of completed runs + new-run CTA. Spec §10 / issue #53.
 *
 * The v2 landing page, rebuilt on the v2.2 design (prototype pages-home.jsx,
 * "list" feed variant): a two-column hero over a bordered feed list. Lists
 * recent `done` runs from `GET /runs` and links each to its result page.
 *
 * `GET /runs` returns `RunFeedItem` — run_id, idea, completed_at and nothing
 * else (app/schemas/runs.py). The prototype's feed rows also showed a signal
 * dot, a category and the top gap; those aren't in the feed payload, and the
 * whole point of the feed is that gap content lives behind the link, so the row
 * carries idea + time only. Adding them would mean widening the feed endpoint.
 *
 * Page-level component owns all state and is the only thing that talks to the
 * backend (frontend/CONTEXT.md).
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PrimaryButton,
  GhostButton,
  Pill,
  Spinner,
  ErrorBanner,
  MetricCell,
} from "./components/atoms";
import { relativeTime } from "./format";

const API_BASE = import.meta.env.VITE_API_BASE;
const FEED_LIMIT = 5;
const REPO_URL = "https://github.com/jdavi977/Trend-Insight-Engine";

async function readError(res) {
  let detail = "";
  try {
    const body = await res.json();
    detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? body);
  } catch {
    detail = res.statusText;
  }
  return detail || `Request failed (${res.status}).`;
}

export default function HomeV2() {
  const navigate = useNavigate();
  const onNewRun = () => navigate("/runs/new");
  const onOpenRun = (runId) => navigate(`/runs/${runId}`);

  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/runs?limit=${FEED_LIMIT}`);
        if (!res.ok) {
          if (active) setError(await readError(res));
          return;
        }
        const data = await res.json();
        if (active) setRuns(Array.isArray(data) ? data : []);
      } catch (err) {
        if (active) setError(err?.message || "Could not reach the engine. Is the backend running?");
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="tie-page tie-page--wide">
      <HomeHero onNewRun={onNewRun} />

      <div style={{ marginTop: "3rem" }}>
        <FeedHeader />
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", gap: ".75rem", color: "var(--tie-fg-3)" }}>
            <Spinner size={20} /> Loading recent runs…
          </div>
        ) : error ? (
          <ErrorBanner title="Couldn’t load recent runs">{error}</ErrorBanner>
        ) : runs.length === 0 ? (
          <EmptyState onNewRun={onNewRun} />
        ) : (
          <div
            style={{
              border: "1px solid var(--tie-border)",
              borderRadius: "var(--tie-radius-md)",
              overflow: "hidden",
              background: "var(--tie-surface)",
            }}
          >
            {runs.map((run, i) => (
              <FeedRow
                key={run.run_id}
                run={run}
                onOpen={() => onOpenRun(run.run_id)}
                divider={i < runs.length - 1}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Hero ───────────────────────────────────────────────────────
function HomeHero({ onNewRun }) {
  return (
    <section
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr)",
        gap: "3rem",
        alignItems: "center",
        paddingTop: "1.5rem",
      }}
    >
      <div>
        <div className="tie-hero-eyebrow">Idea → evidence-backed gaps</div>
        <h1 className="tie-hero-title">
          Submit an idea.
          <br />
          Get the complaints
          <br />
          its competitors can&apos;t hide.
        </h1>
        <p className="tie-hero-sub">
          Trend Insight Engine reads public reviews and comments across the apps and videos your
          idea would compete with, and returns a ranked list of unaddressed pain — every gap
          anchored to verbatim quotes.
        </p>
        <div style={{ display: "flex", gap: ".75rem", marginTop: "1.75rem", alignItems: "center" }}>
          <PrimaryButton size="lg" onClick={onNewRun}>
            Start a run →
          </PrimaryButton>
          <GhostButton onClick={() => window.open(`${REPO_URL}#readme`, "_blank", "noreferrer")}>
            How it works
          </GhostButton>
        </div>

        {/* Only figures the app can actually stand behind. The prototype's
            "≈ 4 min p50" and "10 sources per run" were mock copy — nothing
            measures run duration, and source count varies per pre-flight. */}
        <div style={{ marginTop: "2rem", display: "flex", gap: "2rem", flexWrap: "wrap" }}>
          <MetricCell label="Sources read" value="App Store + YouTube" hint="reviews and comments" />
          <MetricCell label="Citations per gap" value="≥ 2" hint="or the gap is rejected" />
        </div>
      </div>

      <HeroIllustration />
    </section>
  );
}

// A stack of two "evidence cards" — a literal sample of what a result looks
// like, in the product's own components rather than a decorative graphic.
function HeroIllustration() {
  const cardBase = {
    position: "absolute",
    background: "var(--tie-surface)",
    border: "1px solid var(--tie-border)",
    borderRadius: "var(--tie-radius-lg)",
    boxShadow: "var(--tie-shadow-card)",
    padding: "1.25rem",
  };
  const eyebrow = {
    fontSize: ".7rem",
    letterSpacing: ".08em",
    textTransform: "uppercase",
    color: "var(--tie-fg-3)",
    fontWeight: 600,
    marginBottom: 8,
  };
  const title = {
    fontSize: "1rem",
    fontWeight: 600,
    color: "var(--tie-fg-1)",
    lineHeight: 1.35,
    marginBottom: 10,
  };
  const quote = {
    fontFamily: "var(--tie-font-serif)",
    fontSize: ".95rem",
    color: "var(--tie-fg-1)",
    paddingLeft: 10,
    lineHeight: 1.5,
  };
  return (
    <div aria-hidden="true" style={{ position: "relative", height: 360 }}>
      <div style={{ ...cardBase, inset: "20px 60px 60px 0", transform: "rotate(-2deg)" }}>
        <div style={eyebrow}>Gap 02 · 2 of 4 competitors</div>
        <div style={title}>Conflict resolution destroys formatting</div>
        <div style={{ ...quote, borderLeft: "2px solid var(--tie-border)" }}>
          “Lost all the toggle structure I’d spent an hour building.”
        </div>
      </div>
      <div style={{ ...cardBase, inset: "60px 0 20px 60px", transform: "rotate(2.5deg)" }}>
        <div style={eyebrow}>Gap 01 · 4 of 4 competitors</div>
        <div style={title}>Edits made offline silently dropped</div>
        <div style={{ ...quote, borderLeft: "2px solid var(--tie-fg-1)" }}>
          “Wrote on a flight for 3 hours… it was gone. Not even a draft.”
        </div>
        <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
          <Pill>23 mentions</Pill>
          <Pill>5 apps</Pill>
          <Pill muted>12 quotes</Pill>
        </div>
      </div>
    </div>
  );
}

// ── Feed ───────────────────────────────────────────────────────
function FeedHeader() {
  return (
    <div style={{ marginBottom: "1.25rem" }}>
      <h2 style={{ fontSize: "var(--tie-fs-h3)", fontWeight: 700, color: "var(--tie-fg-1)", margin: 0 }}>
        Recent runs
      </h2>
      <p style={{ color: "var(--tie-fg-3)", fontSize: ".95rem", margin: ".35rem 0 0" }}>
        Public by URL. Idea text and timestamp only — gap content lives behind the link.
      </p>
    </div>
  );
}

function FeedRow({ run, onOpen, divider }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      type="button"
      onClick={onOpen}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        width: "100%",
        textAlign: "left",
        padding: "1.1rem 1.25rem",
        background: hover ? "var(--tie-surface-hover)" : "var(--tie-surface)",
        border: "none",
        borderBottom: divider ? "1px solid var(--tie-border)" : "none",
        cursor: "pointer",
        font: "inherit",
        color: "inherit",
        transition: "background .15s ease",
        display: "grid",
        gridTemplateColumns: "minmax(0,1fr) auto",
        gap: "1.5rem",
        alignItems: "center",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: ".78rem", color: "var(--tie-fg-3)", marginBottom: 6 }}>
          {relativeTime(run.completed_at)}
        </div>
        <div
          style={{
            fontSize: "1.1rem",
            fontWeight: 600,
            color: "var(--tie-fg-1)",
            lineHeight: 1.4,
            textWrap: "pretty",
          }}
        >
          {run.idea}
        </div>
      </div>
      <span
        aria-hidden="true"
        style={{
          fontSize: 18,
          color: "var(--tie-fg-1)",
          opacity: hover ? 1 : 0.5,
          transition: "opacity .15s ease",
        }}
      >
        →
      </span>
    </button>
  );
}

function EmptyState({ onNewRun }) {
  return (
    <div
      style={{
        border: "1px dashed var(--tie-border-strong)",
        borderRadius: "var(--tie-radius-md)",
        padding: "3rem 2rem",
        textAlign: "center",
        background: "var(--tie-surface-soft)",
      }}
    >
      <div style={{ fontSize: "1rem", color: "var(--tie-fg-1)", fontWeight: 600, marginBottom: 6 }}>
        No completed runs yet.
      </div>
      <div style={{ color: "var(--tie-fg-3)", fontSize: ".92rem", marginBottom: "1.25rem" }}>
        Submit an idea to see grounded gaps here.
      </div>
      <PrimaryButton size="sm" onClick={onNewRun}>
        Start a run
      </PrimaryButton>
    </div>
  );
}
