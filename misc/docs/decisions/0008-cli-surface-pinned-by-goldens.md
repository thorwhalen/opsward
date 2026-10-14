# 0008 — The CLI surface is pinned by per-CPython golden recordings

## Status

Accepted (2026-08-30)

## Context

Migrating the CLI from `argh` to `cw` ([0007](0007-dependency-light-core-optional-extras.md)) promised that nothing a user sees would change. The shipped skills and CI gates parse opsward's output ([0004](0004-shipped-skills-wrap-the-deterministic-cli.md)), so an unnoticed change to a flag, an exit code or a help text is a breaking change. `argparse`, being standard library, also rewrites its own messages between CPython versions.

## Decision

- `misc/cli_cases.txt` is a corpus of argv cases; `misc/cli_golden_py<major><minor>.json` records, per case, exit code, stdout, stderr, the `usage:` line and the full `--help` body. `tests/test_cli_parity.py` replays the golden for the running CPython in the ordinary test run.
- One golden per CPython version in the CI matrix; a version without a golden fails loudly instead of skipping.
- No case may print an absolute path (so `--format json` and `install-skills` happy paths are excluded), because goldens must replay on any machine.
- `prog=` is not passed to `cw.dispatch`, so `python -m opsward` and the `opsward` console script each keep their own program name.
- Adding a command or flag means re-recording every golden on its own interpreter and putting the diff in the PR; never re-record just to turn a red test green.

## Consequences

- Neither a refactor nor a new `cw` release can silently change the CLI.
- Any user-visible output change, including a new `maintain` check firing on a fixture, costs a re-recording step and a reviewed diff.
- The parity test needs the console script installed; where it is not, CI is the gate.

## Evidence

- Golden recorded before any source edit, replayed after each migration wave, per-version goldens and the no-absolute-path rule: [PR #25](https://github.com/thorwhalen/opsward/pull/25)
- Windows-specific content exceptions removed once display paths were normalised: [PR #27](https://github.com/thorwhalen/opsward/pull/27)
- Procedure: `CLAUDE.md`, "The CLI surface is pinned"
