/* Run Status / Result — stable view of one run, polled live. Spec §10 / issue #52.
 *
 * Opened after a run is approved (status `running`). Polls `GET /runs/:id`
 * every 5s while the run is non-terminal (pending / running / preflight_ready)
 * and stops once `done` or `failed`. Three render states:
 *   - running  → progress shell ("Running across N sources…")
 *   - done     → signal banner, coverage line, optional idea_match card, ranked
 *                gap list with verbatim quotes inline + citation count per gap
 *   - failed   → failure_reason surfaced (never a silent blank)
 *
 * Page-level component owns all state and is the only thing that talks to the
 * backend (frontend/CONTEXT.md). Quotes arrive as a { quote_id: Quote } map and
 * are looked up per gap via evidence_quote_ids.
 *
 * The run id comes from the /runs/:id route (ADR 2026-06-01 / issue #58), so a
 * pasted URL loads the run directly in a fresh tab (US-4, US-5).
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  PrimaryButton,
  Pill,
  Spinner,
  ErrorBanner,
  SignalBadge,
  SourceIcon,
} from "./components/atoms";

const API_BASE = import.meta.env.VITE_API_BASE;
const POLL_MS = 5000; // spec open question #1 — confirmed 5s.

// Non-terminal lifecycle states keep the poll alive; `done`/`failed` stop it.
const POLLING_STATES = new Set(["pending", "preflight_ready", "running"]);

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

export default function RunResult() {
  const { id: runId } = useParams();
  const navigate = useNavigate();
  const onNewRun = () => navigate("/runs/new");

  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!runId) return undefined;
    let active = true;
    let timer;

    async function poll() {
      try {
        const res = await fetch(`${API_BASE}/runs/${runId}`);
        if (!res.ok) {
          if (active) {
            setError(await readError(res));
            setLoading(false);
          }
          return;
        }
        const data = await res.json();
        if (!active) return;
        setRun(data);
        setError("");
        setLoading(false);
        if (POLLING_STATES.has(data.status)) {
          timer = setTimeout(poll, POLL_MS);
        }
      } catch (err) {
        if (!active) return;
        // Transient fetch failure — surface it but keep trying so a brief
        // backend blip doesn't strand a running page.
        setError(err?.message || "Lost contact with the engine. Retrying…");
        setLoading(false);
        timer = setTimeout(poll, POLL_MS);
      }
    }

    poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [runId]);

  if (loading && !run) {
    return (
      <Shell eyebrow="Run" title="Loading run…">
        <div style={{ display: "flex", alignItems: "center", gap: ".75rem", color: "var(--tie-fg-3)" }}>
          <Spinner size={20} /> Fetching the latest state.
        </div>
      </Shell>
    );
  }

  if (!run) {
    return (
      <Shell eyebrow="Run" title="Couldn’t load this run.">
        <ErrorBanner title="Run unavailable">{error || "No run data was returned."}</ErrorBanner>
        {onNewRun && (
          <div style={{ marginTop: "1.5rem" }}>
            <PrimaryButton onClick={onNewRun}>Start a new run →</PrimaryButton>
          </div>
        )}
      </Shell>
    );
  }

  if (run.status === "failed") {
    return <FailedState run={run} onNewRun={onNewRun} />;
  }

  if (run.status === "done") {
    return <DoneState run={run} onNewRun={onNewRun} />;
  }

  // pending / preflight_ready / running
  return <RunningState run={run} error={error} />;
}

// ── Page shell ─────────────────────────────────────────────────
function Shell({ eyebrow, title, sub, children }) {
  return (
    <div className="tie-page tie-page--narrow">
      <div style={{ marginTop: "1.5rem", marginBottom: "2rem" }}>
        <div className="tie-hero-eyebrow">{eyebrow}</div>
        <h1 className="tie-hero-title" style={{ fontSize: "2rem", marginBottom: sub ? ".5rem" : 0 }}>
          {title}
        </h1>
        {sub && <p className="tie-hero-sub">{sub}</p>}
      </div>
      {children}
    </div>
  );
}

// ── Running ────────────────────────────────────────────────────
function RunningState({ run, error }) {
  const total = run.competitors?.length ?? 0;
  return (
    <Shell eyebrow="Run · in progress" title="Reading across your competitors…">
      <div
        style={{
          background: "var(--tie-surface-soft)",
          border: "1px solid var(--tie-border-soft)",
          borderRadius: "var(--tie-radius-md)",
          padding: "1.5rem 1.6rem",
          display: "flex",
          alignItems: "center",
          gap: "1.1rem",
        }}
      >
        <Spinner size={28} />
        <div>
          <div style={{ fontWeight: 600, color: "var(--tie-fg-1)", fontSize: "1.05rem" }}>
            {total > 0 ? `Running across ${total} source${total === 1 ? "" : "s"}…` : "Running…"}
          </div>
          <p style={{ margin: ".3rem 0 0", color: "var(--tie-fg-3)", fontSize: ".9rem", lineHeight: 1.5 }}>
            Extracting complaints per source, then synthesising grounded gaps. This page updates
            automatically — you can leave the tab open.
          </p>
        </div>
      </div>

      <p style={{ margin: "1rem 0 0", fontSize: ".82rem", color: "var(--tie-fg-3)" }}>
        Idea: <span style={{ color: "var(--tie-fg-2)" }}>“{run.idea}”</span>
      </p>

      {error && (
        <div style={{ marginTop: "1.25rem" }}>
          <ErrorBanner title="Reconnecting…" icon="↻">{error}</ErrorBanner>
        </div>
      )}
    </Shell>
  );
}

// ── Failed ─────────────────────────────────────────────────────
function FailedState({ run, onNewRun }) {
  return (
    <Shell eyebrow="Run · failed" title="This run didn’t finish.">
      <ErrorBanner title="The run failed">
        {run.failure_reason || "No failure reason was reported by the backend."}
      </ErrorBanner>
      <p style={{ margin: "1rem 0 0", fontSize: ".82rem", color: "var(--tie-fg-3)" }}>
        Idea: <span style={{ color: "var(--tie-fg-2)" }}>“{run.idea}”</span>
      </p>
      {onNewRun && (
        <div style={{ marginTop: "1.5rem" }}>
          <PrimaryButton onClick={onNewRun}>Start a new run →</PrimaryButton>
        </div>
      )}
    </Shell>
  );
}

// ── Done ───────────────────────────────────────────────────────
function DoneState({ run, onNewRun }) {
  const gaps = run.gaps ?? [];
  const quotes = run.quotes ?? {};
  return (
    <div className="tie-page tie-page--narrow">
      <div style={{ marginTop: "1.5rem", marginBottom: "1.75rem" }}>
        <div className="tie-hero-eyebrow">Run · complete</div>
        <h1 className="tie-hero-title" style={{ fontSize: "2rem", marginBottom: ".5rem" }}>
          {gaps.length} candidate gap{gaps.length === 1 ? "" : "s"}, grounded in real complaints.
        </h1>
        <p style={{ color: "var(--tie-fg-3)", fontSize: ".95rem", margin: 0 }}>
          Idea: <span style={{ color: "var(--tie-fg-1)", fontWeight: 500 }}>“{run.idea}”</span>
          {run.category && <span> · {run.category}</span>}
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <SignalBanner signal={run.signal_strength} reasoning={run.signal_reasoning} />
        {run.coverage && <CoverageLine coverage={run.coverage} />}

        {run.idea_match && (
          <IdeaMatchCard match={run.idea_match} targetGap={run.target_gap} quotes={quotes} />
        )}

        {gaps.length === 0 ? (
          <div
            style={{
              background: "var(--tie-surface-soft)",
              border: "1px solid var(--tie-border-soft)",
              borderRadius: "var(--tie-radius-md)",
              padding: "1.5rem",
              color: "var(--tie-fg-3)",
              fontSize: ".95rem",
            }}
          >
            No gaps cleared the grounding bar (≥2 citations) for this idea. Signal may be thin —
            consider interviews or community digging.
          </div>
        ) : (
          gaps.map((gap, i) => <GapCard key={gap.gap_id} gap={gap} rank={i + 1} quotes={quotes} />)
        )}
      </div>

      {onNewRun && (
        <div style={{ marginTop: "2.5rem" }}>
          <PrimaryButton onClick={onNewRun}>Start another run →</PrimaryButton>
        </div>
      )}
    </div>
  );
}

function SignalBanner({ signal, reasoning }) {
  const isLow = signal === "low";
  return (
    <div
      style={{
        background: isLow ? "var(--tie-error-bg)" : "var(--tie-surface-soft)",
        border: `1px solid ${isLow ? "var(--tie-error-border)" : "var(--tie-border-soft)"}`,
        borderRadius: "var(--tie-radius-md)",
        padding: "1.25rem 1.4rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: ".5rem", gap: 8 }}>
        <span style={{ fontSize: ".72rem", letterSpacing: ".08em", textTransform: "uppercase", fontWeight: 600, color: isLow ? "var(--tie-error-fg)" : "var(--tie-fg-3)" }}>
          Signal strength
        </span>
        <SignalBadge strength={signal} />
      </div>
      {reasoning && (
        <p style={{ margin: 0, color: isLow ? "var(--tie-error-fg)" : "var(--tie-fg-2)", lineHeight: 1.55, fontSize: ".95rem", textWrap: "pretty" }}>
          {reasoning}
        </p>
      )}
    </div>
  );
}

function CoverageLine({ coverage }) {
  const { quotes_retrieved = 0, quotes_cited = 0, citation_ratio = 0 } = coverage;
  const pct = Math.round((citation_ratio ?? 0) * 100);
  return (
    <p style={{ margin: 0, fontSize: ".88rem", color: "var(--tie-fg-3)" }}>
      <strong style={{ color: "var(--tie-fg-2)", fontWeight: 600 }}>{quotes_cited}</strong> of{" "}
      <strong style={{ color: "var(--tie-fg-2)", fontWeight: 600 }}>{quotes_retrieved}</strong> retrieved
      quotes were cited ({pct}%).
    </p>
  );
}

const IDEA_MATCH_LABEL = {
  matches: "Matches your target gap",
  partial: "Partially matches your target gap",
  no_match: "Doesn’t match your target gap",
};

function IdeaMatchCard({ match, targetGap, quotes }) {
  const cited = (match.evidence_quote_ids ?? []).map((id) => quotes[id]).filter(Boolean);
  return (
    <div
      style={{
        background: "var(--tie-surface)",
        border: "1px solid var(--tie-border-strong)",
        borderRadius: "var(--tie-radius-md)",
        padding: "1.25rem 1.4rem",
      }}
    >
      <div style={{ fontSize: ".72rem", letterSpacing: ".08em", textTransform: "uppercase", fontWeight: 600, color: "var(--tie-fg-3)", marginBottom: ".5rem" }}>
        Your target gap
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: ".6rem", flexWrap: "wrap" }}>
        <span style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--tie-fg-1)" }}>
          {IDEA_MATCH_LABEL[match.verdict] ?? match.verdict}
        </span>
      </div>
      {targetGap && (
        <p style={{ margin: ".5rem 0 0", color: "var(--tie-fg-2)", fontSize: ".92rem", lineHeight: 1.5 }}>
          “{targetGap}”
        </p>
      )}
      {cited.length > 0 && (
        <div style={{ marginTop: ".9rem" }}>
          <QuoteList quotes={cited} />
        </div>
      )}
    </div>
  );
}

// Severity 1..5 → label + color (matches the SignalDot palette tone).
function severityMeta(severity) {
  if (severity >= 4) return { label: `Severity ${severity}/5`, color: "#b91c1c", bg: "var(--tie-error-bg)", border: "var(--tie-error-border)" };
  if (severity === 3) return { label: `Severity ${severity}/5`, color: "#ca8a04", bg: "rgba(202,138,4,.10)", border: "rgba(202,138,4,.30)" };
  return { label: `Severity ${severity}/5`, color: "#16a34a", bg: "rgba(22,163,74,.10)", border: "rgba(22,163,74,.30)" };
}

function GapCard({ gap, rank, quotes }) {
  const sev = severityMeta(gap.severity);
  const citationCount = gap.evidence_quote_ids?.length ?? 0;
  const cited = (gap.evidence_quote_ids ?? []).map((id) => quotes[id]).filter(Boolean);
  const present = gap.competitors_present ?? [];

  return (
    <div
      style={{
        background: "var(--tie-surface)",
        border: "1px solid var(--tie-border)",
        borderRadius: "var(--tie-radius-md)",
        overflow: "hidden",
      }}
    >
      <div style={{ padding: "1.2rem 1.4rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "flex-start" }}>
          <div style={{ display: "flex", gap: ".75rem", alignItems: "flex-start", minWidth: 0 }}>
            <span style={{ fontSize: ".95rem", fontWeight: 700, color: "var(--tie-fg-3)", lineHeight: 1.4, flexShrink: 0 }}>
              #{rank}
            </span>
            <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700, color: "var(--tie-fg-1)", lineHeight: 1.4, textWrap: "pretty" }}>
              {gap.gap}
            </h3>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: ".4rem", flexShrink: 0 }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "4px 10px",
                borderRadius: "var(--tie-radius-pill)",
                background: sev.bg,
                border: `1px solid ${sev.border}`,
                color: sev.color,
                fontSize: "var(--tie-fs-micro)",
                fontWeight: 700,
                whiteSpace: "nowrap",
              }}
            >
              {sev.label}
            </span>
            <Pill muted style={{ whiteSpace: "nowrap" }}>
              {citationCount} citation{citationCount === 1 ? "" : "s"}
            </Pill>
          </div>
        </div>

        <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap", marginTop: ".85rem", alignItems: "center" }}>
          <Pill muted>{gap.frequency} mention{gap.frequency === 1 ? "" : "s"}</Pill>
          <Pill muted>{gap.spread} competitor{gap.spread === 1 ? "" : "s"}</Pill>
          {present.map((name) => (
            <Pill key={name}>{name}</Pill>
          ))}
        </div>
      </div>

      {cited.length > 0 && (
        <div style={{ borderTop: "1px solid var(--tie-divider)", background: "var(--tie-surface-soft)", padding: "1rem 1.4rem" }}>
          <div style={{ fontSize: ".72rem", letterSpacing: ".06em", textTransform: "uppercase", fontWeight: 600, color: "var(--tie-fg-3)", marginBottom: ".7rem" }}>
            Verbatim complaints
          </div>
          <QuoteList quotes={cited} />
        </div>
      )}
    </div>
  );
}

function QuoteList({ quotes }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: ".7rem" }}>
      {quotes.map((q) => (
        <blockquote
          key={q.quote_id}
          style={{
            margin: 0,
            padding: ".6rem .85rem",
            borderLeft: "3px solid var(--tie-border-strong)",
            background: "var(--tie-surface)",
            borderRadius: "0 var(--tie-radius-sm) var(--tie-radius-sm) 0",
            fontSize: ".92rem",
            color: "var(--tie-fg-2)",
            lineHeight: 1.5,
          }}
        >
          <span style={{ textWrap: "pretty" }}>“{q.text_redacted}”</span>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: ".45rem", fontSize: ".78rem", color: "var(--tie-fg-3)" }}>
            <SourceIcon source={q.source} size={13} />
            <span>{q.source === "youtube" ? "YouTube" : "App Store"}</span>
            {q.like_count > 0 && (
              <>
                <span aria-hidden="true">·</span>
                <span>{q.like_count} like{q.like_count === 1 ? "" : "s"}</span>
              </>
            )}
          </div>
        </blockquote>
      ))}
    </div>
  );
}
