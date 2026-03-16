"""All dataclasses and type definitions for opsward."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ProjectType(Enum):
    """Detected project type."""

    python = "python"
    jsts = "jsts"
    mixed = "mixed"
    unknown = "unknown"


# ---------------------------------------------------------------------------
# Inventory items
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillInfo:
    """A skill found in .claude/skills/."""

    name: str
    path: Path
    has_skill_md: bool = False
    description: str = ""
    frontmatter: dict = field(default_factory=dict)
    line_count: int = 0


@dataclass(frozen=True)
class AgentInfo:
    """An agent found in .claude/agents/."""

    name: str
    path: Path
    description: str = ""


@dataclass(frozen=True)
class RuleInfo:
    """A rule found in .claude/rules/."""

    name: str
    path: Path
    content: str = ""


@dataclass(frozen=True)
class DocSpec:
    """A document found in the docs directory."""

    name: str
    path: Path
    size_bytes: int = 0


# ---------------------------------------------------------------------------
# Scan output
# ---------------------------------------------------------------------------


@dataclass
class ScanResult:
    """Everything we learned by reading (never writing) a target project."""

    project_root: Path
    project_type: ProjectType = ProjectType.unknown

    # CLAUDE.md
    claude_md_path: Optional[Path] = None
    claude_md_content: str = ""

    # .claude/ inventories
    skills: list[SkillInfo] = field(default_factory=list)
    agents: list[AgentInfo] = field(default_factory=list)
    rules: list[RuleInfo] = field(default_factory=list)

    # Hooks
    hooks_path: Optional[Path] = None
    hooks_config: Optional[dict] = None

    # Docs
    docs: list[DocSpec] = field(default_factory=list)
    has_docs_guide: bool = False
    docs_guide_path: Optional[Path] = None

    # AGENTS.md
    agents_md_path: Optional[Path] = None
    agents_md_content: str = ""

    # Monorepo detection
    is_monorepo: bool = False
    monorepo_packages: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scoring / diagnosis output
# ---------------------------------------------------------------------------


@dataclass
class ComponentScore:
    """Score for a single component (0–100) with optional notes."""

    name: str
    score: int
    max_score: int = 100
    notes: list[str] = field(default_factory=list)


@dataclass
class DiagnosisReport:
    """Report card produced by scoring a ScanResult."""

    project_root: Path
    project_type: ProjectType
    scores: list[ComponentScore] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    # Weighted overall score (0–100), set by score.py
    weighted_score: float = 0.0

    @property
    def overall_score(self) -> float:
        """Weighted score if set, else simple average."""
        if self.weighted_score:
            return self.weighted_score
        if not self.scores:
            return 0.0
        return sum(s.score for s in self.scores) / len(self.scores)

    @property
    def grade(self) -> str:
        """Letter grade: A (90-100), B (80-89), C (70-79), D (60-69), F (<60)."""
        s = self.overall_score
        if s >= 90:
            return "A"
        if s >= 80:
            return "B"
        if s >= 70:
            return "C"
        if s >= 60:
            return "D"
        return "F"

    def __str__(self) -> str:
        lines = [
            f"Diagnosis Report: {self.project_root.name}",
            f"Project type: {self.project_type.value}",
            f"Overall score: {self.overall_score:.0f}/100  (Grade: {self.grade})",
            "",
        ]

        if self.scores:
            lines.append("Components:")
            for cs in self.scores:
                bar = _score_bar(cs.score, cs.max_score)
                lines.append(f"  {cs.name:<25s} {bar} {cs.score}/{cs.max_score}")
                for note in cs.notes:
                    lines.append(f"    - {note}")
            lines.append("")

        if self.missing_items:
            lines.append("Missing:")
            for item in self.missing_items:
                lines.append(f"  [ ] {item}")
            lines.append("")

        if self.suggestions:
            lines.append("Suggestions:")
            for i, sug in enumerate(self.suggestions, 1):
                lines.append(f"  {i}. {sug}")

        return "\n".join(lines)


def _score_bar(score: int, max_score: int, *, width: int = 20) -> str:
    """Return a simple ASCII progress bar."""
    filled = round(width * score / max_score) if max_score else 0
    return "[" + "#" * filled + "." * (width - filled) + "]"


# ---------------------------------------------------------------------------
# Generation output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeneratedFile:
    """A file to be written by the generate step."""

    target_path: Path
    content: str
    overwrite_policy: str = "skip"  # 'skip' | 'overwrite' | 'merge'


# ---------------------------------------------------------------------------
# Maintenance output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MaintenanceSuggestion:
    """A single maintenance action proposed by maintain.py."""

    category: str  # e.g. 'stale_path', 'outdated_doc', 'sync_issue'
    description: str
    diff: str = ""
