# Lifecycle, Governance, and Validation of AI Agent Setups

## Abstract

The configuration layer that steers coding agents — `CLAUDE.md`, `AGENTS.md`, skills, subagents, rules, hooks, and MCP server definitions — is now a first-class software artifact, but it rots faster than the code it describes and faster than the conventions that produced it. An emerging practice variously called **AgentOps** / **context engineering ops** is forming around six concerns: drift detection, evaluation, validation/linting, versioning/governance, fleet-scale consistency, and surviving ecosystem churn [1][4][5]. This report surveys the 2024–2026 state of each, with primary engineering sources, and grounds it in the user's own tooling — `opsward`, which already implements a deterministic scan→score→maintain pipeline plus spec validation — to separate "compose what exists" from "build new." The throughline: opsward already covers most of the *single-repo, deterministic* surface; the open frontier is *cross-repo fleet governance*, *eval-based (not just rubric-based) quality*, and a *self-renewing rubric* that absorbs best-practice change automatically.

## Scope

This report concerns the **setup artifacts**, not the agent's runtime outputs. We are asking: how do you keep the *instructions to the agent* correct and current as (a) the code they describe changes, (b) the host tooling churns (new formats, new hook events, new MCP shapes), and (c) community best practice evolves? We treat the agent config as config-as-code and borrow heavily from IaC drift detection, prompt-versioning, and LLM-eval disciplines. Out of scope: model selection, agent runtime tracing/observability except where it informs config quality, and end-user product evals.

## 1. The discipline: is "AgentOps" real, and what does it cover?

Yes, with caveats. **AgentOps** is being used in 2025–2026 as the superset of LLMOps specialized for autonomous, multi-step agents: design, deploy, monitor, optimize, and *govern* agents in production [4][5]. The crisp distinction in the literature: LLMOps covers single-call applications (tracing, prompt management, eval of one completion); AgentOps adds execution-graph visualization, multi-turn/trajectory evaluation, tool-call correctness, and workflow optimization [4]. MLflow and others frame **LLMOps** as the lower tier (prompt registry, eval, deployment) on which AgentOps sits [6].

Distinct from both is **context engineering**, which Anthropic defines as "the art and science of curating what will go into the limited context window from [a] constantly evolving universe of possible information" — system instructions, tools, MCP, external data, message history [1]. The setup layer this report covers *is* the persistent, authored slice of that context. There is not yet a settled term for the *operational maintenance* of that authored slice; "context engineering ops" is the most honest label. The practical point for opsward: the field has named the problem (config drift, eval, governance) but the tooling is fragmented across prompt-ops platforms (built for product prompts, not repo config) and a thin layer of brand-new config linters. There is room for a tool that treats *repo agent config* as the unit of operation.

## 2. Staleness & drift: two kinds, and the IaC analogue

Drift here has two faces, and conflating them is a common error.

**Code drift (config-vs-reality):** the config describes a world that no longer exists — a renamed module, a removed CLI flag, a moved docs path, a build command that changed. This is mechanically detectable and is exactly what IaC drift detection solves: `terraform plan -refresh-only` compares declared state against actual state and reports divergence, with three remediation paths — *revert* (code is truth), *align* (reality is truth, update the code), or *ignore* (mark a field as legitimately volatile) [20]. The GitOps refinement is *continuous reconciliation*: run the diff on a schedule in CI and alert (or auto-correct) on divergence [20]. This maps directly onto agent config: a scheduled job that re-parses path/command tokens out of `CLAUDE.md` and resolves them against the repo, emitting a typed diff. opsward's `_check_stale_paths` and `sync_issue`/`outdated_doc` categories in `opsward/maintain.py` are precisely the "refresh-only plan" for the path/docs surface; what is missing is the *revert/align/ignore* triage vocabulary and a way to mark a reference as intentionally volatile.

**Best-practice drift (config-vs-norm):** the config is internally accurate but stale against evolving convention — it still uses a deprecated hook event, lacks a post-compaction recovery instruction, or predates the AGENTS.md symlink pattern. This is *not* detectable by diffing against the repo; it requires a versioned external notion of "good." Community guidance has crystallized concrete anti-drift techniques: put hard constraints at the top (attention bias), use commanding "always/never/must" language for invariants vs soft "should," delegate deterministic formatting to scripts rather than prose, add *canaries* that confirm the file was read, and include explicit post-compaction "re-read CLAUDE.md and the plan file" instructions because most drift surfaces after context compression [7][2]. Claude Code itself now ships a memory-reconciliation system prompt that flags possible CLAUDE.md drift during consolidation [2]. The key architectural insight: best-practice drift can only be measured against a **dated, versioned ruleset** — which is the seed of Recommendation 3.

## 3. Evaluation of agent setups (not just agent outputs)

Measuring whether a `CLAUDE.md` or skill *actually helps* is the least mature area, and the most valuable. Two complementary techniques dominate the 2025–2026 literature:

**Rubric scoring (deterministic, cheap).** A fixed set of weighted dimensions scored by rules — this is what opsward's `opsward/score.py` does today (CLAUDE.md across 6 dimensions, overall weighted CLAUDE.md 35 / Docs 25 / Skills 20 / Setup 10 / Cross-ref 10, graded A–F). It is reproducible, fast, CI-friendly, and explainable. Its ceiling is that it measures *form*, not *effect*: a CLAUDE.md can score an A and still mislead the agent.

**LLM-as-judge (judgment, expensive, noisy).** A capable model scores an artifact against a rubric, returning structured scores plus reasoning [12][13]. The hard-won lessons: the *judge's own prompt* must encode an explicit rubric (vague "rate quality" yields noise) [12]; four biases — position, verbosity, self-preference, authority — appear in every untreated judge and must be designed against; and 5–10% of verdicts should be spot-checked against human judgment [13][14]. Critically, **better-looking prompts can score better yet perform worse**, which is why eval must be tied to a downstream task signal, not to the judge's aesthetic preference [evaluation-driven iteration, 12].

**The agent-specific twist: trajectory evals.** Agents evaluated only on final output pass 20–40% more cases than trajectory-level evaluation reveals; the real failure surface is at the step level — tool-call arguments, state propagation, goal-alignment drift [15]. Anthropic's own "Demystifying evals for AI agents" argues evals must measure the *process*, not just the answer, and that you build them from real failure transcripts [3]. The pattern that ports to config quality: maintain a set of **golden tasks** per repo (e.g., "add a function honoring our keyword-only convention," "find where X is configured"), run an agent with vs. without a candidate CLAUDE.md/skill, and score whether the documented convention was actually followed. The same eval definitions should run locally, in CI, and in production [15][16]. This is how you turn "does this skill help?" from opinion into a regression-tested number — and it is exactly the layer opsward lacks today. Anthropic's `skill-creator` already ships a narrow instance of this: a description optimizer that uses train/test splits to tune skill *triggering* accuracy [foundational report].

## 4. Validation & linting: a fast-moving, directly competitive layer

This is the most crowded new niche, and several tools landed in 2025–2026 that overlap opsward's `validate_skill_spec`/`validate_hooks_config`:

- **Agnix** (Show HN, late 2025) lints AI agent configs across `CLAUDE.md`, skills, MCP servers, and hooks; its motivating example is the silent-failure class — a skill with an invalid name format that the host simply ignores, with no error [8]. This is the same failure mode opsward's `validate_hooks_config` targets: an unknown hook event or a non-string `matcher` that "looks configured" but never fires.
- **SkillCheck** validates skills (Claude Code, Cursor, VS Code) against the open standard across 28 check categories, scores 0–100, and gates PRs via a GitHub Action (`uses: olgasafonova/skillcheck@v3`). Notably it layers **OWASP Agentic Top 10 security checks** — tool over-grant, identity override, unpinned deps, eval/exec, goal hijacking, memory poisoning — onto structural validation, and reports that only ~17% of 2,568 scanned public skills met acceptable standards [10]. The quality-vs-security framing ("valid" vs "safe to ship") is a dimension opsward does not currently model.
- **agent-skills-lint** (swarmclawai) is a cross-agent validator/installer with stable exit codes, designed to be run *by* agents non-interactively — collision-aware install plus index generation [9].
- **MCP-specific CI:** the maturing consensus is that `tools/list` is not enough — CI must actually *call* tools and assert on structured + semantic results ("receipts"), validating the contract on every commit [11]. opsward has no MCP validation today beyond hooks.

The schema basis is the **Agent Skills open standard** (agentskills.io): `name` (lowercase, hyphenated, ≤64 chars, must match directory), `description` (≤1024 chars), optional `license`/`compatibility`/`metadata`/`allowed-tools`, ≤500-line SKILL.md, progressive disclosure [agentskills.io]. opsward's `_validate_skill_spec` already enforces this. The strategic question is whether opsward *extends* its validators to MCP and security, or *composes* Agnix/SkillCheck as the schema-lint stage and keeps its differentiation on diagnosis+maintenance.

## 5. Versioning & governance

Product prompt-ops has converged on a mature model that the agent-config world is only beginning to borrow: treat prompts as **core software assets** with immutable history, diffing, approval workflows, environment-pinned versions (dev/staging/prod), release labels, instant rollback, and audit trails for compliance [17][18][19]. Best practices: semantic-version updates, document each change with rationale and test results, run regression evals before promotion, and keep a centralized registry with metadata [17][19]. Platforms (LangSmith, PromptLayer, Braintrust, Vellum) operationalize this for *runtime* prompts [15][17].

For *repo* config the governance unit is different — the config lives in git already, so versioning is partly free, but the missing pieces are (a) a **changelog discipline for config** (why did this rule change?), (b) **rollback as a first-class operation** when a CLAUDE.md edit regresses agent behavior [19], and (c) **multi-repo consistency**. On the last point, the literature is explicit that per-directory CLAUDE.md files "become hard to govern as the codebase grows, with conventions drifting and files going stale," and that this falls to whoever maintains the repo's agent setup rather than each developer [monorepo docs, 24]. The monorepo answer is hierarchical (nearest AGENTS.md wins) [21][22]. The *cross-repo* answer is the **"virtual monorepo" pattern** — "you don't need a monorepo, you need a monorepo view" — giving one agent full-system context across dozens of separate repos [23]. This is the conceptual blueprint for a fleet mode: a single diagnostic view over N independent roots.

## 6. Keeping current as the tooling churns

The ecosystem is moving weekly: new hosts (Copilot added native AGENTS.md support in Aug 2025, joining Codex, Cursor, Jules/Gemini, Factory, Amp, Windsurf, Zed) [22], new formats, new hook events, evolving SKILL.md fields. Three durable strategies emerge:

1. **Converge on a portable SSOT and symlink.** The dominant 2025 advice: write `AGENTS.md` as the source of truth and symlink `CLAUDE.md` to it — "one file on disk, two filenames, zero drift" [hivetrail; dev.to]. AGENTS.md is now backed by a multi-vendor standard (Sourcegraph, OpenAI, Google, Cursor, Factory) and 60k+ repos [21][22]. A maintenance tool should *normalize toward* a portable format and lint the symlink, not pick a side.
2. **Encode host-knowledge as versioned data, not code.** The set of valid hook events, the SKILL.md frontmatter schema, the MCP config shape — these change with the host, so they belong in a dated, swappable ruleset (see opsward's `_KNOWN_HOOK_EVENTS` frozenset, which is correct in *form* but hardcoded in *place*).
3. **Pull, don't re-author.** Lean on the open standard's own validators (`skills-ref validate`) and the linter ecosystem (Agnix, SkillCheck) for the parts that track the host, so you inherit their updates instead of chasing the spec by hand.

## Grounding in the existing ecosystem (opsward + skill)

opsward is the local instantiation of most of this report's *single-repo, deterministic* surface. Concretely, it already provides:

| Concern (this report) | opsward today | File |
|---|---|---|
| Read-only inventory | `scan()` — purely read-only by hard invariant | `opsward/scan.py` |
| Rubric scoring (§3) | weighted A–F across CLAUDE.md/Docs/Skills/Setup/Cross-ref | `opsward/score.py` |
| Code drift (§2) | `stale_path`, `sync_issue`, `outdated_doc`, `incomplete_skill`, `empty_doc` | `opsward/maintain.py` |
| Skill schema validation (§4) | `validate_skill_spec` vs agentskills.io | `opsward/score.py` |
| Hook silent-failure validation (§4) | `validate_hooks_config` (events, matcher type, command) | `opsward/score.py` |
| CI gate (§4) | `diagnose --min-score`, `--format json` | `opsward/cli.py` |
| Generation | `generate`, `generate_skills` from templates | `opsward/generate.py` |
| Tech-stack→skill mapping (§6 pull) | `recommend_skills` | `opsward/recommend.py` |
| Read-only auditor agent | `setup-auditor` subagent | `opsward/data/templates/shared/setup-auditor.md` |

The sibling `skill` package adds cross-host `validate()` and `check_dependencies`, which is the multi-format validation primitive §4/§6 want. **Compose, don't rebuild:** opsward should treat `skill.validate()` (and optionally Agnix/SkillCheck as an external gate) as the schema-lint stage, and keep its own differentiation — *weighted diagnosis + maintenance/drift + generation* — which no competitor combines [foundational report]. The competitive scan confirms the linters (Agnix, SkillCheck, agent-skills-lint) do *validation* well but none do scoring+maintenance, and the prompt-ops platforms do versioning/eval well but for runtime prompts, not repo config.

**What opsward is missing (the gap):**
1. **No cross-repo / fleet view.** Every function is `(one ScanResult) -> one report`. There is no `FleetReport`, no "3 of 200 repos lack `conventions.md`," no virtual-monorepo aggregation [23].
2. **No eval-based quality.** Quality is rubric-only (form), with no LLM-as-judge or golden-task regression layer measuring whether a config actually changes agent behavior (§3) [3][15].
3. **Hardcoded rubric/host-knowledge.** `_OVERALL_WEIGHTS`, dimension maxes, and `_KNOWN_HOOK_EVENTS` are module constants. There is no mechanism to *version* "current best practice" or to propagate an update across repos (§2 best-practice drift, §5, §6).
4. **Thin governance.** No config changelog/rollback vocabulary, no `revert/align/ignore` triage on drift findings, no security/OWASP dimension [10].

## Recommendations

Prioritized; each marked compose (C) or build (B).

**P0 — Cross-repo "fleet" diagnosis mode (B, thin).** Add a `fleet` facade that maps the existing pure `scan→diagnose` over N roots and *aggregates* into a `FleetReport`: per-repo grade plus cross-repo rollups ("missing conventions.md: 47/200", "skills failing spec: 12 repos", "rubric-version lag distribution"). Reuse `scan`/`diagnose` unchanged — this is an aggregation layer, the "monorepo view" [23], and the Terraform-style "plan across the fleet" [20]. State (which repos, last grade, last ruleset) should live in a per-machine JSON manifest, mirroring the existing `priv` rollout pattern rather than a new service.

**P0/P1 — CI gate + schema-lint composition (C).** Keep `--min-score` as the cheap deterministic gate; add a `lint` subcommand that shells to `skill.validate()` (and optionally Agnix/SkillCheck) for schema/security and returns stable exit codes [8][9][10], plus a pre-commit hook and a reusable GitHub Action. Adopt the MCP "receipts" stance — validate MCP configs by *describing* expected tools, not just presence [11].

**P1 — Eval harness atop the rubric (B).** Introduce an optional, opt-in eval layer that complements (never replaces) the rubric: (a) an LLM-as-judge scorer for the subjective dimensions (actionability, conciseness) with an explicit judge rubric and bias controls [12][13]; (b) a **golden-task regression suite** — run an agent with/without a candidate config against repo-specific tasks and score whether documented conventions were honored, the trajectory-level signal [3][15]. Port `skill-creator`'s train/test description optimizer as the first concrete eval [foundational report]. Keep evals out of the default CI path (cost/nondeterminism); gate on rubric, *report* on evals.

**P1 — Versioned, self-renewing ruleset (B, foundational).** Extract `_OVERALL_WEIGHTS`, dimension maxes, `_KNOWN_HOOK_EVENTS`, and template content into a **dated, semver'd ruleset** shipped as package data, while preserving the scoring invariants (weights sum to 1.0, maxes to 100). `diagnose` then reports "ruleset v3 (2026-06), knows hook events through Claude Code X.Y." A repo can pin a ruleset; `opsward update-ruleset` bumps it and re-diagnoses, turning best-practice drift (§2) into a visible, propagatable diff across the fleet. This is the mechanism that lets one rubric improvement reach 200 repos — the missing "self-renewing brain." Note this trades against the project's current rule that the rubric is hardcoded constants; it is a *deliberate* architectural change to be ratified, not a violation to sneak in.

**P2 — Governance vocabulary (B, small).** Give maintenance findings a `revert/align/ignore` triage [20], support an `# opsward: ignore-path` marker for legitimately-volatile references, add a config-changelog convention, and add a security/OWASP advisory dimension informed by SkillCheck's taxonomy [10].

## Open questions / decisions

- **Fleet state home:** per-machine JSON manifest (like `priv`'s rollout state) vs. a GitHub Project / committed file? The privacy rule forbids absolute local paths in committed artifacts, which pushes toward gitignored local state.
- **Ruleset sourcing & trust:** is the "current best practice" ruleset hand-curated, or partly auto-derived from upstream signals (agentskills.io spec changes, new hook events in Claude Code releases)? Who ratifies a bump?
- **Eval cost/determinism boundary:** where exactly is the line between the deterministic rubric gate (always in CI) and the LLM-judge/golden-task evals (opt-in, local, periodic)? What is the ground-truth label that proves a config "helps"?
- **Compose vs. extend on validation:** adopt Agnix/SkillCheck as the schema+security gate and stay thin, or absorb those checks into `validate_*` for a zero-dependency single tool? (The project's "no heavy deps / CI-friendly" stance argues for shelling out.)
- **Format SSOT:** should opsward actively *normalize* repos toward `AGENTS.md` + `CLAUDE.md` symlink [21], and lint the symlink itself, or stay format-agnostic and merely report?
- **Ratifying the rubric-versioning change:** the scoring-invariants rule currently mandates hardcoded constants; moving to a data-shipped ruleset needs an explicit decision record before implementation.
- **Drift remediation autonomy:** should fleet mode ever *auto-fix* (GitOps continuous reconciliation [20]) low-risk drift (e.g., update a moved docs path) under PR, or always stop at a diff?

## References

[1] Anthropic. Effective context engineering for AI agents. 2025. [anthropic.com](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

[2] amattn. Using AGENTS.md or CLAUDE.md to Counteract Agent Drift. 2025. [amattn.com](https://amattn.com/p/using_agentsmd_or_claudemd_to_counteract_agent_drift.html)

[3] Anthropic. Demystifying evals for AI agents. 2025. [anthropic.com](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

[4] ZBrain. A comprehensive guide to AgentOps: scope, core practices, challenges, trends. 2025. [zbrain.ai](https://zbrain.ai/agentops/)

[5] Machine Learning Mastery. The Practitioner's Guide to AgentOps. 2025. [machinelearningmastery.com](https://machinelearningmastery.com/the-practitioners-guide-to-agentops/)

[6] MLflow. What is LLMOps? LLM Operations Guide. 2025. [mlflow.org](https://mlflow.org/llmops)

[7] Anthropic. Writing effective tools for AI agents. 2025. [anthropic.com](https://www.anthropic.com/engineering/writing-tools-for-agents)

[8] Agnix. Show HN: Agnix – lint your AI agent configs (CLAUDE.md, skills, MCP, hooks). 2025. [news.ycombinator.com](https://news.ycombinator.com/item?id=46983879)

[9] swarmclawai. agent-skills-lint: cross-agent skill validator and installer. 2025. [github.com](https://github.com/swarmclawai/agent-skills-lint)

[10] SkillCheck. Validate Agent Skills for Claude, Cursor, VS Code (OWASP Agentic checks, CI gating). 2026. [getskillcheck.com](https://www.getskillcheck.com/)

[11] k08200. MCP CI gates need receipts: tools/list is not enough. 2025. [dev.to](https://dev.to/k08200/mcp-ci-gates-need-receipts-toolslist-is-not-enough-29o4)

[12] Braintrust. What is prompt evaluation? Testing prompts with metrics and judges. 2025. [braintrust.dev](https://www.braintrust.dev/articles/what-is-prompt-evaluation)

[13] Evidently AI. LLM-as-a-judge: a complete guide to using LLMs for evaluations. 2025. [evidentlyai.com](https://www.evidentlyai.com/llm-guide/llm-as-a-judge)

[14] DeepEval. LLM-as-a-Judge in 2026: techniques and best practices. 2026. [deepeval.com](https://deepeval.com/guides/guides-llm-as-a-judge)

[15] Braintrust. Top 5 platforms for agent evals in 2025 (trajectory-level evaluation). 2025. [braintrust.dev](https://www.braintrust.dev/articles/top-5-platforms-agent-evals-2025)

[16] LangChain. LangSmith Evaluation: LLM & AI Agent Evaluation Platform. 2025. [langchain.com](https://www.langchain.com/langsmith/evaluation)

[17] Braintrust. Best Prompt Versioning Tools for Production Teams. 2025. [braintrust.dev](https://www.braintrust.dev/articles/best-prompt-versioning-tools-2025)

[18] LaunchDarkly. Prompt Versioning & Management Guide. 2025. [launchdarkly.com](https://launchdarkly.com/blog/prompt-versioning-and-management/)

[19] Suhas Bhairav. Versioning and Rollback Strategies for Agent System Prompts. 2025. [suhasbhairav.com](https://suhasbhairav.com/blog/managing-versioning-rollback-strategies-for-agent-system-prompts)

[20] Spacelift. Terraform Drift Detection and Remediation Guide. 2025. [spacelift.io](https://spacelift.io/blog/terraform-drift-detection)

[21] AGENTS.md. Open standard for agent instructions. 2025. [agents.md](https://agents.md/)

[22] GitHub Blog. How to write a great agents.md — lessons from over 2,500 repositories. 2025. [github.blog](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)

[23] Owen Zanzal. The "Virtual Monorepo" Pattern: full-system context across 35 repos. 2025. [medium.com](https://medium.com/devops-ai/the-virtual-monorepo-pattern-how-i-gave-claude-code-full-system-context-across-35-repos-43b310c97db8)

[24] Anthropic. Set up Claude Code in a monorepo or large codebase. 2025. [code.claude.com](https://code.claude.com/docs/en/large-codebases)

[25] Agent Skills Open Standard. SKILL.md specification and `skills-ref validate`. 2025. [agentskills.io](https://agentskills.io/)

Related reports: discovery_and_dispatch.md, multiplatform_config.md, adr_and_home_finding.md (in this directory).
