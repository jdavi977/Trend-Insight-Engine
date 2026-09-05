/* Display formatting shared across the v2 pages.
 *
 * `relativeTime` was copy-pasted into Home and My Runs; the v2.2 port adds a
 * third caller (the result header), so it lives here once. `categoryLabel` comes
 * from the prototype's components.jsx — the pre-flight classifier emits the
 * slug, the UI shows the label, and an unknown slug passes through unchanged.
 */

// Compact relative time ("3h ago"); falls back to a date for older runs.
export function relativeTime(iso) {
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

// Absolute timestamp for the result header ("27 May 2026, 2:30 PM").
export function absoluteTime(iso) {
  if (!iso) return "";
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return "";
  return then.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

const CATEGORY_LABELS = {
  "consumer-app": "Consumer app",
  "mobile-game": "Mobile game",
  "creator-tool": "Creator tool",
  productivity: "Productivity",
  "b2b-saas": "B2B SaaS",
  devtools: "Devtools",
  enterprise: "Enterprise",
  other: "Other",
};

// Category slugs come from the pre-flight classifier and are free-form, so an
// unmapped value renders as-is rather than disappearing.
export function categoryLabel(category) {
  if (!category) return "";
  return CATEGORY_LABELS[category] || category;
}

export function plural(count, singular, pluralForm) {
  return count === 1 ? singular : pluralForm ?? `${singular}s`;
}
