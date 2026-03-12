---
name: opsward-generate
description: Generate missing AI setup artifacts for this project. Use when the user asks to scaffold, create, or bootstrap CLAUDE.md, docs, skills, or agent configuration.
---

# Generate AI Setup Artifacts

Use opsward to scaffold missing artifacts, then go beyond templates — read the actual codebase and fill in real content.

## Prerequisites

Requires `opsward` to be installed (`pip install opsward`). If the command is not found, tell the user to install it.

## Workflow

### 1. Preview what would be generated

```bash
opsward generate .
```

This shows a dry-run list of files that would be created. Existing files are never overwritten.

### 2. Present the plan

For each proposed file:
- Explain what it is and why it's useful
- Note if it's a core artifact (CLAUDE.md, docs_guide) vs optional (roadmap, glossary)
- Let the user decide which files to create

### 3. Generate the scaffolds

```bash
opsward generate . --write
```

### 4. Replace templates with real content

This is the critical step. Opsward generates templates with placeholders — you turn them into useful documents by reading the actual project:

- **CLAUDE.md**: Read `pyproject.toml`/`package.json` for real project name and description. Scan source directories to build an accurate module map with real descriptions. Extract actual build/test/lint commands from config files. Check for linter/formatter configs and document real conventions.
- **architecture.md**: Read the source code to understand the real architecture. Document actual data flow, module responsibilities, and key abstractions.
- **conventions.md**: Look at existing code patterns — naming, error handling, import style — and document what you find.
- **docs_guide.md**: Verify it accurately indexes the docs that were created.
- **testing.md**: Read test files to document actual test patterns, fixtures, and how to run tests.

Use Read, Glob, Grep, and Bash freely to understand the project before writing.

### 5. Verify the result

```bash
opsward diagnose .
```

Show the resulting score. If any component scores low, offer to improve it further.

## Permissions

- **Read access**: Used freely to inspect the project (always safe).
- **Write access**: Needed to create new files. Claude Code prompts for approval per the user's permission settings.
- **Bash**: Used to run opsward commands and inspect the project (e.g., `git log`, `tree`).

If the user wants to skip confirmation prompts for file creation, they can configure auto-allow for Write in their Claude Code settings — but this is their choice, not something the skill assumes.
