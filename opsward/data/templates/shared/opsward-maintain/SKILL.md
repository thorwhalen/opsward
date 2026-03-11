---
name: opsward-maintain
description: Check documentation and AI setup for staleness, drift, or inconsistency. Use when the user asks to maintain, refresh, or update project docs and AI configuration.
---

# Maintain AI Setup

Run opsward's maintenance checks, then fix issues found.

## Prerequisites

Requires `opsward` to be installed (`pip install opsward`). If the command is not found, tell the user to install it.

## Workflow

1. **Run maintenance checks** via Bash:
   ```
   opsward maintain . --format json
   ```
   This returns a list of issues categorized as: stale_path, sync_issue, outdated_doc, incomplete_skill, empty_doc.

2. **Also run the text version** for readability:
   ```
   opsward maintain .
   ```

3. **Categorize and prioritize** the issues:
   - **High priority**: stale paths in CLAUDE.md (broken references mislead the AI), sync issues between docs_guide and actual docs
   - **Medium priority**: outdated docs (>90 days since last update), incomplete skills
   - **Low priority**: empty doc stubs

4. **For each issue, propose a concrete fix:**
   - **Stale path**: Read CLAUDE.md, find the reference, determine if the file was renamed/moved/deleted, update or remove the reference
   - **Sync issue**: Add missing docs to docs_guide.md table, or remove references to deleted docs
   - **Outdated doc**: Read the doc and the code it describes, update the doc to reflect current state
   - **Incomplete skill**: Read the skill directory, write a proper SKILL.md with description
   - **Empty doc**: Read the project to understand what should go in the doc, write real content

5. **Apply fixes** with user approval using Edit/Write tools.

6. **Re-run maintenance** to confirm issues are resolved:
   ```
   opsward maintain .
   ```

## Guidelines

- Present all issues first, then ask which to fix.
- For outdated docs, read the actual source code to write accurate updates — don't just bump timestamps.
- After fixing, re-run both `opsward maintain .` and `opsward diagnose .` to show the full picture.
