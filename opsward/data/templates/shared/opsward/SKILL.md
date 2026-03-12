---
name: opsward
description: Run opsward to assess and improve this project's AI agent setup. Use when the user says 'opsward', 'check my setup', 'improve my AI config', or wants a full audit and remediation.
---

# Opsward — AI Setup Manager

Assess this project's AI agent setup and guide improvements. Combines opsward's deterministic CLI tools with your ability to read code, reason about quality, and make intelligent edits.

## Prerequisites

Requires `opsward` to be installed (`pip install opsward`). If the command is not found, tell the user to install it.

## Workflow

### 1. Diagnose

Run the deterministic diagnostic:

```bash
opsward diagnose . --format json
```

```bash
opsward diagnose .
```

### 2. Interpret and decide

Based on the grade, decide the next step:
- **Grade F or D** (score < 70): The project is missing core artifacts. Focus on generation — scaffold CLAUDE.md, docs, skills.
- **Grade C or B** (score 70-89): The structure exists but has drift or gaps. Focus on maintenance — fix stale references, flesh out empty docs.
- **Grade A** (score 90+): Setup is healthy. Offer targeted fine-tuning — improve the lowest-scoring dimensions.

### 3. Go beyond the scores

Opsward's scores are heuristic (regex-based). You can assess semantic quality that opsward can't:
- Is the CLAUDE.md actually accurate for this project?
- Do the docs contain real content or just template stubs?
- Are the commands correct and up-to-date?

Read source files, configs, and existing docs to form your own assessment. Use Read, Grep, Glob, and Bash freely — these are read-only and safe.

### 4. Execute the appropriate workflow

- **Generation**: Run `opsward generate .` to preview, then `opsward generate . --write` to create scaffolds. Then read the project's actual code and customize each generated file with real content.
- **Maintenance**: Run `opsward maintain . --format json` to get structural issues. Also check for semantic drift (docs that no longer match the code). Fix issues using Edit/Write.
- **Fine-tuning**: Read the lowest-scoring component, identify specific improvements, and apply them.

Always ask the user before writing or editing files.

### 5. Re-diagnose

After making changes, run `opsward diagnose .` again. Show before/after scores and summarize what was done.

## Permissions

This skill uses Claude Code's standard permission model:
- **Read-only operations** (Read, Glob, Grep, Bash for inspection): always safe, used freely
- **Write operations** (Write, Edit): Claude Code prompts the user per their permission settings
- **Destructive operations** (deleting files, removing content): always ask for explicit confirmation

The skill never assumes elevated permissions. If the user wants faster workflows, they can configure auto-allow in their Claude Code settings — but this is their choice.
