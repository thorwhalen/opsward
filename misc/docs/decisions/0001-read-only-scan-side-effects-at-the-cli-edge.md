# 0001 — Read-only scan; side effects only at the CLI edge, behind `--write`

## Status

Accepted (2026-03-11, with the initial package; scan invariant codified as a rule 2026-06-05)

## Context

opsward runs against projects it does not own — any repo a user points it at, including several at once. A diagnostic that can mutate the thing it diagnoses is unsafe to run casually, and a generator that can clobber a hand-written CLAUDE.md or doc destroys exactly the content it exists to improve.

## Decision

- `scan.py` is strictly read-only: it only queries the filesystem (`pathlib`, `read_text_safe`, `read_json_safe`, `iter_files`, `iter_subdirs`) and never creates, writes, deletes or renames anything under the scanned root.
- The library stages are side-effect-free transformations of a `ScanResult`: `score.diagnose` returns a `DiagnosisReport`, `generate.generate` / `generate_skills` return `list[GeneratedFile]` (path + content, not a write), `maintain.maintain` returns `list[MaintenanceSuggestion]`.
- The only writes happen in the CLI (`generate` and `install_skills` in `cli.py`), are dry-run by default, require `--write`, and skip any target that already exists.

## Consequences

- Any opsward command except `generate --write` / `install-skills --write` is safe to run on any directory, which is what makes multi-root `diagnose` and CI gating (`--min-score`) practical.
- Every library function is testable without a temp-dir write; tests never assert that scanning produced files.
- `GeneratedFile.overwrite_policy` has `'overwrite'` and `'merge'` values, but the CLI currently skips every existing file regardless; updating an existing artifact is left to the AI skill layer (see [0004](0004-shipped-skills-wrap-the-deterministic-cli.md)).
- `maintain` still runs a read-only `git log` subprocess for doc freshness; read-only, not side-effect-free in the strict sense.
- New facts must be added to the scan, not gathered by downstream writers (see the `opsward-add-scan-field` dev skill).

## Evidence

- Initial package, scan.py docstring "This module NEVER writes to the target project": commit [434917c](https://github.com/thorwhalen/opsward/commit/434917c)
- Codified as `.claude/rules/scan-is-read-only.md` and the generation-safety rule: [PR #5](https://github.com/thorwhalen/opsward/pull/5)
- Write path and existing-file skip: `def generate` / `def install_skills` in `opsward/cli.py`
