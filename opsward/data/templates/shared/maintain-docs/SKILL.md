---
name: maintain-docs
description: Check documentation freshness and consistency. Use when the user asks to maintain, update, or check docs for staleness.
---

# Maintain Docs

Check documentation for drift, staleness, and inconsistency.

## Steps

1. Read `${docs_path}/docs_guide.md` and list all referenced docs
2. Verify each referenced doc exists and has content
3. Check `CLAUDE.md` for stale path references (files that no longer exist)
4. Flag docs that reference code patterns no longer present in the codebase
5. Check `known_issues.md` for entries that may be resolved
6. Verify `docs_guide.md` lists all docs actually in the docs directory

## Output Format

List each issue found with category, description, and suggested fix.
