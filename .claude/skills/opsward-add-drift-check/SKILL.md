---
name: opsward-add-drift-check
description: Add a new staleness or drift check to opsward's maintain stage (maintain.py), so `opsward maintain` reports a new kind of MaintenanceSuggestion — a stale reference, an out-of-sync index, an outdated or empty doc, an incomplete skill. Use when extending what `opsward maintain` detects, adding a suggestion category, or deciding whether a finding belongs in maintain or in the diagnose score. Covers the check-generator shape, categories, the diff field, the exit-code contract, and the CLI golden it can move.
---

# Adding a drift check to opsward

`maintain` answers "what has rotted?" where `diagnose` answers "how good is this setup?". All of it lives in `opsward/maintain.py`. The entry point `def maintain(scan_result, *, previous_report=None, claude_md_max_chars=...)` runs a fixed list of `_check_*` generators and concatenates what they yield into a `list[MaintenanceSuggestion]`.

## maintain or diagnose?

- **maintain**: a concrete, fixable discrepancy between the setup and reality — a path that no longer exists, a doc missing from the index, a doc untouched for 90 days. Each finding is one actionable line.
- **diagnose** (`score.py`, see **opsward-add-scoring**): a graded quality judgment that moves a number.
- **Both**: when a finding should cost points *and* be listed as a chore, compute it once in `score.py` as a public pure function and call it from both, as `def _check_claude_md_size` does with `claude_md_size_overrun` and `docs_dir_hint` (PR #31). Do not reimplement the same heuristic twice; the two reports would drift apart.

## The check shape

Each check is a module-private generator over a `ScanResult`:

```python
def _check_<thing>(sr: ScanResult) -> Iterable[MaintenanceSuggestion]:
    """One-line docstring saying what drift this detects."""
    if not sr.<field>:
        return  # nothing to check — a bare project yields nothing
    for ...:
        yield MaintenanceSuggestion(
            category="<category>",
            description="`<name>` ... — what is wrong, naming the artifact",
            diff="",  # optional: a suggested edit, e.g. def _suggest_guide_addition
        )
```

Then add one line to `def maintain`: `suggestions.extend(_check_<thing>(scan_result))`. The order of those `extend` calls is the order findings are printed. If the check needs a tunable threshold, make it a module constant (like `_STALE_DAYS`, `_MIN_DOC_BYTES`) or, if callers should set it, a keyword-only argument on `def maintain` with the constant as its default (like `claude_md_max_chars`).

## Rules for a check

- **Read from `ScanResult`.** If the data is not there, add it to the scan first (**opsward-add-scan-field**). Reading a file the scan already located via `read_text_safe` is fine (`def _check_docs_guide_sync` re-reads `sr.docs_guide_path`).
- **Never write.** `maintain` reports; it does not fix. Fixing is the job of the AI skill layer (the shipped `opsward-maintain` skill) acting on the report. A suggested edit goes in `diff`, as text.
- **Degrade silently on missing context.** `def _check_doc_freshness` returns nothing when there is no `.git` directory, and `def _days_since_last_commit` returns `None` on any `git` failure or timeout. A check that shells out must do the same: bounded `timeout=`, catch `OSError` / `subprocess.TimeoutExpired`, never raise.
- **Silent on an empty project.** The doctest on `def maintain` asserts `maintain(ScanResult(project_root=Path('/tmp/empty')))` is `[]`; a new check must keep it so.
- **Describe the artifact, not the rule.** Name the file or skill in backticks so an agent can act on the line alone.

## Categories

`MaintenanceSuggestion.category` (`class MaintenanceSuggestion` in `opsward/base.py`) is a free string. Existing ones: `stale_path`, `claude_md_size`, `sync_issue`, `outdated_doc`, `incomplete_skill`, `empty_doc`. Reuse one when the finding is the same kind of problem; add a new one only for a genuinely new kind, and update the example list in the `category` field comment in `base.py`. Categories are consumed by the CLI (`[category] description`), its JSON output, and the shipped `opsward-maintain` skill template (`opsward/data/templates/shared/opsward-maintain/SKILL.md`), which tells agents how to triage them — mention a new category there if it needs special handling.

## The exit-code contract

`opsward maintain` (`def maintain` in `cli.py`) exits **1 if any suggestion is produced**, 0 otherwise (and 2 for a missing root, like every command). A new check therefore can turn a previously clean project's CI red. Make sure it does not fire on healthy projects (run it on opsward itself) and that it is not noisy on edge cases.

## Tests and goldens

- Add tests in `tests/test_maintain.py`: one fixture or temp project where the drift is present (assert the category and that the description names the artifact), and one where it is absent. `tests/fixtures/stale_project` exists for drift cases.
- `misc/cli_cases.txt` contains `maintain tests/fixtures/stale_project`; if your check fires there, `tests/test_cli_parity.py` will fail. Re-record every `misc/cli_golden_py*.json` as `CLAUDE.md` ("The CLI surface is pinned") describes, read the diff, and put it in the PR.
- `previous_report` is accepted by `def maintain` but no check uses it yet; a check that compares against the last diagnosis is the intended use.

## Document it

List the new check in `misc/docs/architecture.md` (the "Maintain" data-flow section) so the documented check list matches `def maintain`.

## Verify

```bash
python -m pytest -q tests/test_maintain.py
python -m pytest -q
python -m opsward maintain .        # opsward on itself: no new false positives
```
