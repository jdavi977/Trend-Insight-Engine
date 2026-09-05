/* New Run — submit an idea, review pre-flight, approve. Spec §10 / issue #51.
 *
 * One page, two phases driven by local state:
 *   1. Submit form: `idea` (required, the only field) → POST /runs.
 *   2. Pre-flight review (rendered inline once POST returns): signal-strength
 *      panel, low-signal acknowledgement gate, editable competitor list →
 *      POST /runs/:id/approve → open the run's result page.
 *
 * Rebuilt on the v2.2 design (prototype pages-newrun.jsx + pages-preflight.jsx,
 * "stacked" variant). The prototype's optional `target_gap` field is gone: it
 * was folded into `idea` in the scope-down (issue #76), and `RunCreate` takes
 * `idea` alone.
 *
 * Page-level component owns all state and is the only thing that talks to the
 * backend (frontend/CONTEXT.md). Pre-flight sub-pieces below are page-specific.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PrimaryButton,
  SecondaryButton,
  TextInput,
  Pill,
  Spinner,
  ErrorBanner,
  ErrorStateCard,
  SignalBadge,
  SourceIcon,
} from "./components/atoms";
import { rememberRunId } from "./runStorage";
import { categoryLabel } from "./format";

const API_BASE = import.meta.env.VITE_API_BASE;

// Render a `Retry-After` value (seconds) as a human hint. Empty if absent so
// callers can omit the timer line entirely (e.g. budget_exhausted has no timer).
function formatRetryAfter(retryAfterRaw) {
  const secs = Number(retryAfterRaw);
  if (!Number.isFinite(secs) || secs <= 0) return "";
  if (secs < 90) return `about ${Math.max(1, Math.round(secs))} seconds`;
  const mins = Math.round(secs / 60);
  if (mins < 90) return `about ${mins} minute${mins === 1 ? "" : "s"}`;
  const hrs = Math.round(mins / 60);
  return `about ${hrs} hour${hrs === 1 ? "" : "s"}`;
}

// The three slice-2 guards (issue #59) all return 429, distinguished by the
// `X-RateLimit-Reason` header and timed by `Retry-After` (both exposed via CORS,
// see app/main.py). Render a distinct, friendly message per reason honoring the
// retry hint — slice 1 assumed the developer; slice 2 assumes a stranger (§9.3).
function rateLimitMessage(res, detail) {
  const reason = res.headers.get("X-RateLimit-Reason") || "";
  const hint = formatRetryAfter(res.headers.get("Retry-After"));
  const retryLine = hint ? ` You can try again in ${hint}.` : "";
  switch (reason) {
    case "busy":
      return `Another run is already in progress — the engine handles one run at a time.${retryLine || " Please try again shortly."}`;
    case "rate_limited":
      return `You've reached the run limit for now (3 per hour, 10 per day).${retryLine || " Please try again later."}`;
    case "budget_exhausted":
      return "Today's analysis budget has been reached. Please try again tomorrow.";
    default:
      // Header not readable (e.g. CORS not exposing it) — fall back to the body.
      return `${detail || "The engine is busy or rate-limited."}${retryLine}`;
  }
}

// Turn a backend error response into a readable line. Slice-2 sad paths
// (rate_limited / budget_exhausted / busy) arrive as 429; surface a distinct
// friendly message per reason rather than failing silently (PRD §8, §9.3).
async function readError(res) {
  let detail = "";
  try {
    const body = await res.json();
    detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? body);
  } catch {
    detail = res.statusText;
  }
  if (res.status === 429) return rateLimitMessage(res, detail);
  return detail || `Request failed (${res.status}).`;
}

// Derive a valid Competitor from a pasted URL. The backend requires non-empty
// source / url / name / identifier, so fall back to the URL itself for the id.
function competitorFromUrl(rawUrl) {
  const url = rawUrl.trim();
  const isYouTube = /youtu\.?be/i.test(url);
  let identifier = url;
  try {
    const u = new URL(url);
    if (isYouTube) {
      identifier = u.searchParams.get("v") || u.pathname.split("/").filter(Boolean).pop() || url;
    } else {
      // App Store ids look like /id123456789
      const m = u.pathname.match(/id(\d+)/i);
      identifier = m ? m[1] : (u.pathname.split("/").filter(Boolean).pop() || url);
    }
  } catch {
    // Not a parseable URL — keep the raw string as both url and identifier.
  }
  return {
    source: isYouTube ? "youtube" : "appstore",
    url,
    name: "Added manually",
    identifier,
    manual: true,
  };
}

export default function NewRun() {
  const navigate = useNavigate();
  const [idea, setIdea] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState("");

  const [preflight, setPreflight] = useState(null); // { run_id, status, preflight: {...} }
  const [competitors, setCompetitors] = useState([]);
  const [acknowledged, setAcknowledged] = useState(false);

  const canSubmit = idea.trim().length > 0 && !submitting;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    setError("");
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idea: idea.trim() }),
      });
      if (!res.ok) {
        setError(await readError(res));
        return;
      }
      const data = await res.json();
      // Remember this run for "My Runs" — collected at submit time, filtered
      // client-side against the public feed (spec §9.4, no accounts in v1).
      rememberRunId(data.run_id);
      setPreflight(data);
      setCompetitors(data.preflight?.candidates ?? []);
      setAcknowledged(false);
    } catch (err) {
      setError(err?.message || "Could not reach the engine. Is the backend running?");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApprove() {
    const pf = preflight?.preflight;
    // Low-signal ack triggers on the backend's count-derived `low_signal` flag,
    // not the LLM `signal_strength` grade (slice 3 §6, issue #69).
    const isLow = pf?.low_signal === true;
    if (!preflight || competitors.length === 0 || (isLow && !acknowledged) || approving) return;
    setError("");
    setApproving(true);
    try {
      const body = {
        competitors: competitors.map(({ source, url, name, identifier }) => ({
          source,
          url,
          name,
          identifier,
        })),
      };
      if (isLow) body.acknowledged_low_signal = acknowledged;

      const res = await fetch(`${API_BASE}/runs/${preflight.run_id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        setError(await readError(res));
        return;
      }
      navigate(`/runs/${preflight.run_id}`);
    } catch (err) {
      setError(err?.message || "Could not start the run. Try again.");
    } finally {
      setApproving(false);
    }
  }

  function startOver() {
    setPreflight(null);
    setCompetitors([]);
    setAcknowledged(false);
    setError("");
  }

  if (preflight) {
    return (
      <PreflightReview
        runIdea={preflight.idea ?? idea}
        preflight={preflight.preflight}
        competitors={competitors}
        setCompetitors={setCompetitors}
        acknowledged={acknowledged}
        setAcknowledged={setAcknowledged}
        approving={approving}
        error={error}
        onApprove={handleApprove}
        onBack={startOver}
      />
    );
  }

  return (
    <div className="tie-page tie-page--narrow">
      <div style={{ marginTop: "1.5rem" }}>
        <div className="tie-hero-eyebrow">Step 1 of 3 · Submit</div>
        <h1 className="tie-hero-title" style={{ fontSize: "2.25rem" }}>
          What are you thinking about building?
        </h1>
        <p className="tie-hero-sub">
          One idea per run. Vague (<em style={{ color: "var(--tie-fg-2)" }}>“2.5d survivor-like”</em>) or
          specific (<em style={{ color: "var(--tie-fg-2)" }}>“notes app with offline sync”</em>) —
          pre-flight will propose the competitors to read.
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ marginTop: "2.5rem", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <Field label="Your idea" hint="Required. Plain language." required>
          <TextInput
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="e.g. Note-taking app with better offline sync"
            multiline
            rows={3}
            autoFocus
          />
        </Field>

        <PublicByUrlNote />

        {error && <ErrorBanner title="Couldn’t run pre-flight">{error}</ErrorBanner>}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", marginTop: ".5rem", flexWrap: "wrap" }}>
          <div style={{ fontSize: ".82rem", color: "var(--tie-fg-3)" }}>
            Pre-flight runs in &lt;10s. You’ll review the competitor list before the full pipeline starts.
          </div>
          <PrimaryButton type="submit" disabled={!canSubmit}>
            {submitting ? (
              <>
                <Spinner size={16} /> Running pre-flight…
              </>
            ) : (
              "Run pre-flight →"
            )}
          </PrimaryButton>
        </div>
      </form>
    </div>
  );
}

// The disclosure the submit step owes the user before anything is persisted:
// completed runs are public by URL, review text is PII-stripped, and there are
// per-IP ceilings (PRD §8; RATE_LIMIT_PER_HOUR / _PER_DAY in app/config).
function PublicByUrlNote() {
  return (
    <div
      style={{
        padding: "1rem 1.1rem",
        background: "var(--tie-surface-soft)",
        border: "1px solid var(--tie-border-soft)",
        borderRadius: "var(--tie-radius-md)",
        fontSize: ".9rem",
        color: "var(--tie-fg-2)",
        lineHeight: 1.55,
        display: "flex",
        gap: ".75rem",
        alignItems: "flex-start",
      }}
    >
      <span aria-hidden="true" style={{ fontSize: "1rem", lineHeight: 1.4 }}>ⓘ</span>
      <div>
        <strong style={{ color: "var(--tie-fg-1)" }}>Public by URL.</strong> Completed runs appear on
        the public feed by their{" "}
        <code style={{ fontFamily: "var(--tie-font-mono)", fontSize: ".85em" }}>run_id</code>. We
        don&apos;t index them in search engines; raw review text is PII-stripped at persist time.
        Per-IP limits: 3 runs per hour, 10 per day.
      </div>
    </div>
  );
}

function Field({ label, hint, children, required }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: ".5rem" }}>
      <span style={{ fontSize: ".95rem", fontWeight: 600, color: "var(--tie-fg-1)" }}>
        {label}
        {required && <span aria-hidden="true" style={{ color: "var(--tie-fg-3)", fontWeight: 400, marginLeft: 4 }}>*</span>}
      </span>
      {children}
      {hint && <span style={{ fontSize: ".82rem", color: "var(--tie-fg-3)", lineHeight: 1.5 }}>{hint}</span>}
    </label>
  );
}

// ── Phase 2: pre-flight review ─────────────────────────────────
function PreflightReview({ runIdea, preflight, competitors, setCompetitors, acknowledged, setAcknowledged, approving, error, onApprove, onBack }) {
  // US-S1 (spec §9.3): pre-flight found zero public sources. The signal-strength
  // analysis is meaningless with nothing to read, so swap the whole panel for a
  // "no public sources" explanation — the only path forward is to paste URLs.
  // `no_sources` reflects the original backend result and stays true even after
  // the user adds competitors, so the context line persists while they paste.
  const noSources = preflight.no_sources === true;
  // Acknowledgement is driven by the count-derived `low_signal` flag (slice 3 §6,
  // issue #69); `signal_strength` stays below only as displayed copy.
  const isLow = !noSources && preflight.low_signal === true;
  const blocked = (isLow && !acknowledged) || competitors.length === 0 || approving;

  return (
    <div className="tie-page tie-page--narrow">
      <div style={{ marginTop: "1.5rem", marginBottom: "2rem" }}>
        <div className="tie-hero-eyebrow">Step 2 of 3 · Review pre-flight</div>
        <h1 className="tie-hero-title" style={{ fontSize: "2rem", marginBottom: ".5rem" }}>
          {noSources ? "No public sources found." : "Here’s what we’ll read."}
        </h1>
        <div style={{ display: "flex", alignItems: "center", gap: ".6rem", flexWrap: "wrap" }}>
          <p style={{ color: "var(--tie-fg-3)", fontSize: ".95rem", margin: 0 }}>
            Idea: <span style={{ color: "var(--tie-fg-1)", fontWeight: 500 }}>“{runIdea}”</span>
          </p>
          {preflight.category && <Pill muted>{categoryLabel(preflight.category)}</Pill>}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {noSources ? (
          <ErrorStateCard
            icon="∅"
            tone="neutral"
            title="No public sources for this idea."
            body={
              <>
                Pre-flight couldn’t surface any App Store apps or YouTube videos to mine for
                complaints. {preflight.signal_reasoning ? <span>{preflight.signal_reasoning} </span> : null}
                If you already know competitors worth reading, paste their App Store or YouTube URLs
                below and we’ll run against those.
              </>
            }
          />
        ) : (
          <>
            <SignalPanel signal={preflight.signal_strength} reasoning={preflight.signal_reasoning} />
            {isLow && <LowSignalAck acknowledged={acknowledged} setAcknowledged={setAcknowledged} />}
          </>
        )}

        <CompetitorEditor competitors={competitors} setCompetitors={setCompetitors} />

        {error && <ErrorBanner title="Couldn’t start the run">{error}</ErrorBanner>}
      </div>

      <div style={{ marginTop: "2.5rem", display: "flex", gap: ".75rem", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
        <div style={{ fontSize: ".85rem", color: "var(--tie-fg-3)", maxWidth: 380, lineHeight: 1.5 }}>
          {noSources
            ? competitors.length === 0
              ? "Paste at least one App Store or YouTube URL above to run."
              : "Using the sources you pasted — pre-flight found none automatically."
            : isLow
            ? acknowledged
              ? "Acknowledged — results will be thinner than usual."
              : "You must acknowledge low signal before continuing."
            : "Once approved, the full pipeline runs in the background. You can leave this tab."}
        </div>
        <div style={{ display: "flex", gap: ".5rem" }}>
          <SecondaryButton onClick={onBack} disabled={approving}>Cancel and refine</SecondaryButton>
          <PrimaryButton onClick={onApprove} disabled={blocked}>
            {approving ? (
              <>
                <Spinner size={16} /> Starting…
              </>
            ) : isLow ? (
              "Continue anyway →"
            ) : (
              "Approve and run →"
            )}
          </PrimaryButton>
        </div>
      </div>
    </div>
  );
}

function SignalPanel({ signal, reasoning }) {
  const isLow = signal === "low";
  return (
    <div style={{
      background: isLow ? "var(--tie-error-bg)" : "var(--tie-surface-soft)",
      border: `1px solid ${isLow ? "var(--tie-error-border)" : "var(--tie-border-soft)"}`,
      borderRadius: "var(--tie-radius-md)",
      padding: "1.25rem 1.4rem",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: ".5rem", gap: 8 }}>
        <span style={{ fontSize: ".72rem", letterSpacing: ".08em", textTransform: "uppercase", fontWeight: 600, color: isLow ? "var(--tie-error-fg)" : "var(--tie-fg-3)" }}>
          Signal strength
        </span>
        <SignalBadge strength={signal} />
      </div>
      <p style={{ margin: 0, color: isLow ? "var(--tie-error-fg)" : "var(--tie-fg-2)", lineHeight: 1.55, fontSize: ".95rem", textWrap: "pretty" }}>
        {reasoning}
      </p>
    </div>
  );
}

function LowSignalAck({ acknowledged, setAcknowledged }) {
  return (
    <div style={{ background: "var(--tie-error-bg)", border: "1px solid var(--tie-error-border)", borderRadius: "var(--tie-radius-md)", padding: "1.25rem 1.4rem" }}>
      <div style={{ display: "flex", gap: ".75rem", alignItems: "flex-start" }}>
        <span aria-hidden="true" style={{ fontSize: "1.05rem", lineHeight: 1.4 }}>⚠️</span>
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: "0 0 .35rem", color: "var(--tie-error-fg)", fontSize: "1.05rem", fontWeight: 700 }}>
            Signal will be thin for this idea.
          </h3>
          <p style={{ margin: 0, color: "var(--tie-error-fg)", fontSize: ".92rem", lineHeight: 1.55, textWrap: "pretty" }}>
            Categories with little public review/comment activity yield <strong>fewer gaps</strong> and{" "}
            <strong>weaker citations</strong>. We’ll still run, but consider interviews or community digging too.
          </p>
          <label style={{ display: "inline-flex", alignItems: "center", gap: ".55rem", cursor: "pointer", fontSize: ".9rem", color: "var(--tie-error-fg)", fontWeight: 500, marginTop: ".85rem" }}>
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              style={{ width: 16, height: 16, accentColor: "#b91c1c" }}
            />
            I understand the signal will be thin.
          </label>
        </div>
      </div>
    </div>
  );
}

function CompetitorEditor({ competitors, setCompetitors }) {
  const [newUrl, setNewUrl] = useState("");

  const remove = (idx) => setCompetitors(competitors.filter((_, i) => i !== idx));
  const addUrl = () => {
    if (!newUrl.trim()) return;
    setCompetitors([...competitors, competitorFromUrl(newUrl)]);
    setNewUrl("");
  };

  const apps = competitors.filter((c) => c.source === "appstore").length;
  const vids = competitors.filter((c) => c.source === "youtube").length;

  return (
    <div style={{ background: "var(--tie-surface)", border: "1px solid var(--tie-border)", borderRadius: "var(--tie-radius-md)", overflow: "hidden" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem", padding: "1.1rem 1.4rem", borderBottom: "1px solid var(--tie-border)", flexWrap: "wrap" }}>
        <div>
          <h2 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700, color: "var(--tie-fg-1)" }}>Competitors ({competitors.length})</h2>
          <p style={{ margin: "0.25rem 0 0", fontSize: ".85rem", color: "var(--tie-fg-3)" }}>
            Add, remove, or paste a URL. These are the sources we’ll read user complaints from.
          </p>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <Pill muted><SourceIcon source="appstore" size={11} /><span style={{ marginLeft: 6 }}>{apps} apps</span></Pill>
          <Pill muted><SourceIcon source="youtube" size={11} /><span style={{ marginLeft: 6 }}>{vids} videos</span></Pill>
        </div>
      </div>

      <div>
        {competitors.length === 0 && (
          <div style={{ padding: "1.4rem", fontSize: ".9rem", color: "var(--tie-fg-3)" }}>
            No competitors. Paste at least one App Store or YouTube URL to run.
          </div>
        )}
        {competitors.map((c, i) => (
          <CompetitorRow key={`${c.identifier}-${i}`} c={c} onRemove={() => remove(i)} divider={i < competitors.length - 1} />
        ))}
      </div>

      <div style={{ padding: "1rem 1.4rem", borderTop: "1px solid var(--tie-border)", background: "var(--tie-surface-soft)", display: "flex", gap: ".5rem" }}>
        <TextInput
          value={newUrl}
          onChange={(e) => setNewUrl(e.target.value)}
          placeholder="Paste an App Store or YouTube URL"
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addUrl(); } }}
        />
        <SecondaryButton onClick={addUrl} disabled={!newUrl.trim()}>Add</SecondaryButton>
      </div>
    </div>
  );
}

function CompetitorRow({ c, onRemove, divider }) {
  const [hover, setHover] = useState(false);
  // The backend Competitor model carries no raw search query, so provenance is
  // the source it was surfaced from plus its identifier (issue #51 source query).
  const provenance = c.manual
    ? "added manually"
    : `found via ${c.source === "youtube" ? "YouTube" : "App Store"} search`;
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: "grid",
        gridTemplateColumns: "auto minmax(0, 1fr) auto",
        gap: "1rem",
        alignItems: "center",
        padding: ".85rem 1.4rem",
        borderBottom: divider ? "1px solid var(--tie-divider)" : "none",
        background: hover ? "var(--tie-surface-hover)" : "transparent",
        transition: "background .15s ease",
      }}
    >
      <SourceIcon source={c.source} size={18} />
      <div style={{ minWidth: 0 }}>
        <a
          href={c.url}
          target="_blank"
          rel="noreferrer"
          style={{ fontSize: ".98rem", color: "var(--tie-fg-1)", fontWeight: 500, lineHeight: 1.35, textDecoration: "none", display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
        >
          {c.name}
        </a>
        <div style={{ fontSize: ".82rem", color: "var(--tie-fg-3)", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginTop: 2 }}>
          <span style={{ fontStyle: "italic" }}>{provenance}</span>
          <span aria-hidden="true">·</span>
          <code style={{ fontFamily: "var(--tie-font-mono)", fontSize: ".75rem" }}>{c.identifier}</code>
        </div>
      </div>
      <button
        type="button"
        onClick={onRemove}
        title="Remove"
        aria-label={`Remove ${c.name}`}
        style={{
          background: hover ? "var(--tie-surface)" : "transparent",
          border: `1px solid ${hover ? "var(--tie-border)" : "transparent"}`,
          color: "var(--tie-fg-3)",
          padding: ".35rem .55rem",
          borderRadius: "var(--tie-radius-sm)",
          fontSize: ".85rem",
          fontFamily: "inherit",
          cursor: "pointer",
          transition: "all .15s ease",
        }}
      >
        Remove
      </button>
    </div>
  );
}
