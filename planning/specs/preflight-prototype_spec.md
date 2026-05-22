# Pre-flight Prototype Spec

| | |
|---|---|
| **Status** | Draft |
| **Created** | 2026-05-21 |
| **Owner** | John Lowen David |
| **Purpose** | De-risk the largest unknown in [PRD v2.1](../../docs/PRD.md) before committing to the v2 rewrite |
| **Budget** | 1 afternoon (~3–4 hours), ~$2 in OpenAI tokens |

---

## 1. Hypothesis Being Tested

The PRD's pre-flight design (§7.3) assumes that for an arbitrary builder idea, the following pipeline produces a useful competitor list:

```
idea text
  → LLM generates App Store + YouTube search queries
  → call iTunes Search API + YouTube Data API search.list
  → LLM ranks + filters the real returned candidates
  → output: 5 apps + 5 videos with justifications
```

The whole PRD direction depends on this step producing competitors that a reasonable builder would actually pick. If pre-flight degrades to junk for >40% of realistic ideas, the synthesis step downstream is grounded in irrelevant data and the product breaks regardless of how well the rest is built.

**This prototype answers one question:** does pre-flight return useful candidates across a realistic range of indie-dev ideas?

## 2. What This Prototype Is (and Isn't)

**Is:**
- A single throwaway Python script
- Lives in `planning/prototypes/preflight/` (new directory, outside the app/ layered structure)
- Calls real OpenAI + real iTunes Search API + real YouTube Data API
- Outputs structured results to a CSV or JSON for manual grading
- Reuses existing clients where possible ([app/clients/openai.py](../../app/clients/openai.py), [app/clients/youtube.py](../../app/clients/youtube.py)). Adds a thin `itunes_search()` function since the current [app/clients/appstore.py](../../app/clients/appstore.py) only does RSS reviews and top-apps lookup, not keyword search.

**Is not:**
- Integrated into the FastAPI app
- A PR-worthy implementation (no tests, no Pydantic schemas, no error handling beyond happy path)
- Persistent (no Supabase writes)
- The synthesis step, PII redaction, rate limiting, or anything else in the PRD past pre-flight
- A demonstration of code quality — the goal is a fast yes/no answer

## 3. Test Set (15 Ideas)

Picked to stress the failure modes called out in the feasibility analysis. Each idea is labeled with the failure mode it tests so grading is honest.

| # | Idea | Tests |
|---|---|---|
| 1 | "note-taking app with better offline sync" | Clean specific idea — baseline happy path |
| 2 | "habit tracker that uses streaks" | Clean specific consumer app |
| 3 | "podcast player with better chapter navigation" | Specific consumer with searchable qualifier |
| 4 | "meditation app for sleep" | Specific consumer, mature category |
| 5 | "expense tracker for freelancers" | Specific with audience qualifier |
| 6 | "2.5d vampire survivors-like game" | **Visual-style qualifier loss** — App Store can't filter by 2D/2.5D/3D |
| 7 | "roguelike deckbuilder" | Mobile game with established sub-genre |
| 8 | "city-builder with realistic logistics" | Game with a feature qualifier |
| 9 | "productivity app" | Vague category — does pre-flight ask for more, or guess? |
| 10 | "fitness app" | Vague category, mature space |
| 11 | "note-taking app for ADHD users with spaced repetition" | **Decomposition** — no single search term captures this; LLM must pick one axis |
| 12 | "video editor for short-form creators" | Audience-qualifier (creator-tools per PRD §7.5) |
| 13 | "Slack alternative for solo developers" | **B2B / audience qualifier invisible to App Store** |
| 14 | "tool for prompt engineers to manage prompts" | **B2B devtools** — PRD §7.5 says this should mark low-signal |
| 15 | "AI companion app for processing dreams" | **Novel category** — no established competitors, tests fallback behavior |

## 4. Implementation Outline

Single script, roughly:

```python
# planning/prototypes/preflight/run_preflight.py

IDEAS = [...]  # 15 ideas from §3

def generate_queries(idea: str) -> dict:
    """LLM call #1. Returns {'appstore': [str], 'youtube': [str], 'category': str, 'signal_strength': 'high'|'medium'|'low', 'signal_reasoning': str}."""

def itunes_search(query: str, limit: int = 10) -> list[dict]:
    """iTunes Search API. New thin function — does not need to live in app/clients yet."""

def youtube_search(query: str, max_results: int = 10) -> list[dict]:
    """YouTube Data API search.list. ~100 quota units per call."""

def rank_candidates(idea: str, apps: list[dict], videos: list[dict]) -> dict:
    """LLM call #2. Picks top 5 apps + top 5 videos with one-line justifications."""

def preflight(idea: str) -> dict:
    queries = generate_queries(idea)
    raw_apps = dedupe([app for q in queries["appstore"] for app in itunes_search(q)])
    raw_videos = dedupe([v for q in queries["youtube"] for v in youtube_search(q)])
    ranked = rank_candidates(idea, raw_apps, raw_videos)
    return {**queries, **ranked, "raw_app_count": len(raw_apps), "raw_video_count": len(raw_videos)}

# main: loop over IDEAS, write results to results.csv
```

**Output CSV columns** (one row per candidate, so 10 rows per idea):

```
idea_id, idea, category, signal_strength, signal_reasoning,
candidate_kind ("app"|"video"), name, identifier (bundle_id or video_id),
url, llm_justification,
useful_y_n (manual fill-in), notes (manual fill-in)
```

A second CSV (`queries.csv`) records the search queries the LLM generated so we can see *what it was looking for*, separate from *what came back*.

## 5. Grading Rubric

For each of the 10 candidates per idea (5 apps + 5 videos), the grader marks **useful** if:

- It's a real entity (no hallucination — should always be true if the pipeline is built right)
- It's in roughly the right category for the idea
- A builder evaluating the idea would plausibly pick it as a competitor to study
- For videos: its comments are likely to contain user pain (review, discussion, "best X" videos pass; gameplay-only let's-plays fail)

For each idea, also grade:

- **Signal-strength correctness** — for ideas 13 (Slack alt) and 14 (prompt eng tools), pre-flight must mark `signal_strength: low` per PRD §7.5. For idea 15 (dreams), `low` or `medium` is acceptable. For ideas 1–8, must be `high` or `medium`.
- **Queries-sane** y/n — did the LLM generate search queries that make sense for that idea? (Diagnostic for failure cases.)

## 6. Pass / Fail Criteria

The prototype passes if **all three** hold:

1. **Aggregate usefulness ≥ 60%.** Across all 150 candidates (15 ideas × 10), at least 90 are graded useful.
2. **Per-idea floor.** At least 11 of 15 ideas have ≥ 5 useful candidates out of 10. (Below 5/10, the user has to rebuild the list from scratch, which defeats pre-flight's purpose.)
3. **Signal-strength classification is correct** on the calibration ideas (1–8 not-low; 13–14 low).

If it fails:

- **Failure mode A — qualifier loss (e.g. idea #6, #11):** Acceptable failure if signal-strength correctly downgrades these. The PRD's competitor-editor UX (§7.6) is the mitigation. Mark this as a known limitation, not a blocker.
- **Failure mode B — useful% < 60% across-the-board:** PRD direction needs rework before any production code. Most likely fix: better query-generation prompt, or a structured query format (genre + keywords) rather than free-text queries.
- **Failure mode C — signal-strength misclassification:** Prompt issue. Iterate on the signal-strength rubric in the generate_queries prompt and re-run.

## 7. Decision Output

After grading, write a short memo to `planning/prototypes/preflight/findings.md` answering:

1. Pass/fail per §6.
2. Which idea categories work / don't.
3. If failed: which fix would be tried next, and at what additional time cost.
4. Recommended next step: proceed to PRD v2 build, iterate on pre-flight, or rethink the PRD.

This memo is the actual deliverable. The script is just how we get there.

## 8. Out of Scope

- Cost optimization (caching, batching). The prototype runs 15 ideas one-shot.
- Async or concurrency. Sequential is fine for 15 calls.
- Frontend, persistence, deployment.
- Integrating into the layered `app/` structure. The prototype lives outside that boundary on purpose — it's research code, not product code.
- Productionizing iTunes Search and YouTube search into `app/clients/`. That happens only if the prototype passes.

## 9. Risks Within The Prototype Itself

- **YouTube quota** — search.list is 100 units per call. 15 ideas × ~3 queries each = ~4,500 units. Fits comfortably in the 10k daily quota but leaves limited room to iterate. If the prompt needs many re-runs, request a quota increase or cache results.
- **iTunes Search API** has no auth but is rate-limited (~20 calls/minute, undocumented). Add a `time.sleep(0.5)` between calls to be safe.
- **OpenAI costs** are minor (~$2 estimated for the full 15-idea run with gpt-4o), but if the rank prompt gets long (many raw candidates passed in), token usage grows. Cap raw candidates at ~30 per source before passing to the ranker.
- **Grading is manual and subjective.** Mitigation: define "useful" before looking at results (§5 rubric). Don't move the goalposts after seeing output.

## 10. Open Questions

1. Which OpenAI model? `gpt-4o` matches the rest of the project. `gpt-4o-mini` would cut cost ~10× but ranking quality on free-text candidates is the riskiest part — start with gpt-4o, downgrade later if it works.
2. Should the rank prompt see App Store description + ratings, or just name + genre? Recommend: name + genre + short description + rating count. Don't pass full descriptions (token bloat).
3. For YouTube, do we filter by view count or comment count at the search stage? Recommend: no filter at search; let the LLM ranker prefer videos with discussion-heavy titles. View/comment thresholds are a §7.5 production concern.
