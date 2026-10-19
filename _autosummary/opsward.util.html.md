# opsward.util

Shared helpers for opsward.

### Functions

| [`iter_files`](#opsward.util.iter_files)(directory, \*[, suffix, ...])   | Yield files in *directory*, optionally filtered by suffix.              |
|---------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`iter_subdirs`](#opsward.util.iter_subdirs)(directory)                    | Yield immediate subdirectories of *directory*, sorted by name.          |
| [`read_json_safe`](#opsward.util.read_json_safe)(path)                       | Read a JSON file, returning None on any failure.                        |
| [`read_text_safe`](#opsward.util.read_text_safe)(path)                       | Read a text file, returning '' if it doesn't exist or can't be decoded. |

### opsward.util.iter_files(directory, , suffix='', recursive=False, \_seen=None)

Yield files in *directory*, optionally filtered by suffix.

`recursive=True` walks subdirectories too, depth-first in name order. Hidden
folders are skipped (opsward’s choice: `.trash` and the like are not agents),
a folder already visited through a symlink is not re-entered, and a folder that
cannot be read is skipped rather than raised.

### opsward.util.iter_subdirs(directory)

Yield immediate subdirectories of *directory*, sorted by name.

### opsward.util.read_json_safe(path)

Read a JSON file, returning None on any failure.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### opsward.util.read_text_safe(path)

Read a text file, returning ‘’ if it doesn’t exist or can’t be decoded.

```pycon
>>> from pathlib import Path
>>> read_text_safe(Path('/nonexistent/file.txt'))
''
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
