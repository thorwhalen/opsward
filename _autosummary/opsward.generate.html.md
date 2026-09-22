# opsward.generate

### opsward.generate(scan_result, , agents_md=False, hooks=False)

Determine which artifacts are missing, render templates, return files to create.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`GeneratedFile`](opsward.base.html.md#opsward.base.GeneratedFile)]

```pycon
>>> from pathlib import Path
>>> from opsward.base import ScanResult
>>> files = generate(ScanResult(project_root=Path('/tmp/empty')))
>>> any(f.target_path.name == 'CLAUDE.md' for f in files)
True
```
