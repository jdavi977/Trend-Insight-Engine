/* Home V2 — public feed of completed runs + new-run CTA. Spec §10 / issue #53.
 *
 * The v2 landing page. Lists recent `done` runs from `GET /runs` (idea text +
 * relative completed-at) and links each to its result page. A prominent
 * "Start a new run" CTA opens New Run.
 *
 * Page-level component owns all state and is the only thing that talks to the
 * backend (frontend/CONTEXT.md). Navigation uses react-router-dom: a run row
 * routes to /runs/:id, the CTA to /runs/new (ADR 2026-06-01 / issue #58).
 */
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { PrimaryButton, Spinner, ErrorBanner } from "./components/atoms";

const API_BASE = import.meta.env.VITE_API_BASE;
const FEED_LIMIT = 20;

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

// Compact relative time ("3h ago"); falls back to a date for older runs.
function relativeTime(iso) {
  if (!iso) return "";
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return "";
  const secs = Math.round((Date.now() - then.getTime()) / 1000);
  if (secs < 60) return "just now";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return then.toLocaleDateString();
}

export default function HomeV2() {
  const navigate = useNavigate();
  const location = useLocation();
  const onNewRun = () => navigate("/runs/new");
  const onOpenRun = (runId) => navigate(`/runs/${runId}`);

  // A run just reported from the Result page lands here with an ack flag; show
  // it once, then clear the history state so a refresh doesn't repeat it.
  const [reportedAck, setReportedAck] = useState(Boolean(location.state?.reported));
  useEffect(() => {
    if (location.state?.reported) {
      navigate(".", { replace: true, state: null });
    }
  }, [location.state, navigate]);

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
    <div className="tie-page tie-page--narrow">
      {reportedAck && (
        <div
          role="status"
          style={{
            marginTop: "1.25rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "1rem",
            padding: ".9rem 1.2rem",
            background: "var(--tie-surface-soft)",
            border: "1px solid var(--tie-border-strong)",
            borderRadius: "var(--tie-radius-md)",
            color: "var(--tie-fg-2)",
            fontSize: ".9rem",
          }}
        >
          <span>Thanks — that run has been reported and hidden pending review.</span>
          <button
            type="button"
            onClick={() => setReportedAck(false)}
            aria-label="Dismiss"
            style={{
              background: "none",
              border: "none",
              color: "var(--tie-fg-3)",
              cursor: "pointer",
              fontSize: "1.05rem",
              lineHeight: 1,
              padding: 0,
              flexShrink: 0,
            }}
          >
            ✕
          </button>
        </div>
      )}

      <div style={{ marginTop: "1.5rem", marginBottom: "2rem" }}>
        <div className="tie-hero-eyebrow">Trend Insight Engine</div>
        <h1 className="tie-hero-title" style={{ fontSize: "2.25rem", marginBottom: ".5rem" }}>
          Idea in, grounded gaps out.
        </h1>
        <p className="tie-hero-sub">
          Submit one idea. We read complaints across real competitors and return ranked,
          evidence-backed gaps — every one grounded in verbatim, redacted quotes.
        </p>
        <div style={{ marginTop: "1.75rem" }}>
          <PrimaryButton onClick={onNewRun}>Start a new run →</PrimaryButton>
        </div>
      </div>

      <div style={{ marginTop: "2.5rem" }}>
        <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--tie-fg-1)", margin: "0 0 1rem" }}>
          Recent runs
        </h2>

        {loading ? (
          <div style={{ display: "flex", alignItems: "center", gap: ".75rem", color: "var(--tie-fg-3)" }}>
            <Spinner size={20} /> Loading recent runs…
          </div>
        ) : error ? (
          <ErrorBanner title="Couldn’t load recent runs">{error}</ErrorBanner>
        ) : runs.length === 0 ? (
          <EmptyState onNewRun={onNewRun} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: ".75rem" }}>
            {runs.map((run) => (
              <RunRow key={run.run_id} run={run} onOpen={() => onOpenRun?.(run.run_id)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RunRow({ run, onOpen }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      type="button"
      onClick={onOpen}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        textAlign: "left",
        width: "100%",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "1rem",
        padding: "1.1rem 1.4rem",
        background: hover ? "var(--tie-surface-hover)" : "var(--tie-surface)",
        border: `1px solid ${hover ? "var(--tie-border-hover)" : "var(--tie-border)"}`,
        borderRadius: "var(--tie-radius-md)",
        cursor: "pointer",
        fontFamily: "inherit",
        transition: "background .15s ease, border-color .15s ease",
      }}
    >
      <span
        style={{
          fontSize: "1rem",
          fontWeight: 500,
          color: "var(--tie-fg-1)",
          lineHeight: 1.4,
          minWidth: 0,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {run.idea}
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: ".75rem", flexShrink: 0 }}>
        <span style={{ fontSize: ".82rem", color: "var(--tie-fg-3)", whiteSpace: "nowrap" }}>
          {relativeTime(run.completed_at)}
        </span>
        <span aria-hidden="true" style={{ color: "var(--tie-fg-3)", fontSize: "1.1rem" }}>
          →
        </span>
      </span>
    </button>
  );
}

function EmptyState({ onNewRun }) {
  return (
    <div
      style={{
        background: "var(--tie-surface-soft)",
        border: "1px solid var(--tie-border-soft)",
        borderRadius: "var(--tie-radius-md)",
        padding: "2rem 1.6rem",
        textAlign: "center",
        color: "var(--tie-fg-3)",
      }}
    >
      <p style={{ margin: "0 0 1.1rem", fontSize: ".95rem", lineHeight: 1.5 }}>
        No completed runs yet. Submit an idea to see grounded gaps here.
      </p>
      <PrimaryButton onClick={onNewRun}>Start a new run →</PrimaryButton>
    </div>
  );
}
