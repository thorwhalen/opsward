# Documentation Catalog

The canonical list of documentation types that opsward knows about. This is the
SSOT for doc type definitions — the generator, diagnostic, and maintenance engine
all derive their behavior from this catalog.

## Core Docs (always recommended)

### `docs_guide.md`
- **Purpose:** Entry-point document. Lists all other docs with descriptions and "when to read" guidance.
- **Naming rationale:** Custom to opsward. Analogous to a table of contents for AI context. Readable by both humans and agents.
- **Maintenance:** Auto-updated by the maintain engine when docs are added or removed.
- **Template:** `shared/docs_guide.md`

### `architecture.md`
- **Purpose:** System design, component relationships, data flow, key abstractions.
- **Naming rationale:** Widely recognized. Used by `project-health` (LobeHub), AGENTS.md best practices, and many open source projects. GitHub's analysis of 2,500+ repos found architecture clarity as a top factor.
- **Also known as:** `ARCHITECTURE.md` (some projects capitalize it)
- **Template:** `shared/architecture.md`

### `known_issues.md`
- **Purpose:** Ledger of problems that agents (or humans) notice. Each entry is a short description with an optional link to a GitHub issue for details.
- **Naming rationale:** Self-explanatory, grep-friendly. The pattern of a lightweight issue ledger separate from the issue tracker is useful because agents can quickly scan it without API calls.
- **Template:** `shared/known_issues.md`

### `conventions.md`
- **Purpose:** Code style, naming patterns, and project-specific rules that differ from language defaults.
- **Naming rationale:** Clear and standard. Distinct from `CONTRIBUTING.md` (which is for humans contributing to the project) — `conventions.md` is specifically about code patterns an agent should follow.
- **Template:** `python/conventions.md`, `jsts/conventions.md`

## Recommended Docs (generated when relevant)

### `roadmap.md`
- **Purpose:** Longer-term plans, feature ideas, technical debt items.
- **Naming rationale:** Standard. Many projects have this.
- **When to generate:** Always offered, never forced.
- **Template:** `shared/roadmap.md`

### `glossary.md`
- **Purpose:** Domain-specific terms, abbreviations, concept definitions.
- **Naming rationale:** Standard. Particularly useful for projects with rich domain models.
- **When to generate:** When domain terms are detected, or project has >5 modules.
- **Template:** `shared/glossary.md`

### `testing.md`
- **Purpose:** How to run tests, what frameworks are used, coverage expectations, test patterns.
- **Naming rationale:** Clear and standard.
- **When to generate:** When test files or test config detected.
- **Template:** `python/testing.md`, `jsts/testing.md`

### `dependencies.md`
- **Purpose:** External services, APIs, system dependencies, required env vars.
- **Naming rationale:** Distinct from `requirements.txt` or `package.json` — this documents the *why* and *how* of external dependencies, not just the list.
- **When to generate:** When external service references detected (env vars, API URLs, Docker service deps).
- **Template:** `shared/dependencies.md`

### `deployment.md`
- **Purpose:** How to deploy, environments, CI/CD pipeline description.
- **Naming rationale:** Standard.
- **When to generate:** When deploy artifacts detected (Dockerfile, CI configs, cloud configs).
- **Template:** `shared/deployment.md`

### `decisions/`
- **Purpose:** MADR-style architectural decision records. Each decision is a separate file: `NNNN-title-with-dashes.md`.
- **Naming rationale:** MADR standard. The `decisions/` directory name is the MADR convention.
- **When to generate:** Always create the directory with a `0000-template.md`. Individual ADRs are written by humans/agents as decisions are made.
- **Template:** `shared/decisions/0000-template.md`

### `session_log.md`
- **Purpose:** Agent session learnings, TIL items, gotchas discovered during Claude Code sessions.
- **Naming rationale:** Descriptive. This is an append-only log, not a structured document.
- **When to generate:** Optional. Offered but not pushed. Most useful for active development projects.
- **Template:** `shared/session_log.md`

## Names We Explicitly Don't Use

| Name | Why Not | Use Instead |
|------|---------|-------------|
| `CONTRIBUTING.md` | Human-facing, not agent-facing | `conventions.md` for agent-relevant style rules |
| `TODO.md` | Too informal, drifts quickly | `roadmap.md` + `known_issues.md` |
| `NOTES.md` | Vague | Specific doc type based on content |
| `docs/index.md` | Conflicts with static site generators | `docs_guide.md` |
| `DESIGN.md` | Ambiguous (UI design? system design?) | `architecture.md` |
