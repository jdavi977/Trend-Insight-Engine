# ADR: iTunes RSS top-apps deprecation
Date: 2026-05-05
Status: Draft

Related spec: planning/specs/automatic-appstore-supabase_spec.md

## Context
> _What situation forced this decision? Describe the state of the codebase, the pain point, or the trigger in your own words. 1–2 sentences. Avoid solution language here — only the problem._

`itunes.apple.com/{country}/rss/topfreeapplications/limit={N}/genre={genreId}/json` endpoint is the only public surface that still exposes per-genre slicing today. However, Apple haas officially deprecated this in favor of `rss.applemarketingtools.com`. This replacement does not have per-genre slicing is mostly used for Apple Music / Books / Podcasts content.

## Options Considered
> _List the real alternatives you weighed. Minimum 2. For each, write one line describing what that path would actually look like in this codebase. If you can only think of one option, the decision is not yet ripe — go think harder before filling this in._

1. **Legacy `itunes.apple.com` RSS** — 
2. **`rss.applemarketingtools.com` feed** —
3. **Scrape the public App Store charts page** — 

## Decision
> _Which option did you choose, and what is the single primary reason? One sentence. If you need a paragraph to justify it, the reason probably isn't the real reason — keep digging._

Chose **Legacy `itunes.apple.com** as only the legacy feed offers it natively and a RSS endpoint is cheaper to maintain than a scrapper.

## Tradeoffs Accepted
> _Every choice gives something up. What did you lose by not picking the other options? What new complexity, discipline, or future cost did you take on? Be specific — "some overhead" is not a tradeoff, "one extra file per endpoint flow" is._

1. Apple can turn it off with no notice, when they do this the weekly cron for Apple insights will stop.
2. No failback wiring exists yet

## Consequences
> _Two halves: what does this **close off** (things the codebase will no longer do, patterns that are now disallowed) and what does this **enable** (things that get easier, seams that now exist). Write at least one of each._

- Closes off:
    1. code touching the `list_top_apps` should assume that the feed can disappear and fail loudly
- Enables:
    1. documented menu of failbacks (scraping, marketing-tools feed), allowing faster response to itunes.apple.com being removed
