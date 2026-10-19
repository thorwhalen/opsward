# 0011 — Cheap-first dispatch: routes, then the listing, then lexical retrieval; no router agent

## Status

Accepted (2026-10-19). Closes [thorwhalen/opsward#14](https://github.com/thorwhalen/opsward/issues/14).

## Context

The issue asked for a few top-level entry agents that find and dispatch to the right specialist, built from `aw.PriorityRouter` with a retrieval-backed strategy and an escalation to an LLM on ambiguity, and for three decisions: the score-gap or abstention boundary and its calibration, how many entry agents, and when routing helps rather than hurts. The research report `misc/docs/research/discovery_and_dispatch.md` had already warned that routing is not universally beneficial, and the #23 report (`skill_tiering_and_reachability.md` §5.2) had costed the always-on residue a router needs and deferred any router to usage evidence, the same gate priv#177 applies to its package-scout hook. What was missing was measurement, so this decision rests on `misc/docs/research/dispatch_probe.md`: fourteen trigger prompts through the host's own listing (13/14), an LLM router holding the complete catalog (12/14 on the raw prompt, 11/14 on a one-line summary, ~15 s per decision), and `ir discover` over the skills corpus (lexical 12/14 in 0.05–0.2 s; hybrid 11/14 in 12–13 s; both near zero on summaries; abstention never fired because duplicate corpus records tie at the top).

## Decision

1. **No new entry agent.** The entry surface stays what it is: the session the user talks to, its always-loaded routes (`CLAUDE.md`, briefs), the host's skill listing (T0 described, T1 name-only, per the #23 tiers), one discovery tool (`ir discover skills`) for everything not listed, and delegation through subagent twins (ADR 0009). A router agent would add a hop and a 79k-character context per decision to score at best one miss worse than the listing. The crowsnest lookout remains the one "top-level agent", and it dispatches to sessions, not to skills.
2. **The dispatch order is cheap-first and each layer only answers when it is sure.** (a) A route: a `CLAUDE.md` line or a brief that names the skill next to its condition, deterministic and free. (b) The listing: description matching in the main context, no extra hop. (c) Lexical retrieval: `ir discover skills --mode lexical` over the raw prompt, wrapped in `aw.routing.ConfidentRetrievalStrategy` so it answers only when its top candidate clears a floor and beats the runner-up by a gap, in-process and under a second. (d) Escalation: an LLM adjudication over the top-k cards from (c), not over the whole catalog, and only when (c) abstains. `PriorityRouter([route, listing, confident_retrieval, adjudicate])` is the shape; the first two layers are the host's, the last two are code.
3. **The router must see the user's words.** A paraphrase is a lossy channel: retrieval collapses on it (0/14 lexical, 4/14 hybrid) and an LLM router loses a case (11 vs 12). Nothing in the chain may summarise the request before matching it.
4. **The abstention boundary is defined, not yet calibrated.** Floor: the lexical score floor `ir calibrate-min-score` produces for the `skills` corpus, persisted with the corpus. Gap: the runner-up at or below 0.9 of the top score (`ir`'s `rel_threshold`), applied after collapsing copies of one skill to one record. Neither can be set today: the live corpus holds 943 records for ~525 skills and the copies tie at identical scores, so every gap reads as zero. De-duplication and a persisted floor are prerequisites, filed on `ir`; until they land, layer (c) runs with `gap=0` and a floor of zero, which makes it a candidate generator for (d) rather than a decider.
5. **When routing helps and when it hurts.** It helps for a skill that is not in the listing (T2/T3) and for a session whose listing has dropped descriptions; it hurts whenever the skill is already listed with its description, because the listing is faster and at least as accurate, and whenever the request reaches the router as a summary. The dominant error in every arm is a naming collision (`tw-deploy`/`twp-deploy`, `zodal-ecosystem`/`zodal-collection-ui`), which no router fixes and a naming lint does.
6. **Where the code lives.** The generic strategy is in `aw` (`ConfidentRetrievalStrategy`, landed in thorwhalen/aw#5, with the search engine injected so `aw` gains no dependency). The retrieval engine and its calibration are `ir`'s. opsward owns the decision, the measurement and the diagnosis of what makes dispatch fail (naming collisions, shadowing, listing budget: #35).

Rejected: a router subagent as the entry point (measured: slower and no better); hybrid retrieval in the hot path (12 s per call for a worse score, RRF scores unusable for abstention); a catalog MCP server as the first surface (a tool must be called, the same failure mode as a skill, and the listing already has no decision point); summarising the request before routing (destroys the trigger).

## Consequences

- Nothing new runs by default. The measured path is the one every session already has; the code added is a strategy that returns `None` until calibration exists, so it cannot mis-route.
- The decisions the issue listed are answered with numbers: entry agents, zero new; boundary, floor from calibration plus a 0.9 relative gap after de-duplication; helps-vs-hurts, stated in §5 with the two conditions.
- Re-run the probe (`routing_probe.py`, ~70 Sonnet calls) after the corpus is de-duplicated or when a CLI version changes the listing budget; the decision stands while the listing stays at or above 12/14 on the probe set.
- priv#177 inherits this evidence: its package-scout and prompt-router hook remain gated, and the gate now has a baseline to beat.

## Evidence

- [thorwhalen/opsward#14](https://github.com/thorwhalen/opsward/issues/14) (the need) and `misc/docs/research/discovery_and_dispatch.md` §3 (the deliberation).
- `misc/docs/research/dispatch_probe.md` (the measurement) and `misc/docs/research/skill_tiering_and_reachability.md` §5.2, §7.
- [thorwhalen/aw#5](https://github.com/thorwhalen/aw/pull/5) (the strategy) and the PR that lands this record, linked from the index.
