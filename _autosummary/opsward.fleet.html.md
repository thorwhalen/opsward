# opsward.fleet

### opsward.fleet(roots, \*, diagnose_root=<function \_diagnose_root>, check_dirs=True)

Diagnose every root and aggregate. A root that fails is recorded, never fatal.

* **Parameters:**
  * **roots** ([`Iterable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]) – project directories, e.g. `git_roots_under(parent)`.
  * **diagnose_root** ([`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)], [`DiagnosisReport`](opsward.base.html.md#opsward.base.DiagnosisReport)]) – `Path -> DiagnosisReport`; defaults to `diagnose(scan(root))`.
  * **check_dirs** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – record a root that is not a directory as an error.
* **Return type:**
  `FleetReport`
