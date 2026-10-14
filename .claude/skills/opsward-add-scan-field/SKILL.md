---
name: opsward-add-scan-field
description: Add a new fact that opsward learns about a target project — a field on ScanResult populated by scan.py — and consume it downstream in score/generate/maintain/recommend. Use when a new check, score, template variable, or drift detector needs data the scan does not yet collect (a new config file, a new .claude/ inventory, a project signal), or when changing project-type detection. Covers the read-only contract, the dataclass-default rule, the util read helpers, and the CLI goldens a scan change can move.
---

# Adding a scan field to opsward

`scan.py` is the first stage of the pipeline and the only one that touches the target project's filesystem. Everything downstream (`score.py`, `generate.py`, `maintain.py`, `recommend.py`) consumes the `ScanResult` it returns. So when a downstream feature needs a new fact, the fact is added here first and then read from `ScanResult` — never re-read from disk by the consumer if it can be avoided.

## The hard invariant: scan never writes

`scan.py` must not create, write, delete, or rename anything under the scanned root. This is an architectural invariant (see `.claude/rules/scan-is-read-only.md` and `misc/docs/decisions/0001-read-only-scan-side-effects-at-the-cli-edge.md`), not a style preference. Allowed: `pathlib.Path` queries (`is_file`, `is_dir`, `exists`, `iterdir`, `read_bytes`) and the helpers in `opsward/util.py` (`read_text_safe`, `read_json_safe`, `iter_files`, `iter_subdirs`). If you believe the scan needs to write something, the design is wrong — surface it instead.

## The three steps

### 1. Declare the field on `ScanResult` (`opsward/base.py`)

`ScanResult` (`class ScanResult` in `base.py`) is a plain `@dataclass` grouped by topic (CLAUDE.md, `.claude/` inventories, hooks, docs, AGENTS.md, monorepo). Add the field in the group it belongs to, **with a default**:

- scalars: `foo_path: Optional[Path] = None`, `foo_content: str = ""`, `has_foo: bool = False`
- collections: `foos: list[FooInfo] = field(default_factory=list)` — never a bare mutable default

The default is load-bearing: doctests and tests across the suite build `ScanResult(project_root=Path(...))` with nothing else, and the doctests on `def diagnose`, `def maintain` and `def recommend_skills` must keep passing on an empty result. A required field breaks all of them.

If the fact is a new kind of inventory item (like `SkillInfo`, `AgentInfo`, `RuleInfo`, `DocSpec`), add a `@dataclass(frozen=True)` for it in the "Inventory items" section of `base.py` and, if library users should get it, export it from `opsward/__init__.py` (the facade).

### 2. Populate it in `def scan` (`opsward/scan.py`)

`def scan` resolves the root, builds an empty `ScanResult`, and fills it one topic at a time by calling a module-private helper. Follow that shape:

- Write a `_find_<thing>(root) -> tuple[Path | None, ...]` (single artifact, see `def _find_claude_md`, `def _find_hooks`) or a generator `_scan_<things>(dir)` that yields inventory items (see `def _scan_skills`, `def _scan_rules`).
- Assign it in `def scan` next to the related fields, e.g. `result.foo_path, result.foo_content = _find_foo(project_root)`.
- Use `read_text_safe` / `read_json_safe` so a missing or undecodable file degrades to `""` / `None` instead of raising. A scan must succeed on any directory, including an empty one.
- If you record a byte size, use `def _content_size` (LF-normalized) rather than `stat().st_size`, so the number does not differ on a CRLF checkout (see PR #27/#28).
- If the field changes project-type detection, edit `def _detect_project_type`; if it changes docs discovery, edit `def _scan_docs` (it checks `docs/` then `misc/docs/`, non-recursively).

### 3. Consume it downstream

A scan field with no consumer is dead weight: `is_monorepo` / `monorepo_packages` (populated by `def _detect_monorepo`) are currently read by nothing outside `scan.py`. Wire the new field into the stage that needed it:

| Consumer | Where | Sibling skill |
|---|---|---|
| a score or validation | a `_score_*` / `_dim_*` helper in `score.py` | **opsward-add-scoring** |
| a template variable | a `_detect_<thing>(sr)` + a key in `def _build_variables` (`generate.py`) | **opsward-add-template** |
| a drift/staleness check | a `_check_<thing>(sr)` in `maintain.py` | **opsward-add-drift-check** |
| a recommendation signal | `def _build_signal_corpus` (`recommend.py`) | **opsward-add-recommendation** |
| the `diagnose -v` inventory | `def _print_verbose` (`cli.py`) | — |

## Tests

- Add a test in `tests/test_scan.py`. Its fixtures are real sample projects under `tests/fixtures/` (`python_project`, `jsts_project`, `bare_project`, `stale_project`); add the artifact to one of them, or build a project in a `tempfile.mkdtemp()` for one-off cases. Assert both the populated value and the default on `bare_project`.
- If you touched a fixture, other tests that scan it may change (`tests/test_score.py`, `tests/test_maintain.py`, `tests/test_generate.py`). Read the failures before adjusting expectations.
- Never assert that scanning produced a file.

## CLI goldens

`tests/test_cli_parity.py` replays `misc/cli_golden_py<major><minor>.json`, which records the output of `diagnose`, `diagnose -v`, `maintain` and `recommend` on the fixture projects (`misc/cli_cases.txt`). A new scan field alone changes nothing printed, but changing a fixture, the `-v` inventory, or a consumer that prints will move a golden. Re-record each golden on its own interpreter as `CLAUDE.md` ("The CLI surface is pinned") describes, read the diff, and put it in the PR.

## Verify

```bash
python -m pytest -q
python -m pytest --doctest-modules opsward/
python -m opsward diagnose -v .     # inventory reflects the new field if you printed it
```
