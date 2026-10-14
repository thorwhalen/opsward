# 0002 — The scoring rubric is hardcoded module constants, not an external file

## Status

Accepted (2026-03-11; invariants codified 2026-06-05; contradicting "custom rubric" extension point removed 2026-09-22)

## Context

Early docs described scoring rubrics loaded from YAML files under `data/rubrics/` and a user-overridable "custom rubric" extension point. Neither ever existed in code. A grade is only useful if it means the same thing across projects and over time: it is used as a CI gate (`diagnose --min-score`) and to compare a project against its own earlier runs.

## Decision

The rubric lives in `opsward/score.py` as module-level constants: the overall component weights `_OVERALL_WEIGHTS`, the CLAUDE.md dimension maxes (`_CMD_MAX`, `_ARCH_MAX`, `_CONV_MAX`, `_CONCISE_MAX`, `_CURRENCY_MAX`, `_ACTION_MAX`), and the Setup budget (`_SETUP_RULES_MAX`, `_SETUP_AGENTS_MAX`, `_SETUP_HOOKS_MAX`). There is no rubric file and no override mechanism. Invariants: weights sum to 1.0, each component's maxes sum to 100, scoring functions are pure.

## Consequences

- Scores are reproducible for a given opsward version; changing the rubric is a code change, reviewed and tested like any other.
- The sums are part of the contract: a test locks the Setup budget at 100 (`tests/test_score.py`); the `_OVERALL_WEIGHTS` = 1.0 and CLAUDE.md-maxes = 100 sums are enforced by the rule file but not yet by a test.
- Users who disagree with a weight cannot tune it locally; the escape hatches are keyword-only thresholds on the functions (e.g. `claude_md_max_chars` on `diagnose` and `maintain`) rather than a rubric file.
- Docs that describe a rubric file or a custom-rubric extension point are wrong by definition, which is how the stale `architecture.md` entry was caught.
- The "why" (comparability across projects and runs) is reconstructed from how the grade is used; the commits record the "what".

## Evidence

- Initial pure scorer with the 6-dimension CLAUDE.md rubric: commit [434917c](https://github.com/thorwhalen/opsward/commit/434917c)
- CLAUDE.md corrected: scoring is hardcoded constants in `score.py`, not `data/rubrics/` YAML: [PR #1](https://github.com/thorwhalen/opsward/pull/1)
- `.claude/rules/scoring-invariants.md` added: [PR #5](https://github.com/thorwhalen/opsward/pull/5)
- Setup budget made module constants and locked by a test: [PR #7](https://github.com/thorwhalen/opsward/pull/7)
- "Custom YAML rubric" extension point removed from `architecture.md` as contradicting the rule: [PR #29](https://github.com/thorwhalen/opsward/pull/29)
