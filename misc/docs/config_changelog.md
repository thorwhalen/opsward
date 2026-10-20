# Agent config changelog

One dated line per change to this repo's agent config (CLAUDE.md, AGENTS.md, anything under `.claude/`), newest first: what changed, why, and its triage (align / revert / ignore) when it answers a drift finding. Add the line in the same commit as the change; `opsward maintain` reports a `config_changelog` finding when a config commit is newer than the last commit to this file.

- 2026-10-20: `opsward-maintain` skill gains the triage step and this changelog step; CLAUDE.md module map lists `fleet`, `lint`, `evals`, `security` and the shared path extractor (#49, #50, #51, #53).
