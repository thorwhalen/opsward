---
name: opsward
description: Run opsward to assess and improve this project's AI agent setup. Use when the user says 'opsward', 'check my setup', 'improve my AI config', or wants a full audit and remediation.
---

# Opsward — AI Setup Manager

Assess this project's AI agent setup and guide improvements using the `opsward` CLI.

## Prerequisites

Requires `opsward` to be installed (`pip install opsward`). If the command is not found, tell the user to install it.

## Workflow

1. **Diagnose** — Run the following via Bash:
   ```
   opsward diagnose . --format json
   ```
   Also run the text version for the human-readable report card:
   ```
   opsward diagnose .
   ```

2. **Interpret the grade** and decide the next step:
   - **Grade F or D** (score < 70): The project is missing core artifacts. Suggest running the generation workflow — scaffold CLAUDE.md, docs, skills.
   - **Grade C or B** (score 70-89): The structure exists but has drift or gaps. Suggest running the maintenance workflow — fix stale references, flesh out empty docs.
   - **Grade A** (score 90+): Setup is healthy. Offer targeted fine-tuning — improve low-scoring dimensions, add missing optional artifacts.

3. **Execute the appropriate workflow:**
   - For generation: run `opsward generate .` to preview, then `opsward generate . --write` to create files. Read each generated file and customize it with project-specific content (fill in TODOs, add real module descriptions, write actual architecture notes).
   - For maintenance: run `opsward maintain . --format json` to get issues, then fix each one using Edit/Write tools.
   - For fine-tuning: read the lowest-scoring component, identify specific improvements, and apply them.

4. **Re-diagnose** — After making changes, run `opsward diagnose .` again to show the improvement.

5. **Present results** — Show the before/after scores and summarize what was done.

## Guidelines

- Always ask the user before writing or editing files.
- Show what you plan to change before changing it.
- When customizing generated files, use your knowledge of the project (read source files, configs, READMEs) to fill in real content rather than leaving placeholders.
- Focus on the highest-impact improvements first.
