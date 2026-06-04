# Rule: `scan.py` is strictly read-only

`opsward/scan.py` must **never** modify the target project. This is a hard
invariant, not a guideline.

- It may only read: `pathlib.Path`, `os.walk`, `read_text_safe`, `read_json_safe`.
- It must never write, create, delete, or rename anything under the scanned root.
- All mutation lives in `generate.py` / `maintain.py`, never in scanning.

When editing `scan.py`, do not introduce any write/IO-mutating call. Tests must
never assert that scanning produces files. If you think scanning needs to write
something, the design is wrong — surface it instead.
