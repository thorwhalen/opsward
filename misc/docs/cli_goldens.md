# CLI goldens

The CLI surface (every command, flag, `--help` body and error message) is pinned so a refactor cannot change it by accident. This page is the procedure for changing it on purpose.

`misc/cli_golden_py<major><minor>.json` records every argv in `misc/cli_cases.txt` — exit code, stdout, stderr, `usage:` line and the full `--help` body — and `tests/test_cli_parity.py` replays the one matching the running CPython. Adding a command or a flag will fail that test. Re-record **every** golden, each on its own interpreter:

```bash
CLAUDE_CONFIG_DIR=$PWD/tests/fixtures/no-such-config-dir \
python3.12 -m cw.testing characterize opsward --cases misc/cli_cases.txt \
    -o misc/cli_golden_py312.json
```

The `CLAUDE_CONFIG_DIR` pin matters: `diagnose` reads the user's global skill scope (`$CLAUDE_CONFIG_DIR/skills`, default `~/.claude/skills`) for shadowing and listing-budget findings, and `tests/test_cli_parity.py` replays with the same pin so the recording and every replay see an empty scope.

Put the resulting diff in the PR. Never re-record to make a red test green without first reading what changed.

Two rules for the corpus:

- **No case may print an absolute path.** The goldens are committed and have to replay on someone else's machine, so `--format json` and `install-skills` happy paths are deliberately excluded (both name the *resolved* project root).
- **One golden per CPython version in the CI matrix.** `argparse` is stdlib and rewrites its own text between versions — 3.12 stopped listing `nargs='*'` positionals among "the following arguments are required", and changed how `invalid choice` quotes the choices. Those are the only two cases that differ between the 3.10 and 3.12 recordings. Adding a version to `[tool.wads.ci.testing]` means recording a golden for it; the test fails loudly rather than skipping if one is missing.

The dispatch itself follows the SSOT pattern: `opsward/cli.py` owns the `_dispatch_funcs` mapping (name → command; `decision` is the one nested group) and `opsward/__main__.py` only runs `cw.dispatch(_dispatch_funcs)`. Do not pass `prog=`: leaving it to `argparse` is what keeps `python -m opsward` reporting `__main__.py` and the console script reporting `opsward`, which the goldens record.
