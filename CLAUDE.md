# Opsward

Diagnose, generate, and maintain the AI agent setup of your projects — CLAUDE.md, skills, subagents, rules, and supporting docs.

## Project Overview

Opsward is a Python CLI tool (and library) that treats a project's AI agent configuration as a first-class artifact. It scans project roots, reports what's missing or stale, scaffolds missing pieces from templates, and keeps everything current as the codebase evolves. It works on Python projects, JS/TS projects, and mixed repos.

There is also an `ow` PyPI package that is a thin re-export shim for `opsward`.

## Tech Stack

- **Language:** Python 3.10+
- **CLI:** `argh` for dispatching functions to CLI commands
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
  - `__init__.py` — public interface (the facade). Exports `diagnose`, `generate`, `generate_skills`, `maintain`, key types
  - `base.py` — core data structures: `ProjectType`, `DiagnosisReport`, `DocSpec`, `SetupComponent`, scoring models
  - `scan.py` — read-only filesystem scanning: detect project type, find CLAUDE.md, skills, agents, rules, hooks, docs
  - `score.py` — quality scoring: CLAUDE.md rubric, skill validation, doc freshness, cross-reference checks
  - `generate.py` — template rendering and file generation (never overwrites without confirmation). Also provides `generate_skills()` for targeted skill/agent installation.
  - `maintain.py` — staleness detection, update suggestions, drift analysis
  - `cli.py` — argh-based CLI entry point
  - `util.py` — internal helpers (underscore-prefixed)
  - `data/` — bundled package resources (accessed via `importlib.resources.files`)
    - `templates/` — generation templates organized by target project type
      - `shared/` — templates that work for any project type
      - `python/` — Python-specific templates (paths use `misc/docs/`)
      - `jsts/` — JS/TS-specific templates (paths use `docs/`)
    - `rubrics/` — scoring criteria (YAML or TOML)
    - `skills/` — Claude Code skill templates (opsward, opsward-diagnose, opsward-generate, opsward-maintain) that opsward installs into target projects
- `tests/` — pytest tests

## Commands

```bash
# Install
pip install opsward   # or: pip install ow

# CLI usage
python -m opsward diagnose-cmd /path/to/project          # Diagnose AI setup
python -m opsward diagnose-cmd /path/to/proj1 /path/to/proj2  # Multi-project
python -m opsward generate-cmd /path/to/project           # Generate missing pieces
python -m opsward maintain-cmd /path/to/project            # Check for staleness/drift
python -m opsward install-skills-cmd --write               # Install Claude Code skills

# After pip install (via pyproject.toml [project.scripts]):
opsward diagnose-cmd .
opsward generate-cmd . --write
opsward maintain-cmd .
opsward install-skills-cmd --write                    # Install into .claude/
opsward install-skills-cmd --global-install --write   # Install into ~/.claude/
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

Follow the argh SSOT dispatch pattern:

```python
# In cli.py
_dispatch_funcs = [diagnose, generate, maintain, install_skills]

if __name__ == "__main__":
    import argh
    argh.dispatch_commands(_dispatch_funcs)
```

```python
# In __main__.py
from opsward.cli import _dispatch_funcs
import argh
argh.dispatch_commands(_dispatch_funcs)
```

### Template Pattern

Templates live in `opsward/data/templates/`. They are plain markdown files with `${variable}` placeholders (using `string.Template`). The generator reads them via `importlib.resources`, substitutes variables from the scan results, and writes to the target project.

### Scoring Pattern

Scoring functions are pure: `(scan_result) -> score_dict`. No side effects. The rubric definitions live in `opsward/data/rubrics/` as YAML. Scoring dimensions for CLAUDE.md (inspired by community best practices):

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
- For multi-project scanning, each project gets its own `DiagnosisReport`. There is also an aggregate `MultiProjectReport` that summarizes cross-project patterns.
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
