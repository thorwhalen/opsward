# 0012 — Portability is scored on drift only, at 0.05, and only where an AGENTS.md exists

## Status

Accepted (2026-10-30), by the operator on [thorwhalen/opsward#75](https://github.com/thorwhalen/opsward/issues/75); proposed 2026-10-20. Decides [thorwhalen/opsward#67](https://github.com/thorwhalen/opsward/issues/67), the scored follow-up of [thorwhalen/opsward#15](https://github.com/thorwhalen/opsward/issues/15).

## Context

Slice 1 of #15 (`opsward.portability`) reports which agent hosts find a repo's instructions and where a render (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, …) drifts from the canonical `AGENTS.md`, as diagnose suggestions only. #69 added the `opsward portability` command and the fleet rollup. #67 asked for a scored component. Two things make that delicate. Any new weight in `_OVERALL_WEIGHTS` moves every grade (`.claude/rules/scoring-invariants.md`: weights sum to 1.0). And host coverage is a choice, not a defect: a repo used only with Claude Code is not worse for lacking a `GEMINI.md`.

A first cut that took the 0.05 from CLAUDE.md quality and gave every repo without an AGENTS.md a full Portability score raised the mean fleet score by 4.1 points (322 repos under t/, i/, tt/ on one machine; up to +5, 3 grades F→D). That is grade inflation: a repo with no instruction file at all gained five points.

## Decision

1. **A sixth component, `Portability`, weight 0.05**, taken from `CLAUDE.md quality` (0.35 → 0.30): drift is a defect of the instruction files, so the split comes out of the component that judges them.
2. **Only drift is scored, never coverage.** Score = 100 − 10 per drift finding (stale, diverged or host-only section), floor 0 (`_PORTABILITY_DRIFT_PENALTY`). An `@AGENTS.md` import shim with Claude-only deltas, a symlink, or an identical copy scores 100.
3. **No AGENTS.md: not applicable, weight returned.** The component shows 100 with a note, and `diagnose` adds its weight back to `CLAUDE.md quality` (`_PORTABILITY_FALLBACK`). A repo without an AGENTS.md scores exactly as it did before this ADR: neither penalised for being Claude-only nor rewarded for being empty.
4. **A shim is judged as read** (from #69): `CLAUDE.md quality` scores a `CLAUDE.md` with its `@AGENTS.md` import inlined, so the shape this component rewards is not punished by the other one.

Rejected: scoring the number of hosts covered (penalises single-host repos, the issue's own recommendation); a flat 100 when no AGENTS.md exists (the inflation measured above); renormalising the other weights when Portability does not apply (moves every grade by a different fraction for no new information).

## Consequences

- Measured on the same 322 repos: 8 scores change, no grade moves. The seven repos with an AGENTS.md and no drift gain at most 5 points (e.g. 7.5 → 12.5). The one repo whose renders drift (8 findings, Portability 20) loses 0.3.
- Every new drift finding in a repo with an AGENTS.md costs 0.5 overall points, so a copied CLAUDE.md now shows up in the grade, not only in the suggestions.
- The weight sum and the fallback are asserted by tests (`tests/test_score.py`, `tests/test_portability.py`). Changing the penalty or the weight is a new ADR.

## Evidence

- [thorwhalen/opsward#67](https://github.com/thorwhalen/opsward/issues/67) (the need and the recommendation), [thorwhalen/opsward#15](https://github.com/thorwhalen/opsward/issues/15), [thorwhalen/opsward#72](https://github.com/thorwhalen/opsward/pull/72) (the shim scored as read), and the PR that lands this record, linked from the index.
