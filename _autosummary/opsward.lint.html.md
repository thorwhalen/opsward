# opsward.lint

Schema lint (opsward#17, gap 2): spec and config violations, pass or fail, no score.

`diagnose --min-score` is the cheap scored gate; `lint` is the strict one. It runs
every *validator* over every project skill, and checks the hooks config, and reports each
violation with a repo-relative path. A validator is `SkillInfo -> list[str]`:

* `opsward` – opsward’s own agentskills.io spec check (`validate_skill_spec()`),
  always available;
* `skill` – the `skill` package’s `skill.validate()` (`pip install 'opsward[lint]'`),
  which composes its own registered validators.

`"auto"` (the default) is `opsward` plus `skill` when it is importable. A host can
pass any mapping of name to validator instead, which is the seam for external linters.

```pycon
>>> from pathlib import Path
>>> from opsward.base import ScanResult, SkillInfo
>>> sr = ScanResult(Path("repo"), skills=[SkillInfo("Bad_Name", Path("repo/.claude/skills/Bad_Name"),
...                                                 has_skill_md=True, frontmatter={"name": "Bad_Name"})])
>>> findings = list(lint(sr, validators={"opsward": opsward_validator}))
>>> findings[0].path, findings[0].source
('.claude/skills/Bad_Name', 'opsward')
```

### Module Attributes

| [`DFLT_VALIDATORS`](#opsward.lint.DFLT_VALIDATORS)   | these names, each when it is available.                                             |
|--------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`VALIDATORS`](#opsward.lint.VALIDATORS)        | name -> (validator, is-it-available).                                               |
| [`HOOKS_FILES`](#opsward.lint.HOOKS_FILES)       | Where Claude Code reads hooks from; a settings file holds hooks only under `hooks`. |

### Functions

| [`lint`](#opsward.lint.lint)(scan_result, \*[, validators])   | Every spec/config violation in the scanned project, skills first, then hooks.    |
|----------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`opsward_validator`](#opsward.lint.opsward_validator)(skill)              | opsward's own spec check; a skill directory without a SKILL.md is one violation. |
| [`resolve_validators`](#opsward.lint.resolve_validators)([spec])            | Turn `"auto"`, `"opsward,skill"` or a mapping into a name -> validator dict.     |
| [`skill_package_validator`](#opsward.lint.skill_package_validator)(skill)        | The `skill` package's `validate()` over the skill's directory.                   |

### Classes

| [`LintFinding`](#opsward.lint.LintFinding)(path, source, message)   | One violation: where (repo-relative), which validator said so, and what.   |
|---------------------------------------------------------------------------------------|----------------------------------------------------------------------------|

### opsward.lint.DFLT_VALIDATORS *= 'auto'*

these names, each when it is available.

* **Type:**
  What `validators="auto"` means

### opsward.lint.HOOKS_FILES *= ('hooks.json', 'settings.json', 'settings.local.json')*

Where Claude Code reads hooks from; a settings file holds hooks only under `hooks`.

### *class* opsward.lint.LintFinding(path, source, message)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One violation: where (repo-relative), which validator said so, and what.

### opsward.lint.VALIDATORS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[SkillInfo](opsward.base.html.md#opsward.base.SkillInfo)], [list](https://docs.python.org/3/builtins/stdtypes.html#list)], [Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[], [bool](https://docs.python.org/3/builtins/functions.html#bool)]]]* *= {'opsward': (<function opsward_validator>, <function <lambda>>), 'skill': (<function skill_package_validator>, <function \_skill_package_available>)}*

name -> (validator, is-it-available).

* **Type:**
  Every known validator

### opsward.lint.lint(scan_result, , validators='auto')

Every spec/config violation in the scanned project, skills first, then hooks.

Hooks are read from every file in [`HOOKS_FILES`](#opsward.lint.HOOKS_FILES) that exists, not only the one
`scan` picked, so an unparseable or shadowed hooks file is still reported.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`LintFinding`](#opsward.lint.LintFinding)]

### opsward.lint.opsward_validator(skill)

opsward’s own spec check; a skill directory without a SKILL.md is one violation.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### opsward.lint.resolve_validators(spec='auto')

Turn `"auto"`, `"opsward,skill"` or a mapping into a name -> validator dict.

* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – an unknown name, or a named validator that is not installed.
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`SkillInfo`](opsward.base.html.md#opsward.base.SkillInfo)], [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)]]

```pycon
>>> list(resolve_validators("opsward"))
['opsward']
>>> resolve_validators("nope")
Traceback (most recent call last):
...
ValueError: unknown validator 'nope' (known: opsward, skill)
```

### opsward.lint.skill_package_validator(skill)

The `skill` package’s `validate()` over the skill’s directory.

A directory with no SKILL.md is left to [`opsward_validator()`](#opsward.lint.opsward_validator) (`skill` would
report it again, with an absolute path).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
