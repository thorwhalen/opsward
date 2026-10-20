"""Shared helpers for opsward."""

import json
import re
from pathlib import Path
from typing import Optional


def read_text_safe(path: Path) -> str:
    """Read a text file, returning '' if it doesn't exist or can't be decoded.

    >>> from pathlib import Path
    >>> read_text_safe(Path('/nonexistent/file.txt'))
    ''
    """
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def read_json_safe(path: Path) -> Optional[dict]:
    """Read a JSON file, returning None on any failure."""
    text = read_text_safe(path)
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def iter_subdirs(directory: Path):
    """Yield immediate subdirectories of *directory*, sorted by name."""
    if not directory.is_dir():
        return
    yield from sorted(
        (p for p in directory.iterdir() if p.is_dir()),
        key=lambda p: p.name,
    )


def iter_files(
    directory: Path,
    *,
    suffix: str = "",
    recursive: bool = False,
    _seen: set | None = None,
):
    """Yield files in *directory*, optionally filtered by suffix.

    ``recursive=True`` walks subdirectories too, depth-first in name order. Hidden
    folders are skipped (opsward's choice: ``.trash`` and the like are not agents),
    a folder already visited through a symlink is not re-entered, and a folder that
    cannot be read is skipped rather than raised.
    """
    if not directory.is_dir():
        return
    seen = _seen if _seen is not None else set()
    try:
        seen.add(directory.resolve())
        entries = sorted(directory.iterdir(), key=lambda p: p.name)
    except OSError:
        return
    for p in entries:
        if p.is_file() and (not suffix or p.suffix == suffix):
            yield p
        elif recursive and p.is_dir() and not p.name.startswith("."):
            try:
                real = p.resolve()
            except OSError:
                continue
            if real in seen:
                continue
            yield from iter_files(p, suffix=suffix, recursive=True, _seen=seen)


#: Put this on a line (as ``<!-- opsward: ignore-path -->`` or ``# opsward: ignore-path``)
#: and the paths on it are not checked; alone on its line, it covers the next line too.
IGNORE_PATH_MARKER = "opsward: ignore-path"

_PATH_PATTERN = re.compile(r"(?:^|[\s`(])(\./)?(\w[\w\-.]*/[\w\-./]+\.\w+)", re.MULTILINE)


def checked_lines(content: str, *, marker: str = IGNORE_PATH_MARKER) -> str:
    """``content`` without the lines an ignore-path marker covers.

    >>> checked_lines("a/b.py\\nold/c.py <!-- opsward: ignore-path -->\\n# opsward: ignore-path\\ntmp/d.py\\ne/f.py")
    'a/b.py\\ne/f.py'
    """
    kept, skip_next = [], False
    for line in content.splitlines():
        if skip_next:
            skip_next = False
            continue
        if marker in line:
            rest = line.replace(marker, "").strip(" \t#<>!-")
            skip_next = not rest  # a marker alone on its line covers the next one
            continue
        kept.append(line)
    return "\n".join(kept)


def extract_paths(content: str) -> list[str]:
    """Plausible repo-relative file paths cited in markdown, minus URLs and ignored lines.

    The one extractor behind the currency score, the cross-reference check, the stale-path
    finding and the ADR drift check, so ``opsward: ignore-path`` silences all of them.

    >>> extract_paths("See `src/a.py`, https://x.io/b.html and ./docs/c.md")
    ['src/a.py', './docs/c.md']
    """
    paths = []
    for m in _PATH_PATTERN.finditer(checked_lines(content)):
        path = (m.group(1) or "") + m.group(2)
        if "://" not in path and not path.startswith("http"):
            paths.append(path)
    return paths
