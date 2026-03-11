---
name: opsward-generate
description: Generate missing AI setup artifacts for this project. Use when the user asks to scaffold, create, or bootstrap CLAUDE.md, docs, skills, or agent configuration.
---

# Generate AI Setup Artifacts

Use opsward to scaffold missing artifacts, then customize them with real project content.

## Prerequisites

Requires `opsward` to be installed (`pip install opsward`). If the command is not found, tell the user to install it.

## Workflow

1. **Preview what would be generated** via Bash:
   ```
   opsward generate .
   ```
   This shows a dry-run list of files that would be created. Existing files are never overwritten.

2. **Present the plan** to the user. For each proposed file:
   - Explain what it is and why it's useful
   - Note if it's a core artifact (CLAUDE.md, docs_guide) vs optional (roadmap, glossary)
   - Let the user decide which files to create

3. **Generate the files:**
   ```
   opsward generate . --write
   ```

4. **Customize each generated file** with real project content:
   - Read the project's source code, configs, and README to understand the project
   - For CLAUDE.md: fill in accurate module descriptions, real build/test commands, actual conventions
   - For architecture.md: describe the real architecture based on code inspection
   - For docs_guide.md: ensure it accurately indexes the docs that were created
   - For skills: verify the generated skills make sense for this project
   - Replace all placeholder text (`<!-- Add ... -->`) with real content

5. **Verify the result:**
   ```
   opsward diagnose .
   ```
   Show the user the resulting score.

## Guidelines

- Always show the dry-run output before writing files.
- Ask the user before creating files.
- After generation, spend time customizing — templates with placeholders are only a starting point.
- Focus on making CLAUDE.md accurate and actionable first, then docs, then skills.
