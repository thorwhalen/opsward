@AGENTS.md

## Claude Code

Claude-only deltas; everything portable lives in AGENTS.md, so edit it there.

- Read the path-scoped rules before editing what they guard: `.claude/rules/scan-is-read-only.md` (`opsward/scan.py`), `.claude/rules/scoring-invariants.md` (`opsward/score.py`), `.claude/rules/templates-generation-and-paths.md` (templates and path citations).
- Use the dev skills in `.claude/skills/` for recurring changes: `opsward-add-scoring`, `opsward-add-scan-field`, `opsward-add-drift-check`, `opsward-add-template`, `opsward-add-recommendation`; `opsward-dev` is the map.
- Hooks live in `.claude/hooks.json`.
