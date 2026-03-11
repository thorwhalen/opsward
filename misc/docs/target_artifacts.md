# Target Artifacts

This document specifies every artifact that opsward can generate or maintain
in a target project. Each artifact has a purpose, a location (which varies by
project type), and a generation strategy.

## Artifact Categories

### 1. Documentation Layer

These are knowledge documents that live in the project's docs directory.

| Artifact | Python Path | JS/TS Path | Generation Strategy |
|----------|------------|------------|-------------------|
| `docs_guide.md` | `misc/docs/docs_guide.md` | `docs/docs_guide.md` | Always generated first. Lists all other docs. Auto-updated when docs change. |
| `architecture.md` | `misc/docs/architecture.md` | `docs/architecture.md` | Scan module map, imports, and structure. Produce skeleton with detected components. |
| `known_issues.md` | `misc/docs/known_issues.md` | `docs/known_issues.md` | Empty ledger with template header. Agents append issues during sessions. |
| `conventions.md` | `misc/docs/conventions.md` | `docs/conventions.md` | Detect linter configs, formatters, existing patterns. Pre-populate with detected conventions. |
| `roadmap.md` | `misc/docs/roadmap.md` | `docs/roadmap.md` | Empty template with section headers (Short-term, Medium-term, Long-term, Tech Debt). |
| `glossary.md` | `misc/docs/glossary.md` | `docs/glossary.md` | Scan for domain-specific terms in code/comments. Seed with detected terms. |
| `testing.md` | `misc/docs/testing.md` | `docs/testing.md` | Detect test framework, test directory, coverage config. Document how to run tests. |
| `dependencies.md` | `misc/docs/dependencies.md` | `docs/dependencies.md` | Scan for external service references, env vars, system deps. |
| `deployment.md` | `misc/docs/deployment.md` | `docs/deployment.md` | Only for projects with deploy configs (Dockerfile, CI/CD, cloud configs). |
| `decisions/` | `misc/docs/decisions/` | `docs/decisions/` | Empty directory with a `0000-template.md` MADR template. |
| `session_log.md` | `misc/docs/session_log.md` | `docs/session_log.md` | Optional. Empty template for agents to log learnings. |

**Selective generation:** Not all docs are generated for every project. Rules:
- `docs_guide.md` — always
- `architecture.md` — always (even a one-module project benefits from stating that)
- `known_issues.md` — always
- `conventions.md` — always
- `testing.md` — only if test files/config detected
- `deployment.md` — only if deploy artifacts detected (Dockerfile, .github/workflows/, Procfile, etc.)
- `glossary.md` — only if domain terms detected, or project has >5 modules
- `dependencies.md` — only if external service references detected
- `roadmap.md`, `decisions/`, `session_log.md` — offered but not pushed

### 2. AI Configuration Layer

These are Claude Code (and cross-agent) configuration files.

| Artifact | Location | Generation Strategy |
|----------|----------|-------------------|
| `CLAUDE.md` | `{project_root}/CLAUDE.md` | Core template populated from scan. Includes project overview, tech stack, module map, commands, conventions, and pointer to `docs_guide.md`. |
| `setup-auditor` agent | `.claude/agents/setup-auditor.md` | Read-only diagnostic subagent with `allowed-tools: Read, Glob, Grep`. |
| `diagnose-setup` skill | `.claude/skills/diagnose-setup/SKILL.md` | Skill that runs the diagnosis workflow. References the auditor subagent. |
| `maintain-docs` skill | `.claude/skills/maintain-docs/SKILL.md` | Skill that checks doc freshness, cross-references, and drift. |
| Rules files | `.claude/rules/` | Only if specific conventions detected (e.g., a `no-any.md` rule if TypeScript strict mode is on). |

### 3. Cross-Agent Compatibility

For projects that use multiple AI agents (not just Claude Code):

| Artifact | Location | Purpose |
|----------|----------|---------|
| `AGENTS.md` symlink | `{project_root}/AGENTS.md → CLAUDE.md` | Compatibility with OpenAI Codex, Copilot, and other agents that read AGENTS.md |
| `.agents/skills/` symlinks | `.agents/skills/ → .claude/skills/` | Cross-agent skill discovery per the Agent Skills open standard |

These symlinks are optional and only created if the user opts in (`--cross-agent` flag).

## CLAUDE.md Template Structure

The generated CLAUDE.md follows this section order:

```markdown
# {Project Name}

{One-sentence description}

## Project Overview
{2-3 sentences: purpose, target users, deployment model}

## Tech Stack
{Detected stack with versions where they matter}

## Documentation
For detailed project knowledge, see `{docs_path}/docs_guide.md`.
Read it to discover which docs to consult for your current task.

## Module Map
{Detected directory structure with role annotations}

## Commands
{Detected build/test/run/lint commands from package.json scripts, Makefile, pyproject.toml, etc.}

## Conventions
{Top 5-10 most important conventions, detected from linter configs and code patterns}

## Non-Obvious Patterns
{Anything surprising about the project — detected from comments, unusual patterns}

## Git Workflow
{Detected from .github/, commit history patterns, branch naming}
```

## JS/TS-Specific Adaptations

When generating for a JS/TS project, opsward adapts:

- **Docs path:** `docs/` instead of `misc/docs/`
- **Commands section:** Scans `package.json` scripts, detects package manager (npm/yarn/pnpm/bun)
- **Tech stack detection:** Reads `package.json` dependencies, `tsconfig.json` settings
- **Framework detection:** React, Next.js, Vue, Svelte, Express, Fastify, etc. — adjusts conventions accordingly
- **Linter detection:** ESLint config, Prettier config, Biome config
- **Test detection:** Vitest, Jest, Playwright, Cypress configs
- **Monorepo detection:** Workspaces in package.json, turbo.json, nx.json, lerna.json

## Python-Specific Adaptations

- **Docs path:** `misc/docs/`
- **Commands section:** Scans pyproject.toml scripts, Makefile, tox.ini
- **Tech stack detection:** Reads pyproject.toml dependencies, setup.cfg
- **Framework detection:** Django, Flask, FastAPI, etc.
- **Linter detection:** Ruff, Black, isort, mypy, pylint configs
- **Test detection:** pytest config, unittest patterns
- **Package detection:** pyproject.toml `[project]` metadata, setup.py

## Template Variable Reference

Variables available in all templates:

| Variable | Source | Example |
|----------|--------|---------|
| `${project_name}` | Directory name or package.json/pyproject.toml name | `cosmograph` |
| `${project_description}` | Package metadata or README first line | `WebGL graph visualization platform` |
| `${project_type}` | Detection logic | `python`, `jsts`, `mixed` |
| `${docs_path}` | Derived from project type | `misc/docs` or `docs` |
| `${tech_stack}` | Detected and formatted | `Python 3.11, FastAPI, PostgreSQL` |
| `${module_map}` | Directory scan, formatted as markdown list | `- src/api/ — REST endpoints` |
| `${commands}` | Detected from config files | `pytest`, `npm run build` |
| `${package_manager}` | Detected | `pip`, `pnpm`, `yarn` |
