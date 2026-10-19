# opsward.score

Pure scoring functions. ScanResult -> DiagnosisReport.

All functions are pure — same input, same output.

### Functions

| [`claude_md_size_overrun`](#opsward.score.claude_md_size_overrun)(content, \*[, ...])       | Return a [`SizeOverrun`](#opsward.score.SizeOverrun) if *content* exceeds *max_chars*, else None.   |
|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| [`diagnose`](#opsward.score.diagnose)(scan_result, \*[, claude_md_max_chars]) | Score a ScanResult and return a DiagnosisReport.                                                                     |
| [`docs_dir_hint`](#opsward.score.docs_dir_hint)(sr)                                | Project-relative docs dir to suggest moving sections into.                                                           |
| [`validate_hooks_config`](#opsward.score.validate_hooks_config)(cfg)                       | Validate a hooks config against Claude Code's expected shape.                                                        |
| [`validate_skill_spec`](#opsward.score.validate_skill_spec)(skill)                       | Validate a SkillInfo against the agentskills.io specification.                                                       |

### Classes

| [`SizeOverrun`](#opsward.score.SizeOverrun)(chars, max_chars, penalty, ...)   | A CLAUDE.md over its size budget, with the sections worth moving out.   |
|------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|

### *class* opsward.score.SizeOverrun(chars, max_chars, penalty, sections, docs_dir)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A CLAUDE.md over its size budget, with the sections worth moving out.

#### describe(, deducted=None)

One-paragraph finding naming the longest sections and where to move them.

`deducted` is the points actually lost (the line-count rule may have
left fewer than `penalty` to take); omit it to leave the figure out.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.score.claude_md_size_overrun(content, , max_chars=10000, docs_dir='misc/docs', top=3)

Return a [`SizeOverrun`](#opsward.score.SizeOverrun) if *content* exceeds *max_chars*, else None.

The penalty is proportional to the overrun: `_CONCISE_SIZE_PENALTY_MAX`
points at twice the threshold (at least 1 once over it).

```pycon
>>> claude_md_size_overrun("x" * 11, max_chars=10).penalty
1
>>> claude_md_size_overrun("short", max_chars=10) is None
True
```

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`SizeOverrun`](#opsward.score.SizeOverrun)]

### opsward.score.diagnose(scan_result, , claude_md_max_chars=10000)

Score a ScanResult and return a DiagnosisReport.

`claude_md_max_chars` is the CLAUDE.md size above which Conciseness
loses points (see [`claude_md_size_overrun()`](#opsward.score.claude_md_size_overrun)).

```pycon
>>> from pathlib import Path
>>> from opsward.base import ScanResult
>>> r = diagnose(ScanResult(project_root=Path('/tmp/empty')))
>>> r.grade
'F'
```

* **Return type:**
  [`DiagnosisReport`](opsward.base.html.md#opsward.base.DiagnosisReport)

### opsward.score.docs_dir_hint(sr)

Project-relative docs dir to suggest moving sections into.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.score.validate_hooks_config(cfg)

Validate a hooks config against Claude Code’s expected shape.

Returns a list of human-readable violation strings (empty = valid). Catches
the silent-failure traps: a non-string `matcher`, an unknown event name,
or an entry with no runnable `command` hook — none of which Claude Code
honors, so the hook never fires even though the file “looks” configured.

```pycon
>>> validate_hooks_config({'hooks': {'PostToolUse': [
...     {'matcher': 'Edit', 'hooks': [{'type': 'command', 'command': 'x'}]}]}})
[]
>>> validate_hooks_config({'pre_commit': ['ruff']})
['no top-level `hooks` key']
>>> 'matcher' in validate_hooks_config({'hooks': {'PostToolUse': [
...     {'matcher': {'tool_name': 'Edit'}, 'hooks': [
...         {'type': 'command', 'command': 'x'}]}]}})[0]
True
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### opsward.score.validate_skill_spec(skill)

Validate a SkillInfo against the agentskills.io specification.

Returns a list of human-readable violation strings (empty = compliant).

```pycon
>>> from pathlib import Path
>>> from opsward.base import SkillInfo
>>> s = SkillInfo(name='good-skill', path=Path('.'), has_skill_md=True,
...     frontmatter={'name': 'good-skill', 'description': 'Does X.'}, line_count=50)
>>> validate_skill_spec(s)
[]
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
