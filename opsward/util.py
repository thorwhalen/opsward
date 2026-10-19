"""Shared helpers for opsward."""

import json
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
