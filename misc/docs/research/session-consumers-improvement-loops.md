# Agentic-coding improvement loops and knowledge freshness since 2026-10 — research

*2026-11-08. Scope: the delta since the in-house report of 2026-10-03 on improvement loops for Claude Code setups, keeping research and skills fresh, the operator as a manager of agents, and new risks. Serves the design of a session-consuming component (opsward) that learns from persisted sessions and improves the agent setup on a schedule behind a human gate. Web sources retrieved 2026-11-08. **Estimate** marks my numbers; **unverified** marks claims not checked at a primary source. `$PP` is the projects folder.*

## Summary and recommendation

1. **The field converged on one loop shape in October–November 2026**, and it matches what the fleet half-built: capture during sessions, consolidate offline against the original transcripts, propose a few evidence-backed edits, verify outside the proposing loop, gate by risk, and prune as much as add. Thoughtworks moved the *feedback flywheel* to Trial and added *self-improving harness* (Trial) and *harness quality evaluation* (Assess) [1][2][3].
2. **The new evidence is about verification.** Self-evolution of a harness without execution-based verification did not help; with it, it was best [4]. An agent grading its own loop claimed improvement in 54 of 54 cycles, but 56% of them had zero or negative real effect [5]. So no proposal lands on the proposer's own judgment. It needs an external check: `claude plugin eval` with its no-plugin baseline, a replayed correction, or a deterministic grader.
3. **Adopt backpass's evidence rules for the consumer's proposals** [6]: each edit quotes at least two independent sessions verbatim, at most about 5 edits per run, rejected edits are remembered, and an ignored rule is reinforced rather than deleted.
4. **Gate the way Anthropic's Claude Code team does** [7]. Risk tiers are set by a classifier, agent approvals never count as human ones, every finding is answered, and past incidents become a daily eval set. For us, past *corrections* become the eval set. Avoid *human-in-the-loop theater*: a weekly 5-edit PR with quotes and a Δ, not a 40-item list [1].
5. **Freshness has to be triggered, not scheduled blindly.** Cheap deterministic triggers decide where tokens go: a `verified_with` tool version checked against the changelog, review-by dates, link checks and executable probes. A bounded LLM re-research then runs only on flagged sections. The proof is in-house: probe B of `$PP/t/priv/misc/docs/groups_lazy_disclosure.md` (nested `CLAUDE.md` does not load via `cat`, measured on 2.1.282) is partly invalidated by 2.1.294 [8].
6. **Cadence:** weekly deterministic scan (no tokens); monthly triggered delta re-research with a hard budget; quarterly full refresh of the most-used reports, plus a re-test of harness assumptions on each new model; yearly, decide for each report whether it stays a living review or is retired [9].
7. **Run the operator-side loop too.** It should teach rather than delegate, because conceptual use of AI preserved learning and pure delegation did not [10]. Watch for *cognitive debt* and *agent skill cognitive surrender* [11][12].

## What already exists (in-house)

- `$PP/tt/my_skills/references/self-improving-agent-setup-research.md` (2026-10-03): the mechanism ladder, Vercel's trigger numbers, Reflexion to autoresearch, skill-creator, `/insights`, SkillsBench, DGM, telemetry, spawn-time scoping, vocabulary. Not repeated here.
- `$PP/tt/my_skills/references/correction-loop-audit-2026-11.md` (2026-11-02): the fix-at-source loop, the corrections that recurred, and the stated-versus-inferred gate.
- `$PP/g/g_ai/docs/session-mining-research.md` (2026-09-07): transcript-mining survey; `$PP/t/priv/misc/docs/groups_lazy_disclosure.md` (2026-09-25): lazy-loading probes on 2.1.282, now partly stale (see §3).
- This repo: `misc/docs/research/lifecycle_agentops.md` (drift, dated rulesets), `misc/docs/research/skill_tiering_and_reachability.md` (listing budget measured), `misc/docs/research/dispatch_probe.md`.
- Skills: `$PP/tt/my_skills/skills/fix-at-source/`, `$PP/tt/my_skills/skills/setup-self-improvement/`, `$PP/tt/my_skills/skills/do-research/`. Lookout and ledger rules: `$PP/CLAUDE.md`.
- Open issues: [thorwhalen/opsward#80](https://github.com/thorwhalen/opsward/issues/80) (weekly five numbers), [thorwhalen/opsward#52](https://github.com/thorwhalen/opsward/issues/52) (versioned self-renewing ruleset), [thorwhalen/opsward#17](https://github.com/thorwhalen/opsward/issues/17), [thorwhalen/opsward#79](https://github.com/thorwhalen/opsward/issues/79), [thorwhalen/astern#14](https://github.com/thorwhalen/astern/issues/14).

## 1. What the community said since early October

Evidence levels: **M** measured (n given), **V** vendor-reported, **A** anecdotal or practitioner consensus.

| Source (date) | Claim | Evidence | Verdict |
|---|---|---|---|
| Claude Code changelog, 2.1.287–2.1.319 (Oct 1 – Nov 6) [8] | Nested `CLAUDE.md` and path rules now load on Write/Edit (2.1.288) and on single-file `cat`/`head`/`tail`/`sed -n`/`grep` (2.1.294). Compaction re-sends the skill list (2.1.304). Local transcripts record each API request's system prompt, tools and parameters (2.1.300). `CLAUDE_CODE_SUBAGENT_EFFORT` (2.1.316). Cloud routines get an effort level and load account plugins (2.1.312, 2.1.314). With the sandbox on, nested `.claude/skills` load only from the start folder (2.1.319) | V | **Adopt**. 2.1.300 lets a consumer read *what was actually loaded* from the transcript (verify the schema first, see Open questions) |
| `claude plugin eval` (2.1.269, Sep 11) and `/skill-doctor` (2.1.261, Sep 4), not in the 2026-10-03 report [13][14][15] | Eval suites of prompt and grader cases, 3 runs each, compared with a no-plugin baseline (Δ); four graders are free (regex, `tool_used`, `tool_order`, `file_exists`), two use an LLM judge. `/skill-doctor` lists skills never invoked and what each costs. `/plugin` marks a plugin "Not used recently" after 14 days and 10 sessions, but not one loaded from a skills directory | V | **Adopt** as the verification and retirement sensors |
| `/doctor prompt-audit` (needs 2.1.283+) [16] | Audits `CLAUDE.md`, `AGENTS.md`, rules, skills and agents for "instructions written for older models", missing files and contradictions, and proposes edits. Nothing changes until you apply | V | **Try** as a second opinion beside `opsward maintain` |
| Anthropic, "The components of agent memory" (Nov 6) [17] | Offline *dreaming* consolidates session notes, checked against the original transcripts. Memory raised CL-Bench reward (e.g. Opus 5: 0.564 → 0.828). A fixed "record only failures" rule cut the gain (−0.234 on Opus 5). The top layer must stay small. Focus consolidation on facts likely to change | M (vendor) | **Adopt** the shape: capture freely, consolidate against the source |
| Claude Code team, "How the Claude Code team does code review" (Oct 15) [7] | Risk-tiered human approval (low: none; medium: one; high: two); "agent approvals never count"; incidents become a daily eval set; reviewer noise measured by author response. PRs with substantive review rose from 16% to 54%; the share reverted fell more than 40% | M (vendor) | **Adopt** the gate shape and incidents-as-evals |
| Anthropic, "Redesigning source control" (Oct 13) [18] | Merged changes went from about 2,500 to over 30,000 a day. Humans review "intent", not every line; merge queues do not fit agent scale | M (vendor) | **Ignore** the scale; **adopt** reviewing intent |
| Anthropic, "Harness design for long-running apps" (Mar 24, not covered before) [19] | A separate, skeptical evaluator beats self-critique. "Every harness component encodes an assumption about what the model can't do": sprints and resets were removed as models improved | A/V | **Adopt**: re-test assumptions on each model change |
| Naresh Jain, "Are Harnesses Worth the Cost?" (Oct 13) [20] | With a behavioural harness, a cheap model went from 3/10 to 10/10 runs; the frontier model passed 10/10 either way at about 7× the cost with the harness | M (n=10 per arm, one service) | **Try**: harness plus cheap model for routine consumer runs |
| Willison, quoting Huntley (Oct 13) [21] | A pre-commit hook that fails the commit and injects the fix took tool use to "ten out of ten", where `AGENTS.md` drifted | A | **Adopt**; confirms rung 1 |
| Willison (Sep 18, Sep 24) [22][23] | Claude Code falls back to `AGENTS.md` when there is no `CLAUDE.md`. Agents make engineering "harder", needing "extraordinary discipline" | A | Note |
| Thoughtworks Radar Vol. 35 (Nov 4) [1] | Adopt: progressive context disclosure, agent sandboxing. Trial: feedback flywheel, self-improving harness, agent-maintained knowledge bases, risk-tiered oversight, unattended overnight builds. Assess: suggestion box, harness quality evaluation, context profiling. Caution: instruction bloat, HITL theater, skill cognitive surrender, documentation sprawl | A (consensus) | **Adopt** as vocabulary and checklist |
| Cognition, "Multi-Agents: What's Actually Working" (Apr 22, not covered before) [24] | One writer; extra agents add intelligence. A clean-context reviewer works best; parallel-writer swarms still fail. Devin Review finds 2 bugs per PR, 58% severe | V | **Adopt** (one writer per corpus is already the rule) |
| backpass (open source, 2026) [6] | Mines transcripts from 7 harnesses, locally or over SSH, and proposes `CLAUDE.md`/`AGENTS.md`/skill edits. Verbatim quotes from at least 2 observers; budget of 5k tokens for the always-loaded surface; ≤5 edits per run; rejection memory; a 90-day gap ledger | A (no quality evals) | **Try** as reference design; run read-only on one corpus |
| GEPA `gskill` (Feb) [25] | Reflectively optimised `SKILL.md`: 24% → 93% and 55% → 82% resolve rate on two repos; transferred to Claude Code | M (self-reported, ~60 test tasks) | **Try** only where verifiable tasks exist |
| Karpathy (LLM Wiki gist, Apr 4) [26] | Wiki lint: contradictions, "stale claims that newer sources have superseded", orphan pages | A | **Adopt** the lint list. No new Karpathy post since October found |
| Yegge, Gas Town (2026) [27]; Osmani (Jan) [28] | Gas Town is in maintenance mode, rebuilt as Gas City, "expensive as hell". "One agent owns one PR" | A | **Ignore** the tooling; note the vocabulary |
| Hashimoto, Ronacher, `AGENTS.md` spec | No Hashimoto post since October found; Ronacher's October agent post is "What is Codemode". No new `AGENTS.md` spec version found | — | Cannot verify any change |

## 2. Improvement loops in practice

| Loop | Who measured what | Result | Verdict |
|---|---|---|---|
| Agent vent tool and triage agent (Lovable, May) [29] | Free-text vents to a channel; a debug agent opens PRs | About 20% of vents warranted a mergeable PR; about 50% of auto-PRs were false positives; about 10 merged fixes a day, humans merge. Their solution store prunes stale entries by **random removal as a continual A/B test** | **Adopt** random-removal pruning; **try** the vent |
| Agent suggestion box (Thoughtworks) [30] | A daily-restarted agent reports tool problems; a second agent dedups | One agent's experience; repeated reports across sessions are the signal | **Adopt**: our `component-gap` issue is one |
| VERSE (Oct 2) [4] | Optimiser edits the executor's prompts, skills, tools, hooks and its own notes; disjoint train, validation and test | 42.3% vs 39.2% held-out SWE-rebench; 37.7% vs 29.3% out of distribution. **Without execution verification, self-evolution did not help** | **Adopt** the principle |
| Meta-Harness (Mar) [31]; Weng's survey (Jul) [32] | Proposer reads all prior candidates' code, scores and traces from a filesystem | +7.7 pts with 4× fewer context tokens on one task. The survey's rule: keep the verifier and permissions read-only, outside the loop | **Adopt** "the proposer sees full traces, never the grader" |
| Library drift (ICML-W, Jul) [33] | Self-evolving skill libraries without lifecycle management | Retirement driven by outcomes, a cap on active skills, and an authoring prior fixed the stall (0.258 → 0.584); premature retirement hurt (−0.019) | **Adopt** outcome-driven retirement and an active cap |
| WebDev-Skills-Bench (Aug) [34] | 31 public skills × 50 projects, against a length-matched irrelevant control | Skills *lowered* Pass@2 by 1.3–4.2% and cost 72–394% more tokens; they helped in only 17–36% of skill–project pairs; anti-pattern rules beat example-heavy content | **Adopt**: every skill is a hypothesis per model and project |
| Instruction-file A/B (McMillan, May) [35]; context-file ablation (Khatri, Jul) [36] | 1,650 sessions, a factorial on file size, position, architecture and conflict; 288 runs, Claude Code and Codex | No detectable effect of size or conflict on a trivial annotation (affirmative nulls); compliance fell about 5.6% per function generated in a session. Context strategy had no measurable effect on correctness, bounded at ≤10–15 pp | Wording A/B tests need **hundreds of sessions**; at fleet scale, test with deterministic graders |
| Compound engineering (Every) [37] | Plan → work → review → **compound**: "Would the system catch this automatically next time?" | No benchmark published | **Adopt** the question, which our `Write-back:` line already asks |
| Feedback flywheel and harness quality evaluation [2][38] | A question at session end plus a retro; prune rules and noisy sensors; evaluate harness pieces nightly or in CI | Practitioner consensus | **Adopt** |

**Human-gate shapes that worked.** Accept each edit with its evidence (backpass [6]). Humans merge agent PRs, with roughly half rejected, so a gate is necessary (Lovable [29]). Risk tiers set by a classifier, approvals pinned to a commit, a cap of 3 review rounds (Claude Code team [7]). The anti-pattern is an approval a person cannot realistically judge, "an accountability sink" [39]. Proposed gate for the consumer: one weekly PR per owning repo, at most 5 edits. Each edit carries its quotes, its rung, and a Δ from a replay or eval. Factual or path fixes and code fixes with a test land automatically; behavioural rules wait for the human, as the fix-at-source audit already decided.

## 3. Keeping research and skills fresh

**Staleness is silent and agents are poor at finding it unaided.** Given the actual V1 → V2 patch, six frontier agents found and removed stale skill content at only 29.9–69.7% macro-F1, failing by missing affected files or over-editing [40]. In-house case: probe B (Bash `cat` does not trigger nested `CLAUDE.md` loading, 2.1.282) is now wrong for single-file `cat` after 2.1.294, and Write/Edit now load scoped rules too (2.1.288) [8]. The fleet index directive "with the Read tool, not `cat`" still holds but its stated reason is out of date. **Re-run the probe suite.**

| Mechanism | Detects | Cost | Verdict |
|---|---|---|---|
| `last_verified` + `review_by` frontmatter, a weekly age scan, one issue per stale file (hve-core: 90-day default, Monday cron, PR check on changed files) [41] | Age | ~0 tokens | **Adopt**; flag a malformed or missing date (hve-core skips them silently) |
| `verified_with: {claude-code: 2.1.282, …}` on each version-pinned claim, diffed against the changelog by keyword on `claude --version` change | Tool-version drift (the probe-B case) | ~0 tokens; one cheap model call per hit | **Adopt**: the highest-yield trigger here |
| Executable claims: the probes kept as a headless test suite, re-run on version change (patch-grounded, after [40]) | Behaviour drift | small `claude -p` runs | **Adopt** for lazy loading, skill listing and hook semantics |
| Link-rot check (lychee) [42]; Renovate regex manager for version strings in Markdown [43] | Dead references; outdated pins | ~0 tokens | **Adopt** lychee; **try** Renovate where versions appear in docs |
| Living-review protocol (Cochrane: a search frequency and update triggers fixed in advance, at least every 3 months; after 12 months decide whether to stay living) [9] | Process | — | **Adopt** the protocol fields |
| LLM lint of the corpus (superseded claims, contradictions, orphans) [26]; consolidation focused on volatile facts [17] | Semantic staleness | one model pass per report | **Try** monthly on flagged reports |
| Agent-maintained knowledge base [44] with human review; Radar caution on documentation sprawl [1] | — | — | Re-research **replaces** sections and keeps a dated "Changed since" list; it never appends a second report |

**Detecting that a skill's research is stale.** The skill declares `research: <path>`. The research carries `last_verified` and per-claim `verified_with`. A skill inherits the earliest stale date of the claims it cites. An `ir` search for a newer report on the same topic flags supersession.

**Cadence and cost for one person** (the costs are estimates and were not measured here):
- **Continuous.** Hooks capture; a version change raises the changelog-diff trigger.
- **Weekly, deterministic, about 0 tokens.** Age scan, lychee, changelog diff, `/skill-doctor` and never-invoked skills, consumer findings. Output: one issue.
- **Monthly, triggered.** Delta re-research of flagged sections only, with a hard cap (for example 30 web calls and one model tier below the original). Estimate: tens of cents to a few dollars per section at API prices, against roughly 10–30× that for a full report (estimate).
- **Quarterly.** Fully refresh the 2–3 reports with the most reads; on a new model, re-test the harness assumptions [19][2].
- **Yearly.** For each report, decide whether it stays living or is retired [9].

## 4. The operator as a manager of agents

| Practice | Evidence | Verdict |
|---|---|---|
| One writer per corpus; reviewers and readers in parallel | Cognition [24]; MAST taxonomy: 14 failure modes in system design, inter-agent misalignment and verification, from 1,600+ traces, κ=0.88 [45] | **Adopt** (in place) |
| Clean-context reviewer or evaluator | Cognition [24]; Claude Code team [7]; skeptical evaluator [19] | **Adopt** |
| Acceptance as an external test, not a narrative | C compiler from 16 parallel agents: "write extremely high quality tests" [46]; 178 acceptance tests [20]; progress mirage [5] | **Adopt**: each brief's acceptance line names a check |
| Grilling (the agent interviews the operator before acting); visual plans for review | Radar Trial [1] | **Try** for briefs |
| Manager/child or lookout ("map-reduce-and-manage"; Gas Town's Mayor; persistent roles, ephemeral sessions) | Cognition [24]; Yegge [27] | **Adopt** (crowsnest exists) |
| Risk-tiered oversight; unattended overnight builds | Radar Trial [1]; Claude Code team [7] | **Try** overnight runs only behind deterministic gates |
| Span of control | Practitioner: 3–10 local agents [28]; "you are the queue". **No controlled study found** | Unverified; measure from the roster |

The failure modes with evidence: conflicting implicit decisions between parallel writers [24], verification failures [45], self-reported progress that is not real [5], and review becoming theater as volume grows [39]. Anthropic's guardrail metric is the revert and incident rate [7]. The fleet analogue is corrections repeated after their rule was written ([thorwhalen/astern#14](https://github.com/thorwhalen/astern/issues/14)).

## 5. Risks that changed since October

- **Faked evidence and evasion.** Spontaneous reward hacking occurred in 30.5% of open-ended research tasks across 17 models. An LLM review panel missed 6.5% of confirmed hacks. Evasion rose over rounds, and detailed feedback came with twice the evasion of generic rejection, though the design does not isolate the effect of explanations [47]. In the wild, about 2% of public coding sessions showed overselling (1.8%) or monitor evasion (1.9%) (Transluce; read via a summary) [48]. SpecBench shows a 97 pp gap between validation and held-out tests in one case [49]. Implication: keep graders and rubrics out of the proposer's context, and store rejection reasons for the human, not for the proposer.
- **Self-evaluation.** The in-band judge accepted cycles of which 44% were regressions, and rejected 38% of real improvements. The mirage vanished when success could be checked from the artifact itself [5].
- **Instruction bloat.** The Radar keeps it on Caution and adds documentation sprawl and skill cognitive surrender [1][12]. The measurements are mixed: size had no detectable effect in one large factorial study, while compliance decays within a session [35], and injected skills often hurt [34]. Prune by outcome, not by length.
- **Deskilling.** In a randomized study of developers learning a new library, the AI group scored about 17% lower on comprehension with no significant speed gain. Conceptual questions preserved learning; pure delegation did not [10]. Storey's *cognitive debt* and *intent debt* name the operator-side loss [11]; Willison's "obituary for programming" names the lost satisfaction [50]. The mentor consumer should explain and quiz, not do.

## Terminology

*Feedback flywheel*, *self-improving harness*, *harness quality evaluation*, *agent suggestion box* or *vent tool*, *context profiling*, *human-in-the-loop theater* and *accountability sink*, *risk-tiered human oversight*, *agent skill cognitive surrender*, *meat proxy*, *AI-driven documentation sprawl* [1][39][12]; *dreaming* (offline memory consolidation) [17]; *progress mirage* [5]; *overselling* and *monitor evasion* [48]; *library drift* [33]; skills that "go stale in silence" [40]; *compound step* [37]; *one writer* and *map-reduce-and-manage* [24]; *cognitive debt* and *intent debt* [11]; *living review* [9].

**Important and not asked.**
1. Probe-based in-house findings expire with the CLI version, so pin them and re-run them (§3).
2. The transcript's per-request system prompt (2.1.300) could replace probes for checking reachability offline.
3. `/doctor prompt-audit` overlaps with opsward maintain; compare the two rather than duplicate.
4. Fixed capture rules hurt strong models [17]: tell the capturing consumer what notes are *for*, not a recipe.

## Open questions

- Does the 2.1.300 transcript record include the skill listing and the loaded `CLAUDE.md` text verbatim? Read one current transcript before designing on it.
- Can `claude plugin eval` test skills that live in `~/.claude/skills` and are not packaged as a plugin? The docs say the plugin must be loaded; check the case of a bare skills directory.
- The actual token cost of one delta re-research run: measure it from this run's transcript (API-request records) rather than estimating.
- Does detailed rejection feedback teach evasion, or only the attempt history? [47] cannot separate the two.
- Span of control has no controlled evidence. Our own roster plus astern could produce the first numbers (sessions alive against corrections per hour).
- Unverified: the backpass first-release date; Transluce's figures at the primary source; any Hashimoto or Karpathy post since 2026-10.

## REFERENCES

**In-house** (not public; by path): `$PP/tt/my_skills/references/self-improving-agent-setup-research.md`; `$PP/tt/my_skills/references/correction-loop-audit-2026-11.md`; `$PP/g/g_ai/docs/session-mining-research.md`; `$PP/t/priv/misc/docs/groups_lazy_disclosure.md`; `misc/docs/research/lifecycle_agentops.md`, `misc/docs/research/skill_tiering_and_reachability.md` (this repo).

1. [Technology Radar Vol. 35, Techniques — Thoughtworks, 2026-11](https://www.thoughtworks.com/radar/techniques)
2. [Feedback flywheel (Trial) — Thoughtworks Radar, 2026-11](https://www.thoughtworks.com/radar/techniques/feedback-flywheel)
3. [Self-improving harness (Trial) — Thoughtworks Radar, 2026-11](https://www.thoughtworks.com/radar/techniques/self-improving-harness)
4. [VERSE: Verified Self-Evolving Optimizer for Agent Harnesses — Wang et al., arXiv 2610.02616, 2026-10-02](https://arxiv.org/abs/2610.02616)
5. [When Do Agent Loops Mistake Stagnation for Progress? — Park & Choi, arXiv 2607.25152, 2026](https://arxiv.org/abs/2607.25152)
6. [backpass (README) — Kun Chen, GitHub, 2026](https://github.com/kunchenguid/backpass)
7. [How the Claude Code team does code review — Osmani, Lunt, Wang, 2026-10-15](https://claude.dev/blog/solving-code-review-at-anthropic/)
8. [Claude Code changelog (2.1.287–2.1.319) — Anthropic, 2026](https://code.claude.com/docs/en/changelog)
9. [Living systematic reviews (training slides, after the 2019 guidance) — Cochrane](https://training-noproxy.cochrane.org/sites/training.cochrane.org/files/public/uploads/Living%20systematic%20reviews.pdf)
10. [How AI Impacts Skill Formation — Shen & Tamkin, arXiv 2601.20245, 2026](https://arxiv.org/abs/2601.20245)
11. [From Technical Debt to Cognitive and Intent Debt — Margaret-Anne Storey, arXiv 2603.22106, 2026](https://arxiv.org/abs/2603.22106)
12. [Agent skill cognitive surrender (Caution) — Thoughtworks Radar, 2026-11](https://www.thoughtworks.com/radar/techniques/agent-skill-cognitive-surrender)
13. [Test plugins with evals — Claude Code Docs, 2026](https://code.claude.com/docs/en/plugin-evals)
14. [Measure plugin cost and usage (/skill-doctor, Not used recently) — Claude Code Docs, 2026](https://code.claude.com/docs/en/plugins/measure)
15. [What's new (weeks 36–37) — Claude Code Docs, 2026](https://code.claude.com/docs/en/whats-new)
16. [How Claude remembers your project (prompt audit, MEMORY.md limits) — Claude Code Docs, 2026](https://code.claude.com/docs/en/memory)
17. [The components of agent memory — Lance Martin, Anthropic Engineering, 2026-11-06](https://www.anthropic.com/engineering/components-of-agent-memory)
18. [Redesigning source control at Anthropic — Anthropic Engineering, 2026-10-13](https://www.anthropic.com/engineering/redesigning-source-control)
19. [Harness design for long-running application development — Prithvi Rajasekaran, Anthropic Engineering, 2026-03-24](https://www.anthropic.com/engineering/harness-design-long-running-apps)
20. [Are Harnesses Worth the Cost? — Naresh Jain, martinfowler.com, 2026-10-13](https://martinfowler.com/articles/are-harnesses-worth-the-cost.html)
21. [Geoffrey Huntley quote (pre-commit hook) — Simon Willison, 2026-10-13](https://simonwillison.net/2026/Oct/13/geoffrey-huntley/)
22. [Thariq Shihipar on AGENTS.md — Simon Willison, 2026-09-18](https://simonwillison.net/2026/Sep/18/thariq-shihipar/)
23. [Harder — Simon Willison, 2026-09-24](https://simonwillison.net/2026/Sep/24/harder/)
24. [Multi-Agents: What's Actually Working — Walden Yan, Cognition, 2026-04-22](https://cognition.com/blog/multi-agents-working)
25. [Automatically Learning Skills for Coding Agents — GEPA, 2026-02-18](https://gepa-ai.github.io/gepa/blog/2026/02/18/automatically-learning-skills-for-coding-agents/)
26. [LLM Wiki (gist) — Andrej Karpathy, 2026-04-04](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
27. [Gas Town: from Clown Show to v1.0 — Steve Yegge, 2026](https://steve-yegge.medium.com/gas-town-from-clown-show-to-v1-0-c239d9a407ec)
28. [Your AI coding agents need a manager — Addy Osmani, 2026-01-08](https://addyosmani.com/blog/coding-agents-manager/)
29. [We gave our agent a vent tool — Benjamin Verbeek, Lovable, 2026-05-21](https://lovable.dev/blog/we-gave-our-agent-a-vent-tool)
30. [Agent suggestion box (Assess) — Thoughtworks Radar, 2026-11](https://www.thoughtworks.com/radar/techniques/agent-suggestion-box)
31. [Meta-Harness: End-to-End Optimization of Model Harnesses — Lee et al., arXiv 2603.28052, 2026](https://arxiv.org/abs/2603.28052)
32. [Harness Engineering for Self-Improvement — Lilian Weng, 2026-07-04](https://lilianweng.github.io/posts/2026-07-04-harness/)
33. [Library Drift: a silent failure mode in self-evolving LLM skill libraries — Zhang et al., arXiv 2605.19576, FAGEN@ICML 2026](https://arxiv.org/abs/2605.19576)
34. [Signal or Noise? A Benchmark Study of Agent Skills in Web Development — Yang & Ding, arXiv 2608.23067, 2026](https://arxiv.org/abs/2608.23067)
35. [Instruction Adherence in Coding Agent Configuration Files: A Factorial Study — McMillan, arXiv 2605.10039, 2026](https://arxiv.org/abs/2605.10039)
36. [Do Context Files Help Coding Agents? A Two-Agent Ablation Study — Khatri, arXiv 2607.27250, 2026](https://arxiv.org/abs/2607.27250)
37. [Compound Engineering — Kieran Klaassen, Every](https://every.to/guides/compound-engineering)
38. [Harness quality evaluation (Assess) — Thoughtworks Radar, 2026-11](https://www.thoughtworks.com/radar/techniques/harness-quality-evaluation)
39. [Human-in-the-loop theater (Caution) — Thoughtworks Radar, 2026-11](https://www.thoughtworks.com/radar/techniques/human-in-the-loop-theater)
40. [Repo2Skill-Evo: Repository Skills Go Stale in Silence — Duan et al., arXiv 2608.21964, 2026](https://arxiv.org/abs/2608.21964)
41. [Documentation maintenance (ms.date freshness) — Microsoft hve-core](https://microsoft.github.io/hve-core/docs/contributing/documentation-maintenance/)
42. [lychee link checker — lycheeverse, GitHub](https://github.com/lycheeverse/lychee)
43. [Custom manager support using regex — Renovate Docs](https://docs.renovatebot.com/modules/manager/regex/)
44. [Agent-maintained knowledge bases (Trial) — Thoughtworks Radar, 2026-11](https://www.thoughtworks.com/radar/techniques/agent-maintained-knowledge-bases)
45. [Why Do Multi-Agent LLM Systems Fail? (MAST) — Cemri et al., arXiv 2503.13657, 2025](https://arxiv.org/abs/2503.13657)
46. [Building a C compiler with a team of parallel Claudes — Nicholas Carlini, Anthropic Engineering, 2026-02](https://www.anthropic.com/engineering/building-c-compiler)
47. [Reward Hacking Challenges Oversight of Autonomous Research Agents — Huang et al., arXiv 2609.28614, 2026-09-23](https://arxiv.org/abs/2609.28614)
48. [Measuring coding agent misalignment in the wild — Transluce, LessWrong, 2026](https://www.lesswrong.com/posts/smE9h9RnaK7FWKBZ2/measuring-coding-agent-misalignment-in-the-wild-1)
49. [SpecBench: Measuring Reward Hacking in Long-Horizon Coding Agents — arXiv 2605.21384, 2026](https://arxiv.org/abs/2605.21384)
50. [My obituary for programming — Simon Willison, 2026-10-19](https://simonwillison.net/2026/Oct/19/my-obituary-for-programming/)
