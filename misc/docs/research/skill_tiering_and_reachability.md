# Skill scope tiering and reachability at fleet scale

**Abstract.** This report closes Parts 2–6 of [thorwhalen/opsward#23](https://github.com/thorwhalen/opsward/issues/23): a survey of the fleet's skills, the context cost of advertising them measured on the real host rather than estimated, the research delta over `discovery_and_dispatch.md` and priv's `groups_lazy_disclosure.md`, a tiering design with its rejected alternatives, a staged migration, and the list of what could not be determined. The verdict the issue asked for is mixed but mostly cheap: **the layout is already specified and simply not enforced** (skill-package-setup names the canonical location; 327 of 814 real skill files still sit as real directories under `.claude/skills/`, and 169 names are defined more than once); **the host already tiers the listing, silently and by its own rule** (Claude Code caps the listing at 1% of the context window, observed as exactly 30,000 characters in 3,532 sessions, and drops descriptions least-invoked-first, so a median session sees 130 skill names and only 50 descriptions); and **the one genuine design decision, which skills keep a description, is answerable from data the fleet already records** (45 days of transcripts give per-skill invocation counts, and they show that skills are reached by file path about eight times more often than through the `Skill` tool, which is why the hand-written prose routes in `CLAUDE.md` work). The design is therefore an enforcement layer plus one declared list, not a router.

Measured 2026-10-19 on the Mac. `$PP` is the projects folder. Scripts and raw JSON are in `$PP/_agent_work/opsward/2026-10-19-skill-tiering/` (`census.py`, `listing_scan.py`, `global_usage.json`); nothing in this report is derived from the issue's earlier numbers without re-measurement.

## 0. Verdict in one table

| Question the issue asks | Answer | Evidence |
|---|---|---|
| Enforcement problem or design problem? | **Enforcement**, for placement, duplication, drift and the two accounts. **One design decision** remains: the always-on set. | §2, §3 |
| Is "all or nothing" the constraint? | **No.** The host already has a middle tier (name-only) and applies it to most skills without being asked. The cost is capped; what is lost is the *trigger*. | §3.1 |
| What is the middle tier? | `skillOverrides: name-only` (listed, invocable by name, readable by path, no description), as priv#175 already uses for groups. | §4, [3][4] |
| Does a router subagent replace the listing? | **Not yet.** The residue it would need (a line telling the main thread to ask) already exists as prose routes in `CLAUDE.md`, and those routes carry ~80% of skill reads today. Build a router only on evidence, as priv#177 already gates it. | §3.3, §5.2 |
| Is reachability verifiable? | **Yes, offline.** Every session records the listing it was offered (`skill_listing` attachments; priv#71 shipped the reader). The comparison against what resolves is the gap. | §5.6 |

## 1. What we already have (verified 2026-10-19)

Everything below was checked on disk or on GitHub today. The report builds on it and does not repeat it.

- **Research already written.** `misc/docs/research/discovery_and_dispatch.md` (this repo) covers progressive disclosure, router patterns and registries [1]. `$PP/t/priv/misc/docs/groups_lazy_disclosure.md` [2] measured a `g_av` session at 268,732 instruction characters and a 235-skill listing, and ran eleven headless probes on Claude Code 2.1.282 that settle how the host loads lazily: nested `.claude/skills/` appear only after a `Read` through the subtree (not after `cat`), `paths:`-scoped skills are not listed until their glob matches, `--add-dir` contributes skills but not `CLAUDE.md`, and `skillOverrides: name-only` keeps the name and drops the description. `$PP/t/skill/misc/docs/` holds the landscape survey, the cross-agent compatibility report and the spec limits (name regex `^[a-z0-9]+(-[a-z0-9]+)*$`, description 1–1024 characters) [5][6].
- **Machinery already built.** `ir discover skills` over a `skills` corpus fed by `priv.skills_index` (opsward#12, #13, closed). `skill.link_skills`, `skill validate` (with a length check), the `skill-package-setup` / `skill-enable` / `skill-sync` skills. `opsward.score.validate_skill_spec` already flags a description over 1,024 characters. `priv upkeep`'s `claude-config` check (priv#70) and the `SessionStart` sync hook keep the two config directories aligned; today both hold 121 entries with zero drift. `priv.claude_transcripts` streams `skill_listing` attachments (priv#71). priv#175 (closed) budgets group farms with a `featured_skills` list and generated `name-only` overrides, and priv#177 (open) gates a router hook and a scout subagent on usage evidence.
- **Policy already written.** `skill-package-setup` mandates one real location per skill (`<pkg>/data/skills/<name>/` for pip-shipped packages, `skills/<name>/` otherwise) with `.claude/skills/<name>` as a relative per-skill symlink, never a real directory and never a whole-directory link [6]. [thorwhalen/skill#8](https://github.com/thorwhalen/skill/issues/8) and [#9](https://github.com/thorwhalen/skill/issues/9) (open) are deciding the default and the migration skill; [thorwhalen/priv#155](https://github.com/thorwhalen/priv/issues/155) (open, blocked on them) is the fleet sweep.
- **Host facts from the official docs** [3][4]: the listing always contains every skill name; the budget "scales at 1% of the model's context window"; on overflow "Claude Code drops descriptions starting with the skills you invoke least"; each entry's `description` plus `when_to_use` is capped at 1,536 characters (`skillListingMaxDescChars`); the budget is raised with `skillListingBudgetFraction` or pinned with `SLASH_COMMAND_TOOL_CHAR_BUDGET`; `/doctor` estimates the listing cost and `/skill-doctor` lists unused skills; name conflicts resolve enterprise > personal > project; `claude plugin validate <dir>` finds frontmatter that does not parse.

## 2. The census (Part 5.2)

Method: walk `$PP` for `SKILL.md`, resolve symlinks, hash content, parse frontmatter; cross-reference the two global scopes (`~/.claude/skills`, `~/.claude-iq/skills`) and the eight group farms (`$PP/g/*/.claude/skills`). Excluded as not-the-fleet: `node_modules`, `.git`, virtualenvs, `$PP/_agent_work` (session scratch), `.sync-backups`, `_worktrees`, `.cache`. With the scratch and backup trees included the count is 1,461 files, which is why every census must state its exclusions.

### 2.1 Counts

| Measure | 2026-08-24 (issue) | 2026-09-15 (priv#155) | **2026-10-19** |
|---|---|---|---|
| `SKILL.md` files | 558 | 789 | **815** |
| distinct real files | 557 | | 814 |
| distinct by content hash | 433 | | **605** |
| distinct `name:` values | 394 | | **528** |
| names defined more than once | 109 | | **169** (138 across repos, 31 within one repo) |
| content-identical groups | 98 (222 files) | | 138 (347 files, 209 pure copies) |

The three earlier counts are not contradictory: they used different exclusion sets and the fleet grew by a third in eight weeks (394 → 528 names). Whatever check comes out of this must print its exclusions next to its totals.

Placement, by real file: `.claude/skills/` 327, top-level `skills/` 314, `<pkg>/data/skills/` 166, other 7. Spec violations: 2 files with no `name`, 3 with no `description`, 2 names with underscores (`contaix_docs_to_markdown`, `contaix_web_aggregate`, both globally linked, both silently non-compliant with the spec regex), and **24 files (17 distinct names) with a description over 1,024 characters**, up from the issue's 3. The worst is 1,790. The host cap is 1,536, so the three longest are already being truncated at the source of their trigger, exactly the silent-trigger-loss the issue warned about.

### 2.2 Where the duplicates come from

The 169 collisions fall into five kinds, and only the last two are defects:

1. **Git worktrees under `<repo>/.claude/worktrees/<branch>/`** — crowsnest's four skills exist 15 times, reelee's 13 skills four times. These are the same skill at different commits; Claude Code's worktree feature puts them there. A census must exclude `.claude/worktrees`.
2. **The cross-machine mirror** `$PP/tt/_priv_claude_sync/skills/` (90 files): resolved copies of `~/.claude/skills` for the Linux machine. It is a *scope snapshot*, not an owner, and it shows up as the second owner of 60 names. It should be treated as a scope in a census, and the two-hop ownership (package → `~/.claude` → mirror) is why its copies lag.
3. **`.agents/skills` + `.claude/skills` real pairs** in the cosmograph repos (`history`, `cd`, `review-app`, …): not ours to change.
4. **Real copies of another package's skill**, sometimes diverged: `r/crew` holds copies of eight `my_skills` skills (`architecture-first` in two different contents, `needs-human` in three across `r/crew`, `t/openloops-lab` and the mirror); `t/denote` holds all four opsward skills; `i/_zodals` has `zodal-ecosystem` twice; `workspace-overview` has three different contents in `g/g_av`, `r/crew` and `t/priv`; `editable-install-health` three contents between `t/priv` and the mirror.
5. **Same-repo duplicates**: `r/mixing` 5 names, `t/priv` 6, `r/falaw`, `i/mergeset`, `r/yb` one each, where both the real location and `.claude/skills` are real directories (the unmigrated state priv#155 counted as 45 repos).

Kind 4 is the one that matters for routing, and it has a sharper consequence than "which copy wins in a ranker": Claude Code resolves name conflicts personal > project [3], so a *project* skill whose name is also linked globally is **shadowed and never loads**, with no warning. Every name in kind 4 that is also in `~/.claude/skills` (`needs-human`, `architecture-first`, the opsward four in denote, …) is in that state today.

### 2.3 Scopes

| Scope | entries | advertised chars if every description were shown | ≈ tokens | over 1,024 |
|---|---|---|---|---|
| `~/.claude/skills` | 121 (117 symlinks, 3 real dirs, 1 without `SKILL.md`) | 78,924 | 19.7k | 3 |
| `~/.claude-iq/skills` | 121 (identical set) | 78,924 | 19.7k | 3 |
| `g_av` farm | 150 | 95,779 | 23.9k | 6 |
| `g_embeddings` | 49 | 32,236 | 8.1k | 3 |
| `g_ai` | 55 | 28,719 | 7.2k | 0 |
| `g_musicai` / `cosm` / `g_fin` / `g_tp` / `g_inoocq` | 18 / 16 / 12 / 2 / 0 | 9.5k / 7.1k / 5.6k / 1.3k / 0 | | |

Global links by owner: `tt/my_skills` 39, `i/wads` 12, `t/priv` 7, `t/ge` 7, `t/acquaint` 6, `t/skill` 6, `t/coact` 5, then a long tail of 1–4. The global set is 2.6× the listing budget on its own (§3.1), before any project, group, plugin or bundled skill is counted.

Reachability by scope: 117 real skills are linked globally, 238 are in at least one group farm, and **492 of 814 are in neither**, reachable only when the cwd is their package (or a `Read` enters it) or by absolute path.

### 2.4 What the survey concludes

The placement policy is specified and about half-enforced; the duplicates are two-thirds artefacts (worktrees, the mirror) and one-third real copies that the policy already forbids; the global scope was assembled by accretion (23 of its 121 skills were not touched in 45 days, §3.2). Nothing here needs a design. It needs a lint that runs without anyone remembering, and a decision about the always-on set.

## 3. The cost, measured on the real host (Part 3, re-verified)

Source: the `skill_listing` attachment Claude Code writes into every session transcript (`~/.claude*/projects/**/*.jsonl`), which carries the exact listing text the model received, plus every `Skill` tool call and every `Read`/`cat` of a `SKILL.md`. Window: 45 days to 2026-10-19, both accounts, 3,532 sessions with a listing, CLI versions 2.1.260–2.1.296.

### 3.1 The listing is capped and already tiered

| | min | median | max |
|---|---|---|---|
| skills in the initial listing | 1 | **130** | 335 |
| of which with a description | 1 | **50** | 58 |
| listing characters | 495 | **29,982** | 30,002 |
| fraction with a description | 0.04 | **0.37** | 1.0 |

By listing size: 100–149 skills (2,047 sessions) keep a median 51 descriptions; 150–199 (1,131) keep 48; 300–349 (108, the `g_av` sessions) keep **43**. The listing never exceeds 30,000 characters whatever the count. That is 1% of a 1M-token window at 3 characters per token, the same formula an independent 160-skill experiment derived on 2.1.289 [20]; on a 200K window the same experiment measured **0 of 160** descriptions surviving, because the bundled skills alone exceed the 6,000-character budget.

So the "always-on cost" the issue extrapolated to 58k tokens does not occur. The cost is pinned at roughly 7.5k tokens per turn (cached system prompt), and what grows with the fleet is the number of skills whose trigger text the model never sees: 63% of them in a median session, 88% in a group session. The host's drop order is "least invoked first" [3], so a skill that is new, or that is reached by path rather than by `Skill()`, loses its description first; nothing reports which ones.

### 3.2 How skills are actually reached

| Channel (45 days, both accounts) | events | distinct skills |
|---|---|---|
| `Skill` tool invocation | 594 | 118 |
| `Read` tool on a `SKILL.md` | 331 | 88 |
| Bash `cat`/`sed`/`head` of a `SKILL.md` | 4,656 | 375 |

Skills are reached by path about eight times more often than through the tool that the listing exists to serve. The top of the by-path list is the global `CLAUDE.md`'s own routes: `landing-a-branch` (65 invocations, 309 path reads), `needs-human` (6, 165), `architecture-first` (8, 100), `tw-frontend-ux` (12, 95), `app-data-lifecycle` (4, 66), `fleet-protocol` (6, 50). Of the 121 global skills, 98 were used in 45 days by one channel or the other, 56 ever through `Skill()`, and **23 by neither**: `ai-assistant-agent-runtime`, `ai-assistant-chat-ui`, `ai-assistant-prompts-skills`, `ci-advisor`, `contaix-acquire-docs`, `contaix_docs_to_markdown`, `contaix_web_aggregate`, `dn-repair`, `ge-analyze`, `ge-autonomous-execution`, `ge-context`, `ge-cross-repo-triage`, `ge-roadmap-execution`, `pdfdol-read`, `skill-docs`, `synced`, `thorwhalen-github-manager`, `wads-changelog`, `wads-import-time`, `wads-repo-doctor`, `wads-test-coverage`, `wads-type-coverage`, `yb-podcast`. Thirteen of these are already `off` in `settings.json`, by hand.

### 3.3 Why the prose route works, and what a generated one would lose

The issue asked why the sentence *"the `ge-write-issue` skill governs anything written into an issue here"* in a project `CLAUDE.md` routed correctly when the listing did not. The measurement answers it: a prose route is **path-addressed and condition-addressed**. It names the skill next to the condition, in a file that is always loaded, and the agent then reads the file by path, which no listing budget, no `skillOverrides`, and no resolver can interrupt. The listing is **description-addressed**: the model must match the live prompt against text that the budget may have dropped. The 160-skill experiment found described skills triggered 5/5 and name-only skills **0/3** [20]; in this fleet, name-only skills are still reached hundreds of times, because a `CLAUDE.md` or another skill names them.

A generated router would lose exactly the part of the sentence that does the work: the condition written by the person who knows when the skill applies ("before landing", "anything written into an issue here"). A description is the author's guess at the trigger; a route is the operator's decision about it. The design in §5 keeps routes as the residue and generates only the tier table.

## 4. Research delta (Part 5.3)

Only what `discovery_and_dispatch.md` [1] and `groups_lazy_disclosure.md` [2] do not already cover. Thirty-two sources were fetched for this section; the briefing with per-finding confidence is in the working folder.

**Does a flat list degrade selection, and at what N?** It degrades gradually for strong models and falls off a cliff for small ones. Naive all-in-prompt tool selection on ToolBench goes from 92.4% at 15 tools to 78.2% at 640, with refusal-to-call rising from 8% to 19% [13]. On BFCL-live, an 8B model scores 97.0 with ≤10 candidates, 84.5 at 100 and 38.5 at the full 457-tool pool; retrieval pre-filtering recovers it to 79.4 [12]; hierarchical category-then-tool retrieval over 16K APIs gained +35.4% pass rate over flat retrieval [15]. For small models the cliff is earlier: an 8B model at a 16K window failed a query with 46 tools visible and passed with 19, which the authors attribute to option count rather than context length [17]. OpenAI's own guidance is to keep fewer than 20 functions visible at the start of a turn and defer the rest behind tool search [16]. The widely repeated "43% → 2% from 4 to 51 tools" figure attributed to BFCL has no locatable source and is not used here [18].

**Does retrieving a top-k recover it, and what does retrieval miss?** A *trained* retriever over 16k APIs matches the oracle (67.3 vs 66.7 pass rate), but off-the-shelf lexical and embedding retrievers lose half the targets (NDCG@5 17.0 and 45.4 vs 84.9) [8]. The reason is measured: user phrasing shares almost no vocabulary with tool documentation (ROUGE-L overlap 0.06 against 0.31–0.34 for ordinary QA corpora), and the best general retriever reaches NDCG@10 of 33.8 on a 43k-tool benchmark [9]. A weak retriever is worse than none: GPT-4 with BM25 retrieval scored *lower* than zero-shot on Gorilla's TorchHub (35.5 vs 38.7), and the authors warn that "a non-optimal retriever at test time will sometime misguide the model" [7]. Two failure modes recur: prerequisite tools the target depends on, and under-specified queries, where query rewriting lifts top-15 recall from 80.8 to 99.7 [13]. The standard fix on the index side is **document expansion**: write the queries a tool answers into its index entry (Re-Invoke +20/+39% nDCG@5 [10]; Toolshed +46–56 recall@5 [11]; Toollery's SkillRouter recall@10 0.571 → 0.942 [12]). The fleet's `description: … Triggers on: '…', '…'` convention is exactly this, done by hand; `ir`'s skills corpus should index those phrases as queries, not prose.

**How large should the visible set be?** Per query, not fixed: an adaptive shortlist averaging 7 tools reaches the coverage of a fixed 50 on BFCL, and a fixed top-5 finds 0% of queries whose target ranks 6–20 [14]. A community router measured its embedding pre-filter at recall@3 of 80%, so one query in five never reaches the judge with the right tool: "the prefilter is a ceiling no judge can overcome" [19]. This is the number to hold against any two-stage design.

**Practitioners with large private fleets.** The canonical Claude Code thread, [anthropics/claude-code#11045](https://github.com/anthropics/claude-code/issues/11045), is a 100-skill fleet behind ten router skills: the routers "get buried", Claude bypasses triage or picks nothing; measurements in-thread put the then-budget at ~16k characters and ~109 characters of per-skill overhead; a 185-skill plugin showed "50 of 185"; the proposed `hidden`/`router` flags were closed "not planned" [25]. The 160-skill experiment [26] is the best measured data: descriptions kept 10/10, 22/40, 21/80, 20/160 on a 1M window; 50/160 at `skillListingBudgetFraction: 0.02`; drop order least-invoked then name order; name-only recall 0/3. A ~480-skill fleet measured `/doctor` at 11,870 tokens against a 1,250-token budget (9.5× over, 425 descriptions dropped) and answered with **deploy-time scoping** by path signals, not runtime routing [27]. One project computes a per-profile budget fraction (floor 0.01, ceiling 0.05) and sets off-profile skills `name-only`; at 0.015 seven of eight required skills were still name-only [28]. Superpowers 4.0 merges rarely used skills, and its meta-skill is a discipline ("even a 1% chance … invoke it") with no discovery mechanism of its own [29][30]. The one community linter that measures rather than advises checks the budget, pairwise TF-IDF overlap between descriptions (≥0.35 flagged) and live trigger and false-trigger rates, but with a four-prompt smoke eval [31]. SkillReducer, over 55,315 public skills, found 26.4% lack a description, that 48% compression of descriptions preserved routing on 536/536 cases, and that 10.7% of skills never trigger even with their original description: "too short → router never selects the skill" [32]. Anthropic's own `skill-creator` states that "Claude has a tendency to undertrigger skills" and ships a description optimizer, with no published trigger-rate-versus-count figure [38].

**Other hosts.** Codex caps its instruction set at 2% of context or 8,000 characters and shortens descriptions first [27]; Codex CLI ships `tool_search` and a `tool_suggest` that "recommends tools for the current task", the nearest shipped form of the conversational router [33][34]. MCP paginates `tools/list` with opaque cursors; that solves transport, not selection [20]. Claude Code defers all MCP tools behind tool search by default, with `ENABLE_TOOL_SEARCH=auto` loading upfront until definitions reach 10% of context, per-tool `alwaysLoad`, and the advice to "put the words Claude would search for near the start" [21]; the API's `defer_loading` does not apply to skills [25]. OpenAI's tool search (gpt-5.4+) notes that "deferred loading adds a discovery step and depends on the model finding the right tool" [22]; its Agents SDK closed a request for dynamic tool groups as not planned [23], and proxies such as LiteLLM collapse a server's tools into a handful of virtual search tools ranked by keyword overlap [24].

**The conversational router.** No paper names it. The closest shipped artefact is Codex's `tool_suggest` [33]; the closest benchmarked design is tool-to-agent retrieval, which embeds tools and their parent agents in one space and traverses tool → agent (+19.4% recall@5 on LiveMCPBench) [35]; "librarian" is taken for a persistent code-search subagent whose point is that output tokens cost 30–1000× input, so a sub-agent that *reads* and returns one page is cheap while one that *summarises* widely is not [36]. Nobody has measured its latency in a coding harness; vendor figures put a semantic router at 5–20 ms and an LLM router at 200–800 ms per hop [37]. Nothing found states "two-stage routing destroys the trigger" in those words; the adjacent evidence is the vocabulary gap [9], the thin-query result [13] and the pre-filter ceiling [19], all pointing the same way.

**What the delta changes in the design.** (i) The host already implements the middle tier; the fleet's job is to *decide* its membership instead of letting an invisible usage counter decide. (ii) Retrieval over the catalog needs trigger phrases indexed as queries, and is a complement to routes, not a replacement, because of the pre-filter ceiling. (iii) Name-only is invisible to description matching, so every name-only skill must be reachable by a route (prose, or a package card) or it is effectively tier 3.

## 5. Design (Part 5.4)

### 5.1 Tiers

| Tier | Where it lives | What the model sees | How it is reached | Who decides membership |
|---|---|---|---|---|
| **T0 always-on, described** | `~/.claude/skills` link, `skillOverrides` absent or `on` | name + description in every session | description match, `Skill()`, `/name`, path | **declared list**, justified line by line (§5.3) |
| **T1 global, name-only** | `~/.claude/skills` link, `skillOverrides: name-only` | name only | a route in `CLAUDE.md` or another skill; `Skill()` by name; path | default for any globally linked skill not in T0 |
| **T2 scoped** | the package's own `.claude/skills` (bridge symlinks to its real location); a group farm with priv#175 `featured_skills` | listed when the cwd is in the package or a `Read` enters it [2] | description match within scope; package card (priv#173) | the package maintainer; the group manifest |
| **T3 on demand** | the package only, not linked anywhere | nothing | `ir discover skills` / `priv skills-index -f`, then `Read` by path | the default for a new skill |

Demotion is free and reversible at every boundary: T0 → T1 is one `skillOverrides` entry; T1 → T2 is removing one symlink; T2 → T3 is removing the bridge. The 23 unused global skills in §3.2 go to T2 now.

### 5.2 The always-on residue, costed

A router subagent would move the listing out of the main context and add one round trip before the main thread knows what it can do, and the main thread has to know to ask. The residue that makes it ask is already in the system prompt and already works: the global `CLAUDE.md` names 27 of the 121 global skills next to their conditions, and those 27 account for the top of §3.2. Its cost is the ~17.6k characters of the user `CLAUDE.md` [2], paid today with or without a router. Adding a router adds its own residue (one paragraph, ~500 characters) *plus* the round trip *plus* a pre-filter ceiling of roughly one miss in five [19], and saves at most the 30k-character listing, which a 35-skill T0 already fits under. The honest comparison is therefore: **T0 + routes ≈ 7.5k tokens of listing and no new failure mode, versus router ≈ 0.1k tokens of residue, one extra hop per task, and a measured recall ceiling.** The router is not worth it until usage shows T0 + routes missing, which is the gate priv#177 already states. The fleet index (priv#172) and package cards (priv#173) are the same mechanism extended to packages: passive, path-addressed, no decision point.

### 5.3 The always-on set, justified from data

Rule, applied to the 45-day counts: a global skill is T0 if it is named in the global `CLAUDE.md`, or was invoked through `Skill()` at least 5 times, or was read by path at least 40 times. Today that yields **39 skills and 27,659 advertised characters**, inside the 30,000-character cap with no fraction change: `landing-a-branch`, `needs-human`, `crowsnest-worker`, `architecture-first`, `tw-frontend-ux`, `twp-deploy`, `frontend`, `app-data-lifecycle`, `crowsnest-dispatch`, `crowsnest`, `deslop`, `crowsnest-report`, `tw-deploy`, `fleet-protocol`, `local-package-ecosystem`, `python-dispatching`, `skill-package-setup`, `do-research`, `astern-recall`, `github-memory`, `python-storage`, `dev-skills-workflow`, `ge`, `session-handoff`, `branch-hygiene`, `acquaint-write`, `ge-write-issue`, `python-project-structure`, `audio`, `epythet-docs`, `gap-to-issue`, `yb-publish`, `yb-download`, `annals-publish`, `session-scoping`, `setup-self-improvement`, `prework-alignment`, `components-and-combinators`, `python-iterables`. The remaining 59 used skills are T1 (37,084 characters that no longer compete), the 23 unused are T2. The bundled and plugin skills (47 names in this session) share the budget; if `/doctor` shows T0 descriptions still being dropped, the first lever is trimming T0 descriptions to the key use case (SkillReducer: 48% compression preserved routing [32]), the second is `skillListingBudgetFraction: 0.02` (+7.5k cached tokens per turn [26]), and only then a smaller T0. The thresholds (5, 40, 45 days) are policy constants to be revisited quarterly from the same transcript counts; the rule is what matters, not the numbers.

### 5.4 Ownership, registration, the two accounts

- **Ownership** stays in the package: the real `SKILL.md` lives where `skill-package-setup` says; `~/.claude/skills/<name>` and every farm entry are symlinks to it; the mirror repo is a derived snapshot. Non-negotiable, and already policy.
- **Tier declaration** belongs with the skill, in the spec-allowed `metadata` map (`metadata: {tier: global}` as the owner's *proposal*), and the operator's decision lives in one per-machine list that priv renders into `skillOverrides` for **both** `settings.json` files (which are deliberately not shared, per the Part 1 decision). Deep-merge only the `skillOverrides` key, as priv#175 already does for group settings, because Claude Code writes the rest of that file.
- **Registration / CRUD is one command**: `skill link-skills .` creates the package bridge (exists); the global link plus the tier entry plus both settings renders become one `priv` verb (`priv claude-skills add <pkg>/<name> --tier T0|T1`, naming to be settled in priv), and removal is its inverse. The `SessionStart` sync hook already propagates the link to the second account; the render must be idempotent so the same hook can call it.
- **Canonicalisation rule** for the 169 collisions: the canonical copy is the one at the owning package's declared location; `.claude/skills` entries must be symlinks; worktrees and mirrors are excluded from ownership; any other real file carrying a name that exists elsewhere is a defect, fixed by replacing it with a symlink or by renaming it with the package prefix the fleet already uses (`vd-add-backend`, `reelee-live-api-testing`). A project skill whose name is linked globally is flagged as *shadowed* (§2.2), because the host will never load it.

### 5.5 Failure modes

| Failure | Detector | Repair |
|---|---|---|
| advertised but unloadable (listing and resolver disagree) | transcript diff: names in `skill_listing` not resolvable in the scopes that applied (§5.6) | the reachability probe on CLI upgrade; file upstream if it recurs |
| description dropped by the budget (trigger silently lost) | described-fraction per session from the same attachment; `/doctor` | demote to T1 explicitly, trim descriptions, or raise the fraction |
| dangling symlink / dir without `SKILL.md` | `priv upkeep claude-config` (exists) | the sync hook (exists) |
| two packages defining one name | census lint: same name, different real files | symlink or rename with the package prefix |
| project skill shadowed by a global name | census lint: project name ∈ global scope | rename the project one, or unlink the global one |
| description over 1,024 / name with underscore | `opsward diagnose` (exists for length), `skill validate`, census lint | edit the source |
| a package moves | absolute links break → dangling, caught above; relative bridge links survive | relink via the one command; `priv pkg` already forbids moving a registered checkout |
| the two accounts diverge | hook + upkeep (exist) | automatic |
| the mirror lags | mirror export is explicit (`sync_claude_config.py export`) | run it; a census that counts the mirror as an owner is the bug |

### 5.6 Verification: proving a skill is reachable

Three layers, cheapest first.

1. **Static** (exists): `priv upkeep`'s `claude-config` check, weekly, report-never-repair.
2. **Offline, per session, batch**: for each transcript, the `skill_listing` union (initial plus later batches) minus the names resolvable in the scopes that applied at that time (global dir, cwd's project and nested dirs, plugins, bundled) gives the advertised-but-unloadable set; the described count over the union gives budget health. `priv.claude_transcripts` already yields the records (priv#71); the comparison and the two metrics are the missing ~100 lines, and they belong in `priv upkeep`'s `fast` scope next to `claude-config`. This covers every session, both accounts, retroactively, at zero model cost, and it is the check the issue asked for in the form the issue did not know was available.
3. **Live, on each CLI upgrade**: the headless canary protocol priv already used [2] (`claude --print` from a throwaway root with a planted skill, read the session's own transcript for the listing and the `Skill()` result). About $2 per run; runs when the version changes, not on a schedule.

### 5.7 Rejected alternatives

- **Raise the budget fraction to 5%** (150k characters): pays ~37k cached tokens per turn to keep descriptions the data says are read by path anyway; and the drop rule still decides membership, not the operator.
- **A router subagent as the primary mechanism**: §5.2; also the measured prefilter ceiling [19] and the buried-router report [25]; kept as priv#177's evidence-gated add.
- **Merging skills into fewer mega-skills** (Superpowers 4.0 [29]): breaks ownership in the package and the one-skill-one-concern rule the fleet's skills follow.
- **Linking every skill globally**: the wall in §3.1, measured, and 0/160 on a smaller window [26].
- **Plugins as scoping**: cached copies that fight a fleet changing 50 packages a week; rejected in [2] as P7.
- **`hidden`/`router` frontmatter flags**: requested upstream, closed not planned [25].
- **Symlinking `~/.claude-iq` → `~/.claude`**: rejected in Part 1 for the billing-boundary reason; stands.
- **Mechanism inside opsward**: opsward diagnoses; the link/render/sync verbs are per-machine plumbing (priv) and the bridge is package layout (skill). opsward's part is the lint findings and the listing-health report in `opsward diagnose`.

## 6. Migration (Part 5.5)

Each stage leaves the fleet working; none is a big bang; every one is reversible by deleting what it added.

| Stage | Change | Reversal | Depends on |
|---|---|---|---|
| 0 | Census and lint as a priv component (exclusions printed; collisions, shadowing, over-length, underscore names, mirror and worktree handling), run in `priv upkeep fast` | none, read-only | nothing |
| 1 | Render `skillOverrides` for both accounts from the declared T0 list (§5.3); unlink the 23 unused global skills; delete the 13 hand-written `off` entries the render now owns | delete the key; relink | stage 0 for the counts; the user's approval of the list |
| 2 | Dedup the kind-4 copies (r/crew, t/denote, t/openloops-lab, i/_zodals) into symlinks; fix 17 over-length descriptions and 2 underscore names at the source | git revert per repo | skill#8/#9 for the per-repo layout; priv#155 sweep does the rest |
| 3 | Offline reachability and budget-health check in `priv upkeep fast` (§5.6 layer 2) | remove the check | priv#71 (done) |
| 4 | Index trigger phrases as queries in `ir`'s skills corpus; name T1 and T3 discovery (`ir discover skills`) in the `fleet-protocol` route (already there) | reindex | opsward#13 (done) |
| 5 | Evidence-gated: router hook and scout, per priv#177, only if stage 3 shows T0 + routes missing | per priv#177 | stages 1–3 for two weeks |

## 7. What could not be determined (Part 5.6)

- **The exact budget formula.** Anthropic's docs say "1% of the model's context window" [3]. The constant 30,000 characters is observed here and derived as 1M × 0.01 × 3 characters per token in [26]; the 3 is inferred, not documented. A 200K-window session would see ~6,000 characters [26]; none of this fleet's recent sessions ran on one, so that regime is unmeasured here.
- **The host's drop order within "least invoked".** Its counter is not visible; the 45-day transcript counts are a proxy and may differ from it (for instance it may not count `/name` invocations or by-path reads the same way).
- **Whether two-stage routing loses the trigger, in this fleet.** Not tested here; the external evidence (§4) points one way. Protocol, for the follow-up: ten prompts carrying a T0 skill's own trigger phrases, each run three ways through a headless session (full prompt in the main thread; a one-line summary handed to a router subagent holding the listing; the router given the raw prompt), scoring which runs invoke the right skill. Cost roughly $5 at Sonnet prices.
- **Why a name-only or description-dropped skill was still invoked.** A `Skill()` call in a transcript does not say whether the model matched a description, followed a prose route, or was told by the user. The 8:1 by-path ratio is the strongest available signal, not a controlled measurement.
- **Selection accuracy at 400–500 skills on Claude Code.** No measured data exists anywhere (§4); the closest anchors are 20/160 descriptions kept [26], 50/185 [25] and 425 dropped of 393-plus [27], all about *visibility*, not *selection*.
- **The cosmograph `.agents/skills` + `.claude/skills` pairs**: counted, not ours to change.
- **The 2.1.241 enumeration leak** (Part 1): still unexplained; the CLI is closed source and the leak does not reproduce on current versions.

## 8. Follow-ups filed

Listed here so the report is the index; each issue holds its own acceptance line.

- [thorwhalen/priv#250](https://github.com/thorwhalen/priv/issues/250): skills census fields and lint (stage 0), with the ad hoc `census.py` as the starter.
- [thorwhalen/priv#251](https://github.com/thorwhalen/priv/issues/251): tier render for `skillOverrides` across both accounts and the one-command add/remove (stage 1).
- [thorwhalen/priv#252](https://github.com/thorwhalen/priv/issues/252): offline reachability and budget-health check in `upkeep fast` (stage 3).
- [thorwhalen/opsward#35](https://github.com/thorwhalen/opsward/issues/35): `diagnose` reports shadowed, unmigrated and budget-at-risk skills for a project.
- [thorwhalen/opsward#36](https://github.com/thorwhalen/opsward/issues/36) (`manual-task`): the always-on list of §5.3 for the user's approval.
- [thorwhalen/opsward#14](https://github.com/thorwhalen/opsward/issues/14): the two-stage-routing probe (§7) and the tier boundary this report supplies, as a comment there.

## REFERENCES

[1] Whalen T. Intelligent Discovery and Dispatch over a Large Personal AI-Asset Ecosystem. 2026. `misc/docs/research/discovery_and_dispatch.md` (this repository).

[2] Whalen T. Groups disclose lazily — design. 2026. `$PP/t/priv/misc/docs/groups_lazy_disclosure.md`; epic [thorwhalen/priv#170](https://github.com/thorwhalen/priv/issues/170).

[3] Anthropic. Claude Code docs: Extend Claude with skills (listing budget, skillOverrides, paths, name conflicts, troubleshooting). 2026. [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills)

[4] Anthropic. Claude Code docs: Settings reference (skillListingBudgetFraction, skillListingMaxDescChars, skillOverrides). 2026. [code.claude.com/docs/en/settings-reference](https://code.claude.com/docs/en/settings-reference)

[5] Agent Skills. Specification. 2025. [agentskills.io/specification](https://agentskills.io/specification)

[6] Whalen T. skill-package-setup skill and `skill-management-best-practices.md`. 2026. `$PP/t/skill/`.

[7] Patil SG, Zhang T, Wang X, Gonzalez JE. Gorilla: Large Language Model Connected with Massive APIs. 2023. [arxiv.org/abs/2305.15334](https://arxiv.org/html/2305.15334v1)

[8] Qin Y, et al. ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs. 2023. [arxiv.org/abs/2307.16789](https://arxiv.org/html/2307.16789v2)

[9] Shi Z, et al. Retrieval Models Aren't Tool-Savvy: Benchmarking Tool Retrieval for Large Language Models (ToolRet). 2025. [arxiv.org/abs/2503.01763](https://arxiv.org/html/2503.01763)

[10] Google Research. Re-Invoke: Tool invocation rewriting for zero-shot tool retrieval. 2024. [research.google/blog/re-invoke](https://www.research.google/blog/re-invoke-tool-invocation-rewriting-for-zero-shot-tool-retrieval/)

[11] Lumer E, et al. Toolshed: Scale Tool-Equipped Agents with Advanced RAG-Tool Fusion and Tool Knowledge Bases. 2024. [arxiv.org/abs/2410.14594](https://arxiv.org/abs/2410.14594)

[12] Tian, Guan. Toollery: skill and tool routing over ~79K capabilities. 2026. [arxiv.org/abs/2609.22218](https://arxiv.org/html/2609.22218v1)

[13] Li, et al. Scalable LLM Agent Tool Access in the Cloud. 2026. [arxiv.org/abs/2607.15593](https://arxiv.org/html/2607.15593)

[14] Repantis, et al. How Many Tools Should an LLM Agent See? 2026. [arxiv.org/abs/2605.24660](https://arxiv.org/abs/2605.24660)

[15] DAIR.AI. AnyTool: hierarchical API retrieval over 16K APIs (summary). 2024. [academy.dair.ai/papers/anytool](https://academy.dair.ai/papers/anytool)

[16] OpenAI. Function calling guide ("fewer than 20 functions available at the start of a turn"). 2026. [developers.openai.com/api/docs/guides/function-calling](https://developers.openai.com/api/docs/guides/function-calling)

[17] Less is More: Optimizing Function Calling for LLM Execution on Edge Devices. 2024. [arxiv.org/abs/2411.15399](https://arxiv.org/html/2411.15399)

[18] Pan T. The Tool Selection Problem: agent tool routing at scale. 2026. [tianpan.co](https://tianpan.co/blog/2026/04/09/tool-selection-problem-agent-tool-routing-at-scale) (the "43%→2%" BFCL figure cited there is unsourced).

[19] Govender D. agent-tool-router (embedding pre-filter recall@3 = 80%). 2026. [github.com/darrshangovender/agent-tool-router](https://github.com/darrshangovender/agent-tool-router)

[20] Model Context Protocol. Specification 2025-11-25: Pagination. [modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination)

[21] Anthropic. Claude Code docs: MCP (tool search, ENABLE_TOOL_SEARCH, alwaysLoad). 2026. [code.claude.com/docs/en/mcp](https://code.claude.com/docs/en/mcp)

[22] OpenAI. Tool search guide (defer_loading). 2026. [developers.openai.com](https://developers.openai.com/api/docs/guides/tools-tool-search.md)

[23] openai/openai-agents-python#2149: dynamic tool groups (closed, not planned). 2025. [github.com](https://github.com/openai/openai-agents-python/issues/2149)

[24] LiteLLM. MCP tool search. 2026. [docs.litellm.ai/docs/mcp_tool_search](https://docs.litellm.ai/docs/mcp_tool_search)

[25] anthropics/claude-code#11045: Skill routing / hidden skills for large skill sets (closed, not planned). 2025–2026. [github.com](https://github.com/anthropics/claude-code/issues/11045)

[26] rulestack. With 160 skills installed, Claude Code kept 20 descriptions and the model found 0 of 3 name-only skills. 2026. [dev.to](https://dev.to/rulestack/with-160-skills-installed-claude-code-kept-20-descriptions-and-the-model-found-0-of-3-skills-that-10j2)

[27] aiwg. Skills listing budget guide (393-skill `/doctor` measurement; deploy-time scoping). 2026. [cdn.jsdelivr.net/npm/aiwg](https://cdn.jsdelivr.net/npm/aiwg@2026.8.8/docs/skills-budget-guide.md)

[28] yotamleo/Himmel PR #1565: per-profile skillListingBudgetFraction and name-only overrides. 2026. [github.com](https://github.com/yotamleo/Himmel/pull/1565)

[29] Vincent J. Claude Code skills not triggering (the 15,000-character budget). 2025. [blog.fsck.com](https://blog.fsck.com/2025/12/17/claude-code-skills-not-triggering/)

[30] obra/superpowers. using-superpowers SKILL.md. 2026. [github.com](https://raw.githubusercontent.com/obra/superpowers/main/skills/using-superpowers/SKILL.md)

[31] Ramim T. skill-trigger-bench. 2026. [github.com](https://github.com/TanbirRamim/skill-trigger-bench)

[32] SkillReducer: compressing agent skills while preserving routing (55,315 public skills). 2026. [arxiv.org/abs/2603.29919](https://arxiv.org/html/2603.29919)

[33] Inside the Scaffold: an anatomy of coding-agent harnesses (Codex `tool_search`, `tool_suggest`). 2026. [arxiv.org/abs/2604.03515](https://arxiv.org/html/2604.03515)

[34] Vincent J. Codex skills. 2025. [blog.fsck.com](https://blog.fsck.com/2025/12/19/codex-skills/)

[35] Tool-to-Agent Retrieval: bridging tools and agents for scalable LLM multi-agent systems. 2025. [arxiv.org/abs/2511.01854](https://arxiv.org/abs/2511.01854)

[36] Long Live the Librarian: a persistent code-search sub-agent. 2026. [arxiv.org/abs/2605.27787](https://arxiv.org/abs/2605.27787)

[37] 123ofAI. Agent router building block (latency tiers). 2026. [123ofai.com](https://123ofai.com/articles/blocks/agent-router)

[38] Anthropic. skill-creator SKILL.md ("Claude has a tendency to undertrigger skills"). 2026. [github.com/anthropics/skills](https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md)

Related reports: `discovery_and_dispatch.md`, `multiplatform_config.md`, `lifecycle_agentops.md` (in this directory).
