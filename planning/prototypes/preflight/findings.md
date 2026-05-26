# Pre-flight Prototype Findings

| | |
|---|---|
| **Spec** | [preflight-prototype_spec.md](../../specs/preflight-prototype_spec.md) |
| **Graded** | 2026-05-22 |
| **Grader** | Claude (LLM) — see [§Caveats](#caveats) |
| **Outcome** | **PASS** — all three §6 criteria met |

---

## 1. Pass / fail per §6

| Criterion | Threshold | Result | Verdict |
|---|---|---|---|
| Aggregate usefulness | ≥ 60% (≥ 90/150) | **136/150 = 90.7%** | PASS |
| Per-idea floor | ≥ 11/15 ideas with ≥ 5 useful | **15/15** | PASS |
| Signal-strength correct | Ideas 1–8 not-low; 13–14 low; 15 low-or-medium | All correct | PASS |

### Per-idea breakdown

| # | Idea | Signal (got / required) | Sig OK? | Queries sane? | Useful |
|---|---|---|---|---|---|
| 1 | note-taking app with better offline sync | high / not-low | y | y | 10/10 |
| 2 | habit tracker that uses streaks | high / not-low | y | y | 10/10 |
| 3 | podcast player with better chapter navigation | high / not-low | y | y | 10/10 |
| 4 | meditation app for sleep | high / not-low | y | y | 10/10 |
| 5 | expense tracker for freelancers | high / not-low | y | y | 9/10 |
| 6 | 2.5d vampire survivors-like game | medium / not-low | y | y | 9/10 |
| 7 | roguelike deckbuilder | high / not-low | y | y | 9/10 |
| 8 | city-builder with realistic logistics | high / not-low | y | y | 8/10 |
| 9 | productivity app | high / (none) | — | y | 10/10 |
| 10 | fitness app | high / (none) | — | y | 10/10 |
| 11 | note-taking app for ADHD users with spaced repetition | medium / (none) | — | y | 7/10 |
| 12 | video editor for short-form creators | high / (none) | — | y | 10/10 |
| 13 | Slack alternative for solo developers | low / low | y | y | 10/10 |
| 14 | tool for prompt engineers to manage prompts | low / low | y | y | 5/10 |
| 15 | AI companion app for processing dreams | medium / low-or-med | y | y | 9/10 |

## 2. What works, what doesn't

**Works cleanly (≥ 9/10):**
- Mature consumer app categories: note-taking (#1), habit tracking (#2), podcasts (#3), meditation (#4), productivity (#9), fitness (#10), video editing (#12). All hit 10/10.
- Audience-qualified consumer (#5 freelancers): App Store has specialised apps; the qualifier survives.
- Established game sub-genres (#6 survivors-like, #7 roguelike deckbuilder): the genre tag is searchable, even when a visual-style qualifier (2.5D) is lost.

**Degrades but stays above the per-idea floor:**
- City-builder with logistics (#8): the App Store side is fine, but YouTube returned two gameplay let's-plays (not reviews/discussion). Dropped to 8/10. The signal-strength was correctly high, but the rubric's "gameplay-only fails" filter clipped two videos. Not a real concern — the remaining 8 are strong.
- Decomposition idea (#11 note app for ADHD + spaced repetition): 7/10. Apps degraded to 2/5 useful — the LLM picked the dominant "note-taking" axis and returned generic notes apps (OneNote, Notability, Goodnotes) that have neither ADHD focus nor spaced repetition. Videos held at 5/5 because the LLM happened to issue ADHD-specific YouTube queries. This is **failure mode A from the spec** (qualifier loss) and is the expected behaviour.
- B2B devtools (#14 prompt engineer tools): 5/10 — right at the floor. App Store returned five small indie prompt-manager iOS apps (Promptler, PromptPaste, etc.) which technically qualify, but the *real* competitor space (PromptLayer, LangSmith, Helicone, Latitude) is web/SaaS and never appears. Videos all degraded to prompt-engineering-as-skill content (courses, tutorials, "you suck at prompting") rather than prompt-management tools. Signal-strength correctly flagged this as low.

**Surprises:**
- Idea #13 (Slack alternative for solo developers) scored 10/10 even though the spec predicted it would fail (B2B audience qualifier invisible to App Store). The App Store *does* surface team-comms tools (Slack itself, Zoho Cliq, Flock, Rocket.Chat, Google Chat), and YouTube has plenty of "Slack alternatives" review content. The "for solo developers" qualifier *is* lost — none of the candidates are solo-dev-targeted — but the rubric asks whether a builder would plausibly study them, and the answer is yes (they're the reference set of the broader competitor space). Worth re-examining whether the test set is actually exposing the failure modes it intended to. Signal-strength was still correctly marked low, which is what matters for the downstream UX.

## 3. Known limitations

- **Failure mode A (qualifier loss) confirmed on idea #11.** Generic notes apps came back when the LLM should have picked the "spaced repetition" or "ADHD" axis as the dominant search term. PRD §7.6's competitor-editor UX is the right mitigation — the user is the failsafe here, not the LLM. Idea #6 (2.5D vampire-survivors) also has the qualifier-loss shape on paper but didn't degrade in practice because the survivors-genre tag was strong enough to return relevant games.
- **B2B devtools (#14) found shallow App Store competitors.** The real prompt-engineering tools live on the web; iOS results are largely indie/hobby apps. Signal-strength=low correctly warns the user, and the downstream synthesis will (per PRD §7.5) treat low-signal categories with appropriate scepticism.
- **YouTube ranker keeps occasional let's-plays.** Ideas #8 and #15 each had one gameplay-style video that should have been filtered out by the ranker. Minor; doesn't move pass/fail.
- **Test set may not stress real failure modes hard enough.** #13 was supposed to fail and didn't. Worth adding more genuinely-fringe ideas if the v2 build wants to re-validate this surface (e.g. an industrial/enterprise idea like "OSHA compliance tracker for warehouse managers").

## 4. Caveats

- **Grader bias.** The spec (§9) calls grading "manual and subjective" with the implicit assumption of a human grader. This memo's grades were applied by an LLM (the same model family used to generate the queries and rank the candidates). That introduces a known bias: the grader is more likely to agree with the ranker's framing. A 90.7% aggregate score should be interpreted with that in mind — a human grader could reasonably land anywhere in the ~75–95% range depending on how strictly they apply the "plausibly pick as competitor" test. The pass margin (90/150 vs. 136/150) is wide enough that LLM-grader optimism doesn't flip the outcome on aggregate or per-idea criteria; signal-strength is objective and unaffected.
- Grades were committed to the rubric (§5) before tallying, per spec §9's "don't move the goalposts" rule.

## 5. Recommendation

**Proceed to PRD v2 build.** The pre-flight stage produces useful competitor lists across the realistic range of indie-dev ideas tested, including correctly downgrading low-signal categories. The two real degradations (idea #11 qualifier loss, idea #14 shallow App Store devtools) are both already designed-for in the PRD: §7.6 competitor editor for #11-style cases, and §7.5 low-signal handling for #14-style cases.

**Before the v2 build starts:**
1. Productionise `itunes_search()` into [app/clients/appstore.py](../../app/clients/appstore.py) (currently RSS-only).
2. Tighten the YouTube ranker's filter for gameplay-only let's-plays — the prompt currently lets ~1 in 10 through.
3. Optional: add an industrial/enterprise idea to the test set if we want to re-validate after prompt changes (the current set didn't surface a clean B2B failure).

No reason to iterate on the pre-flight prompt before building. Failure modes A and the B2B devtools shape are understood and mitigated downstream.
