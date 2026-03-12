---
name: opsward-diagnose
description: Diagnose the health of this project's AI agent setup. Use when the user asks to check, audit, or score the project's CLAUDE.md, skills, docs, or agent configuration.
---

# Diagnose AI Setup

Run opsward's deterministic diagnostic, then go deeper with your own analysis, and offer fixes.

## Prerequisites

Requires `opsward` to be installed (`pip install opsward`). If the command is not found, tell the user to install it.

## Workflow

### 1. Run the deterministic diagnostic

```bash
opsward diagnose . --format json
```

This returns structured scores (0-100) for CLAUDE.md quality, documentation, skills, setup, and cross-references. Also run the text version for the user:

```bash
opsward diagnose .
```

### 2. Go deeper than the scores

Opsward uses regex heuristics — it catches structural issues but can't assess semantic quality. You can. For each component:

- **CLAUDE.md**: Read it. Is the module map accurate? Are the commands actually correct? Does it match the real project structure? Check `pyproject.toml`, `package.json`, source directories.
- **Docs**: Read each doc. Is the content real or just a template stub? Does `architecture.md` describe the actual architecture?
- **Skills**: Read each SKILL.md. Are the trigger descriptions clear? Do the instructions make sense for this project?
- **Cross-references**: Opsward checks path existence. You can check whether referenced files have the content the reference implies.

Use Read, Glob, and Grep freely to inspect the project — these are read-only and safe.

### 3. Present findings

For each component:
- State the opsward score and what it measures
- Add your own observations (what opsward can't catch)
- Highlight the most impactful improvements

### 4. Offer fixes

For each issue, propose a concrete fix:
- Missing CLAUDE.md → offer to generate or write a tailored one
- Inaccurate module map → read the actual directory structure and rewrite it
- Low commands score → read `pyproject.toml`/`package.json` and add real commands
- Broken cross-references → identify stale paths, update or remove them
- Missing/empty docs → read the codebase and write real content (not just templates)
- Missing skill descriptions → read the skill directory and write a proper description

### 5. Apply fixes with user approval

Always ask before writing or editing files. Show the proposed change first.

### 6. Re-run diagnostic

```bash
opsward diagnose .
```

Show before/after scores.

## Scoring Dimensions (for reference)

- **CLAUDE.md quality** (35% weight): commands/workflows, architecture clarity, conventions, conciseness, currency, actionability
- **Documentation** (25%): docs_guide.md, core docs, content, cross-refs
- **Skills** (20%): SKILL.md presence, descriptions
- **Setup** (10%): rules, agents, hooks configuration
- **Cross-references** (10%): paths in CLAUDE.md that actually exist on disk

## Permissions

This skill needs no special permissions for diagnosis (read-only). Applying fixes requires write permission — Claude Code will prompt the user for approval on each write/edit action as configured in their permission settings.
