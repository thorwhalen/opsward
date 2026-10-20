---
name: opsward-maintain
description: Check documentation and AI setup for staleness, drift, or inconsistency. Use when the user asks to maintain, refresh, or update project docs and AI configuration.
---

# Maintain AI Setup

Run opsward's maintenance checks, go deeper with your own analysis, then fix issues found.

## Prerequisites

Requires `opsward` to be installed (`pip install opsward`). If the command is not found, tell the user to install it.

## Workflow

### 1. Run maintenance checks

```bash
opsward maintain . --format json
```

This returns issues categorized as: stale_path, sync_issue, outdated_doc, incomplete_skill, empty_doc, subagent_twin (a skill's declared subagent twin is missing, stale, or hand-written; see the `opsward-subagents` skill), stale_adr (a decision record cites a path that no longer exists, or has no Status: write a superseding ADR or a log entry; the accepted one is only edited to point its Status at the successor). Also run the text version:

```bash
opsward maintain .
```

### 2. Go deeper than opsward

Opsward catches structural drift (broken paths, unlisted docs, empty stubs). You can catch semantic drift:

- **Accuracy**: Read docs and compare against the actual code. Does `architecture.md` still describe the real architecture? Has the module map in CLAUDE.md drifted from the actual directory structure?
- **Completeness**: Are there new modules, commands, or patterns not yet documented? Check `git log` for recent changes to source files that docs reference.
- **Obsolescence**: Do docs reference removed features, old API signatures, or deprecated patterns?
- **Consistency**: Do different docs contradict each other? Does CLAUDE.md say one thing while conventions.md says another?

Use Read, Grep, Glob, and Bash (`git log`, `git diff`) freely for this analysis.

### 3. Categorize and prioritize

Group all issues (opsward's + yours) by severity:
- **High priority**: Incorrect information (wrong commands, inaccurate architecture), broken references that mislead
- **Medium priority**: Outdated docs, incomplete descriptions, missing new content
- **Low priority**: Empty stubs, minor formatting, cosmetic issues

### 4. Triage every drift finding: align, revert or ignore

Each finding carries a recommended `triage` (in `--format json`, and after the category in the text output). Decide one of three per finding, and say which in your proposal:

- **align**: the code is right and the config is stale: update the reference, the doc or the skill to match the code. The usual case.
- **revert**: the config is right and the code drifted from it (a file deleted by mistake, a convention broken): restore the code, not the doc.
- **ignore**: the reference is legitimately volatile (a generated file, an example path, a file that exists only on some machines): add `<!-- opsward: ignore-path -->` at the end of that line, or alone on the line before it, and opsward stops checking the paths it covers.

### 5. Propose and apply fixes

For each issue, propose a concrete fix:
- **Stale path**: Determine if the file was renamed, moved, or deleted. Update or remove the reference.
- **Inaccurate doc**: Read the source code and rewrite the relevant section with correct information.
- **Sync issue**: Add missing docs to docs_guide.md, or remove references to deleted docs.
- **Outdated doc**: Read the code it describes, update to reflect current state.
- **Incomplete skill**: Read the skill directory, write a proper SKILL.md with description.
- **Empty doc**: Read the project to understand what should go in it, write real content.

Always ask the user before writing or editing. Show proposed changes first. For destructive operations (removing content, deleting files), explain why and get explicit confirmation.

### 6. Verify

```bash
opsward maintain .
opsward diagnose .
```

Show that issues are resolved and the overall score improved.

## Permissions

- **Read/Grep/Glob**: Used freely for analysis (always safe).
- **Edit**: Needed to fix existing files. Claude Code prompts per user settings.
- **Write**: Needed for new files. Claude Code prompts per user settings.
- **Bash**: For opsward commands and git inspection. Claude Code prompts per user settings.

This skill never deletes files without explicit user confirmation, even if the user has auto-allow enabled for other operations.
