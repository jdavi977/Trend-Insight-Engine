/* Shared v2 UI atoms, built on the --tie-* design tokens (tokens.css).
 * Ported from the v2.2 prototype components.jsx into ES modules. These are the
 * cross-page atoms (buttons, inputs, signal + source glyphs) reused by New Run,
 * Pre-flight, Result and Home — keep one-off UI in its page (frontend/CONTEXT.md).
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

export function PrimaryButton({ children, disabled, onClick, type, style, ...rest }) {
  const [hover, setHover] = useState(false);
  const [press, setPress] = useState(false);
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

export function SecondaryButton({ children, onClick, style, disabled, type, ...rest }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      type={type || "button"}
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: ".8rem 1.2rem",
        fontSize: ".95rem",
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
