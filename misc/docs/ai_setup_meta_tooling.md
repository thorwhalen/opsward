# AI Agent Setup Meta-Tooling: Diagnosis, Generation & Maintenance

## Research Summary

This document covers the landscape of tools for diagnosing, creating, and maintaining the AI agent configuration layer of a project — specifically CLAUDE.md, skills, subagents, commands, rules, and supporting documentation. It then proposes a concrete design for a reusable meta-tooling system.

---

## 1. What Exists Today

### 1.1 Official Anthropic Tools

Anthropic provides one official meta-skill: **`skill-creator`** from the `anthropics/skills` repo [1]. It's a comprehensive skill that walks you through designing, testing, and optimizing skills — including an eval framework with `generate_review.py` and a description optimizer that uses train/test splits to tune skill triggering [1][2]. It can be installed via:

```bash
npx skills add anthropics/skills --skill skill-creator
```

Beyond that, there is **no official "project AI setup diagnostic" tool**. Anthropic provides the primitives (CLAUDE.md, `.claude/skills/`, `.claude/agents/`, `.claude/rules/`, hooks) but no built-in command that audits or scaffolds them [3][4]. The `/init` command in Claude Code creates a basic CLAUDE.md but doesn't diagnose the full AI setup.

The **Agent Skills open standard** at agentskills.io [5] and the **`npx skills` CLI** from Vercel [6] provide cross-platform skill management (install, list, find, update, check) — but again, no diagnostic/maintenance tooling.

### 1.2 Community Skills Worth Knowing About

From **skills.sh** and **LobeHub**, several community skills address pieces of the meta-tooling problem:

| Skill | Source | What It Does |
|-------|--------|-------------|
| **skill-creator** | anthropics/skills [1] | Official. Full skill creation + eval + description optimization workflow |
| **skill-development** | melodic-software (LobeHub) [7] | Comprehensive meta-skill for creating, validating, auditing skills. Includes YAML frontmatter guidance, naming conventions, progressive disclosure patterns, `allowed-tools` configuration |
| **claude-md-management** | giuseppe-trisciuoglio (LobeHub) [8] | Full lifecycle CLAUDE.md management: discovery, quality assessment (6-dimension rubric, 0-100 scoring), reporting, improvement, maintenance |
| **claude-md-management** | doancan-mags (LobeHub) [9] | Lighter version: templates for CLAUDE.md sections (Project Overview, Tech Stack, Module Map, Conventions) |
| **project-health** | jezweb (LobeHub) [10] | All-in-one: bootstrap, audit, tidy. Checks permissions, context quality, MCP coverage, leaked secrets, stale docs. Uses sub-agents for heavy analysis |
| **my-claude (brewcode)** | kochetkov-ma (LobeHub) [11] | Documents your local Claude Code setup — spawns parallel Explore agents to scan global config, project config, and memory files, then generates a report |
| **skills-collection-manager** | jackspace (LobeHub) [12] | Manages large skill collections: health checks, dedup, categorization, weekly maintenance scripts |
| **agent-skill-creator** | FrancyJGLisboa (GitHub) [13] | Cross-platform (14 agents) skill generator with auto-install scripts, format adapters for Cursor/Windsurf |
| **find-skills** | vercel-labs/skills [6] | #1 most-installed skill (478K installs). Searches and discovers skills from the ecosystem |

**Reference architecture repos** — these aren't tools but demonstrate what "good" Claude Code setups look like in practice:

| Repo | What It Demonstrates |
|------|---------------------|
| **ChrisWiles/claude-code-showcase** [25] | Skill-evaluation hooks (UserPromptSubmit → skill-eval.sh → skill-rules.json), auto-formatting PostToolUse hooks, GitHub Actions for monthly doc sync + weekly code quality + biweekly dependency audits, PR review automation |
| **diet103/claude-code-infrastructure-showcase** [26] | Hook-based skill auto-activation (solving the "skills don't activate" problem via skill-rules.json pattern matching). Modular skills with 500-line rule, progressive disclosure, dev docs for cross-session persistence (plan/context/tasks files) |
| **disler/claude-code-hooks-mastery** [27] | All 13 hook events implemented. Meta-agent that generates sub-agents. UV single-file scripts for hook isolation (each script self-contained with embedded deps). Builder/Validator agent pairs |
| **philoserf/claude-code-setup** [28] | 5 hooks, 8 rules, 23 skills, 2 commands. Observability via session directories and shell snapshots. Skill quality assessment skills. "Don't install this, just steal what you like" philosophy |
| **christianestay/claude-code-base-project** [29] | 4 agents, 12 skills (all agentskills.io-compliant). Self-improvement loop (tasks/todo.md + tasks/lessons.md). 6-layer anti-hallucination architecture. Progressive disclosure: metadata (~100 tokens) → instructions (~200 tokens) → references (on demand) |

**Ecosystem resources**:

| Resource | What It Is |
|----------|-----------|
| **VoltAgent/awesome-agent-skills** [30] | Curated catalog of 549+ skills from official dev teams (Anthropic, Google Labs, Vercel, Stripe, Cloudflare, Supabase). Cross-platform. Could opsward recommend/install skills from here based on project analysis? |
| **hesreallyhim/awesome-claude-code** [31] | Best single index of the Claude Code ecosystem — skills, workflows, tooling, hooks, slash-commands, alternative clients. No mention of diagnostic tools → confirms the gap opsward fills |
| **Mintlify skill.md auto-generation** [32] | Auto-generates `/.well-known/skills/default/skill.md` from docs sites. Same philosophy as opsward (generate agent-readable context from existing artifacts), applied to documentation instead of codebases. Decision tables, explicit boundaries, gotchas sections |
| **TÂCHES Claude Code Resources** [31] | Meta-skills: skill-auditor, hook creation, adaptable workflows. Self-referential tooling in the same vein as opsward |

**The gap**: None of these tools combine all three concerns — (1) diagnosing the full AI setup, (2) generating missing pieces, and (3) maintaining/updating the documentation layer — into a single cohesive workflow that works across multiple project roots. The closest competitor (spec-kit [18]) covers scaffolding but has no diagnosis or maintenance. The inside-agent tools (skill-factory [19], agents-md-generator [21]) can't run in CI or across projects.

### 1.3 Related Standards

- **AGENTS.md** [14]: Open standard from OpenAI/community for agent instructions. Claude Code uses CLAUDE.md instead but they can be symlinked. GitHub found 6 core areas in effective agent config: commands, testing, project structure, code style, git workflow, and boundaries [15].
- **MADR** (Markdown Any Decision Records) [16]: Structured format for architectural decisions in `decisions/` folders.
- **`.agent/` directory proposal** [17]: A GitHub issue proposing a standardized `.agent` directory as a single source of truth for project context (specs, wiki, resources, links). Not adopted yet but the right instinct.

### 1.4 Closest Competitors & Peer Tools

These are the CLI tools and generators that operate closest to opsward's space. For each: what it does, how it differs, and what opsward should do about it.

| Tool | What It Does | Key Difference from Opsward | Opsward Posture |
|------|-------------|---------------------------|----------------|
| **spec-kit** (GitHub) [18] | Python CLI (`specify init`) that scaffolds agent config for 20+ AI agents. Template-based, supports `--ai claude`, `--ai-skills` for SKILL.md generation. Maintained under the GitHub org. | Template-based scaffolding only — no diagnosis, no scoring, no maintenance. Single-project. Focused on "spec-driven development" (specs → implementation). | **Integrate**: opsward's `generate` could optionally emit spec-kit-compatible project structures. Don't compete on scaffolding — compete on diagnosis + maintenance. |
| **claude-code-skill-factory** [19] | Interactive builders (`/build skill`, `/build agent`, `/build hook`, `/build prompt`) + CLAUDE.md analyzer/enhancer with quality scoring. 5 interactive guide agents, 9 production skills. | Operates *inside* Claude Code via prompts — not a standalone CLI. Consumes agent context. No multi-project support. No staleness/drift detection. | **Mention**: good for individual skill authoring. Opsward's external CLI approach is CI-friendly and context-free. |
| **ccexp** [20] | Interactive TUI (React Ink) for discovering/browsing Claude Code config files. Split-pane layout, search, preview. | Read-only browser — no generation, no diagnosis, no scoring. Complements opsward rather than competing. | **Mention**: nice companion for manual exploration. Orthogonal to opsward. |
| **agents-md-generator** (LobeHub) [21] | Skill that auto-generates/updates CLAUDE.md and AGENTS.md by scanning project files. Multi-tech-stack detection, merge-safe updates preserving custom sections. | Runs inside an agent (context-consuming). No quality scoring, no multi-project, no maintenance loop. | **Mention**: similar generation philosophy. Opsward does it externally and adds diagnosis + maintenance. |
| **netresearch/agent-rules-skill** [22] | Skill for generating AGENTS.md from inside Claude Code. Creates thin root files + scoped subsystem files. Idempotent updates with managed headers. | Inside-agent only. AGENTS.md-specific (not CLAUDE.md). No scoring or drift detection. | **Integrate**: opsward could adopt its scoped-AGENTS.md pattern for monorepos. |
| **claudekit** [23] | CLI toolkit with auto-save checkpointing, code quality hooks, spec generation, 20+ specialized subagents. | Broader scope (checkpointing, hooks, subagents) but no diagnostic scoring or maintenance loop. More of an "enhanced Claude Code runtime" than a meta-tooling system. | **Mention**: different problem space. Not a direct competitor. |
| **Vercel skills CLI** (`npx skills`) [6] | Cross-platform skill package manager: install, list, find, update, check, init. Supports GitHub/GitLab/local sources. | Package manager, not a generator or diagnostician. Manages individual skills, not the full AI setup. | **Integrate**: opsward-generated skills should be installable via `npx skills add`. |
| **wshobson/agents** [24] | Monorepo of 72 plugins, 112 agents, 146 skills, 16 orchestrators. Batteries-included, plugin-based architecture. | Opposite philosophy: pre-built configs vs. project-specific generation. No diagnosis. | **Mention**: good for users who want off-the-shelf configs. Opsward generates *project-specific* configs. |

**Takeaway**: No existing tool combines diagnosis + generation + maintenance in a standalone, CI-friendly CLI. spec-kit is closest on generation but lacks diagnosis/scoring entirely. The inside-agent tools (skill-factory, agents-md-generator) solve similar problems but consume context and can't run in CI or across multiple projects.

### 1.5 Open Standards Opsward Should Target

Three open standards are relevant to opsward's output:

**1. Agent Skills Open Standard (agentskills.io)** [5]

The cross-platform SKILL.md specification adopted by Claude Code, Codex, Copilot, Cursor, Gemini CLI, OpenCode, and 20+ tools. Defines:
- Required frontmatter: `name` (1-64 chars, lowercase+hyphens, must match directory name), `description` (1-1024 chars)
- Optional frontmatter: `license`, `compatibility`, `metadata` (arbitrary key-value), `allowed-tools` (space-delimited, experimental)
- Directory structure: `SKILL.md` (required) + optional `scripts/`, `references/`, `assets/`
- Progressive disclosure: metadata (~100 tokens) → instructions (<5000 tokens) → resources (on demand)
- Main SKILL.md should stay under 500 lines
- Validation via `skills-ref validate ./my-skill`

**Opsward status**: Opsward already generates SKILL.md files and follows the directory convention. It should add a **validation step** to `diagnose` that checks existing skills against the agentskills.io spec (name format, frontmatter fields, size limits).

**2. AGENTS.md Standard** [14]

Cross-platform convention supported by 60,000+ open-source projects and agents including Codex, Jules, Copilot, Cursor, Devin, Gemini CLI, and others. Key properties:
- Standard Markdown, flexible headings, no required fields
- Placed at repo root or in subdirectories (nearest file to edited content wins)
- Complements CLAUDE.md: AGENTS.md = cross-platform behavioral guidance; CLAUDE.md = Claude-specific configuration
- Common sections: project overview, build/test commands, code style, testing, PR instructions, security

**Opsward status**: Opsward currently generates CLAUDE.md but not AGENTS.md. It should add an `--agents-md` flag to `generate` that emits an AGENTS.md alongside (or instead of) CLAUDE.md, making the project's AI setup portable across agents.

**3. MADR (Markdown Any Decision Records)** [16]

Structured format for architectural decisions in `decisions/` folders.

**Opsward status**: Already targeted. Opsward's `generate` creates a `decisions/` folder with MADR-style templates. No changes needed.

---

## 2. Recommended Documentation Structure

Based on research across the ecosystem, here's the proposed **docs structure** — adapted for your Python (`misc/docs/`) and JS/TS (`docs/`) convention:

### 2.1 The Docs Catalog

| Document | Filename | Purpose |
|----------|----------|---------|
| **Docs Guide** | `docs_guide.md` | Entry point. Lists all docs with descriptions. CLAUDE.md points here. |
| **Architecture Notes** | `architecture.md` | System design, component relationships, data flow, key abstractions |
| **Known Issues** | `known_issues.md` | Ledger of problems agents notice. Links to GitHub issues for details |
| **Changelog** | `CHANGELOG.md` | Standard. Keep at project root AND/OR in docs/ |
| **Roadmap** | `roadmap.md` | Longer-term plans, feature ideas, technical debt items |
| **Decision Log** | `decisions/NNNN-title.md` | MADR-style architectural decision records [16] |
| **Conventions** | `conventions.md` | Code style, naming, patterns that differ from defaults |
| **Glossary** | `glossary.md` | Domain-specific terms, abbreviations, concept definitions |
| **Dependencies** | `dependencies.md` | External services, APIs, system deps, env vars needed |
| **Testing Guide** | `testing.md` | How to run tests, what frameworks, coverage expectations |
| **Deployment** | `deployment.md` | How to deploy, environments, CI/CD pipeline |
| **Session Log** | `session_log.md` | Optional. Agent session learnings, "TIL" items from Claude Code sessions |

### 2.2 Naming Rationale

These names were chosen for maximum ecosystem compatibility:
- `architecture.md` / `ARCHITECTURE.md` — widely recognized across GitHub repos and agent tooling [10][15]
- `CHANGELOG.md` — standard (keepachangelog.com)
- `decisions/` — MADR standard [16]
- `known_issues.md` — self-explanatory, grep-friendly
- `docs_guide.md` — your custom entry-point innovation (analogous to a table of contents for AI context)

---

## 3. Proposed Meta-Tooling Design

### 3.1 Architecture Overview

The system is a **skill + subagent + command trio** installed either globally (`~/.claude/`) or per-project (`.claude/`):

```
.claude/
├── skills/
│   └── ai-setup/                    # The meta-skill
│       ├── SKILL.md                 # Main instructions
│       └── references/
│           ├── diagnosis_checklist.md
│           ├── doc_templates/
│           │   ├── docs_guide.template.md
│           │   ├── architecture.template.md
│           │   ├── known_issues.template.md
│           │   └── ...
│           └── scoring_rubric.md
├── agents/
│   └── setup-auditor.md             # Read-only diagnostic subagent
└── commands/                        # (now unified with skills, but for clarity)
    ├── diagnose-setup.md            # /diagnose-setup
    ├── generate-docs.md             # /generate-docs
    └── maintain-setup.md            # /maintain-setup
```

### 3.2 The Three Commands

#### `/diagnose-setup` — The Diagnostic

Scans one or more project roots and produces a report card:

**What it checks:**
1. **CLAUDE.md** — exists? scored on quality rubric (commands, architecture clarity, conventions, currency, actionability) [8]
2. **Skills** (`.claude/skills/`) — inventory, frontmatter validity, description quality, size (<500 lines)
3. **Subagents** (`.claude/agents/`) — inventory, tool permissions, model routing
4. **Rules** (`.claude/rules/`) — inventory, size (target 20-80 lines per file) [10]
5. **Hooks** (`.claude/hooks.json` or `settings.local.json`) — any configured?
6. **Docs directory** — exists? which docs present? `docs_guide.md` as entry point?
7. **Cross-references** — does CLAUDE.md point to docs? do skills reference docs? stale paths?
8. **Project type detection** — Python vs JS/TS vs mixed → determines expected doc location

**Output:** A structured report with scores, missing items, and prioritized suggestions.

**Implementation pattern:** Uses the `setup-auditor` subagent with `context: fork` and `allowed-tools: Read, Glob, Grep` (read-only) to keep main context clean.

#### `/generate-docs` — The Generator

Creates missing documentation from templates, informed by codebase analysis:

**What it generates:**
- `docs_guide.md` — always first, as the entry point
- Missing docs from the catalog above, populated by scanning the codebase
- CLAUDE.md sections that are missing or thin
- Skeleton skills for common project patterns (commit, test, review)

**Key behavior:** Never overwrites existing content. Presents diffs for approval. Uses templates from `references/doc_templates/`.

#### `/maintain-setup` — The Maintenance Loop

Checks for staleness and drift:

**What it maintains:**
- `known_issues.md` — appends new issues discovered during the session, links to GitHub issues
- `docs_guide.md` — updates if new docs were added or old ones removed
- CLAUDE.md — suggests updates if project structure changed (new modules, renamed files)
- `architecture.md` — flags if code structure has diverged from documented architecture
- Skill descriptions — runs the description optimizer pattern from Anthropic's skill-creator [1]
- `session_log.md` — captures learnings from the current session

### 3.3 The `docs_guide.md` Pattern

This is the keystone document. CLAUDE.md contains a single pointer:

```markdown
## Documentation
For detailed project knowledge, see `docs/docs_guide.md` (JS/TS) or `misc/docs/docs_guide.md` (Python).
Read it to discover which other docs to consult for your current task.
```

And `docs_guide.md` itself looks like:

```markdown
# Documentation Guide

This directory contains project knowledge documents for both human developers
and AI agents. Consult this guide to find the right document for your task.

| Document | When to Read | Last Updated |
|----------|-------------|--------------|
| `architecture.md` | Before making structural changes, adding modules, or refactoring | 2026-03-01 |
| `known_issues.md` | Before starting work (check if your task has known gotchas) | 2026-03-10 |
| `conventions.md` | Before writing new code (style, patterns, naming) | 2026-02-15 |
| `decisions/` | Before proposing architectural changes (check prior decisions) | varies |
| `roadmap.md` | When prioritizing work or proposing new features | 2026-02-20 |
| `glossary.md` | When encountering unfamiliar domain terms | 2026-01-30 |
| `testing.md` | Before writing or modifying tests | 2026-02-10 |
| `dependencies.md` | When adding external services or system deps | 2026-02-01 |
| `deployment.md` | Before deploying or modifying CI/CD | 2026-01-15 |
| `session_log.md` | Optional — review for context on recent agent sessions | 2026-03-11 |
```

### 3.4 Python vs JS/TS Adaptation

The skill auto-detects project type and adapts paths:

| Signal | Type | Docs Location |
|--------|------|--------------|
| `pyproject.toml`, `setup.py`, `setup.cfg` | Python | `misc/docs/` |
| `package.json`, `tsconfig.json` | JS/TS | `docs/` |
| Both present | Mixed | `docs/` (JS/TS convention wins for shared repos) |

### 3.5 Multi-Project Scanning

For your use case of pointing at multiple project roots:

```
/diagnose-setup ~/projects/cosmograph ~/projects/py_cosmograph ~/projects/accompy
```

The command spawns one `setup-auditor` subagent per project (parallel via `context: fork`), collects results, and presents a unified report with per-project scores and cross-project patterns (e.g., "3 of 5 projects are missing `conventions.md`").

---

## 4. Implementation Priority

Recommended build order:

1. **`docs_guide.md` template + CLAUDE.md pointer pattern** — immediate value, zero tooling needed
2. **`/diagnose-setup` command** — the diagnostic is the most useful standalone piece
3. **Doc templates** in `references/doc_templates/` — so `/generate-docs` has good starting points
4. **`/generate-docs` command** — scaffold missing docs
5. **`/maintain-setup` command** — the maintenance loop (highest complexity, most value over time)
6. **Description optimizer** integration — port the train/test pattern from Anthropic's skill-creator [1]

---

## 5. Key Design Principles

Drawing from your coding philosophy:

- **Progressive disclosure**: `/diagnose-setup` works with zero config. Advanced users can customize rubrics, templates, and scoring weights.
- **SSOT**: `docs_guide.md` is the single entry point. CLAUDE.md doesn't duplicate doc content — it points to docs_guide.
- **Mapping pattern**: The docs catalog is essentially a `Mapping[str, DocMetadata]` — key is filename, value is purpose + freshness.
- **Functional over OOP**: The skills are prompt-driven workflows, not class hierarchies. Each command is a pure function: project_root → diagnosis_report.
- **Facade**: The three commands (`diagnose`, `generate`, `maintain`) are the facade over the full complexity of skills, subagents, docs, rules, hooks, and CLAUDE.md management.
- **Read-only diagnosis**: The auditor subagent has `allowed-tools: Read, Glob, Grep` — it can never accidentally modify anything.

---

## References

[1] Anthropic. "skill-creator." [anthropics/skills](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)

[2] Anthropic. "The Complete Guide to Building Skills for Claude." [PDF](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)

[3] Anthropic. "Extend Claude with skills." [Claude Code Docs](https://code.claude.com/docs/en/skills)

[4] Anthropic. "Agent Skills Overview." [Platform Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

[5] Agent Skills Open Standard. [agentskills.io](https://agentskills.io/integrate-skills)

[6] Vercel Labs. "Skills CLI." [vercel-labs/skills](https://github.com/vercel-labs/skills)

[7] melodic-software. "skill-development." [LobeHub](https://lobehub.com/skills/melodic-software-claude-code-plugins-skill-development)

[8] giuseppe-trisciuoglio. "claude-md-management." [LobeHub](https://lobehub.com/skills/giuseppe-trisciuoglio-developer-kit-claude-md-management)

[9] doancan-mags. "claude-md-management." [LobeHub](https://lobehub.com/skills/doancan-mags-claude-md-management)

[10] jezweb. "project-health." [LobeHub](https://lobehub.com/skills/jezweb-claude-skills-project-health)

[11] kochetkov-ma. "my-claude (brewcode)." [LobeHub](https://lobehub.com/skills/kochetkov-ma-claude-brewcode-my-claude)

[12] jackspace. "skills-collection-manager." [LobeHub](https://lobehub.com/skills/jackspace-claudeskillz-skills-collection-manager)

[13] FrancyJGLisboa. "agent-skill-creator." [GitHub](https://github.com/FrancyJGLisboa/agent-skill-creator)

[14] AGENTS.md Standard. [agents.md](https://agents.md/)

[15] GitHub Blog. "How to write a great agents.md." [GitHub Blog](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)

[16] MADR. "Markdown Any Decision Records." [adr.github.io/madr](https://adr.github.io/madr/)

[17] agentsmd/agents.md Issue #71. "Proposal: Standardize a .agent Directory." [GitHub](https://github.com/agentsmd/agents.md/issues/71)

[18] GitHub. "spec-kit (Specify CLI)." [github/spec-kit](https://github.com/github/spec-kit)

[19] Alireza Rezvani. "Claude Code Skill Factory." [GitHub](https://github.com/alirezarezvani/claude-code-skill-factory)

[20] nyatinte. "ccexp — Claude Code Explorer." [GitHub](https://github.com/nyatinte/ccexp)

[21] thienanblog. "agents-md-generator." [LobeHub](https://lobehub.com/skills/thienanblog-awesome-agent-skills-agents-md-generator)

[22] Netresearch. "agent-rules-skill." [GitHub](https://github.com/netresearch/agent-rules-skill)

[23] Carl Rannaberg. "claudekit." Referenced in [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)

[24] wshobson. "agents — 72 plugins, 112 agents, 146 skills." [GitHub](https://github.com/wshobson/agents)

[25] Chris Wiles. "claude-code-showcase." [GitHub](https://github.com/ChrisWiles/claude-code-showcase)

[26] diet103. "claude-code-infrastructure-showcase." [GitHub](https://github.com/diet103/claude-code-infrastructure-showcase)

[27] disler. "claude-code-hooks-mastery." [GitHub](https://github.com/disler/claude-code-hooks-mastery)

[28] philoserf. "claude-code-setup." [GitHub](https://github.com/philoserf/claude-code-setup)

[29] Christian Estay. "claude-code-base-project." [GitHub](https://github.com/christianestay/claude-code-base-project)

[30] VoltAgent. "awesome-agent-skills." [GitHub](https://github.com/VoltAgent/awesome-agent-skills)

[31] hesreallyhim. "awesome-claude-code." [GitHub](https://github.com/hesreallyhim/awesome-claude-code)

[32] Mintlify. "Auto-generated skill.md." [Blog](https://www.mintlify.com/blog/skill-md)
