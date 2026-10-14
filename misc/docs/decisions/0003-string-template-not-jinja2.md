# 0003 — Templates use `string.Template`, with no logic inside a template

## Status

Accepted (2026-03-11)

## Context

opsward renders markdown templates (docs, CLAUDE.md, skills, the auditor agent) into target projects. A template engine such as Jinja2 would add a runtime dependency and invite conditionals and loops inside templates, where they are hard to test and easy to get wrong. opsward aims to stay a light tool (see [0007](0007-dependency-light-core-optional-extras.md)).

## Decision

- Templates are plain markdown with `${variable}` placeholders, rendered by the standard library's `string.Template.safe_substitute` (`def _render` in `generate.py`).
- No conditionals or loops in a template. A variant that differs by project type is a separate file (`python/`, `jsts/`, falling back to `shared/` via `def _template_for_doc`).
- Anything conditional is computed in Python, by a `_detect_*` helper feeding `def _build_variables`, and arrives in the template as a ready-made string.
- Templates are bundled package data read via `importlib.resources.files` (`def _load_template`), never by filesystem path.

## Consequences

- Zero template dependencies, and every template remains valid, readable markdown even with placeholders unreplaced.
- `safe_substitute` leaves unknown placeholders literal instead of raising, so a typo surfaces as a visible `${...}` in output rather than a crash, and template prose that needs a literal `$name` must write `$$name`.
- Conditional content is testable Python: e.g. the testing doc's conftest bullet is the `${test_structure}` variable built by `def _detect_test_structure`, not an `{% if %}` block.
- The number of template files grows with the number of variants; accepted as the cost of keeping logic out of templates.

## Evidence

- Initial template set and `importlib.resources` loading: commit [434917c](https://github.com/thorwhalen/opsward/commit/434917c)
- Rule text: `CLAUDE.md` ("Templates are **not** Jinja2"), `.claude/rules/templates-generation-and-paths.md` ([PR #5](https://github.com/thorwhalen/opsward/pull/5))
- Conditional content moved into a Python-computed variable (`${test_structure}`): [PR #11](https://github.com/thorwhalen/opsward/pull/11)
