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


# The SSOT of hosts. Source: misc/docs/research/multiplatform_config.md, comparison table.
HOSTS: Mapping[str, HostSpec] = {
    h.name: h
    for h in (
        HostSpec("claude", ("CLAUDE.md",), (".claude/rules",)),
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
        HostSpec("aider", ("CONVENTIONS.md",)),
        HostSpec("cline", (), (".clinerules",), reads_agents_md=True),
        HostSpec("zed", (".rules",), reads_agents_md=True),
    )
}

_IMPORT_RE = re.compile(rf"^\s*@(?:\./)?{re.escape(CANONICAL)}\s*$", re.MULTILINE)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


@dataclass(frozen=True)
class HostFile:
    """One host instruction file (or rule folder) as found on disk."""

    path: str  # relative to the project root
    content: str = ""
    links_to_canonical: bool = False
    is_dir: bool = False

    @property
    def relation(self) -> str:
        """``symlink``, ``import``, ``rules`` or ``copy`` (see the module docstring)."""
        if self.is_dir:
            return "rules"
        if self.links_to_canonical:
            return "symlink"
        if _IMPORT_RE.search(self.content):
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
        """Hosts that find project instructions, in ``HOSTS`` order."""
        return [h for h, rel in self.coverage.items() if rel != "none"]

    def to_dict(self) -> dict:
        return {
            "coverage": dict(self.coverage),
            "findings": [vars(f) for f in self.findings],
        }


def read_host_files(root: Path, *, hosts: Mapping[str, HostSpec] = HOSTS) -> dict:
    """Every host instruction file and rule folder present under *root*. Read-only."""
    root = Path(root)
    canonical = root / CANONICAL

    def links_to_canonical(p: Path) -> bool:
        return p.is_symlink() and canonical.exists() and p.resolve() == canonical.resolve()

    found: dict[str, HostFile] = {}
    for spec in hosts.values():
        for rel in spec.instruction_files:
            p = root / rel
            if p.is_file():
                found[rel] = HostFile(rel, read_text_safe(p), links_to_canonical(p))
        for rel in spec.rule_dirs:
            if (root / rel).is_dir():
                found[rel] = HostFile(rel, is_dir=True)
    return found


def analyze(
    canonical: str,
    host_files: Mapping[str, HostFile],
    *,
    hosts: Mapping[str, HostSpec] = HOSTS,
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


def portability(root: Path, *, hosts: Mapping[str, HostSpec] = HOSTS) -> PortabilityReport:
    """``analyze`` over what is on disk under *root*: the library entry point."""
    root = Path(root)
    return analyze(
        read_text_safe(root / CANONICAL), read_host_files(root, hosts=hosts), hosts=hosts
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
            "see `opsward.portability.portability(root)` for the list"
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
    if relation in ("symlink", "rules"):
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
    """Second-level-and-below sections keyed by normalised heading; bodies whitespace-normalised.

    The level-1 title is skipped: it names the file, not content.

    >>> _sections("# T\\n\\n## Build & Test\\n\\n  pytest  \\n\\n\\n## Notes\\nx")
    {'build test': 'pytest', 'notes': 'x'}
    """
    out: dict[str, list[str]] = {}
    current: Optional[str] = None
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else _HEADING_RE.match(line)
        if m and len(m.group(1)) > 1:
            current = _norm_heading(m.group(2))
            out.setdefault(current, [])
        elif m:
            current = None
        elif current is not None:
            out[current].append(line.strip())
    return {h: "\n".join(l for l in lines if l) for h, lines in out.items()}


def _norm_heading(heading: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", heading.lower()).split())
