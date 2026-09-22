# opsward.maintain

### opsward.maintain(scan_result, , previous_report=None)

Detect maintenance issues and return suggestions.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`MaintenanceSuggestion`](opsward.base.md#opsward.base.MaintenanceSuggestion)]

```pycon
>>> from pathlib import Path
>>> from opsward.base import ScanResult
>>> maintain(ScanResult(project_root=Path('/tmp/empty')))
[]
```
