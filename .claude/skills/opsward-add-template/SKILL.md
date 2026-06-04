---
name: opsward-add-template
description: Add or edit a generation template in opsward — a doc template (architecture.md, testing.md, …), an installable skill (SKILL.md), or an agent definition — and wire it into generate.py so opsward produces it. Use when adding a new artifact opsward should scaffold into target projects, adding a template variable, or changing what `opsward generate` / `install-skills` emit. Covers string.Template rules and the python/jsts/shared layout.
---

# Adding a generation template to opsward

Templates live in `opsward/data/templates/` and are rendered by `generate.py`.
They are plain markdown with `${variable}` placeholders.

## The two-step rule

Adding a template file is **not enough** — nothing renders it until you wire it
into `generate.py`. Every template needs (1) a file under `data/templates/`, and
(2) a `_render(...)` call in `generate()` (or `generate_skills()`).

## Template mechanics

- **Engine:** `string.Template` with `safe_substitute` (`generate.py:_render`).
  Placeholders are `${var}`. Unknown placeholders are left **literal** (`${var}`)
  rather than erroring — so a stray `$` in template prose must be written `$$`.
- **No logic in templates.** No conditionals or loops. If a doc needs to differ
  by project type, create a type-specific variant (see layout below) — do not
  branch inside the file.
- **Loaded via `importlib.resources`** (`_load_template`, `generate.py:140`).
  Just drop the file in the right folder; never reference it by filesystem path.

## Directory layout & type resolution

```
data/templates/
  shared/   templates that work for any project type (the default)
  python/   Python-specific variants (docs paths use misc/docs/)
  jsts/     JS/TS-specific variants (docs paths use docs/)
```

For **docs**, `_template_for_doc(doc_name, project_type)` (`generate.py:453`)
prefers `python/<doc>.md` or `jsts/<doc>.md` when present and falls back to
`shared/<doc>.md`. So: put the common version in `shared/`, and only add a
`python/` or `jsts/` file when the content genuinely differs.

Docs output location is `_docs_path()`: `misc/docs/` for python/mixed, `docs/`
for jsts. Use `${docs_path}` in templates instead of hardcoding either.

## Available template variables

Anything in the dict returned by `_build_variables()` (`generate.py:200`):
`project_name`, `project_description`, `project_type`, `docs_path`,
`tech_stack`, `module_map`, `commands`, `conventions`, `package_manager`,
`formatter`, `linter`, `line_length`, `test_framework`, `test_command`,
`test_dir`, `coverage_command`, `additional_docs_table`, `glossary_entries`,
`env_vars_table`.

**Adding a new variable:** add a `_detect_<thing>(sr)` helper and a key in
`_build_variables`. Keep detection read-only (it consumes a `ScanResult`).

## Recipes

### Add a new doc template (e.g. `security.md`)

1. Create `data/templates/shared/security.md` with `${...}` placeholders.
2. In `generate()`, add it to the right tier:
   - **always** generated: the `for doc_name in (...)` loop near `generate.py:60`.
   - **conditional**: gate on a `ScanResult` signal, mirroring `_has_tests` /
     `_has_deploy_artifacts` (e.g. only emit `security.md` if a signal exists).
   - **offered** (low priority, generate if missing): mirror the `roadmap` block.
3. Honor existing-file checks (`if doc_name not in existing_docs`).

### Add a new installable skill

1. Create `data/templates/shared/<skill-name>/SKILL.md` with valid frontmatter
   (`name:` must equal `<skill-name>`; `description:` present). Keep it ≤ 500
   lines — opsward's own validator enforces this.
2. Add `<skill-name>` to `_SKILL_NAMES` (`generate.py:14`). That single tuple
   drives both `generate()` and `generate_skills()` (the `install-skills`
   command), so no other wiring is needed.

### Add a new agent definition

1. Create `data/templates/shared/<agent-name>.md`.
2. Add `<agent-name>` to `_AGENT_NAMES` (`generate.py:22`) and, if it should be
   emitted by the full `generate()` path too, add a `_render` call alongside the
   `setup-auditor` block (`generate.py:95`).

## Verify

```bash
# Render against a throwaway project and eyeball output
python -m opsward generate /tmp/sample           # dry run — shows what would be created
python -m opsward install-skills --write /tmp/sample   # for skills/agents
pytest                                            # add/extend a test in tests/
```

Confirm placeholders all resolved (no stray `${...}` unless intentional) and the
new file lands at the expected path for both python and jsts targets.
