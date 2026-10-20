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

_ADR_FILE_RE = re.compile(
    r"^(?P<number>\d{4})[-_](?P<slug>[^/]*)\.md$"
)  # any numbered .md counts for numbering
_STATUS_HEADING_RE = re.compile(r"^#{2,3}\s+Status\s*$\n+(?P<text>[^\n]*)", re.M)
_STATUS_LINE_RE = re.compile(
    r"^\**Status\**\s*:\**\s*(?P<text>[^\n]+)$", re.M | re.I
)  # the colon is required
_FRONTMATTER_STATUS_RE = re.compile(
    r"\A---\n(?:.*\n)*?status:\s*(?P<text>[^\n]+)\n(?:.*\n)*?---", re.M
)
_CLOSED_STATUSES = ("superseded", "deprecated", "rejected")
_FENCE_RE = re.compile(r"^(`{3,}|~{3,}).*?^\1[ \t]*$", re.M | re.S)
_LINK_RE = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
_DOMAIN_RE = re.compile(
    r"^[\w-]+(\.[\w-]+)*\.[a-z]{2,6}$"
)  # a host name, not a file: no slash yet, dotted labels
_STRIKE_RE = re.compile(r"~~.*?~~", re.S)
_HISTORICAL_RE = re.compile(
    r"\b(formerly|previously|moved|migrated|renamed|replaced|removed|retired|deleted)\b",
    re.I,
)
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


def clean_title(title: str) -> str:
    r"""One line, single-spaced; empty is an error the CLI reports.

    >>> clean_title("  two\n lines ")
    'two lines'
    """
    return " ".join(title.split())


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
    numbers = [
        int(_ADR_FILE_RE.match(p.name).group("number"))
        for p in adr_files(decisions_dir)
    ]
    return (max(numbers) + 1) if numbers else 1


def _template(name: str) -> str:
    return (
        importlib.resources.files("opsward.data")
        .joinpath(f"templates/shared/decisions/{name}")
        .read_text(encoding="utf-8")
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
        title=clean_title(title),
        status=status,
        date=date.isoformat(),
        evidence=evidence.strip()
        or "<!-- the issue, discussion or PR this rests on -->",
    )
    return GeneratedFile(
        target_path=decisions_dir / f"{number:04d}-{slugify(title)}.md", content=content
    )


def log_entry(text: str, *, date: Optional[_dt.date] = None) -> str:
    """One Y-statement line for ``decisions/log.md``.

    >>> log_entry("In the context of goldens, facing drift, we decided for pinning.", date=_dt.date(2026, 10, 19))
    '- 2026-10-19 — In the context of goldens, facing drift, we decided for pinning.'
    """
    date = date or _dt.date.today()
    return f"- {date.isoformat()} — {' '.join(text.split())}"


def log_append(
    decisions_dir: Path, text: str, *, date: Optional[_dt.date] = None
) -> tuple[Path, str]:
    """The log file and the full content it should hold after appending *text*.

    A missing log starts from the ``log.md`` template. The existing log is read
    strictly: an unreadable or non-UTF-8 log raises (``OSError`` /
    ``UnicodeDecodeError``) rather than being replaced by the new line alone. The
    caller writes; this does not.
    """
    path = decisions_dir / _LOG_NAME
    existing = (
        path.read_text(encoding="utf-8") if path.exists() else _template(_LOG_NAME)
    )
    if existing and not existing.endswith("\n"):
        existing += "\n"
    return path, existing + log_entry(text, date=date) + "\n"


def decision_docs(sr: ScanResult) -> list[DocSpec]:
    """The ADRs a scan found (``ScanResult.decisions``), numbered files only."""
    return [
        d
        for d in sr.decisions
        if _ADR_FILE_RE.match(d.path.name) and int(d.path.name[:4]) > 0
    ]


def status_of(content: str) -> Optional[str]:
    r"""The ADR's status text, from a ``## Status`` heading, a ``**Status:**`` line or
    MADR front matter; ``None`` when there is none.

    >>> status_of("# x\n\n## Status\n\nAccepted (2026-01-01)\n")
    'Accepted (2026-01-01)'
    >>> status_of("---\nstatus: accepted\n---\n# x\n"), status_of("**Status:** Superseded by 0003"), status_of("# x\nno status")
    ('accepted', 'Superseded by 0003', None)
    """
    for rx in (_STATUS_HEADING_RE, _FRONTMATTER_STATUS_RE, _STATUS_LINE_RE):
        m = rx.search(content)
        if m:
            return m.group("text").strip() or ""
    return None


def cited_paths(content: str) -> list[str]:
    r"""Paths an ADR cites as current, outside fenced code: bare path tokens and Markdown
    link targets (relative ones only; URLs and host names are not paths).

    A path the record cites as history is not checked: wrap it in ``~~strikethrough~~``,
    or say so on the line (``formerly``, ``previously``, ``moved``, ``migrated``,
    ``renamed``, ``replaced``, ``removed``, ``retired``, ``deleted``), as in "we moved `pkg/old.py` to `pkg/new.py`" — there
    only `pkg/new.py` must exist.

    >>> cited_paths("See `pkg/a.py`, [0002](0002-x.md), [doc](../research/r.md), https://x.io/a/b.py, docs.github.com/en/x.md\n```\nsrc/in/fence.py\n```")
    ['../research/r.md', '0002-x.md', 'pkg/a.py']
    >>> cited_paths("We moved `pkg/old.py` to `pkg/new.py`; ~~`pkg/gone.py`~~ is history.")
    ['pkg/new.py']
    >>> cited_paths("It was read from `pkg/live.py`.\nRenamed [old](../old.md) to [new](../new.md).")
    ['../new.md', 'pkg/live.py']
    """
    from opsward.maintain import _extract_paths  # the same extractor CLAUDE.md uses
    from opsward.util import checked_lines  # `opsward: ignore-path` covers links too

    prose = checked_lines(_STRIKE_RE.sub("", _FENCE_RE.sub("", content)))
    found = set()
    for line in prose.splitlines():
        historical = bool(_HISTORICAL_RE.search(line))
        for p in _extract_paths(line):
            if _DOMAIN_RE.match(p.split("/", 1)[0]):
                continue
            if historical and not _is_destination(line, p):
                continue
            found.add(p)
        for target in _LINK_RE.findall(line):
            if "://" in target or target.startswith(("mailto:", "/")):
                continue
            if historical and not _is_destination(line, target):
                continue
            found.add(target)
    return sorted(found)


def _is_destination(line: str, path: str) -> bool:
    """On a historical line, the path after "to"/"into"/"now" is the current one."""
    at = line.find(path)
    before = line[:at].lower()
    # the path may be a code span (`x`) or a link target ([label](x)) right after the word
    return bool(
        re.search(
            r"\b(to|into|now|now at|lives in|is now)\s*(\[[^\]]*\]\(|[`\[])?$",
            before.rstrip(),
        )
    )


def check_decisions(sr: ScanResult) -> Iterable[MaintenanceSuggestion]:
    """``maintain`` check: ADRs citing paths that no longer exist, or carrying no status.

    Rot in a decision record is a path that moved: the rationale still reads well and
    points at nothing. Superseded, deprecated and rejected ADRs are history and are not
    checked for paths: the superseding record is where the current paths live. This
    reports; it never rewrites an accepted ADR (ADR 0010).
    """
    for doc in decision_docs(sr):
        content = read_text_safe(doc.path)
        rel = _rel(doc.path, sr.project_root)
        status = status_of(content)
        if status is None:
            yield MaintenanceSuggestion(
                category="stale_adr",
                description=f"`{rel}` has no status (a `## Status` section, `**Status:**` line or front matter) — an ADR without one cannot be superseded",
            )
            continue
        if any(word in status.lower() for word in _CLOSED_STATUSES):
            continue
        # a cited path may be repo-relative, relative to the ADR's folder (a sibling or a
        # `../` link), or relative to the docs folder above it
        bases = (sr.project_root, doc.path.parent, doc.path.parent.parent)
        missing = [
            p for p in cited_paths(content) if not any((b / p).exists() for b in bases)
        ]
        if missing:
            yield MaintenanceSuggestion(
                category="stale_adr",
                description=(
                    f"`{rel}` cites path(s) that no longer exist: {', '.join(f'`{p}`' for p in missing[:5])}"
                    f"{' …' if len(missing) > 5 else ''} — write a superseding ADR (or a log entry) that says where it went "
                    '("moved from `old` to `new`", or ~~old~~, keeps the old path out of this check); '
                    "the accepted one is only edited to point at its successor"
                ),
            )


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
