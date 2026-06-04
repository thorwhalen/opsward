# Testing — opsward

## Test Framework

`pytest`, plus **doctests** on public functions where they double as usage examples.

## Running Tests

```bash
pytest                              # unit + integration tests in tests/
pytest --doctest-modules opsward/   # run the doctests embedded in the package
```

Both are run in CI. Keep doctests cheap and deterministic (no network, no real
filesystem writes outside tmp).

## Test Structure

- Tests live in `tests/`, one file per module: `test_{module}.py`
  (`test_scan.py`, `test_score.py`, `test_generate.py`, …).
- There is **no** `conftest.py`; fixtures are defined inline at the top of each
  test file with `@pytest.fixture` (e.g. `python_scan`, `jsts_scan`, `bare_scan`).
- Sample target projects used as fixtures live under `tests/fixtures/`
  (`python_project/`, `jsts_project/`, `bare_project/`, `stale_project/`). These
  are read-only inputs to `scan()` — never mutate them in a test.

## Conventions

- One behavior per test; descriptive names: `test_{what}_{condition}_{expected}`.
- `scan.py` is read-only by invariant — tests must never assert it writes.
- For anything that writes files (`generate`), build the target in a
  `tempfile.TemporaryDirectory()` and assert on the returned `GeneratedFile`
  list and/or on-disk results; never write into the repo.
- When changing the scoring rubric, assert the invariants hold:
  `_OVERALL_WEIGHTS` sums to 1.0 and each CLAUDE.md dimension's `_*_MAX` sums to 100.
- New skills/agents must pass `validate_skill_spec` (agentskills.io spec, ≤500 lines).

## Coverage

```bash
pytest --cov
```
