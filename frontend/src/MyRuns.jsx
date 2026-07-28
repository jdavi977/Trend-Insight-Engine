/* My Runs — runs started in this browser. Spec §9.4 / issue #64.
 *
 * No accounts in v1 (PRD §5), so this is a frontend-only filter of the public
 * `GET /runs` feed against the run ids collected in localStorage at submit time
 * (see runStorage.js). No backend change. A run started in another browser — or
 * one that never reached `done` and so is absent from the feed — won't appear.
 *
 * Page-level component owns all state and is the only thing that talks to the
 * backend (frontend/CONTEXT.md). Navigation uses react-router-dom.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PrimaryButton, SecondaryButton, Spinner, ErrorBanner } from "./components/atoms";
import { getMyRunIds } from "./runStorage";

const API_BASE = import.meta.env.VITE_API_BASE;
const FEED_LIMIT = 100;

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

export default function MyRuns() {
  const navigate = useNavigate();
  const onNewRun = () => navigate("/runs/new");
  const onOpenRun = (runId) => navigate(`/runs/${runId}`);

  // The set of run ids this browser remembers — read once on mount.
  const myIds = useMemo(() => new Set(getMyRunIds()), []);

  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      // Nothing to fetch if this browser has no remembered runs.
      if (myIds.size === 0) {
        setLoading(false);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/runs?limit=${FEED_LIMIT}`);
        if (!res.ok) {
          if (active) setError(await readError(res));
          return;
        }
        const data = await res.json();
        const feed = Array.isArray(data) ? data : [];
        if (active) setRuns(feed.filter((run) => myIds.has(run.run_id)));
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
  }, [myIds]);

  return (
    <div className="tie-page tie-page--narrow">
      <div style={{ marginTop: "1.5rem", marginBottom: "2rem" }}>
        <div className="tie-hero-eyebrow">Trend Insight Engine</div>
        <h1 className="tie-hero-title" style={{ fontSize: "2.25rem", marginBottom: ".5rem" }}>
          My runs
        </h1>
        <p className="tie-hero-sub">
          Runs you started in this browser. There are no accounts in v1 — this list
          lives only on this device, so clearing site data clears it.
        </p>
        <div style={{ marginTop: "1.75rem" }}>
          <PrimaryButton onClick={onNewRun}>Start a new run →</PrimaryButton>
        </div>
      </div>

      <div style={{ marginTop: "2.5rem" }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", gap: ".75rem", color: "var(--tie-fg-3)" }}>
            <Spinner size={20} /> Loading your runs…
          </div>
        ) : error ? (
          <ErrorBanner title="Couldn’t load your runs">{error}</ErrorBanner>
        ) : runs.length === 0 ? (
          <EmptyState onNewRun={onNewRun} onBrowse={() => navigate("/")} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: ".75rem" }}>
            {runs.map((run) => (
              <RunRow key={run.run_id} run={run} onOpen={() => onOpenRun(run.run_id)} />
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

function EmptyState({ onNewRun, onBrowse }) {
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
        No runs from this browser yet. Once you submit an idea and it completes, it
        shows up here.
      </p>
      <div style={{ display: "flex", gap: ".5rem", justifyContent: "center" }}>
        <PrimaryButton onClick={onNewRun}>Start a new run →</PrimaryButton>
        <SecondaryButton onClick={onBrowse}>Browse all runs</SecondaryButton>
      </div>
    </div>
  );
}
