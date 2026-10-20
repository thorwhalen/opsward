"""Multi-host portability: which agent hosts a repo satisfies, and canonical↔render drift.

The canonical project brief is ``AGENTS.md`` (opsward#15). Every other host's instruction
file (``CLAUDE.md``, ``GEMINI.md``, ``.github/copilot-instructions.md``, …) is a *render*
of it, related to it in one of three ways:

* ``symlink`` — the file is a symlink to ``AGENTS.md``: byte-identical, cannot drift;
* ``import`` — the file imports it (``@AGENTS.md``) and adds host-only deltas: the
  recommended shape for hosts with an import syntax (Claude Code, Gemini CLI);
* ``copy`` — a separate file: everything in it can drift from the canonical.

The check is a *linter*: the canonical is authoritative and drift in a render is
reported, never merged back. Three finding kinds, matched section by section (by
normalised heading):

* ``stale`` — a canonical section is missing from a copy;
* ``diverged`` — a section is in both, with different bodies (a stale render or a hand
  edit in the render: the files alone cannot say which);
* ``host_only`` — a section only the render has: promote it to ``AGENTS.md`` if it is
  portable, or keep it as a host delta (after an ``@AGENTS.md`` import).

Scoped-rule folders (``.cursor/rules/``, ``.windsurf/rules/``, ``.clinerules/``) count
towards coverage but are not compared: they are not renders of one brief.

Files that are only coverage signals (``CONVENTIONS.md`` is often a contributor doc, not a
render) are compared only when they import or link the canonical.

``read_host_files`` is read-only (it backs ``scan``); ``analyze`` is pure.

>>> report = analyze(
...     "# P\\n\\n## Build\\n\\npytest\\n",
...     {"CLAUDE.md": HostFile("CLAUDE.md", "## Build\\n\\npytest -x\\n## Claude\\n\\nx\\n")},
... )
>>> report.coverage["claude"], report.coverage["codex"]
('copy', 'native')
>>> sorted((f.kind, f.section) for f in report.findings)
[('diverged', 'build'), ('host_only', 'claude')]
"""

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from opsward.util import read_text_safe

CANONICAL = "AGENTS.md"


@dataclass(frozen=True)
class HostSpec:
    """Where one agent host looks for project instructions (research table, opsward#15)."""

    name: str
    instruction_files: tuple[str, ...] = ()
    rule_dirs: tuple[str, ...] = ()
    reads_agents_md: bool = False
    # False: the file name is too common to assume it renders AGENTS.md (see module doc)
    compared: bool = True


# The SSOT of hosts. Source: misc/docs/research/multiplatform_config.md, comparison table.
AGENT_HOSTS: Mapping[str, HostSpec] = {
    h.name: h
    for h in (
        HostSpec("claude", ("CLAUDE.md", ".claude/CLAUDE.md"), (".claude/rules",)),
        HostSpec("codex", reads_agents_md=True),
        HostSpec(
            "copilot",
            (".github/copilot-instructions.md",),
            (".github/instructions",),
            reads_agents_md=True,
        ),
        HostSpec("cursor", (".cursorrules",), (".cursor/rules",), reads_agents_md=True),
        HostSpec("windsurf", (".windsurfrules", ".windsurfrules.md"), (".windsurf/rules",)),
        HostSpec("gemini", ("GEMINI.md",)),
        HostSpec("aider", ("CONVENTIONS.md",), compared=False),
        HostSpec("cline", (".clinerules",), (".clinerules",), reads_agents_md=True),
        HostSpec("zed", (".rules",), reads_agents_md=True),
    )
}

_IMPORT_RE = re.compile(rf"(?<!\S)@(?:\./)?{re.escape(CANONICAL)}(?![\w.])")
_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
_SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)\s*$")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_INLINE_CODE_RE = re.compile(r"(`+).*?\1")


@dataclass(frozen=True)
class HostFile:
    """One host instruction file (or rule folder) as found on disk."""

    path: str  # relative to the project root
    content: str = ""
    links_to_canonical: bool = False
    is_dir: bool = False
    compared: bool = True

    @property
    def relation(self) -> str:
        """``symlink``, ``import``, ``rules`` or ``copy`` (see the module docstring)."""
        if self.is_dir:
            return "rules"
        if self.links_to_canonical:
            return "symlink"
        prose = "\n".join(line for line, fenced in _lines(self.content) if not fenced)
        if _IMPORT_RE.search(_INLINE_CODE_RE.sub("", prose)):
            return "import"
        return "copy"


@dataclass(frozen=True)
class DriftFinding:
    """One section that differs between ``AGENTS.md`` and a render."""

    kind: str  # 'stale' | 'diverged' | 'host_only'
    path: str
    section: str

    def __str__(self) -> str:
        what = {
            "stale": "missing from the render",
            "diverged": "differs from AGENTS.md",
            "host_only": "only in the render (promote, or keep as a host delta)",
        }[self.kind]
        return f"{self.path}: section '{self.section}' {what}"


@dataclass
class PortabilityReport:
    """Host coverage (host -> relation, ``native`` or ``none``) and drift findings."""

    coverage: dict[str, str] = field(default_factory=dict)
    findings: list[DriftFinding] = field(default_factory=list)

    @property
    def covered(self) -> list[str]:
        """Hosts that find project instructions, in ``AGENT_HOSTS`` order."""
        return [h for h, rel in self.coverage.items() if rel != "none"]

    def to_dict(self) -> dict:
        return {
            "coverage": dict(self.coverage),
            "findings": [vars(f) for f in self.findings],
        }


def read_host_files(root: Path, *, hosts: Mapping[str, HostSpec] = AGENT_HOSTS) -> dict:
    """Every host instruction file and rule folder present under *root*. Read-only."""
    root = Path(root)
    canonical = root / CANONICAL

    def same_as_canonical(p: Path) -> bool:
        # A symlink either way round, or a hard link: the same bytes cannot drift
        try:
            return canonical.exists() and p.samefile(canonical)
        except OSError:
            return False

    def is_kind(p: Path, kind: str) -> bool:
        try:
            return getattr(p, kind)()
        except OSError:  # an unreadable parent must not crash scan
            return False

    found: dict[str, HostFile] = {}
    for spec in hosts.values():
        for rel in spec.instruction_files:
            p = root / rel
            if is_kind(p, "is_file"):
                content = read_text_safe(p).lstrip("\ufeff")
                found[rel] = HostFile(rel, content, same_as_canonical(p), compared=spec.compared)
        for rel in spec.rule_dirs:
            if is_kind(root / rel, "is_dir"):
                found[rel] = HostFile(rel, is_dir=True)
    return found


def analyze(
    canonical: str,
    host_files: Mapping[str, HostFile],
    *,
    hosts: Mapping[str, HostSpec] = AGENT_HOSTS,
) -> PortabilityReport:
    """Coverage and drift of *host_files* against the *canonical* ``AGENTS.md`` text. Pure."""
    report = PortabilityReport()
    for spec in hosts.values():
        relations = [
            host_files[rel].relation
            for rel in (*spec.instruction_files, *spec.rule_dirs)
            if rel in host_files
        ]
        native = ["native"] if canonical and spec.reads_agents_md else []
        report.coverage[spec.name] = _strongest([*relations, *native])
    if canonical:
        for hf in host_files.values():
            report.findings.extend(_drift(canonical, hf))
    return report


def check_portability(root: Path, *, hosts: Mapping[str, HostSpec] = AGENT_HOSTS) -> PortabilityReport:
    """``analyze`` over what is on disk under *root*: the library entry point."""
    root = Path(root)
    return analyze(
        read_text_safe(root / CANONICAL).lstrip("\ufeff"),
        read_host_files(root, hosts=hosts), hosts=hosts
    )


def summarize(report: PortabilityReport) -> Iterator[str]:
    """One diagnose suggestion per drifting render."""
    by_path: dict[str, list[DriftFinding]] = {}
    for f in report.findings:
        by_path.setdefault(f.path, []).append(f)
    for path, findings in by_path.items():
        counts = {
            kind: sum(f.kind == kind for f in findings)
            for kind in ("stale", "diverged", "host_only")
        }
        parts = [f"{n} {kind.replace('_', '-')}" for kind, n in counts.items() if n]
        yield (
            f"{path} drifts from AGENTS.md ({', '.join(parts)} section(s)) — "
            "see `opsward.check_portability(root)` for the list"
        )


# Strongest first: a host covered several ways reports the least drift-prone one.
_RELATION_ORDER = ("symlink", "import", "native", "copy", "rules")


def _strongest(relations: list[str]) -> str:
    for rel in _RELATION_ORDER:
        if rel in relations:
            return rel
    return "none"


def _drift(canonical: str, hf: HostFile) -> Iterator[DriftFinding]:
    relation = hf.relation
    # An empty (or undecodable: read as '') file says nothing about drift
    if relation in ("symlink", "rules") or not hf.content.strip():
        return
    if not hf.compared and relation == "copy":
        return
    canon = _sections(canonical)
    render = _sections(hf.content)
    for heading, body in render.items():
        if heading in canon:
            if canon[heading] != body:
                yield DriftFinding("diverged", hf.path, heading)
        elif relation == "copy":
            # After an import, render-only sections are the intended host deltas.
            yield DriftFinding("host_only", hf.path, heading)
    if relation == "copy":
        for heading in canon:
            if heading not in render:
                yield DriftFinding("stale", hf.path, heading)


def _sections(text: str) -> dict[str, str]:
    """Sections keyed by normalised heading; bodies whitespace-normalised.

    The first level-1 heading is skipped (it titles the file); ATX and setext headings
    count, fenced code (backtick or tilde) never does.

    >>> _sections("# T\\n\\n## Build & Test\\n\\n  pytest  \\n\\n\\n## Notes\\nx")
    {'build test': 'pytest', 'notes': 'x'}
    >>> _sections("# T\\n~~~\\n## not one\\n~~~\\n# Usage\\nrun\\nAPI\\n---\\nf()")
    {'usage': 'run', 'api': 'f()'}
    """
    out: dict[str, list[str]] = {}
    current: Optional[str] = None
    title_seen = False
    pending: Optional[str] = None  # a prose line that a setext underline may promote

    def start(level: int, heading: str) -> None:
        nonlocal current, title_seen
        if level == 1 and not title_seen:
            title_seen, current = True, None
            return
        title_seen = True
        current = _norm_heading(heading)
        out.setdefault(current, [])

    def emit(line: str) -> None:
        if current is not None:
            out[current].append(line.strip())

    for line, fenced in _lines(text):
        setext = None if fenced else _SETEXT_RE.match(line)
        if setext and pending and pending.strip():
            start(1 if setext.group(1)[0] == "=" else 2, pending.strip())
            pending = None
            continue
        if pending is not None:
            emit(pending)
            pending = None
        atx = None if fenced else _HEADING_RE.match(line)
        if atx:
            start(len(atx.group(1)), atx.group(2))
        elif not fenced and line.strip() and not _FENCE_RE.match(line):
            pending = line
        else:
            emit(line)
    if pending is not None:
        emit(pending)
    return {h: "\n".join(l for l in lines if l) for h, lines in out.items()}


def _lines(text: str) -> Iterator[tuple[str, bool]]:
    """Each line with whether it is inside (or delimits) a fenced code block.

    A fence closes only on the same character, at least as long, with no info string;
    a backtick fence's info string may not contain a backtick (CommonMark).
    """
    fence: Optional[str] = None
    for line in text.splitlines():
        m = _FENCE_RE.match(line)
        if fence is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
                yield line, True
            else:
                yield line, False
        else:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None
            yield line, True


def _norm_heading(heading: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", heading.lower()).split())
