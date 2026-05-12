# ADR: RAG Embedding Model Selection

Date: 2026-05-11
Status: Draft

Related spec: planning/specs/rag-insights-retrieval_spec.md

## Context
> _What situation forced this decision? Describe the state of the codebase, the pain point, or the trigger in your own words. 1–2 sentences. Avoid solution language here — only the problem._

Need to embed problem text for semantic similarity search. Database will be of small scale.

## Options Considered
> _List the real alternatives you weighed. Minimum 2. For each, write one line describing what that path would actually look like in this codebase. If you can only think of one option, the decision is not yet ripe — go think harder before filling this in._

1. **text-embedding-3-small** — Extend existing OpenAI client
2. **text-embedding-3-large** — Higher quality embeddings but higher cost and latency

## Decision
> _Which option did you choose, and what is the single primary reason? One sentence. If you need a paragraph to justify it, the reason probably isn't the real reason — keep digging._

Chose **text-embedding-3-small** because it is cheaper and more reasonable for a small scale of data. text-embedding-3-large would cost 5x more and produce 3x the dimensions which is too much for low amounts of data. 

## Tradeoffs Accepted
> _Every choice gives something up. What did you lose by not picking the other options? What new complexity, discipline, or future cost did you take on? Be specific — "some overhead" is not a tradeoff, "one extra file per endpoint flow" is._


- Lost: Higher quality embeddings from large model.
- Gained: Embedding model cost to each API call (small but non-zero budget impact)
- Gained: Dependency on OpenAI's embedding service uptime
- Gained: Re-embedding cost if model changes in future

## Consequences
> _Two halves: what does this **close off** (things the codebase will no longer do, patterns that are now disallowed) and what does this **enable** (things that get easier, seams that now exist). Write at least one of each._

- Closes off: Using open-source embedding models without additional infrastructure
- Enables: Single OpenAI integration point for both extraction (gpt-4o) and embeddings (text-embedding-3-small)
- Enables: Trivial addition to existing clients/openai.py (no new dependencies)
- Enables: Low per-call overhead 

