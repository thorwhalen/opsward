---
name: opsward-diagnose
description: Diagnose the health of this project's AI agent setup. Use when the user asks to check, audit, or score the project's CLAUDE.md, skills, docs, or agent configuration.
---

# Diagnose AI Setup

Run opsward's deterministic diagnostic, then interpret results and offer fixes.

## Prerequisites

Requires `opsward` to be installed (`pip install opsward`). If the command is not found, tell the user to install it.

## Workflow

1. **Run the diagnostic** via Bash:
   ```
   opsward diagnose . --format json
   ```
   This returns structured scores for: CLAUDE.md quality, documentation, skills, setup (rules/agents/hooks), and cross-references. Each scored 0-100 with an overall weighted grade.

2. **Run the text report** for presentation:
   ```
   opsward diagnose .
   ```

3. **Present the report card** to the user. For each component:
   - State the score and what it measures
   - Explain why it scored the way it did (read the relevant files if needed to give specific feedback)
   - Highlight the most impactful improvement opportunities

4. **For each suggestion or low-scoring area**, offer a concrete fix:
   - Missing CLAUDE.md → offer to generate one (via `opsward generate . --write` or write a tailored one)
   - Low commands/workflows score → read the project's build config and add the real commands to CLAUDE.md
   - Broken cross-references → identify the stale paths and update or remove them
   - Missing docs → offer to create them with real content
   - Missing skill descriptions → read the skill and write a proper description

5. **Apply fixes** with user approval, using Edit/Write tools.

6. **Re-run diagnostic** after fixes to show improvement:
   ```
   opsward diagnose .
   ```

## Scoring Dimensions (for reference)

- **CLAUDE.md quality** (35% weight): commands/workflows, architecture clarity, conventions, conciseness, currency, actionability
- **Documentation** (25%): docs_guide.md, core docs, content, cross-refs
- **Skills** (20%): SKILL.md presence, descriptions
- **Setup** (10%): rules, agents, hooks configuration
- **Cross-references** (10%): paths in CLAUDE.md that actually exist on disk
