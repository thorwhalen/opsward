# Decisions

Architectural decision records (MADR-style) for opsward: the load-bearing, expensive-to-reverse choices behind the code, each with the PR or commit it rests on. Read the relevant one before revisiting a choice it covers.

| ADR | Decision | Rests on |
|---|---|---|
| [0001](0001-read-only-scan-side-effects-at-the-cli-edge.md) | `scan.py` is read-only; library stages are side-effect-free; writes happen only in the CLI, behind `--write`, never over an existing file | commit 434917c, PR #5 |
| [0002](0002-hardcoded-scoring-rubric.md) | The scoring rubric is hardcoded constants in `score.py`, with fixed sums; no rubric file, no custom-rubric override | PRs #1, #5, #7, #29 |
| [0003](0003-string-template-not-jinja2.md) | Templates use `string.Template`; no logic in templates; variants are separate files; conditional content is computed in Python | commit 434917c, PRs #5, #11 |
| [0004](0004-shipped-skills-wrap-the-deterministic-cli.md) | Shipped skills run the deterministic CLI and let the agent interpret; opsward makes no model calls | commit 138f95e, PR #1 |
| [0005](0005-actionable-scores.md) | Scores reward validity, not presence; every deduction says how to fix it; every maximum is reachable | PRs #7, #9, #31 |
| [0006](0006-evidence-gated-generation.md) | Generated content asserts only what the scan can back up; absent evidence means omit, not guess | PRs #5, #11 |
| [0007](0007-dependency-light-core-optional-extras.md) | One runtime dependency (`cw`); heavier capabilities are lazily-imported optional extras | PR #25, commit 9d22c4f |
| [0008](0008-cli-surface-pinned-by-goldens.md) | The CLI surface is pinned by per-CPython golden recordings replayed in the test suite | PR #25 |
| [0009](0009-skills-declare-their-subagent-twin.md) | A skill opts into a subagent twin with `metadata: subagent: true`; `generate` renders `.claude/agents/<name>.md` preloading it, `maintain` checks the sync; `context: fork` is the alternative for delegate-only skills | issue #26 |
| [0010](0010-two-tier-decision-capture.md) | Two-tier decision capture: a Y-statement line in `log.md` or a numbered ADR, chosen by reversal cost; immutable and superseding; Evidence links the issue, discussion and PR; `opsward decision new|note` writes, `maintain` reports rot under `stale_adr` | issue #16 |
| [0011](0011-cheap-first-dispatch-no-router-agent.md) | No router agent: dispatch is route → listing → confident lexical retrieval → LLM adjudication over top-k; the router must see the user's words; abstention floor and gap defined but uncalibrated until the skills corpus is de-duplicated | issue #14 |

PR and issue numbers refer to [thorwhalen/opsward](https://github.com/thorwhalen/opsward); each ADR links them in full.

## Conventions

- One file per decision, `NNNN-short-title.md`, numbered in order; start from [`0000-template.md`](0000-template.md) (the same template `opsward generate` scaffolds into target projects).
- Sections: Status, Context, Decision, Consequences, plus Evidence linking the PR, commit or issue the decision rests on. Record only decisions with evidence in the history; do not reconstruct ones nobody made.
- Accepted ADRs are immutable. To change a decision, write a new ADR and mark the old one `Superseded by [NNNN](NNNN-title.md)`.
- Add a row to the table above for every new ADR. Small decisions go in [`log.md`](log.md) as one Y-statement line (`opsward decision note`); a numbered file is allocated with `opsward decision new "title" --write` (ADR 0010 says which tier).
- The decision-capture workflow these follow (two tiers: one-line Y-statements for small choices, numbered ADRs for load-bearing ones) is tracked in [thorwhalen/opsward#16](https://github.com/thorwhalen/opsward/issues/16) and researched in [`../research/adr_and_home_finding.md`](../research/adr_and_home_finding.md). This backfill is that issue's "dogfood" item and part of [thorwhalen/opsward#18](https://github.com/thorwhalen/opsward/issues/18).
