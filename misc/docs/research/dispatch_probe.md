# Cheap-first dispatch, measured: listing vs router vs retrieval

**Scope.** The two experiments [thorwhalen/opsward#14](https://github.com/thorwhalen/opsward/issues/14) and the #23 report (§7) asked for, run on 2026-10-19 on the Mac: does a routing step beat the host's own skill listing, does a lossy summary destroy the trigger, and how accurate and how fast is deterministic retrieval over the skills corpus. The numbers back [ADR 0011](../decisions/0011-cheap-first-dispatch-no-router-agent.md). Scripts and raw results: `$PP/_agent_work/opsward/2026-10-19-skill-tiering/routing_probe.py`, `routing_probe.json`, `ir_eval.py`, `ir_eval.json`, `ir_eval.log`. An adversarial review of the first draft of this note recomputed every figure and corrected several; the corrections are folded in and the review's caveats are in Limits.

## Method

Fourteen prompts, one per T0 skill of the #23 report's always-on set, each written by the author in the skill's own trigger vocabulary (the "raw" channel), plus a one-line paraphrase that deliberately drops the trigger words (the "summary" channel, e.g. "User wants a document's wording improved" for `deslop`). Expected answer: that skill. The prompts are therefore the best case for description matching and the summaries the worst; neither is a sample of real requests.

Three arms through `claude --print` (Sonnet, the user's subscription, from a throwaway cwd so only the global scope is listed; every run also carried the user's global `CLAUDE.md` and hooks, which is what a real session carries too):

- **A, the host's listing**: the raw prompt in a normal session, with the instruction to invoke the applicable skill through the `Skill` tool and stop; scored from the session transcript's `Skill` call. This is what every session has today, at no extra hop. The instruction gives the model no "none" option.
- **B, router with a lossy channel**: a run with every tool denied, holding the **full** catalog of the 120 global skills that have a `SKILL.md`, with complete descriptions (79,283 chars, nothing budget-dropped), given the summary, answering with one name or NONE.
- **C, router with the raw channel**: the same catalog, the raw prompt.

B and C were run twice: the first run's harness read a stderr warning as the answer, so both were re-run with stdout-only parsing; the first run's transcripts were kept and re-scored from the assistant's final text, which gives a second draw of the same experiment.

Deterministic arm, in-process: `ir.discover("skills", prompt, k=10)` on the live skills corpus (943 records, duplicates included), modes `lexical` and `hybrid` (RRF fusion, as `ir` implements it today), strategies `score_gap` and `conservative`, both channels, **no `min_score` floor passed and none persisted for the corpus**; top-1 after collapsing `name@base` copies.

## Results

| Arm | raw prompt (n=14) | summary (n=14) | seconds per decision |
|---|---|---|---|
| A: host listing, no extra hop | **13/14** | n/a | 18.4 (a full turn, including the answer) |
| C: LLM router, full catalog, raw prompt | **12/14** in both runs (identical answers) | n/a | 15.3 |
| B: LLM router, full catalog, summary | n/a | **11/14** re-run, **9/14** first run (3 answers changed) | 14.5 |
| `ir` lexical / score_gap | **12/14** top-1 (13 in the selected set) | **0/14** | 0.04–0.06 after a 4 s cold first call |
| `ir` lexical / conservative | 12/14 | 0/14 | 0.05 |
| `ir` hybrid (RRF) / score_gap | 11/14 | 4/14 (6 in the set) | 12.5 |
| `ir` hybrid (RRF) / conservative | 11/14 | 4/14 | 13.2 |

Every `claude --print` call also waited about 3 s on stdin before starting, so the LLM latencies above are inflated by that much.

Misses. `twp-deploy` vs `tw-deploy`: A and C chose `tw-deploy` (whose own description also says "deploy apps to thorwhalen.com … check server status", and which the global `CLAUDE.md` routes "deploy to thorwhalen.com" to, so the gold label is contestable), B chose `frontend`, lexical ties the two at an identical score 40.26. `crowsnest-worker`: B and C answered NONE in both runs; A found it, but A had no NONE option. `setup-py-project` and `zodal-ecosystem`: B only (NONE in the first run, a wrong name or the right one in the re-run). `zodal-ecosystem` in retrieval: lexical top-1 `zodal-collection-ui`, hybrid top-1 `zodal-collections`. `do-research`: hybrid only.

Abstention never fired in any `ir` arm. The reason is that `ir`'s `score_gap` and `conservative` selectors abstain only on an empty result or when the top score is under an explicit `min_score`, and none was passed or persisted for the `skills` corpus; the scores themselves would not have helped either: a direct `ir discover` call before the eval returned `branch-hygiene` and `branch-hygiene@priv` as the top two with identical scores (copies of one skill from two bases), and hybrid RRF scores sit around 0.03 with third-decimal differences.

## What the numbers say

1. **The listing routes well.** 13/14 with no extra hop, on prompts written in the descriptions' vocabulary, with the global `CLAUDE.md` routes also present.
2. **No evidence that a router step beats it.** With the complete catalog and the raw prompt, C scored 12/14, one case below A; the single discordant case (`crowsnest-worker`) is one where A had no NONE option and C took it, so on n=14 the two arms are indistinguishable (exact McNemar p = 1). What a router step certainly adds is a separate call of ~15 s and a 79k-character context per decision.
3. **A summary costs accuracy, and the router arm is noisy.** B scored 11/14 and 9/14 on two draws of the same prompts, against C's 12/14 twice; the run-to-run variance of B (3 answers changed) is as large as the A-vs-C difference. The direction is consistent across both draws and matches retrieval, where a summary is fatal (lexical 0/14, hybrid 4/14): whatever routes should see the user's words, and a paraphrase should be assumed lossy.
4. **Lexical retrieval is the cheap layer, as `ir` is implemented today.** 12/14 top-1 on raw prompts at 0.05 s per call in-process; hybrid with RRF costs 11–13 s per call (the dense embedding path, reproducible after warm-up, not contention) for a worse score, and its scores are unusable for a gap test. `ir`'s `--fusion blend`, documented as better for abstention, was not tested. All fourteen targets are T0 skills that the listing already carries, so whether retrieval helps for skills *outside* the listing was not measured; it is the expected use, not a result.
5. **Abstention cannot be calibrated on this corpus yet.** No floor exists for `skills`; duplicate records tie at the top; a persisted lexical floor and de-duplication by skill name are prerequisites ([i2mint/ir#111](https://github.com/i2mint/ir/issues/111)).
6. **Naming collisions are the repeat offender.** `tw-deploy`/`twp-deploy` and `zodal-ecosystem`/`zodal-collection(s|-ui)` are the misses that recur across arms; distinct names and prefixes would buy more than routing machinery, with the caveat that the `twp-deploy` label itself is arguable.

## Limits

- n=14, one prompt per skill, prompts and summaries written by the same author who knows the descriptions: an upper bound on trigger matching and a lower bound on paraphrase, not a user study. No difference between arms here is statistically distinguishable; the latencies and the summary-channel collapse of retrieval are the robust findings.
- Arm A was forced to choose (no NONE), while B and C could abstain; arm A and arm C both ran with the global `CLAUDE.md` loaded, so A is "listing plus routes", not the listing alone, and C is "catalog plus listing plus routes", not a clean router.
- The gold label for the `twp-deploy` prompt is contestable; relabelled to `tw-deploy`, A scores 14/14 and C 13/14.
- One draw per cell for A and for retrieval; two for B and C (the first discarded for a harness bug, then re-scored from its transcripts).
- Every LLM latency includes ~3 s of stdin wait; A's includes the model's answer turn.
- The `ir` corpus had 943 records for ~525 distinct skills; results after de-duplication may differ in both directions.
