# opsward.util

Shared helpers for opsward.

### Functions

| [`iter_files`](#opsward.util.iter_files)(directory, \*[, suffix])   | Yield files in *directory* (non-recursive), optionally filtered by suffix.   |
|----------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`iter_subdirs`](#opsward.util.iter_subdirs)(directory)               | Yield immediate subdirectories of *directory*, sorted by name.               |
| [`read_json_safe`](#opsward.util.read_json_safe)(path)                  | Read a JSON file, returning None on any failure.                             |
| [`read_text_safe`](#opsward.util.read_text_safe)(path)                  | Read a text file, returning '' if it doesn't exist or can't be decoded.      |

### opsward.util.iter_files(directory, , suffix='')

Yield files in *directory* (non-recursive), optionally filtered by suffix.

### opsward.util.iter_subdirs(directory)

Yield immediate subdirectories of *directory*, sorted by name.

### opsward.util.read_json_safe(path)

Read a JSON file, returning None on any failure.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### opsward.util.read_text_safe(path)

Read a text file, returning ‘’ if it doesn’t exist or can’t be decoded.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> from pathlib import Path
>>> read_text_safe(Path('/nonexistent/file.txt'))
''
```
