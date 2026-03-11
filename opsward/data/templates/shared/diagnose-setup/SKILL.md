---
name: diagnose-setup
description: Diagnose the health of this project's AI agent setup. Use when the user asks to check, audit, or score the project's CLAUDE.md, skills, docs, or agent configuration.
---

# Diagnose Setup

Run a diagnostic check on this project's AI agent configuration.

## Steps

1. Read `CLAUDE.md` and assess its quality (conciseness, actionability, currency)
2. Check `${docs_path}/docs_guide.md` exists and indexes all docs
3. Inventory `.claude/skills/` — verify each has a SKILL.md with description
4. Inventory `.claude/rules/` — verify rules are specific
5. Check `.claude/agents/` for configured subagents
6. Validate cross-references — do paths in CLAUDE.md exist?
7. Summarize with per-component scores and prioritized suggestions

## Output Format

Present results as a report card with letter grade (A-F) and specific, actionable improvement suggestions.
