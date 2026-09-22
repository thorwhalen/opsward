# opsward.score

Pure scoring functions. ScanResult -> DiagnosisReport.

All functions are pure — same input, same output.

### Functions

| [`diagnose`](#opsward.score.diagnose)(scan_result)      | Score a ScanResult and return a DiagnosisReport.               |
|-----------------------------------------------------------------------------|----------------------------------------------------------------|
| [`validate_hooks_config`](#opsward.score.validate_hooks_config)(cfg) | Validate a hooks config against Claude Code's expected shape.  |
| [`validate_skill_spec`](#opsward.score.validate_skill_spec)(skill) | Validate a SkillInfo against the agentskills.io specification. |

### opsward.score.diagnose(scan_result)

Score a ScanResult and return a DiagnosisReport.

* **Return type:**
  [`DiagnosisReport`](opsward.base.html.md#opsward.base.DiagnosisReport)

```pycon
>>> from pathlib import Path
>>> from opsward.base import ScanResult
>>> r = diagnose(ScanResult(project_root=Path('/tmp/empty')))
>>> r.grade
'F'
```

### opsward.score.validate_hooks_config(cfg)

Validate a hooks config against Claude Code’s expected shape.

Returns a list of human-readable violation strings (empty = valid). Catches
the silent-failure traps: a non-string `matcher`, an unknown event name,
or an entry with no runnable `command` hook — none of which Claude Code
honors, so the hook never fires even though the file “looks” configured.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

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

### opsward.score.validate_skill_spec(skill)

Validate a SkillInfo against the agentskills.io specification.

Returns a list of human-readable violation strings (empty = compliant).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> from pathlib import Path
>>> from opsward.base import SkillInfo
>>> s = SkillInfo(name='good-skill', path=Path('.'), has_skill_md=True,
...     frontmatter={'name': 'good-skill', 'description': 'Does X.'}, line_count=50)
>>> validate_skill_spec(s)
[]
```
