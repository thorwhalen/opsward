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

from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
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

    def worst(self, n: int = DFLT_WORST_SHOWN) -> list[DiagnosisReport]:
        """The ``n`` lowest-scoring repos, ties broken by name."""
        return sorted(
            self.reports, key=lambda r: (r.overall_score, r.project_root.name)
        )[:n]

    def to_dict(self) -> dict:
        """A JSON-ready summary keyed by repo *name*, never by absolute path."""
        return {
            "repos": {
                r.project_root.name: {
                    "score": round(r.overall_score, 1),
                    "grade": r.grade,
                    "missing": list(r.missing_items),
                }
                for r in self.reports
            },
            "errors": {Path(k).name: v for k, v in self.errors.items()},
            "grade_counts": self.grade_counts(),
            "mean_score": round(self.mean_score(), 1),
            "missing_rollup": self.missing_rollup(),
            "component_rollup": self.component_rollup(),
        }

    def __str__(self) -> str:
        n = len(self.reports)
        lines = [f"Fleet report: {n} repo(s), mean score {self.mean_score():.1f}"]
        lines.append(
            "Grades: " + ", ".join(f"{g} {c}" for g, c in self.grade_counts().items())
        )
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
            lines.append("Worst repos:")
            lines += [
                f"  {r.project_root.name}: {r.overall_score:.1f} ({r.grade})"
                for r in self.worst()
            ]
        if self.errors:
            lines.append("Could not diagnose:")
            lines += [
                f"  {Path(root).name}: {why}" for root, why in self.errors.items()
            ]
        return "\n".join(lines)


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
