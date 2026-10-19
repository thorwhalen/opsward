# Cheap-first dispatch, measured: listing vs router vs retrieval

**Scope.** The two experiments [thorwhalen/opsward#14](https://github.com/thorwhalen/opsward/issues/14) and the #23 report (§7) asked for, run on 2026-10-19 on the Mac: does a routing subagent beat the host's own skill listing, does a lossy summary destroy the trigger, and how good and how fast is deterministic retrieval over the skills corpus. The numbers back [ADR 0011](../decisions/0011-cheap-first-dispatch-no-router-agent.md). Scripts and raw results: `$PP/_agent_work/opsward/2026-10-19-skill-tiering/routing_probe.py`, `routing_probe.json`, `ir_eval.py`, `ir_eval.json`.

## Method

Fourteen prompts, one per T0 skill of the #23 report's always-on set, each written in the skill's own trigger vocabulary (the "raw" channel), plus a one-line paraphrase that drops the trigger words (the "summary" channel, e.g. "User wants a document's wording improved" for `deslop`). Expected answer: that skill.

Three arms through `claude --print` (Sonnet, the user's subscription, from a throwaway cwd so only the global scope is listed):

- **A, the host's listing**: the raw prompt in a normal session, with the instruction to invoke the applicable skill through the `Skill` tool and stop; scored from the session transcript's `Skill` call. This is what every session has today, at no extra hop.
- **B, router with a lossy channel**: a no-tools run holding the **full** catalog of all 121 global skills with complete descriptions (79,283 chars, nothing budget-dropped), given the summary, answering with one name.
- **C, router with the raw channel**: the same catalog, the raw prompt.

Deterministic arm, in-process: `ir.discover("skills", prompt, k=10)` on the live skills corpus (943 records, duplicates included), modes `lexical` and `hybrid`, strategies `score_gap` and `conservative`, both channels; top-1 after collapsing `name@base` copies; warm latency.

## Results

| Arm | raw prompt (n=14) | summary (n=14) | seconds per decision |
|---|---|---|---|
| A: host listing, no extra hop | **13/14** | n/a | 18.4 (a full turn) |
| B: LLM router, full catalog, summary | n/a | **11/14** | 14.5 |
| C: LLM router, full catalog, raw prompt | **12/14** | n/a | 15.3 |
| `ir` lexical / score_gap | **12/14** top-1 (13 in the selected set) | **0/14** | **0.19** |
| `ir` lexical / conservative | 12/14 | 0/14 | 0.05 |
| `ir` hybrid / score_gap | 11/14 | 4/14 (6 in set) | 12.5 |
| `ir` hybrid / conservative | 11/14 | 4/14 | 13.2 |

Misses, every arm: `twp-deploy` vs `tw-deploy` (two deploy skills; A and C chose `tw-deploy`, lexical ties them at an identical score 40.26, B chose `frontend`). Other misses: `crowsnest-worker` (B and C answered NONE; A found it), `setup-py-project` (B only, summary "start something new" went to `fleet-protocol`), `zodal-ecosystem` (lexical and hybrid: `zodal-collection-ui` outranks it, same score), `do-research` (hybrid only).

Abstention never fired in any `ir` arm. The reason is visible in the scores: the top two results are routinely the *same* skill in two corpus copies (`branch-hygiene`, `branch-hygiene@priv`) with identical scores, so every score-gap test sees a gap of zero between twins and a real gap only further down. Hybrid RRF scores sit around 0.03 with differences in the third decimal, which is the "unusable for abstention" finding of ir_07 reproduced on the live corpus.

## What the numbers say

1. **The listing already routes well.** 13/14 with no extra hop, and the one miss is a naming collision no router resolves (C missed it the same way).
2. **A router agent does not beat it.** With the complete catalog and the raw prompt it scores 12/14 at a cost of ~15 s and ~79k characters per decision, in a separate context. With a summary it drops to 11/14. The "two-stage routing destroys the trigger" risk is real but mild for an LLM router (one more miss) and severe for retrieval (lexical 0/14, hybrid 4/14 on summaries): whatever routes must see the user's words, never a paraphrase.
3. **Lexical retrieval is the only cheap layer.** 12/14 top-1 on raw prompts in 0.05–0.2 s, in-process; hybrid costs 12–13 s per call for a worse score. For skills outside the listing (T2/T3), lexical `ir discover` is the deterministic candidate generator, not a replacement for the listing.
4. **Abstention cannot be calibrated on this corpus yet.** Duplicate records tie at the top and defeat any gap test; the corpus needs de-duplication by skill name (the #23 census, priv#250) and a persisted lexical floor (`ir calibrate-min-score`, none exists for `skills`) before a floor or gap is meaningful. Filed on `ir`.
5. **Naming is the dominant error source.** `tw-deploy`/`twp-deploy` and `zodal-ecosystem`/`zodal-collection-ui` are the misses that repeat across arms; a naming lint (distinct prefixes, no near-duplicates) buys more accuracy than any routing machinery.

## Limits

- n=14, one prompt per skill, prompts written by the same author who knows the descriptions: an upper bound on trigger matching, not a user study.
- Single run per cell; the probe took one Sonnet call per arm and cell (42 + 28 calls, the router arms re-run once after a harness bug read a stderr warning as the answer).
- Arm A's latency includes the model's answer turn; the routing decision itself is a fraction of it.
- The `ir` corpus had 943 records for ~525 distinct skills; results after de-duplication may differ in both directions (fewer ties, but the surviving copy may be the stale one).
