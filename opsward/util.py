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
        return path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return ''


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


def iter_files(directory: Path, *, suffix: str = ''):
    """Yield files in *directory* (non-recursive), optionally filtered by suffix."""
    if not directory.is_dir():
        return
    for p in sorted(directory.iterdir(), key=lambda p: p.name):
        if p.is_file() and (not suffix or p.suffix == suffix):
            yield p
