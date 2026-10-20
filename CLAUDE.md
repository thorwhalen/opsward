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
  - `lint.py` — strict schema lint (opsward#17, gap 2): every validator (`opsward`'s own spec check, the optional `skill` package's `validate()`, the external `agnix` and `skillcheck` when on PATH) over the project's skills, plus the hooks config; pass/fail, no score. Shipped with `action.yml` (reusable Action) and `.pre-commit-hooks.yaml` at the repo root
  - `evals.py` — opt-in, report-only evals (opsward#17, gap 3): LLM-as-judge (`judge_claude_md`) and with/without-config golden tasks (`run_golden_tasks`); free defaults `rubric_judge`/`echo_agent`, paid `anthropic_judge`/`anthropic_agent` never used by tests
  - `security.py` — OWASP-style advisories in `DiagnosisReport.advisories`; never scored
  - `cli.py` — CLI command functions (the `_dispatch_funcs` SSOT)
  - `util.py` — shared helpers, incl. `extract_paths` (the one path extractor; honours the `opsward: ignore-path` marker)
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

Full rules: `misc/docs/conventions.md`. The ones agents trip on:

- **Python style**: functional, dataclasses for data, keyword-only from the 3rd argument, `yield` over lists, `Mapping` for storage. Bundled data via `importlib.resources.files("opsward.data")`, never a filesystem path.
- **CLI**: `cli.py` owns the `_dispatch_funcs` mapping (`decision` is the one nested group); `__main__.py` only runs `cw.dispatch(_dispatch_funcs)`. Do not pass `prog=`.
- **The CLI surface is pinned**: `misc/cli_golden_py<major><minor>.json` (one per CPython in the CI matrix, cases in `misc/cli_cases.txt`) is replayed by `tests/test_cli_parity.py`, so adding a command or a flag fails it. Re-record every golden with the procedure in `misc/docs/cli_goldens.md` (the `CLAUDE_CONFIG_DIR` pin and the no-absolute-path rule matter), read the diff, and put it in the PR.
- **Templates**: `opsward/data/templates/*.md`, `string.Template` `${variable}` placeholders, read through `importlib.resources`.
- **Scoring** is pure, `(scan_result) -> DiagnosisReport`; the rubric is module-level constants in `score.py` (`_OVERALL_WEIGHTS`, `_CMD_MAX`, `_ARCH_MAX`, …). Dimensions: `misc/docs/scoring_rubric.md`.
- **Project type**: Python signals (`pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile`) put docs in `misc/docs/`; JS/TS (`package.json`, `tsconfig.json`, `deno.json`) and mixed projects in `docs/`.
- **Generated for target projects** (docs layer, `.claude/` skills and agents): `misc/docs/target_artifacts.md`.
- **Output**: never overwrite without confirmation; dry-run by default (`--write` / `--apply` to write); diff-first; generate only what the project type needs.

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
