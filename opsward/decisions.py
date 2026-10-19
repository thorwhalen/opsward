"""Decision capture: numbered ADRs, the one-line decision log, and their drift.

Two tiers, per ADR 0010 and ``misc/docs/research/adr_and_home_finding.md``: a
trivial or medium decision is one **Y-statement** line appended to ``decisions/log.md``
("In the context of …, facing …, we decided for …, to achieve …, accepting …,
because …"); a load-bearing, expensive-to-reverse one is a numbered **MADR** file
``decisions/NNNN-slug.md`` that is never edited once accepted, only superseded.

Pure functions here; the CLI (``opsward decision new|note``) is the only writer, and
it never overwrites. ``maintain`` uses :func:`check_decisions` to report an ADR that
cites a path which no longer exists, or that has no Status, which is how rot shows up.
"""

from __future__ import annotations

import datetime as _dt
import importlib.resources
import re
from pathlib import Path
from string import Template
from typing import Iterable, Iterator, Optional

from opsward.base import DocSpec, GeneratedFile, MaintenanceSuggestion, ScanResult
from opsward.util import read_text_safe

_ADR_FILE_RE = re.compile(r"^(?P<number>\d{4})-(?P<slug>[a-z0-9][a-z0-9-]*)\.md$")
_STATUS_RE = re.compile(r"^##\s+Status\s*$", re.M)
_LOG_NAME = "log.md"
_TEMPLATE_NAME = "0000-template.md"
_SLUG_MAX = 60


def slugify(title: str) -> str:
    """A file-name slug: lowercase, hyphens, nothing else, at most 60 characters.

    >>> slugify("Pin the CLI surface by goldens!")
    'pin-the-cli-surface-by-goldens'
    """
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:_SLUG_MAX].rstrip("-") or "decision"


def adr_files(decisions_dir: Path) -> Iterator[Path]:
    """The numbered ADR files in *decisions_dir*, in number order (the template is not one)."""
    if not decisions_dir.is_dir():
        return
    found = []
    for p in decisions_dir.iterdir():
        m = _ADR_FILE_RE.match(p.name)
        if m and p.is_file() and int(m.group("number")) > 0:
            found.append((int(m.group("number")), p))
    for _, p in sorted(found):
        yield p


def next_number(decisions_dir: Path) -> int:
    """One more than the highest numbered ADR, so numbers never collide (1 for an empty dir).

    >>> import tempfile
    >>> next_number(Path(tempfile.mkdtemp()))
    1
    """
    numbers = [int(_ADR_FILE_RE.match(p.name).group("number")) for p in adr_files(decisions_dir)]
    return (max(numbers) + 1) if numbers else 1


def _template(name: str) -> str:
    return importlib.resources.files("opsward.data").joinpath(f"templates/shared/decisions/{name}").read_text(
        encoding="utf-8"
    )


def new_adr(
    decisions_dir: Path,
    title: str,
    *,
    status: str = "Proposed",
    date: Optional[_dt.date] = None,
    evidence: str = "",
) -> GeneratedFile:
    """The next numbered ADR for *title*, rendered from the ``adr.md`` template.

    *evidence* is the issue, discussion or PR the decision rests on (a URL or ``#N``);
    it lands in the Evidence section so the three surfaces stay linked.

    >>> import tempfile
    >>> gf = new_adr(Path(tempfile.mkdtemp()), "Pin the CLI surface", date=_dt.date(2026, 10, 19), evidence="#8")
    >>> gf.target_path.name, gf.content.splitlines()[0]
    ('0001-pin-the-cli-surface.md', '# 0001 — Pin the CLI surface')
    """
    number = next_number(decisions_dir)
    date = date or _dt.date.today()
    content = Template(_template("adr.md")).substitute(
        number=f"{number:04d}",
        title=title.strip(),
        status=status,
        date=date.isoformat(),
        evidence=evidence.strip() or "<!-- the issue, discussion or PR this rests on -->",
    )
    return GeneratedFile(target_path=decisions_dir / f"{number:04d}-{slugify(title)}.md", content=content)


def log_entry(text: str, *, date: Optional[_dt.date] = None) -> str:
    """One Y-statement line for ``decisions/log.md``.

    >>> log_entry("In the context of goldens, facing drift, we decided for pinning.", date=_dt.date(2026, 10, 19))
    '- 2026-10-19 — In the context of goldens, facing drift, we decided for pinning.'
    """
    date = date or _dt.date.today()
    return f"- {date.isoformat()} — {' '.join(text.split())}"


def log_append(decisions_dir: Path, text: str, *, date: Optional[_dt.date] = None) -> tuple[Path, str]:
    """The log file and the full content it should hold after appending *text*.

    A missing log starts from the ``log.md`` template. The caller writes; this does not.
    """
    path = decisions_dir / _LOG_NAME
    existing = read_text_safe(path) if path.is_file() else _template(_LOG_NAME)
    if existing and not existing.endswith("\n"):
        existing += "\n"
    return path, existing + log_entry(text, date=date) + "\n"


def decision_docs(sr: ScanResult) -> list[DocSpec]:
    """The ADRs a scan found (``ScanResult.decisions``), numbered files only."""
    return [d for d in sr.decisions if _ADR_FILE_RE.match(d.path.name) and int(d.path.name[:4]) > 0]


def check_decisions(sr: ScanResult) -> Iterable[MaintenanceSuggestion]:
    """``maintain`` check: ADRs citing paths that no longer exist, or carrying no Status.

    Rot in a decision record is a path that moved: the rationale still reads well and
    points at nothing. This reports; it never rewrites an accepted ADR (ADR 0010).
    """
    from opsward.maintain import _extract_paths  # the same extractor CLAUDE.md uses

    for doc in decision_docs(sr):
        content = read_text_safe(doc.path)
        rel = _rel(doc.path, sr.project_root)
        if not _STATUS_RE.search(content):
            yield MaintenanceSuggestion(
                category="stale_adr",
                description=f"`{rel}` has no `## Status` section — an ADR without a status cannot be superseded",
            )
        # a cited path may be repo-relative or relative to the ADR's own folder (a sibling file)
        missing = sorted(
            {p for p in _extract_paths(content) if not ((sr.project_root / p).exists() or (doc.path.parent / p).exists())}
        )
        if missing:
            yield MaintenanceSuggestion(
                category="stale_adr",
                description=(
                    f"`{rel}` cites path(s) that no longer exist: {', '.join(f'`{p}`' for p in missing[:5])}"
                    f"{' …' if len(missing) > 5 else ''} — write a superseding ADR (or a log entry) that says where it went; do not edit the accepted one"
                ),
            )


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
