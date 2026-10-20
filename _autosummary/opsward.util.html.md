# opsward.util

Shared helpers for opsward.

### Module Attributes

| [`IGNORE_PATH_MARKER`](#opsward.util.IGNORE_PATH_MARKER)   | Put this on a line (as `<!-- opsward: ignore-path -->` or `# opsward: ignore-path`) and the paths on it are not checked; alone on its line, it covers the next line too.   |
|-----------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### Functions

| [`checked_lines`](#opsward.util.checked_lines)(content, \*[, marker])     | `content` without the lines an ignore-path marker covers.                           |
|-------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`extract_paths`](#opsward.util.extract_paths)(content)                   | Plausible repo-relative file paths cited in markdown, minus URLs and ignored lines. |
| [`iter_files`](#opsward.util.iter_files)(directory, \*[, suffix, ...]) | Yield files in *directory*, optionally filtered by suffix.                          |
| [`iter_subdirs`](#opsward.util.iter_subdirs)(directory)                  | Yield immediate subdirectories of *directory*, sorted by name.                      |
| [`read_json_safe`](#opsward.util.read_json_safe)(path)                     | Read a JSON file, returning None on any failure.                                    |
| [`read_text_safe`](#opsward.util.read_text_safe)(path)                     | Read a text file, returning '' if it doesn't exist or can't be decoded.             |

### opsward.util.IGNORE_PATH_MARKER *= 'opsward: ignore-path'*

Put this on a line (as `<!-- opsward: ignore-path -->` or `# opsward: ignore-path`)
and the paths on it are not checked; alone on its line, it covers the next line too.

### opsward.util.checked_lines(content, , marker='opsward: ignore-path')

`content` without the lines an ignore-path marker covers.

A marker quoted in backticks (prose *about* the marker) is not a marker.

```pycon
>>> checked_lines("a/b.py\nold/c.py <!-- opsward: ignore-path -->\n# opsward: ignore-path\ntmp/d.py\ne/f.py")
'a/b.py\ne/f.py'
>>> checked_lines("<!-- opsward: ignore-path -->\n<!-- opsward: ignore-path -->\nx/y.py\nz/w.py")
'z/w.py'
>>> checked_lines("Use `<!-- opsward: ignore-path -->` on src/a.py")
'Use `<!-- opsward: ignore-path -->` on src/a.py'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.util.extract_paths(content)

Plausible repo-relative file paths cited in markdown, minus URLs and ignored lines.

The one extractor behind the currency score, the cross-reference check, the stale-path
finding and the ADR drift check, so `opsward: ignore-path` silences all of them.

```pycon
>>> extract_paths("See `src/a.py`, https://x.io/b.html and ./docs/c.md")
['src/a.py', './docs/c.md']
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

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
