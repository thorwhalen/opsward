---
name: opsward-dev
description: Contributor guide for developing opsward itself — its architecture, hard invariants, and where each kind of change goes. Use when modifying opsward's own source (scan/score/generate/maintain/recommend/cli), adding a template, scoring dimension, or skill recommendation, or when unsure which module owns a change. NOT for running opsward on a target project (use the `opsward` skill for that).
---

# Developing opsward

Opsward is a lightweight, dependency-light Python tool that treats a project's AI
agent setup (CLAUDE.md, skills, agents, rules, docs) as a first-class artifact:
it **scans** (read-only), **scores**, **generates** (from templates), and
**maintains** (drift detection). This skill orients you when changing opsward's
own code. For task-specific changes, defer to the sibling dev skills.

## Mental model: the pipeline

```
scan.py        ScanResult        (read the project — NEVER writes)
   │
   ├── score.py     -> DiagnosisReport   (pure scoring, no side effects)
   ├── generate.py  -> list[GeneratedFile] (render templates; write only on --write)
   ├── maintain.py  -> list[MaintenanceSuggestion] (drift/staleness)
   └── recommend.py -> list[SkillRecommendation]   (tech-stack -> skills)

base.py    all dataclasses + ProjectType enum (the shared vocabulary)
cli.py     argh dispatch over the public functions
__init__.py the facade — what library users import
```

Everything flows from `ScanResult` (`base.py`). When adding a capability, first
ask: *does `scan.py` already surface the data I need on `ScanResult`?* If not,
extend the scan first (keeping it read-only), then consume it downstream.

## Hard invariants — do not break these

1. **`scan.py` is purely read-only.** It uses `pathlib`/`os.walk` and never
   writes, creates, or mutates anything in the target project. This is a hard
   contract other modules rely on. Never add a write to scan.
2. **Generation never overwrites.** `GeneratedFile.overwrite_policy` defaults to
   `"skip"`; the CLI skips existing files. Dry-run is the default — files are
   only written when the user passes `--write`.
3. **Templates are `string.Template`, not Jinja2.** Placeholders are `${var}`,
   rendered with `safe_substitute` (unknown vars stay literal `${var}`). No
   conditionals/loops in templates — split into separate template files per
   variant instead. Keep dependencies light; do not add a templating engine.
4. **Bundled data is read via `importlib.resources.files("opsward.data...")`** —
   never hardcode filesystem paths to package data. See `_load_template` in
   `generate.py:140`.
5. **Scoring functions are pure** — `(ScanResult) -> ...`, no I/O, no side
   effects beyond appending to the passed-in `missing`/`suggestions` lists.

## Coding conventions (this repo)

- Functional over OOP. `dataclasses` for data, plain functions for logic.
- Keyword-only arguments from the 3rd positional onward (`*,` in signatures).
- Helpers: inner function if single-caller, `_underscore` prefix if module-private.
- Minimal docstring on every module and public function; add a simple doctest
  when practical (existing functions show the style — see `score.diagnose`).
- `yield`/generators over building and returning lists where natural.

## Where does my change go?

| I want to… | Go to | Sibling skill |
|---|---|---|
| Add/edit a generated doc, skill, or agent template | `data/templates/` + `generate.py` | **opsward-add-template** |
| Add/adjust a quality score or weighting | `score.py` | **opsward-add-scoring** |
| Map a dependency/framework to a recommended skill | `recommend.py` | **opsward-add-recommendation** |
| Surface new facts about a project | `scan.py` + a field on `ScanResult` (`base.py`) | — |
| Detect a new kind of staleness/drift | `maintain.py` | — |
| Expose a new CLI command | add a function, append it to `_dispatch_funcs` (`cli.py`) | — |
| Change the public API | update imports in `__init__.py` (the facade) | — |

## After any change

```bash
pip install -e ".[dev]" --break-system-packages   # if not already installed
pytest                                             # unit + doctests in tests/
pytest --doctest-modules opsward/                  # doctests embedded in source
```

Add or extend a test in `tests/` for behavior changes. If you add a public
function, export it from `__init__.py` and add it to `cli._dispatch_funcs` if it
should be a command.

**Dogfood it:** opsward manages its own setup. After changing generation or
scoring, run `python -m opsward diagnose .` and `python -m opsward maintain .`
on opsward itself and sanity-check the output. Keep `CLAUDE.md` and the module
map in sync with the code — stale self-documentation is exactly what opsward
exists to catch.
