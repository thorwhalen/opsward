# 0005 — Scores reward validity, and every deduction says how to fix it

## Status

Accepted (2026-06-06)

## Context

opsward is a diagnose-then-act tool: its report is read by an agent that is expected to fix what it finds. Two failures surfaced while dogfooding. Setup scoring rewarded mere presence (any non-empty `hooks` config earned full credit, including the malformed one opsward's own generator emitted, which Claude Code silently ignores). And points were deducted with no explanation, including points that no input could ever earn (a per-skill integer floor capped perfect skill sets at 80; the best Architecture branch returned 16 of 20).

## Decision

- Score validity, not presence: hooks are checked against Claude Code's real shape (`validate_hooks_config`, public, symmetric with `validate_skill_spec`), stub rules and description-less agents earn no credit.
- Every branch that deducts points appends a component-local note of the form "what is wrong → how to fix". The global `suggestions` list stays reserved for missing artifacts and cross-cutting actions.
- A deduction with no possible fix is a scorer bug: a perfect input must be able to reach the maximum.

## Consequences

- A report is a to-do list; the agent reading it does not have to guess where the missing points went.
- Fixing unreachable maxima raised opsward's own grade (87 B → 93 A) legitimately, without changing the rubric constants ([0002](0002-hardcoded-scoring-rubric.md)).
- New scoring code carries an obligation: a test that the fix note is emitted, and that the maximum is reachable. Later findings follow the same pattern, e.g. the CLAUDE.md size deduction names the three longest sections and where to move each.

## Evidence

- Validity-aware Setup scoring (hooks, rules, agents): [PR #7](https://github.com/thorwhalen/opsward/pull/7)
- Explainable scores and the two unreachable-max fixes: [PR #9](https://github.com/thorwhalen/opsward/pull/9)
- Size finding that names sections and destinations: [PR #31](https://github.com/thorwhalen/opsward/pull/31)
