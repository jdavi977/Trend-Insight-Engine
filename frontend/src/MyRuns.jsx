/* My Runs — runs started in this browser. Spec §9.4 / issue #64.
 *
 * No accounts in v1 (PRD §5), so this is a frontend-only filter of the public
 * `GET /runs` feed against the run ids collected in localStorage at submit time
 * (see runStorage.js). No backend change. A run started in another browser — or
 * one that never reached `done` and so is absent from the feed — won't appear.
 *
 * Rebuilt on the v2.2 design (prototype pages-myruns.jsx): a bordered list
 * whose rows carry the run id as a monospace chip, because on this page the id
 * is the thing that makes the run "yours".
 *
 * Paging is client-side (PAGE_SIZE rows at a time). It has to be: the visible
 * list is the feed *after* the localStorage filter, so a backend `before`
 * cursor page of 10 could yield anywhere from 0 to 10 of "mine". We fetch the
 * feed window once and page over the filtered result.
 *
 * Page-level component owns all state and is the only thing that talks to the
 * backend (frontend/CONTEXT.md).
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PrimaryButton, SecondaryButton, Spinner, ErrorBanner } from "./components/atoms";
import { getMyRunIds } from "./runStorage";
import { relativeTime } from "./format";

const API_BASE = import.meta.env.VITE_API_BASE;
const FEED_LIMIT = 100;
const PAGE_SIZE = 10;

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

export default function MyRuns() {
  const navigate = useNavigate();
  const onNewRun = () => navigate("/runs/new");
  const onOpenRun = (runId) => navigate(`/runs/${runId}`);

  // The set of run ids this browser remembers — read once on mount.
  const myIds = useMemo(() => new Set(getMyRunIds()), []);

  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(0);

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

  // Newest-first ordering comes from the feed; slice the window this page shows.
  const pageCount = Math.max(1, Math.ceil(runs.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const start = currentPage * PAGE_SIZE;
  const pageRuns = runs.slice(start, start + PAGE_SIZE);

  return (
    <div className="tie-page">
      <div style={{ marginTop: "1.5rem" }}>
        <div className="tie-hero-eyebrow">My runs</div>
        <h1 className="tie-hero-title" style={{ fontSize: "2rem" }}>
          Just yours.
        </h1>
        <p className="tie-hero-sub">
          We don&apos;t have accounts — “My Runs” is a frontend filter of the public feed against
          the <code style={{ fontFamily: "var(--tie-font-mono)", fontSize: ".9em" }}>run_id</code>s
          saved in your browser. Clear your local storage and these disappear.
        </p>
      </div>

      <div style={{ marginTop: "2.5rem" }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", gap: ".75rem", color: "var(--tie-fg-3)" }}>
            <Spinner size={20} /> Loading your runs…
          </div>
        ) : error ? (
          <ErrorBanner title="Couldn’t load your runs">{error}</ErrorBanner>
        ) : runs.length === 0 ? (
          <EmptyMyRuns onNewRun={onNewRun} onBrowse={() => navigate("/")} hasIds={myIds.size > 0} />
        ) : (
          <div
            style={{
              border: "1px solid var(--tie-border)",
              borderRadius: "var(--tie-radius-md)",
              overflow: "hidden",
              background: "var(--tie-surface)",
            }}
          >
            {pageRuns.map((run, i) => (
              <MyRunRow
                key={run.run_id}
                run={run}
                onOpen={() => onOpenRun(run.run_id)}
                divider={i < pageRuns.length - 1}
              />
            ))}
          </div>
        )}

        {!loading && !error && runs.length > 0 && pageCount > 1 && (
          <Pager
            page={currentPage}
            pageCount={pageCount}
            first={start + 1}
            last={start + pageRuns.length}
            total={runs.length}
            onPrev={() => setPage(currentPage - 1)}
            onNext={() => setPage(currentPage + 1)}
          />
        )}
      </div>
    </div>
  );
}

// Prev/next over the filtered list. Rendered only when there's more than one
// page, so the empty and single-page states stay uncluttered.
function Pager({ page, pageCount, first, last, total, onPrev, onNext }) {
  return (
    <div
      style={{
        marginTop: "1rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "1rem",
        flexWrap: "wrap",
      }}
    >
      <div style={{ color: "var(--tie-fg-3)", fontSize: ".85rem" }}>
        Showing {first}–{last} of {total} · page {page + 1} of {pageCount}
      </div>
      <div style={{ display: "flex", gap: ".5rem" }}>
        <SecondaryButton size="sm" onClick={onPrev} disabled={page === 0}>
          ← Previous
        </SecondaryButton>
        <SecondaryButton size="sm" onClick={onNext} disabled={page >= pageCount - 1}>
          Next →
        </SecondaryButton>
      </div>
    </div>
  );
}

function MyRunRow({ run, onOpen, divider }) {
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
        padding: "1.1rem 1.4rem",
        background: hover ? "var(--tie-surface-hover)" : "var(--tie-surface)",
        border: "none",
        borderBottom: divider ? "1px solid var(--tie-divider)" : "none",
        cursor: "pointer",
        font: "inherit",
        color: "inherit",
        display: "grid",
        gridTemplateColumns: "minmax(0,1fr) auto auto",
        gap: "1.5rem",
        alignItems: "center",
        transition: "background .15s ease",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: ".78rem", color: "var(--tie-fg-3)", marginBottom: 4 }}>
          {relativeTime(run.completed_at)}
        </div>
        <div style={{ fontSize: "1rem", color: "var(--tie-fg-1)", fontWeight: 500, lineHeight: 1.4, textWrap: "pretty" }}>
          {run.idea}
        </div>
      </div>
      <code
        style={{
          fontFamily: "var(--tie-font-mono)",
          color: "var(--tie-fg-3)",
          fontSize: ".8rem",
          background: "var(--tie-surface-muted)",
          padding: "2px 8px",
          borderRadius: 4,
          whiteSpace: "nowrap",
        }}
      >
        {run.run_id}
      </code>
      <span
        aria-hidden="true"
        style={{ color: "var(--tie-fg-1)", opacity: hover ? 1 : 0.5, transition: "opacity .15s ease", fontSize: 18 }}
      >
        →
      </span>
    </button>
  );
}

// Two distinct empties: this browser has never started a run, or it has but
// none of those runs has reached `done` yet (the feed only carries completed
// runs, so an in-flight run is remembered locally but invisible here).
function EmptyMyRuns({ onNewRun, onBrowse, hasIds }) {
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
        {hasIds ? "Nothing finished yet." : "No runs yet."}
      </div>
      <div style={{ color: "var(--tie-fg-3)", fontSize: ".92rem", marginBottom: "1.25rem", lineHeight: 1.5 }}>
        {hasIds
          ? "You've started a run from this browser, but none has completed. Runs appear here once they reach done."
          : "Start a run and we'll remember its ID locally."}
      </div>
      <div style={{ display: "flex", gap: ".5rem", justifyContent: "center", flexWrap: "wrap" }}>
        <PrimaryButton size="sm" onClick={onNewRun}>
          Start a run
        </PrimaryButton>
        <SecondaryButton size="sm" onClick={onBrowse}>
          Browse all runs
        </SecondaryButton>
      </div>
    </div>
  );
}
