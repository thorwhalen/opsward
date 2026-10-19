# opsward.scan

### opsward.scan(project_root, \*, claude_config_dir=<object object>)

Scan *project_root* and return a ScanResult.

`claude_config_dir` is the user’s Claude Code config dir, whose `skills/` is
the global scope a project skill competes with (shadowing, listing budget). It
defaults to `default_claude_config_dir()`; pass `None` to read nothing
outside the project (tests, portable goldens). Reading it is still read-only.

```pycon
>>> import tempfile, pathlib
>>> r = scan(pathlib.Path(tempfile.mkdtemp()), claude_config_dir=None)
>>> r.project_type, r.global_skills
(<ProjectType.unknown: 'unknown'>, [])
```

* **Return type:**
  [`ScanResult`](opsward.base.html.md#opsward.base.ScanResult)
