/* Run Status / Result — stable view of one run, polled live. Spec §10 / issue #52.
 *
 * Opened after a run is approved (status `running`). Polls `GET /runs/:id`
 * every 5s while the run is non-terminal (pending / running / preflight_ready)
 * and stops once `done` or `failed`. Three render states:
 *   - running  → per-source progress shell (prototype pages-running.jsx)
 *   - done     → editorial report: signal, coverage, methodology, ranked gaps
 *                with verbatim quotes inline (prototype pages-result.jsx,
 *                "editorial" variant)
 *   - failed   → failure_reason surfaced (never a silent blank)
 *
 * Page-level component owns all state and is the only thing that talks to the
 * backend (frontend/CONTEXT.md). Quotes arrive as a { quote_id: Quote } map and
 * are looked up per gap via evidence_quote_ids.
 *
 * The run id comes from the /runs/:id route (ADR 2026-06-01 / issue #58), so a
 * pasted URL loads the run directly in a fresh tab (US-4, US-5).
 *
 * Dropped from the prototype, deliberately: the thumbs-up ("new to me")
 * control, the direction prompt and the "Report this run" dialog all belonged
 * to the feedback + report surface removed in the scope-down (issue #89) — the
 * Result page is read-only. `target_gap` and its match card went the same way
 * (issue #76). The per-gap `summary` paragraph has no field in `GapItem`.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  PrimaryButton,
  SecondaryButton,
  Pill,
  Spinner,
  ErrorBanner,
  ErrorStateCard,
  PartialSourcesBanner,
  SignalBadge,
  SourceIcon,
  QuoteBlock,
  MetricCell,
  StepBadge,
} from "./components/atoms";
import { absoluteTime, categoryLabel } from "./format";

const API_BASE = import.meta.env.VITE_API_BASE;
const POLL_MS = 5000; // spec open question #1 — confirmed 5s.

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
        <div style={{ marginTop: "1.5rem" }}>
          <PrimaryButton onClick={onNewRun}>Start a new run →</PrimaryButton>
        </div>
      </Shell>
    );
  }

  if (run.status === "failed") return <FailedState run={run} onNewRun={onNewRun} />;
  if (run.status === "done") return <DoneState run={run} onNewRun={onNewRun} />;
  return <RunningState run={run} runId={runId} error={error} />;
}

// ── Page shell (loading / error / failed) ──────────────────────
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
/* The prototype animated each source through queued → ingesting → … → done.
 * The real pipeline tracks that stage in an in-memory job registry that
 * `GET /runs/:id` does not expose (app/services/run_pipeline_service.py), so
 * there is no honest per-source percentage to render. The layout is kept — the
 * source list, the synthesis card, the failure-policy note — but the motion is
 * indeterminate: a travelling bar and a live badge per source, no fake numbers.
 * Wiring real progress means adding a `stage` field to `RunStateResponse`.
 */
function RunningState({ run, runId, error }) {
  const competitors = run.competitors ?? [];
  const total = competitors.length;

  return (
    <div className="tie-page tie-page--wide">
      <div style={{ marginTop: "1.5rem", marginBottom: "2rem" }}>
        <div className="tie-hero-eyebrow">Step 3 of 3 · Running</div>
        <h1 className="tie-hero-title" style={{ fontSize: "2rem", marginBottom: ".5rem" }}>
          {total > 0
            ? `Reading complaints from ${total} source${total === 1 ? "" : "s"}.`
            : "Starting your run."}
        </h1>
        <p style={{ color: "var(--tie-fg-3)", margin: 0, fontSize: ".95rem" }}>
          You can leave this tab — we’ll keep this URL for the result.
          <span style={{ marginLeft: 10, color: "var(--tie-fg-2)", fontFamily: "var(--tie-font-mono)" }}>
            /runs/{runId}
          </span>
        </p>
      </div>

      <IndeterminateBar
        label={
          run.status === "running"
            ? "Extracting pain per source, then synthesising grounded gaps"
            : "Waiting for the pipeline to pick this run up"
        }
      />

      <div
        style={{
          marginTop: "2rem",
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) minmax(260px, 320px)",
          gap: "2rem",
          alignItems: "start",
        }}
      >
        <div
          style={{
            background: "var(--tie-surface)",
            border: "1px solid var(--tie-border)",
            borderRadius: "var(--tie-radius-md)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "1rem 1.4rem",
              borderBottom: "1px solid var(--tie-border)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: ".75rem",
            }}
          >
            <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 700, color: "var(--tie-fg-1)" }}>
              Sources being read
            </h2>
            <span style={{ fontSize: ".82rem", color: "var(--tie-fg-3)", fontVariantNumeric: "tabular-nums" }}>
              {total} in this run
            </span>
          </div>
          {total === 0 ? (
            <div style={{ padding: "1.4rem", fontSize: ".9rem", color: "var(--tie-fg-3)" }}>
              The source list appears once the run is approved.
            </div>
          ) : (
            competitors.map((c, i) => (
              <SourceRow key={`${c.identifier}-${i}`} c={c} divider={i < total - 1} />
            ))
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "1rem", position: "sticky", top: "5rem" }}>
          <SidePanel title="Synthesis" badge={<StepBadge tone="default">Pending</StepBadge>}>
            Once every source finishes, we pool their quotes and synthesise ranked gaps. Every gap
            must cite at least two quote IDs from that pool — or it’s rejected.
          </SidePanel>
          <SidePanel title="Source failure policy" muted>
            Each source retries once with backoff. If fewer than 70% succeed the run fails;
            otherwise the result names the sources that dropped out.
          </SidePanel>
          <p style={{ margin: 0, fontSize: ".82rem", color: "var(--tie-fg-3)", lineHeight: 1.5 }}>
            Idea: <span style={{ color: "var(--tie-fg-2)" }}>“{run.idea}”</span>
          </p>
        </div>
      </div>

      {error && (
        <div style={{ marginTop: "1.5rem" }}>
          <ErrorBanner title="Reconnecting…" icon="↻">{error}</ErrorBanner>
        </div>
      )}
    </div>
  );
}

function IndeterminateBar({ label }) {
  return (
    <div>
      <div style={{ marginBottom: ".5rem", fontSize: ".88rem", color: "var(--tie-fg-2)", fontWeight: 500 }}>
        {label}
      </div>
      <div
        role="progressbar"
        aria-label={label}
        style={{
          height: 6,
          background: "var(--tie-surface-muted)",
          borderRadius: "var(--tie-radius-pill)",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            width: "40%",
            background: "var(--tie-accent-gradient)",
            borderRadius: "var(--tie-radius-pill)",
            animation: "tie-bar 1.6s ease-in-out infinite",
          }}
        />
      </div>
    </div>
  );
}

function SourceRow({ c, divider }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "auto minmax(0,1fr) auto",
        gap: "1rem",
        alignItems: "center",
        padding: "0.95rem 1.4rem",
        borderBottom: divider ? "1px solid var(--tie-divider)" : "none",
      }}
    >
      <SourceIcon source={c.source} size={16} />
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            fontSize: ".95rem",
            color: "var(--tie-fg-1)",
            fontWeight: 500,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {c.name}
        </div>
        <div style={{ fontSize: ".8rem", color: "var(--tie-fg-3)", marginTop: 2, fontFamily: "var(--tie-font-mono)" }}>
          {c.identifier}
        </div>
      </div>
      <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
        <span style={{ animation: "tie-pulse 1.6s ease-in-out infinite", display: "inline-flex" }}>
          <StepBadge tone="active">In progress</StepBadge>
        </span>
      </span>
    </div>
  );
}

function SidePanel({ title, badge, muted, children }) {
  return (
    <div
      style={{
        background: muted ? "var(--tie-surface-soft)" : "var(--tie-surface)",
        border: `1px solid ${muted ? "var(--tie-border-soft)" : "var(--tie-border)"}`,
        borderRadius: "var(--tie-radius-md)",
        padding: "1.1rem 1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: ".6rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: ".5rem" }}>
        <h3 style={{ margin: 0, fontSize: ".95rem", fontWeight: 700, color: "var(--tie-fg-1)" }}>{title}</h3>
        {badge}
      </div>
      <p style={{ margin: 0, fontSize: ".85rem", color: "var(--tie-fg-3)", lineHeight: 1.55 }}>{children}</p>
    </div>
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
      <ErrorStateCard
        icon="⚠️"
        tone="error"
        title="The run failed."
        body={copy.message}
        cta={[
          <PrimaryButton key="new" size="sm" onClick={onNewRun}>
            Start a new run →
          </PrimaryButton>,
        ]}
      />
      <p style={{ margin: "1.25rem 0 0", fontSize: ".82rem", color: "var(--tie-fg-3)" }}>
        Idea: <span style={{ color: "var(--tie-fg-2)" }}>“{run.idea}”</span>
      </p>
    </Shell>
  );
}

// ── Done — the editorial report ────────────────────────────────
function DoneState({ run, onNewRun }) {
  const gaps = run.gaps ?? [];
  const quotes = run.quotes ?? {};

  // Quotes carry `source_id`, which the pipeline sets to the competitor's
  // `identifier` (run_pipeline_service.py). Resolving it here gives every quote
  // the competitor name in its caption instead of an opaque id.
  const competitors = useMemo(() => run.competitors ?? [], [run.competitors]);
  const sourceNames = useMemo(() => {
    const map = {};
    competitors.forEach((c) => {
      map[c.identifier] = c.name;
    });
    return map;
  }, [competitors]);

  // `competitors_present` arrives as "<source>:<identifier>" tokens
  // (e.g. "youtube:qjeCeznj77s"). Show the competitor's name instead, falling
  // back to the raw token if the id isn't in this run's competitor list.
  const namedCompetitor = (token) => {
    const id = typeof token === "string" ? token.slice(token.indexOf(":") + 1) : token;
    return sourceNames[id] ?? sourceNames[token] ?? token;
  };

  return (
    <div className="tie-page">
      <ResultHeader run={run} />

      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <SignalReadout signal={run.signal_strength} reasoning={run.signal_reasoning} />
        {run.partial_sources && <PartialSourcesBanner partial={run.partial_sources} />}
        <CoverageStrip run={run} />
        {run.coverage && <CoverageLine coverage={run.coverage} />}
        <Methodology competitors={competitors} />

        <div style={{ marginTop: ".5rem" }}>
          <SectionHeading
            title="Findings"
            subtitle="Ordered by the synthesiser. Every claim cites at least two quote IDs."
          />
        </div>

        {gaps.length === 0 ? (
          <ErrorStateCard
            icon="∅"
            tone="neutral"
            title="No gap cleared the grounding bar."
            body="Nothing reached the two-citation minimum for this idea, so there is nothing we'd stand behind. Signal may be thin — consider interviews or community digging."
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {gaps.map((gap, i) => (
              <GapArticle
                key={gap.gap_id}
                gap={gap}
                index={i + 1}
                quotes={quotes}
                sourceNames={sourceNames}
                competitorCount={competitors.length}
                nameFor={namedCompetitor}
              />
            ))}
          </div>
        )}
      </div>

      <ResultFooter onNewRun={onNewRun} />
    </div>
  );
}

function ResultHeader({ run }) {
  return (
    <header style={{ marginTop: "1rem", marginBottom: "2rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
          gap: "1rem",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: ".8rem", color: "var(--tie-fg-3)", flexWrap: "wrap" }}>
          <span style={{ fontWeight: 600, letterSpacing: ".05em", textTransform: "uppercase" }}>Run result</span>
          <span aria-hidden="true">·</span>
          <code style={{ fontFamily: "var(--tie-font-mono)", color: "var(--tie-fg-2)" }}>/runs/{run.run_id}</code>
          {/* `RunStateResponse` has no completed_at; on a terminal run updated_at
              is the moment it finished. */}
          <span aria-hidden="true">·</span>
          <span>{absoluteTime(run.updated_at)}</span>
        </div>
        <div style={{ display: "flex", gap: ".5rem", alignItems: "center" }}>
          {run.category && <Pill muted>{categoryLabel(run.category)}</Pill>}
          <SignalBadge strength={run.signal_strength} />
        </div>
      </div>
      <h1 className="tie-hero-title" style={{ fontSize: "2.4rem", marginBottom: 0, textWrap: "balance" }}>
        “{run.idea}”
      </h1>
    </header>
  );
}

function SignalReadout({ signal, reasoning }) {
  const isLow = signal === "low";
  return (
    <section
      style={{
        padding: "1.4rem 1.5rem",
        background: isLow ? "var(--tie-error-bg)" : "var(--tie-surface-soft)",
        border: `1px solid ${isLow ? "var(--tie-error-border)" : "var(--tie-border-soft)"}`,
        borderRadius: "var(--tie-radius-md)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: ".5rem", gap: 8 }}>
        <span
          style={{
            fontSize: ".72rem",
            letterSpacing: ".08em",
            textTransform: "uppercase",
            fontWeight: 600,
            color: isLow ? "var(--tie-error-fg)" : "var(--tie-fg-3)",
          }}
        >
          Signal &amp; framing
        </span>
        <SignalBadge strength={signal} />
      </div>
      {reasoning && (
        <p
          style={{
            margin: 0,
            fontSize: ".95rem",
            color: isLow ? "var(--tie-error-fg)" : "var(--tie-fg-2)",
            lineHeight: 1.6,
            textWrap: "pretty",
          }}
        >
          {reasoning}
        </p>
      )}
    </section>
  );
}

function CoverageStrip({ run }) {
  const { quotes_retrieved = 0, quotes_cited = 0, citation_ratio = 0 } = run.coverage ?? {};
  const competitors = run.competitors ?? [];
  const apps = competitors.filter((c) => c.source === "appstore").length;
  const vids = competitors.filter((c) => c.source === "youtube").length;
  return (
    <section
      style={{
        padding: "1rem 1.4rem",
        background: "var(--tie-surface)",
        border: "1px solid var(--tie-border)",
        borderRadius: "var(--tie-radius-md)",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
        gap: "1.5rem",
        alignItems: "center",
      }}
    >
      <MetricCell label="Gaps surfaced" value={(run.gaps ?? []).length.toString()} />
      <MetricCell label="Quotes retrieved" value={quotes_retrieved.toLocaleString()} />
      <MetricCell
        label="Quotes cited"
        value={quotes_cited.toLocaleString()}
        hint={`${Math.round((citation_ratio ?? 0) * 100)}% citation ratio`}
      />
      <MetricCell
        label="Competitors read"
        value={competitors.length.toString()}
        hint={`${apps} app${apps === 1 ? "" : "s"} · ${vids} video${vids === 1 ? "" : "s"}`}
      />
    </section>
  );
}

// The coverage sentence PRD §7.8 asks for in words, not just as tiles: a low
// citation ratio is the reader's cue that most of the pool went unused.
function CoverageLine({ coverage }) {
  const { quotes_retrieved = 0, quotes_cited = 0, citation_ratio = 0 } = coverage;
  const pct = Math.round((citation_ratio ?? 0) * 100);
  return (
    <p style={{ margin: 0, fontSize: ".88rem", color: "var(--tie-fg-3)" }}>
      <strong style={{ color: "var(--tie-fg-2)", fontWeight: 600 }}>{quotes_cited}</strong> of{" "}
      <strong style={{ color: "var(--tie-fg-2)", fontWeight: 600 }}>{quotes_retrieved}</strong>{" "}
      retrieved quotes were cited ({pct}%).
    </p>
  );
}

function Methodology({ competitors }) {
  const apps = competitors.filter((c) => c.source === "appstore").length;
  const vids = competitors.filter((c) => c.source === "youtube").length;
  return (
    <section
      style={{
        background: "var(--tie-surface)",
        border: "1px solid var(--tie-border)",
        borderRadius: "var(--tie-radius-md)",
        padding: "1.25rem 1.4rem",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "1.5rem",
      }}
    >
      <MethodCell
        title="Sources"
        body={`${apps} app${apps === 1 ? "" : "s"} + ${vids} video${vids === 1 ? "" : "s"}. Engagement-filtered before extraction.`}
      />
      <MethodCell
        title="Quote-then-claim"
        body="Every gap cites ≥2 quote IDs from the retrieval pool. No citations → rejected."
      />
      <MethodCell
        title="Idea-blinded extraction"
        body="The per-source pass never sees the idea text. Only synthesis sees both."
      />
    </section>
  );
}

function MethodCell({ title, body }) {
  return (
    <div>
      <div style={{ fontSize: ".72rem", letterSpacing: ".08em", textTransform: "uppercase", color: "var(--tie-fg-3)", fontWeight: 600, marginBottom: 4 }}>
        {title}
      </div>
      <div style={{ fontSize: ".88rem", color: "var(--tie-fg-2)", lineHeight: 1.5 }}>{body}</div>
    </div>
  );
}

function SectionHeading({ title, subtitle }) {
  return (
    <div
      style={{
        borderBottom: "1px solid var(--tie-fg-1)",
        paddingBottom: ".75rem",
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        gap: 8,
        flexWrap: "wrap",
      }}
    >
      <h2 style={{ margin: 0, fontSize: "var(--tie-fs-h3)", fontWeight: 700, color: "var(--tie-fg-1)", letterSpacing: "-0.01em" }}>
        {title}
      </h2>
      {subtitle && <span style={{ fontSize: ".85rem", color: "var(--tie-fg-3)" }}>{subtitle}</span>}
    </div>
  );
}

function GapArticle({ gap, index, quotes, sourceNames, competitorCount, nameFor }) {
  const cited = (gap.evidence_quote_ids ?? []).map((id) => quotes[id]).filter(Boolean);
  const citationCount = gap.evidence_quote_ids?.length ?? 0;
  const present = gap.competitors_present ?? [];

  return (
    <article
      id={`g-${gap.gap_id}`}
      style={{
        background: "var(--tie-surface)",
        border: "1px solid var(--tie-border)",
        borderRadius: "var(--tie-radius-md)",
        padding: "1.75rem 1.75rem 1.5rem",
        display: "flex",
        flexDirection: "column",
        gap: "1.25rem",
      }}
    >
      <header>
        <span
          style={{
            display: "inline-block",
            marginBottom: ".4rem",
            fontSize: ".72rem",
            letterSpacing: ".08em",
            textTransform: "uppercase",
            color: "var(--tie-fg-3)",
            fontWeight: 600,
          }}
        >
          Gap {String(index).padStart(2, "0")}
        </span>
        <h3
          style={{
            margin: 0,
            fontSize: "1.3rem",
            fontWeight: 700,
            color: "var(--tie-fg-1)",
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
            textWrap: "balance",
          }}
        >
          {gap.gap}
        </h3>
      </header>

      <GapMetadata
        gap={gap}
        citationCount={citationCount}
        competitorCount={competitorCount}
        present={present}
        nameFor={nameFor}
      />

      {/* Quotes sit inline under the claim, never behind a drill-down — the
          grounding is the point (frontend/CONTEXT.md, PRD §7.6). */}
      {cited.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.1rem", paddingTop: ".25rem" }}>
          {cited.map((q) => (
            <QuoteBlock key={q.quote_id} quote={q} sourceName={sourceNames[q.source_id]} />
          ))}
        </div>
      )}

      <div
        style={{
          borderTop: "1px solid var(--tie-divider)",
          paddingTop: "1rem",
          fontSize: ".82rem",
          color: "var(--tie-fg-3)",
          fontFamily: "var(--tie-font-mono)",
        }}
      >
        evidence: {cited.length} of {citationCount} cited quote{citationCount === 1 ? "" : "s"} resolved
      </div>
    </article>
  );
}

function GapMetadata({ gap, citationCount, competitorCount, present, nameFor }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
        gap: "0.85rem 1.5rem",
        padding: ".85rem 0",
        borderTop: "1px solid var(--tie-divider)",
        borderBottom: "1px solid var(--tie-divider)",
      }}
    >
      <MetaCell
        label="Spread"
        value={competitorCount ? `${gap.spread} of ${competitorCount} competitors` : `${gap.spread} competitors`}
      />
      {/* Citations are the strength signal now that severity/frequency are gone:
          2 citations is visibly weaker than 12 and the reader has to see which
          they're looking at (PRD §7.8). */}
      <MetaCell label="Citations" value={`${citationCount} quote${citationCount === 1 ? "" : "s"}`} />
      {present.length > 0 && (
        <MetaCellWrap label="Surfaced in">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {present.map((token) => (
              <Pill key={token}>{nameFor(token)}</Pill>
            ))}
          </div>
        </MetaCellWrap>
      )}
    </div>
  );
}

function MetaCell({ label, value }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{ fontSize: ".7rem", letterSpacing: ".08em", textTransform: "uppercase", color: "var(--tie-fg-3)", fontWeight: 600 }}>
        {label}
      </span>
      <span style={{ fontSize: ".95rem", color: "var(--tie-fg-1)", fontWeight: 500, fontVariantNumeric: "tabular-nums" }}>
        {value}
      </span>
    </div>
  );
}

function MetaCellWrap({ label, children }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: ".7rem", letterSpacing: ".08em", textTransform: "uppercase", color: "var(--tie-fg-3)", fontWeight: 600 }}>
        {label}
      </span>
      {children}
    </div>
  );
}

function ResultFooter({ onNewRun }) {
  return (
    <footer
      style={{
        marginTop: "3rem",
        padding: "1.5rem 0 0",
        borderTop: "1px solid var(--tie-divider)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: "1rem",
        flexWrap: "wrap",
      }}
    >
      <div style={{ fontSize: ".85rem", color: "var(--tie-fg-3)", maxWidth: "55ch", lineHeight: 1.55 }}>
        This result is decision support, not a verdict. Take the strongest gap into five interviews
        before committing build time.
      </div>
      <SecondaryButton size="sm" onClick={onNewRun}>
        Run a new idea
      </SecondaryButton>
    </footer>
  );
}

