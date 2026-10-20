"""Fleet mode: diagnose many project roots and roll the results up (opsward#17, gap 1).

``scan`` and ``diagnose`` stay per-repo and unchanged; this module only maps them over
N roots and aggregates. The rollups answer fleet questions a single report cannot:
how many repos miss the same item, which component is weakest across the fleet, and
which repos are worst.

>>> from pathlib import Path
>>> from opsward.base import ComponentScore, DiagnosisReport, ProjectType
>>> def fake(root):
...     missing = ["CLAUDE.md"] if root.name != "good" else []
...     return DiagnosisReport(root, ProjectType.python, [ComponentScore("claude_md", 90 if not missing else 20)],
...                            missing_items=missing)
>>> report = fleet(["good", "bad", "worse"], diagnose_root=fake, check_dirs=False)
>>> report.missing_rollup()
{'CLAUDE.md': 2}
>>> report.grade_counts()
{'A': 1, 'F': 2}
>>> [r.project_root.name for r in report.worst(1)]
['bad']
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from opsward.base import DiagnosisReport

#: A component scoring below this percentage of its max counts as weak in the rollup.
DFLT_WEAK_COMPONENT_PCT = 60
#: How many worst repos the text summary lists.
DFLT_WORST_SHOWN = 10


def _diagnose_root(root: Path) -> DiagnosisReport:
    from opsward.scan import scan
    from opsward.score import diagnose

    return diagnose(scan(root))


@dataclass
class FleetReport:
    """Every repo's :class:`~opsward.base.DiagnosisReport`, plus the roots that failed."""

    reports: list[DiagnosisReport] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    def grade_counts(self) -> dict[str, int]:
        """Repos per letter grade, best grade first."""
        return dict(sorted(Counter(r.grade for r in self.reports).items()))

    def mean_score(self) -> float:
        return mean(r.overall_score for r in self.reports) if self.reports else 0.0

    def missing_rollup(self) -> dict[str, int]:
        """How many repos miss each item, most common first ("CLAUDE.md": 47)."""
        counts = Counter(
            item for r in self.reports for item in dict.fromkeys(r.missing_items)
        )
        return dict(counts.most_common())

    def component_rollup(
        self, *, weak_pct: float = DFLT_WEAK_COMPONENT_PCT
    ) -> dict[str, dict[str, float]]:
        """Per component: the mean percentage score and how many repos score it as weak."""
        by_name: dict[str, list[float]] = {}
        for report in self.reports:
            for s in report.scores:
                by_name.setdefault(s.name, []).append(
                    100 * s.score / s.max_score if s.max_score else 0.0
                )
        return {
            name: {
                "mean_pct": round(mean(pcts), 1),
                "weak": sum(p < weak_pct for p in pcts),
                "repos": len(pcts),
            }
            for name, pcts in sorted(by_name.items(), key=lambda kv: mean(kv[1]))
        }

    def portability_rollup(self) -> dict:
        """Repos each host finds instructions in, and AGENTS.md drift across the fleet.

        ``covered`` follows ``AGENT_HOSTS`` order and omits hosts no repo covers;
        ``uncovered`` counts repos no host finds anything in (opsward#15).
        """
        from opsward.portability import AGENT_HOSTS, DRIFT_KINDS

        reports = [r.portability for r in self.reports if r.portability is not None]
        covered = Counter(h for p in reports for h in p.covered)
        drift = Counter(f.kind for p in reports for f in p.findings)
        return {
            "covered": {h: covered[h] for h in AGENT_HOSTS if covered[h]},
            "uncovered": sum(not p.covered for p in reports),
            "drift": {kind: drift[kind] for kind in DRIFT_KINDS},
            "drifting_repos": sum(bool(p.findings) for p in reports),
        }

    def worst(self, n: int = DFLT_WORST_SHOWN) -> list[DiagnosisReport]:
        """The ``n`` lowest-scoring repos, ties broken by name."""
        return sorted(
            self.reports, key=lambda r: (r.overall_score, r.project_root.name)
        )[:n]

    def names(self) -> dict[str, str]:
        """Root (as a string) -> display name: the basename, or more when basenames clash."""
        return unique_names(
            [*(str(r.project_root) for r in self.reports), *self.errors]
        )

    def to_dict(self) -> dict:
        """A JSON-ready summary keyed by repo *name*, never by absolute path."""
        names = self.names()
        return {
            "repos": {
                names[str(r.project_root)]: {
                    "score": round(r.overall_score, 1),
                    "grade": r.grade,
                    "missing": list(r.missing_items),
                }
                for r in self.reports
            },
            "errors": {names[k]: v for k, v in self.errors.items()},
            "grade_counts": self.grade_counts(),
            "mean_score": round(self.mean_score(), 1),
            "missing_rollup": self.missing_rollup(),
            "component_rollup": self.component_rollup(),
            "portability_rollup": self.portability_rollup(),
        }

    def __str__(self) -> str:
        n = len(self.reports)
        names = self.names()
        lines = [f"Fleet report: {n} repo(s), mean score {self.mean_score():.1f}"]
        if grades := self.grade_counts():
            lines.append("Grades: " + ", ".join(f"{g} {c}" for g, c in grades.items()))
        if missing := self.missing_rollup():
            lines.append("Missing across the fleet:")
            lines += [f"  {item}: {count}/{n}" for item, count in missing.items()]
        if components := self.component_rollup():
            lines.append("Components, weakest first (mean %, weak repos):")
            lines += [
                f"  {name}: {c['mean_pct']}%, {c['weak']}/{c['repos']}"
                for name, c in components.items()
            ]
        if self.reports:
            lines += _portability_lines(self.portability_rollup())
            lines.append("Worst repos:")
            lines += [
                f"  {names[str(r.project_root)]}: {r.overall_score:.1f} ({r.grade})"
                for r in self.worst()
            ]
        if self.errors:
            lines.append("Could not diagnose:")
            lines += [f"  {names[root]}: {why}" for root, why in self.errors.items()]
        return "\n".join(lines)


def _portability_lines(rollup: dict) -> list[str]:
    hosts = [f"{h} {n}" for h, n in rollup["covered"].items()]
    hosts.append(f"none {rollup['uncovered']}")
    lines = [f"Host coverage (repos): {', '.join(hosts)}"]
    if rollup["drifting_repos"]:
        kinds = ", ".join(
            f"{kind.replace('_', '-')} {n}" for kind, n in rollup["drift"].items() if n
        )
        lines.append(f"AGENTS.md drift: {rollup['drifting_repos']} repo(s) ({kinds})")
    return lines


def unique_names(paths: Iterable[str | Path]) -> dict[str, str]:
    """Each path's shortest trailing part that no other path shares (never the full path).

    >>> unique_names(["/x/a/proj", "/x/b/proj", "/x/c"])
    {'/x/a/proj': 'a/proj', '/x/b/proj': 'b/proj', '/x/c': 'c'}
    """
    paths = list(dict.fromkeys(map(str, paths)))
    parts = {p: Path(p).parts for p in paths}
    names = {}
    for p in paths:
        tail = parts[p][-1:]
        for k in range(1, len(parts[p]) + 1):
            tail = parts[p][-k:]
            if not any(q != p and parts[q][-k:] == tail for q in paths):
                break
        names[p] = "/".join(tail)
    return names


def fleet(
    roots: Iterable[str | Path],
    *,
    diagnose_root: Callable[[Path], DiagnosisReport] = _diagnose_root,
    check_dirs: bool = True,
) -> FleetReport:
    """Diagnose every root and aggregate. A root that fails is recorded, never fatal.

    :param roots: project directories, e.g. ``git_roots_under(parent)``.
    :param diagnose_root: ``Path -> DiagnosisReport``; defaults to ``diagnose(scan(root))``.
    :param check_dirs: record a root that is not a directory as an error.
    """
    report = FleetReport()
    for root in map(Path, roots):
        if check_dirs and not root.is_dir():
            report.errors[str(root)] = "not a directory"
            continue
        try:
            report.reports.append(diagnose_root(root))
        except Exception as error:  # one broken repo must not stop the fleet
            report.errors[str(root)] = f"{type(error).__name__}: {error}"
    return report


def git_roots_under(parent: str | Path, *, depth: int = 1) -> Iterator[Path]:
    """Directories under ``parent`` (to ``depth`` levels) that hold a ``.git``, sorted."""
    level = [Path(parent)]
    for _ in range(depth):
        children = sorted(
            p
            for d in level
            for p in d.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )
        yield from (p for p in children if (p / ".git").exists())
        level = [p for p in children if not (p / ".git").exists()]


#: Format version of the fleet manifest written by :func:`write_manifest`.
MANIFEST_VERSION = 1


def manifest_record(
    roots: Iterable[str | Path], report: FleetReport, *, updated: str | None = None
) -> dict:
    """The per-machine fleet manifest: the roots that make up the fleet and the last summary.

    The roots are this machine's (absolute) paths, which is why the manifest is
    per-machine and must stay out of version control; the summary is name-keyed.

    >>> rec = manifest_record(["a", "b"], FleetReport(), updated="2026-10-20T00:00:00+00:00")
    >>> rec["roots"], rec["report"]["repos"], rec["updated"]
    (['a', 'b'], {}, '2026-10-20T00:00:00+00:00')
    """
    return {
        "opsward_fleet_manifest": MANIFEST_VERSION,
        "updated": updated or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "roots": [str(r) for r in roots],
        "report": report.to_dict(),
    }


def write_manifest(
    path: str | Path, roots: Iterable[str | Path], report: FleetReport
) -> Path:
    """Write :func:`manifest_record` as JSON to ``path`` (parents created) and return it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest_record(roots, report), indent=2) + "\n", encoding="utf-8"
    )
    return path


def manifest_roots(path: str | Path) -> list[str]:
    """The fleet's roots as recorded in the manifest at ``path``; ``[]`` if it does not exist.

    :raises ValueError: when the file exists but is not a fleet manifest.
    :raises OSError: when it cannot be read (a directory, no permission).
    """
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "opsward_fleet_manifest" not in data:
        raise ValueError(f"{path.name} is not an opsward fleet manifest")
    roots = data.get("roots", [])
    if not isinstance(roots, list) or not all(isinstance(r, str) for r in roots):
        raise ValueError(f"{path.name}: `roots` must be a list of paths")
    return roots
