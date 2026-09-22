# opsward.scan

### opsward.scan(project_root)

Scan *project_root* and return a ScanResult.

* **Return type:**
  [`ScanResult`](opsward.base.md#opsward.base.ScanResult)

```pycon
>>> import tempfile, pathlib
>>> r = scan(pathlib.Path(tempfile.mkdtemp()))
>>> r.project_type
<ProjectType.unknown: 'unknown'>
```
