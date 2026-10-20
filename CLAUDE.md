# Opsward

Diagnose, generate, and maintain the AI agent setup of your projects — CLAUDE.md, skills, subagents, rules, and supporting docs.

## Project Overview

Opsward is a Python CLI tool (and library) that treats a project's AI agent configuration as a first-class artifact. It scans project roots, reports what's missing or stale, scaffolds missing pieces from templates, and keeps everything current as the codebase evolves. It works on Python projects, JS/TS projects, and mixed repos.

There is also an `ow` PyPI package that is a thin re-export shim for `opsward`.

## Tech Stack

- **Language:** Python 3.10+
- **CLI:** `cw` for dispatching functions to CLI commands (MIT; reproduces argh's grammar)
- **Templates:** String-based (`string.Template` or simple f-string/jinja2-minimal) — keep deps light
- **Data structures:** `dataclasses` for models, `Mapping`/`MutableMapping` where storage is involved
- **File access:** `importlib.resources.files` for bundled templates in `opsward/data/`
- **Testing:** `pytest`, doctests where practical
- **No heavy deps:** This is a lightweight diagnostic/scaffolding tool. Avoid pulling in large frameworks.

## Documentation

For detailed project knowledge, see `misc/docs/docs_guide.md`.
Read it to discover which docs to consult for your current task.

Key docs to read before starting work:
- `misc/docs/ai_setup_meta_tooling.md` — the foundational research report (what exists, what we're building, why)
- `misc/docs/architecture.md` — system design, module responsibilities, data flow
- `misc/docs/conventions.md` — coding style and patterns for this project
- `misc/docs/target_artifacts.md` — complete spec of what opsward generates for target projects

## Module Map

- `opsward/` — the main package
  - `__init__.py` — public interface (the facade). Exports `diagnose`, `generate`, `generate_skills`, `maintain`, `recommend_skills`, `validate_skill_spec`, `SkillRecommendation`, key types
  - `base.py` — core data structures: `ProjectType`, `ScanResult`, `DiagnosisReport`, `ComponentScore`, `DocSpec`, `SkillInfo`, `AgentInfo`, `RuleInfo`, `GeneratedFile`, `MaintenanceSuggestion`
  - `scan.py` — read-only filesystem scanning: detect project type, find CLAUDE.md, skills, agents, rules, hooks, docs; also the user's global skill scope (`scan(root, claude_config_dir=...)`, `None` disables)
  - `score.py` — quality scoring: CLAUDE.md rubric, skill validation, skill reachability findings (shadowed by a global skill, unmigrated bridge, listing budget), doc freshness, cross-reference checks. Rubric weights/dimensions are hardcoded module constants (no external rubric files)
  - `generate.py` — template rendering and file generation (never overwrites without confirmation). Also provides `generate_skills()` for targeted skill/agent installation.
  - `maintain.py` — staleness detection, update suggestions, drift analysis
  - `recommend.py` — map detected tech-stack signals (deps, frameworks) to curated ecosystem skill recommendations
  - `decisions.py` — decision capture: the next numbered ADR from the template, the Y-statement log, and the `stale_adr` drift check (ADR 0010)
  - `subagents.py` — a skill's declared subagent twin (`metadata: subagent: true`): spec, rendered `.claude/agents/<name>.md` preloading the skill, sync states; used by generate, maintain and the diagnosis note (ADR 0009)
  - `fleet.py` — fleet mode: map `scan → diagnose` over N roots and aggregate into a `FleetReport` (opsward#17, gap 1)
  - `lint.py` — strict schema lint (opsward#17, gap 2): every validator (`opsward`'s own spec check, the optional `skill` package's `validate()`) over the project's skills, plus the hooks config; pass/fail, no score. Shipped with `action.yml` (reusable Action) and `.pre-commit-hooks.yaml` at the repo root
  - `evals.py` — opt-in, report-only evals (opsward#17, gap 3): LLM-as-judge (`judge_claude_md`) and with/without-config golden tasks (`run_golden_tasks`); free defaults `rubric_judge`/`echo_agent`, paid `anthropic_judge`/`anthropic_agent` never used by tests
  - `cli.py` — CLI command functions (the `_dispatch_funcs` SSOT)
  - `util.py` — internal helpers (underscore-prefixed)
  - `data/` — bundled package resources (accessed via `importlib.resources.files`)
    - `templates/` — generation templates organized by target project type
      - `shared/` — templates that work for any project type. **This is also where the installable Claude Code skills live**, as `opsward/data/templates/shared/<skill-name>/SKILL.md` (opsward, opsward-diagnose, opsward-generate, opsward-maintain, opsward-subagents) plus the `opsward/data/templates/shared/setup-auditor.md` agent. `generate.py` installs these into a target project's `.claude/`.
      - `python/` — Python-specific templates (paths use `misc/docs/`)
      - `jsts/` — JS/TS-specific templates (paths use `docs/`)
- `tests/` — pytest tests

## Commands

```bash
# Install
pip install opsward   # or: pip install ow

# CLI usage
python -m opsward diagnose /path/to/project          # Diagnose AI setup
python -m opsward diagnose /path/to/proj1 /path/to/proj2  # Multi-project
python -m opsward generate /path/to/project           # Generate missing pieces
python -m opsward maintain /path/to/project            # Check for staleness/drift
python -m opsward recommend /path/to/project           # Recommend ecosystem skills from tech stack
python -m opsward fleet --under /path/to/projects      # Diagnose every repo under a folder, rolled up
python -m opsward lint /path/to/project               # Strict spec/config lint (exit 1 on any finding)
python -m opsward install-skills --write               # Install Claude Code skills
python -m opsward decision new "title" --write          # Allocate the next numbered ADR
python -m opsward decision note "In the context of …" --write   # One-line decision in misc/docs/decisions/log.md

# After pip install (via pyproject.toml [project.scripts]):
opsward diagnose .
opsward generate . --write
opsward maintain .
opsward install-skills --write                    # Install into .claude/
opsward install-skills --global-install --write   # Install into ~/.claude/
```

## Conventions

### Python Style

- Functional over OOP. Use dataclasses for data, plain functions for logic.
- Keyword-only arguments from the 3rd position onward.
- Small helper functions: inner if single-caller, underscore-prefixed if module-private.
- Minimal docstrings on everything. Simple doctests when practical.
- `yield` over `return list`. Generators for sequences.
- `Mapping`/`MutableMapping` for storage abstractions.
- Use `importlib.resources.files("opsward.data")` to access bundled templates — never hardcode filesystem paths to package data.

### CLI Pattern

Follow the SSOT dispatch pattern: `cli.py` owns the command list, `__main__.py`
only runs it.

```python
# In cli.py — a name → command mapping; `decision` is the one nested group
_dispatch_funcs = {
    "diagnose": diagnose,
    "generate": generate,
    "maintain": maintain,
    "recommend": recommend,
    "install-skills": install_skills,
    "find": find,
    "fleet": fleet,
    "lint": lint,
    "decision": [new, note],
}
```

```python
# In __main__.py
import cw
from opsward.cli import _dispatch_funcs


def main():
    raise SystemExit(cw.dispatch(_dispatch_funcs))
```

Do not pass `prog=` — leaving it to `argparse` is what keeps `python -m opsward`
reporting `__main__.py` and the console script reporting `opsward`.

**The CLI surface is pinned.** `misc/cli_golden_py<major><minor>.json` records every
argv in `misc/cli_cases.txt` — exit code, stdout, stderr, `usage:` line and the full
`--help` body — and `tests/test_cli_parity.py` replays the one matching the running
CPython. Adding a command or a flag will fail that test. Re-record **every** golden,
each on its own interpreter:

```bash
CLAUDE_CONFIG_DIR=$PWD/tests/fixtures/no-such-config-dir \
python3.12 -m cw.testing characterize opsward --cases misc/cli_cases.txt \
    -o misc/cli_golden_py312.json
```

The `CLAUDE_CONFIG_DIR` pin matters: `diagnose` reads the user's global skill scope
(`$CLAUDE_CONFIG_DIR/skills`, default `~/.claude/skills`) for shadowing and
listing-budget findings, and `tests/test_cli_parity.py` replays with the same pin so
the recording and every replay see an empty scope.

and put the resulting diff in the PR. Never re-record to make a red test green without
first reading what changed.

Two rules for the corpus:

- **No case may print an absolute path.** The goldens are committed and have to replay
  on someone else's machine, so `--format json` and `install-skills` happy paths are
  deliberately excluded (both name the *resolved* project root).
- **One golden per CPython version in the CI matrix.** `argparse` is stdlib and rewrites
  its own text between versions — 3.12 stopped listing `nargs='*'` positionals among
  "the following arguments are required", and changed how `invalid choice` quotes the
  choices. Those are the only two cases that differ between the 3.10 and 3.12
  recordings. Adding a version to `[tool.wads.ci.testing]` means recording a golden for
  it; the test fails loudly rather than skipping if one is missing.

### Template Pattern

Templates live in `opsward/data/templates/`. They are plain markdown files with `${variable}` placeholders (using `string.Template`). The generator reads them via `importlib.resources`, substitutes variables from the scan results, and writes to the target project.

### Scoring Pattern

Scoring functions are pure: `(scan_result) -> DiagnosisReport`. No side effects. The rubric — overall weights (`_OVERALL_WEIGHTS`) and per-dimension max scores (`_CMD_MAX`, `_ARCH_MAX`, …) — is defined as hardcoded module-level constants in `score.py`, not in external data files. Scoring dimensions for CLAUDE.md (inspired by community best practices):

1. **Commands/Workflows** (0-20): Are build/test/run commands documented?
2. **Architecture Clarity** (0-20): Is the module map present and accurate?
3. **Conventions** (0-15): Are non-obvious patterns documented?
4. **Conciseness** (0-15): Is it dense and scannable, not bloated?
5. **Currency** (0-15): Do referenced paths/files actually exist?
6. **Actionability** (0-15): Can an agent act on the instructions without guessing?

### Project Type Detection

```python
# Detection signals — check in this order:
PYTHON_SIGNALS = ("pyproject.toml", "setup.py", "setup.cfg", "Pipfile")
JSTS_SIGNALS = ("package.json", "tsconfig.json", "deno.json")

# Docs location by type:
# Python  -> misc/docs/
# JS/TS   -> docs/
# Mixed   -> docs/  (JS/TS convention wins)
```

### What Opsward Generates for Target Projects

When generating for a target project, opsward can produce:

**Documentation layer** (the `docs/` or `misc/docs/` folder):
- `docs_guide.md` — always first. Entry point listing all other docs.
- `architecture.md`, `known_issues.md`, `conventions.md`, `roadmap.md`, `glossary.md`, `testing.md`, `dependencies.md`, `deployment.md`
- `decisions/` folder for MADR-style architectural decision records

**AI configuration layer** (the `.claude/` folder):
- `CLAUDE.md` at project root (or updates to existing one)
- `.claude/skills/opsward/SKILL.md` — meta-orchestrator: diagnose → generate/maintain → re-diagnose
- `.claude/skills/opsward-diagnose/SKILL.md` — run `opsward diagnose`, interpret scores, offer fixes
- `.claude/skills/opsward-generate/SKILL.md` — run `opsward generate`, customize with real content
- `.claude/skills/opsward-maintain/SKILL.md` — run `opsward maintain`, prioritize and fix issues
- `.claude/skills/opsward-subagents/SKILL.md` — decide which skills should also run as subagents, declare it in the skill, generate the twins (ADR 0009)
- `.claude/agents/setup-auditor.md` — read-only auditor subagent (uses opsward CLI)
- `.claude/rules/` files if appropriate

These skills are AI-enhanced: they invoke opsward's deterministic CLI tools via Bash, then Claude Code interprets the structured output and acts on suggestions. No API keys needed.

See `misc/docs/target_artifacts.md` for the full spec of generated artifacts.

### Output Principles

- **Never overwrite** existing files without explicit confirmation.
- **Dry-run by default** for generate/maintain. Use `--write` or `--apply` to actually write.
- **Diff-first**: Show what would change before changing it.
- **Minimal generation**: Only suggest docs/skills that are genuinely useful for the detected project type. Don't generate a `deployment.md` template for a library with no deployment.

## Non-Obvious Patterns

- Templates are **not** Jinja2. Use `string.Template` for simplicity and zero deps. If a template needs conditionals, split it into separate template files per variant.
- The `diagnose` function returns a `DiagnosisReport` dataclass that is both human-readable (via `__str__`) and machine-consumable (via dataclass fields). The CLI pretty-prints it; library users get structured data.
- The `scan.py` module must be **purely read-only** — it never modifies the target project. This is a hard invariant. It uses `pathlib.Path` and `os.walk`, never writes.
- For multi-project scanning, each project gets its own `DiagnosisReport`. The CLI's `diagnose` accepts multiple roots (`*project_roots`) and reports each independently. The aggregate is `opsward fleet` (CLI) over `opsward.fleet.fleet(roots)`, which returns a `FleetReport` (grade counts, missing-item and component rollups, worst repos, a name-keyed `to_dict()`); `git_roots_under(parent)` lists the repos under a folder. `--manifest PATH` writes the per-machine manifest (absolute roots + the summary): it must stay out of version control.
- The `ow` shim package is a separate `pyproject.toml` / directory. It literally just does `from opsward import *` and declares `opsward` as a dependency.

## Git Workflow

- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- No AI attribution in commit messages.

## Build & Test

```bash
pip install -e ".[dev]" --break-system-packages
pytest
pytest --doctest-modules opsward/
```
