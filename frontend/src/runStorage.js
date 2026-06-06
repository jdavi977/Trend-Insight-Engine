/* Local record of runs started in *this* browser. There are no accounts in v1
 * (PRD §5), so "My Runs" is a frontend-only filter of the public feed against
 * the run ids we collected at submit time (spec §9.4 / issue #64). No backend
 * change — the public `GET /runs` feed is filtered client-side against this set.
 */
const STORAGE_KEY = "tie_my_run_ids";

// Read the remembered run ids as an array (newest last). Tolerates a missing or
// corrupt value — localStorage is best-effort, never load-bearing.
export function getMyRunIds() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((id) => typeof id === "string") : [];
  } catch {
    return [];
  }
}

// Append a run id at submit time (deduped). Best-effort: a write failure (quota,
// private mode) must not break the submit flow, so swallow errors.
export function rememberRunId(runId) {
  if (!runId) return;
  try {
    const ids = getMyRunIds();
    if (!ids.includes(runId)) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids, runId]));
    }
  } catch {
    // ignore — My Runs is a convenience, not a source of truth.
  }
}
