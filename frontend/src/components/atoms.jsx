/* Shared v2 UI atoms, built on the --tie-* design tokens (tokens.css).
 * Ported from the v2.2 prototype components.jsx into ES modules. These are the
 * cross-page atoms (buttons, inputs, signal + source glyphs, quote block,
 * metric cells) reused by New Run, Pre-flight, Result, Running, Home and My
 * Runs — keep one-off UI in its page (frontend/CONTEXT.md).
 */
import { useState } from "react";

const primaryBase = {
  padding: ".85rem 1.35rem",
  borderRadius: "var(--tie-radius-md)",
  border: "none",
  fontWeight: "var(--tie-fw-semibold)",
  fontSize: "var(--tie-fs-body)",
  color: "#fff",
  background: "var(--tie-accent-gradient)",
  boxShadow: "var(--tie-shadow-cta)",
  cursor: "pointer",
  fontFamily: "inherit",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: ".5rem",
  transition: "transform .12s ease, box-shadow .2s ease, opacity .2s ease",
};

export function PrimaryButton({ children, disabled, onClick, size, type, style, ...rest }) {
  const [hover, setHover] = useState(false);
  const [press, setPress] = useState(false);
  const sizing =
    size === "sm" ? { padding: ".6rem 1rem", fontSize: ".95rem" } :
    size === "lg" ? { padding: "1rem 1.6rem", fontSize: "1.05rem" } : {};
  return (
    <button
      type={type || "button"}
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setPress(false); }}
      onMouseDown={() => setPress(true)}
      onMouseUp={() => setPress(false)}
      style={{
        ...primaryBase,
        ...sizing,
        ...(disabled ? { opacity: 0.55, cursor: "not-allowed", boxShadow: "none" } : {}),
        ...(hover && !disabled ? { transform: press ? "translateY(0)" : "translateY(-1px)", boxShadow: "var(--tie-shadow-cta-hover)" } : {}),
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({ children, onClick, size, style, disabled, type, ...rest }) {
  const [hover, setHover] = useState(false);
  const sizing =
    size === "sm" ? { padding: ".55rem .9rem", fontSize: ".9rem" } :
    size === "lg" ? { padding: ".95rem 1.4rem", fontSize: "1rem" } :
    { padding: ".8rem 1.2rem", fontSize: ".95rem" };
  return (
    <button
      type={type || "button"}
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        ...sizing,
        borderRadius: "var(--tie-radius-md)",
        border: `1px solid ${hover ? "var(--tie-border-hover)" : "var(--tie-border-strong)"}`,
        background: hover ? "var(--tie-surface-hover)" : "var(--tie-surface)",
        color: "var(--tie-fg-1)",
        fontWeight: "var(--tie-fw-semibold)",
        fontFamily: "inherit",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.55 : 1,
        transition: "all .2s ease",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: ".4rem",
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Pill({ children, muted, style }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "5px 10px",
        borderRadius: "var(--tie-radius-pill)",
        background: muted ? "var(--tie-pill-bg-muted)" : "var(--tie-pill-bg)",
        color: muted ? "var(--tie-pill-fg-muted)" : "var(--tie-pill-fg)",
        fontSize: "var(--tie-fs-micro)",
        fontWeight: "var(--tie-fw-semibold)",
        lineHeight: 1.2,
        ...style,
      }}
    >
      {children}
    </span>
  );
}

export function TextInput({ value, onChange, placeholder, onKeyDown, multiline, rows, autoFocus, style }) {
  const [focus, setFocus] = useState(false);
  const common = {
    width: "100%",
    padding: ".9rem 1rem",
    border: `1px solid ${focus ? "var(--tie-accent)" : "var(--tie-border-strong)"}`,
    borderRadius: "var(--tie-radius-md)",
    fontSize: "var(--tie-fs-body)",
    fontFamily: "inherit",
    background: "var(--tie-surface)",
    color: "var(--tie-fg-1)",
    boxShadow: focus ? "0 0 0 3px var(--tie-accent-focus-ring)" : "none",
    outline: "none",
    transition: "border-color .2s ease, box-shadow .2s ease",
    resize: multiline ? "vertical" : "none",
    lineHeight: 1.5,
    boxSizing: "border-box",
    ...style,
  };
  if (multiline) {
    return (
      <textarea
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        rows={rows || 3}
        style={common}
      />
    );
  }
  return (
    <input
      type="text"
      value={value}
      onChange={onChange}
      onKeyDown={onKeyDown}
      onFocus={() => setFocus(true)}
      onBlur={() => setFocus(false)}
      placeholder={placeholder}
      autoFocus={autoFocus}
      style={common}
    />
  );
}

export function Spinner({ size = 32 }) {
  return (
    <div
      role="status"
      aria-label="Loading"
      style={{
        width: size,
        height: size,
        border: `${Math.max(2, Math.round(size / 14))}px solid var(--tie-border)`,
        borderTopColor: "var(--tie-fg-1)",
        borderRadius: "50%",
        animation: "tie-spin 0.8s linear infinite",
      }}
    />
  );
}

export function ErrorBanner({ title, children, icon = "⚠️" }) {
  return (
    <div
      role="alert"
      style={{
        color: "var(--tie-error-fg)",
        background: "var(--tie-error-bg)",
        padding: "12px 16px",
        borderRadius: "var(--tie-radius-sm)",
        border: "1px solid var(--tie-error-border)",
        display: "flex",
        gap: ".75rem",
        alignItems: "flex-start",
      }}
    >
      <span aria-hidden="true" style={{ lineHeight: 1.4 }}>{icon}</span>
      <div style={{ lineHeight: 1.5 }}>
        {title && <div style={{ fontWeight: 600, marginBottom: children ? 4 : 0 }}>{title}</div>}
        {children && <div style={{ fontSize: ".95rem" }}>{children}</div>}
      </div>
    </div>
  );
}

export function SignalDot({ strength, size = 8 }) {
  const color =
    strength === "high"   ? "#16a34a" :
    strength === "medium" ? "#ca8a04" :
    strength === "low"    ? "#b91c1c" : "#9ca3af";
  return (
    <span
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        display: "inline-block",
        flexShrink: 0,
      }}
    />
  );
}

export function SignalBadge({ strength, style }) {
  const label =
    strength === "high"   ? "High signal" :
    strength === "medium" ? "Medium signal" :
    strength === "low"    ? "Low signal" : "Signal unknown";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "5px 12px 5px 10px",
        borderRadius: "var(--tie-radius-pill)",
        background: "var(--tie-surface)",
        border: "1px solid var(--tie-border)",
        color: "var(--tie-fg-1)",
        fontSize: "var(--tie-fs-micro)",
        fontWeight: "var(--tie-fw-semibold)",
        lineHeight: 1.2,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      <SignalDot strength={strength} />
      {label}
    </span>
  );
}

export function SourceIcon({ source, size = 16 }) {
  const s = source === "youtube" || source === "YouTube" ? "youtube" : "appstore";
  if (s === "youtube") {
    return (
      <span
        aria-label="YouTube"
        title="YouTube"
        style={{
          display: "inline-flex",
          width: size,
          height: size * 0.7,
          background: "#1a1a1a",
          borderRadius: 3,
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <span style={{
          width: 0, height: 0,
          borderLeft: `${size * 0.22}px solid #fff`,
          borderTop: `${size * 0.16}px solid transparent`,
          borderBottom: `${size * 0.16}px solid transparent`,
          marginLeft: 1,
        }} />
      </span>
    );
  }
  return (
    <span
      aria-label="App Store"
      title="App Store"
      style={{
        display: "inline-flex",
        width: size,
        height: size,
        borderRadius: size * 0.25,
        background: "var(--tie-fg-1)",
        color: "#fff",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.6,
        fontWeight: 700,
        flexShrink: 0,
        lineHeight: 1,
      }}
    >A</span>
  );
}

export function GhostButton({ children, onClick, style, ...rest }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: ".5rem .75rem",
        borderRadius: "var(--tie-radius-sm)",
        background: hover ? "var(--tie-surface-hover)" : "transparent",
        border: "1px solid transparent",
        color: "var(--tie-fg-2)",
        fontWeight: "var(--tie-fw-medium)",
        fontFamily: "inherit",
        cursor: "pointer",
        fontSize: ".9rem",
        transition: `all var(--tie-ease)`,
        display: "inline-flex",
        alignItems: "center",
        gap: ".35rem",
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

// Square / circle / triangle — the three source shapes, standing in for the
// three surfaces a run reads. Decorative, so it is hidden from assistive tech.
export function LogoMark({ size = 9 }) {
  const shape = { width: size, height: size, background: "var(--tie-fg-2)", display: "inline-block" };
  return (
    <span aria-hidden="true" style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
      <i style={{ ...shape, borderRadius: 1 }} />
      <i style={{ ...shape, borderRadius: "50%" }} />
      <i style={{ ...shape, clipPath: "polygon(50% 0%, 100% 100%, 0% 100%)" }} />
    </span>
  );
}

export function Card({ children, padded = true, hoverable, style }) {
  const [hover, setHover] = useState(false);
  return (
    <div
      onMouseEnter={hoverable ? () => setHover(true) : undefined}
      onMouseLeave={hoverable ? () => setHover(false) : undefined}
      style={{
        background: "var(--tie-surface)",
        border: "1px solid var(--tie-border)",
        borderColor: hover ? "var(--tie-border-hover)" : "var(--tie-border)",
        borderRadius: "var(--tie-radius-md)",
        padding: padded ? "1.5rem" : 0,
        transition: `border-color var(--tie-ease), box-shadow var(--tie-ease)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function Divider({ style }) {
  return <hr style={{ border: 0, borderTop: "1px solid var(--tie-divider)", margin: 0, ...style }} />;
}

// A labelled number. Used in the home hero, the result coverage strip and the
// running page — anywhere a figure needs a caption rather than a sentence.
export function MetricCell({ label, value, hint, align = "left" }) {
  const items = align === "right" ? "flex-end" : align === "center" ? "center" : "flex-start";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: items, lineHeight: 1.2, minWidth: 0 }}>
      <div style={{ fontSize: ".72rem", letterSpacing: ".08em", textTransform: "uppercase", color: "var(--tie-fg-3)", fontWeight: 600, lineHeight: 1.2 }}>
        {label}
      </div>
      <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--tie-fg-1)", fontVariantNumeric: "tabular-nums", lineHeight: 1 }}>
        {value}
      </div>
      {hint && <div style={{ fontSize: ".78rem", color: "var(--tie-fg-3)", lineHeight: 1.35 }}>{hint}</div>}
    </div>
  );
}

export function StepBadge({ children, tone = "default" }) {
  const palette = {
    default: { bg: "var(--tie-pill-bg-muted)", fg: "var(--tie-pill-fg-muted)" },
    active: { bg: "var(--tie-fg-1)", fg: "#fff" },
    done: { bg: "#dcfce7", fg: "#15803d" },
    failed: { bg: "var(--tie-error-bg)", fg: "var(--tie-error-fg)" },
  }[tone] ?? { bg: "var(--tie-pill-bg-muted)", fg: "var(--tie-pill-fg-muted)" };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "3px 8px",
        borderRadius: "var(--tie-radius-pill)",
        background: palette.bg,
        color: palette.fg,
        fontSize: ".72rem",
        fontWeight: 600,
        letterSpacing: ".02em",
        lineHeight: 1.2,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}

// A verbatim, PII-redacted complaint set in serif, with its provenance beneath.
// The quote is the product — it is never collapsed behind a drill-down
// (frontend/CONTEXT.md, PRD §7.6). `sourceName` is the competitor the quote was
// read from, resolved by the page from `quote.source_id`.
export function QuoteBlock({ quote, sourceName, compact, style }) {
  return (
    <figure
      style={{
        margin: 0,
        padding: compact ? "0 0 0 .9rem" : "0 0 0 1.1rem",
        borderLeft: `2px solid ${compact ? "var(--tie-border)" : "var(--tie-fg-1)"}`,
        ...style,
      }}
    >
      <blockquote
        style={{
          margin: 0,
          fontFamily: "var(--tie-font-serif)",
          fontSize: compact ? "1rem" : "1.08rem",
          lineHeight: 1.5,
          color: "var(--tie-fg-1)",
          fontWeight: 400,
          textWrap: "pretty",
        }}
      >
        “{quote.text_redacted}”
      </blockquote>
      <figcaption
        style={{
          marginTop: ".5rem",
          fontSize: ".82rem",
          color: "var(--tie-fg-3)",
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <SourceIcon source={quote.source} size={13} />
        <span style={{ fontWeight: 500, color: "var(--tie-fg-2)" }}>
          {sourceName || (quote.source === "youtube" ? "YouTube" : "App Store")}
        </span>
        {quote.like_count > 0 && (
          <>
            <span aria-hidden="true">·</span>
            <span style={{ fontVariantNumeric: "tabular-nums" }}>
              👍 {quote.like_count.toLocaleString()}
            </span>
          </>
        )}
        <span aria-hidden="true">·</span>
        <code
          style={{
            fontFamily: "var(--tie-font-mono)",
            fontSize: ".72rem",
            background: "var(--tie-surface-muted)",
            padding: "1px 6px",
            borderRadius: 4,
            color: "var(--tie-fg-3)",
          }}
        >
          {quote.quote_id}
        </code>
      </figcaption>
    </figure>
  );
}

// A sad-path card: icon, headline, explanation, optional actions. One shape for
// every terminal state so "no sources", "run failed" and "rate limited" read as
// the same kind of event rather than three different bugs.
export function ErrorStateCard({ icon, title, body, cta, tone = "neutral" }) {
  const palette = {
    neutral: { bg: "var(--tie-surface)", border: "var(--tie-border)", fg: "var(--tie-fg-1)" },
    warn: { bg: "#fffbeb", border: "#fde68a", fg: "#854d0e" },
    error: { bg: "var(--tie-error-bg)", border: "var(--tie-error-border)", fg: "var(--tie-error-fg)" },
  }[tone];
  return (
    <div
      style={{
        background: palette.bg,
        border: `1px solid ${palette.border}`,
        borderRadius: "var(--tie-radius-md)",
        padding: "1.5rem 1.6rem",
        display: "grid",
        gridTemplateColumns: "auto 1fr",
        gap: "1.25rem",
        alignItems: "flex-start",
      }}
    >
      <div
        aria-hidden="true"
        style={{
          width: 40,
          height: 40,
          borderRadius: "50%",
          background: tone === "neutral" ? "var(--tie-surface-muted)" : "rgba(255,255,255,0.6)",
          border: `1px solid ${palette.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.1rem",
          color: palette.fg,
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div>
        <h3 style={{ margin: "0 0 .35rem", fontSize: "1.05rem", color: palette.fg, fontWeight: 700 }}>
          {title}
        </h3>
        <div
          style={{
            color: tone === "neutral" ? "var(--tie-fg-2)" : palette.fg,
            fontSize: ".95rem",
            lineHeight: 1.55,
            marginBottom: cta ? ".85rem" : 0,
            textWrap: "pretty",
          }}
        >
          {body}
        </div>
        {cta && <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>{cta}</div>}
      </div>
    </div>
  );
}

// `partial_sources` banner (slice 2 §9.2 / PRD §7.6). A `done` run that lost
// sources must say so, by name — the findings are one source thinner per
// dropout and the reader has to be able to discount them.
export function PartialSourcesBanner({ partial }) {
  const { failed = [], succeeded_count = 0, total_count = 0 } = partial ?? {};
  return (
    <div
      style={{
        background: "#fffbeb",
        border: "1px solid #fde68a",
        borderRadius: "var(--tie-radius-md)",
        padding: "1.1rem 1.4rem",
      }}
    >
      <div style={{ display: "flex", gap: ".75rem", alignItems: "flex-start" }}>
        <span aria-hidden="true" style={{ fontSize: "1.05rem", marginTop: 1, color: "#854d0e" }}>◐</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <strong style={{ color: "#854d0e", fontSize: "1rem", display: "block", marginBottom: 6 }}>
            Partial result — {succeeded_count} of {total_count} source
            {total_count === 1 ? "" : "s"} finished.
          </strong>
          <div style={{ color: "#854d0e", fontSize: ".92rem", lineHeight: 1.5, marginBottom: failed.length ? ".75rem" : 0 }}>
            The synthesis still ran — but treat the findings as one source thinner per dropout.
          </div>
          {failed.length > 0 && (
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: ".4rem" }}>
              {failed.map((f, i) => (
                <li key={`${f.name}-${i}`} style={{ fontSize: ".88rem", color: "#854d0e", display: "flex", gap: ".5rem" }}>
                  <span aria-hidden="true">×</span>
                  <span>
                    <strong>{f.name}</strong>
                    {f.reason && <span style={{ color: "rgba(133,77,14,0.7)", marginLeft: 6 }}>— {f.reason}</span>}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
