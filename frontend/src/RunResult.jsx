/* Run Status / Result — stable view of one run, polled live. Spec §10 / issue #52.
 *
 * Opened after a run is approved (status `running`). Polls `GET /runs/:id`
 * every 5s while the run is non-terminal (pending / running / preflight_ready)
 * and stops once `done` or `failed`. Three render states:
 *   - running  → progress shell ("Running across N sources…")
 *   - done     → signal banner, coverage line, ranked gap list with verbatim
 *                quotes inline + citation count per gap
 *   - failed   → failure_reason surfaced (never a silent blank)
 *
 * Page-level component owns all state and is the only thing that talks to the
 * backend (frontend/CONTEXT.md). Quotes arrive as a { quote_id: Quote } map and
 * are looked up per gap via evidence_quote_ids.
 *
 * The run id comes from the /runs/:id route (ADR 2026-06-01 / issue #58), so a
 * pasted URL loads the run directly in a fresh tab (US-4, US-5).
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  PrimaryButton,
  SecondaryButton,
  Pill,
  Spinner,
  ErrorBanner,
  SignalBadge,
  SourceIcon,
  TextInput,
} from "./components/atoms";

const API_BASE = import.meta.env.VITE_API_BASE;
const POLL_MS = 5000; // spec open question #1 — confirmed 5s.
const FEEDBACK_DEBOUNCE_MS = 800; // batch rapid thumbs-up toggles into one append-only write.

// Human-readable copy per `failure_reason` enum (slice 2 §5.3 / §9.2). Never
// surface the raw enum string — each terminal cause gets a clear explanation.
const FAILURE_COPY = {
  server_restart: {
    title: "This run was interrupted.",
    message:
      "The engine restarted while this run was still in progress, so it couldn’t finish. Nothing was lost on your end — start a fresh run to try again.",
  },
  sources_below_threshold: {
    title: "Too many sources failed to load.",
    message:
      "Fewer than 70% of the competitor sources came back, so we couldn’t synthesise gaps you could trust. Source errors are often transient — try the run again in a few minutes.",
  },
  budget_exhausted: {
    title: "Daily analysis budget reached.",
    message:
      "The engine hit its daily budget cap, so this run couldn’t complete. Please try again tomorrow when the budget resets.",
  },
  internal_error: {
    title: "Something went wrong on our end.",
    message:
      "An unexpected error stopped this run before it finished. This one’s on us — start a new run to try again.",
  },
};

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
    return <DoneState run={run} runId={runId} navigate={navigate} onNewRun={onNewRun} />;
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
  // Map the structured failure_reason to humane copy; fall back gracefully for
  // any reason the frontend doesn't yet know about (never show the raw enum).
  const copy = FAILURE_COPY[run.failure_reason] ?? {
    title: "This run didn’t finish.",
    message: "The run failed before it could produce results. Start a new run to try again.",
  };
  return (
    <Shell eyebrow="Run · failed" title={copy.title}>
      <ErrorBanner title="The run failed">{copy.message}</ErrorBanner>
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
function DoneState({ run, runId, navigate, onNewRun }) {
  const gaps = run.gaps ?? [];
  const quotes = run.quotes ?? {};

  // Feedback (PRD §4/§9) is append-only and page-level: children call up via
  // callbacks, the page owns the single fetch (frontend/CONTEXT.md).
  const [feedbackError, setFeedbackError] = useState("");

  async function postFeedback(payload) {
    try {
      const res = await fetch(`${API_BASE}/runs/${runId}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        setFeedbackError(await readError(res));
        return false;
      }
      setFeedbackError("");
      return true;
    } catch (err) {
      setFeedbackError(err?.message || "Couldn’t record that — check your connection.");
      return false;
    }
  }

  // Thumbs-up: track the set of "new to me" gaps and flush the whole set on a
  // debounce so rapid toggles collapse into one append-only feedback row.
  const [newToMe, setNewToMe] = useState(() => new Set());
  const isFirstFlush = useRef(true);

  function toggleNewToMe(gapId) {
    setNewToMe((prev) => {
      const next = new Set(prev);
      if (next.has(gapId)) next.delete(gapId);
      else next.add(gapId);
      return next;
    });
  }

  useEffect(() => {
    // Skip the initial mount (empty set) and any state where nothing is marked.
    if (isFirstFlush.current) {
      isFirstFlush.current = false;
      return undefined;
    }
    if (newToMe.size === 0) return undefined;
    const timer = setTimeout(() => {
      postFeedback({ new_to_me_gap_ids: [...newToMe] });
    }, FEEDBACK_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newToMe]);

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
        {run.partial_sources && <PartialSourcesBanner partial={run.partial_sources} />}
        {run.coverage && <CoverageLine coverage={run.coverage} />}

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
          gaps.map((gap, i) => (
            <GapCard
              key={gap.gap_id}
              gap={gap}
              rank={i + 1}
              quotes={quotes}
              newToMe={newToMe.has(gap.gap_id)}
              onToggleNewToMe={() => toggleNewToMe(gap.gap_id)}
            />
          ))
        )}
      </div>

      {gaps.length > 0 && <DirectionPrompt onChoose={(direction) => postFeedback({ direction })} />}

      {feedbackError && (
        <p style={{ margin: "1rem 0 0", fontSize: ".8rem", color: "var(--tie-error-fg)" }}>
          {feedbackError}
        </p>
      )}

      <div
        style={{
          marginTop: "2.5rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
          flexWrap: "wrap",
        }}
      >
        {onNewRun && <PrimaryButton onClick={onNewRun}>Start another run →</PrimaryButton>}
        <ReportControl runId={runId} navigate={navigate} />
      </div>
    </div>
  );
}

// ── partial_sources banner (slice 2 §9.2) ──────────────────────
function PartialSourcesBanner({ partial }) {
  const { succeeded_count = 0, total_count = 0, failed = [] } = partial;
  return (
    <div
      style={{
        background: "rgba(202,138,4,.10)",
        border: "1px solid rgba(202,138,4,.30)",
        borderRadius: "var(--tie-radius-md)",
        padding: "1rem 1.25rem",
      }}
    >
      <div style={{ fontWeight: 600, color: "#92600a", fontSize: ".95rem", marginBottom: failed.length ? ".4rem" : 0 }}>
        Completed with {succeeded_count} of {total_count} source{total_count === 1 ? "" : "s"}.
      </div>
      {failed.length > 0 && (
        <p style={{ margin: 0, color: "var(--tie-fg-2)", fontSize: ".85rem", lineHeight: 1.5 }}>
          Failed:{" "}
          {failed
            .map((f) => (f.reason ? `${f.name} (${f.reason})` : f.name))
            .join(", ")}
        </p>
      )}
    </div>
  );
}

// ── Direction prompt (slice 2 §9.2) ────────────────────────────
const DIRECTION_OPTIONS = [
  { value: "continue", label: "Continuing with it" },
  { value: "shift", label: "Shifting the angle" },
  { value: "drop", label: "Dropping it" },
  { value: "need_more_research", label: "Need more research" },
];

function DirectionPrompt({ onChoose }) {
  const [dismissed, setDismissed] = useState(false);
  const [chosen, setChosen] = useState(null);

  if (dismissed) return null;

  if (chosen) {
    return (
      <div
        style={{
          marginTop: "2rem",
          padding: "1rem 1.25rem",
          background: "var(--tie-surface-soft)",
          border: "1px solid var(--tie-border-soft)",
          borderRadius: "var(--tie-radius-md)",
          color: "var(--tie-fg-3)",
          fontSize: ".9rem",
        }}
      >
        Thanks — noted that you’re{" "}
        <strong style={{ color: "var(--tie-fg-2)" }}>
          {DIRECTION_OPTIONS.find((o) => o.value === chosen)?.label.toLowerCase()}
        </strong>
        .
      </div>
    );
  }

  return (
    <div
      style={{
        marginTop: "2rem",
        padding: "1.25rem 1.4rem",
        background: "var(--tie-surface-soft)",
        border: "1px solid var(--tie-border-soft)",
        borderRadius: "var(--tie-radius-md)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
        <div style={{ fontWeight: 600, color: "var(--tie-fg-1)", fontSize: ".98rem" }}>
          After seeing these gaps, where’s your idea headed?
        </div>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss"
          style={{
            background: "none",
            border: "none",
            color: "var(--tie-fg-3)",
            cursor: "pointer",
            fontSize: "1.1rem",
            lineHeight: 1,
            padding: 0,
            flexShrink: 0,
          }}
        >
          ✕
        </button>
      </div>
      <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap", marginTop: ".9rem" }}>
        {DIRECTION_OPTIONS.map((opt) => (
          <SecondaryButton
            key={opt.value}
            onClick={() => {
              setChosen(opt.value);
              onChoose(opt.value);
            }}
            style={{ padding: ".55rem .9rem", fontSize: ".88rem" }}
          >
            {opt.label}
          </SecondaryButton>
        ))}
      </div>
    </div>
  );
}

// ── Report this run (slice 2 §9.2) ─────────────────────────────
function ReportControl({ runId, navigate }) {
  const [confirming, setConfirming] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    const trimmed = reason.trim();
    if (!trimmed) {
      setError("Please add a brief reason.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/runs/${runId}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: trimmed }),
      });
      if (!res.ok) {
        setError(await readError(res));
        setSubmitting(false);
        return;
      }
      // Hidden pending admin review — send the user home with an acknowledgement.
      navigate("/", { state: { reported: true } });
    } catch (err) {
      setError(err?.message || "Couldn’t submit the report — check your connection.");
      setSubmitting(false);
    }
  }

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        style={{
          background: "none",
          border: "none",
          color: "var(--tie-fg-3)",
          textDecoration: "underline",
          cursor: "pointer",
          fontSize: ".82rem",
          fontFamily: "inherit",
          padding: 0,
        }}
      >
        Report this run
      </button>
    );
  }

  return (
    <div
      style={{
        flex: "1 1 100%",
        padding: "1.1rem 1.25rem",
        background: "var(--tie-surface-soft)",
        border: "1px solid var(--tie-border-strong)",
        borderRadius: "var(--tie-radius-md)",
      }}
    >
      <div style={{ fontWeight: 600, color: "var(--tie-fg-1)", fontSize: ".95rem", marginBottom: ".25rem" }}>
        Report this run?
      </div>
      <p style={{ margin: "0 0 .75rem", color: "var(--tie-fg-3)", fontSize: ".85rem", lineHeight: 1.5 }}>
        It’ll be hidden from the public feed pending review. Tell us what’s wrong with it.
      </p>
      <TextInput
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="e.g. offensive content, spam, broken results…"
        multiline
        rows={2}
        autoFocus
      />
      {error && (
        <p style={{ margin: ".5rem 0 0", fontSize: ".8rem", color: "var(--tie-error-fg)" }}>{error}</p>
      )}
      <div style={{ display: "flex", gap: ".5rem", marginTop: ".75rem" }}>
        <PrimaryButton onClick={submit} disabled={submitting}>
          {submitting ? "Reporting…" : "Confirm report"}
        </PrimaryButton>
        <SecondaryButton onClick={() => setConfirming(false)} disabled={submitting}>
          Cancel
        </SecondaryButton>
      </div>
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

// Severity 1..5 → label + color (matches the SignalDot palette tone).
function severityMeta(severity) {
  if (severity >= 4) return { label: `Severity ${severity}/5`, color: "#b91c1c", bg: "var(--tie-error-bg)", border: "var(--tie-error-border)" };
  if (severity === 3) return { label: `Severity ${severity}/5`, color: "#ca8a04", bg: "rgba(202,138,4,.10)", border: "rgba(202,138,4,.30)" };
  return { label: `Severity ${severity}/5`, color: "#16a34a", bg: "rgba(22,163,74,.10)", border: "rgba(22,163,74,.30)" };
}

function GapCard({ gap, rank, quotes, newToMe, onToggleNewToMe }) {
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
            <button
              type="button"
              onClick={onToggleNewToMe}
              aria-pressed={newToMe}
              title={newToMe ? "Marked as new to you" : "This gap is new to me"}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: ".3rem",
                padding: "4px 9px",
                borderRadius: "var(--tie-radius-pill)",
                border: `1px solid ${newToMe ? "var(--tie-border-strong)" : "var(--tie-border)"}`,
                background: newToMe ? "var(--tie-surface-hover)" : "var(--tie-surface)",
                color: newToMe ? "var(--tie-fg-1)" : "var(--tie-fg-3)",
                cursor: "pointer",
                fontFamily: "inherit",
                fontSize: "var(--tie-fs-micro)",
                fontWeight: 600,
                whiteSpace: "nowrap",
                transition: "all .15s ease",
              }}
            >
              <span aria-hidden="true" style={{ opacity: newToMe ? 1 : 0.5 }}>👍</span>
              <span>New to me</span>
            </button>
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
