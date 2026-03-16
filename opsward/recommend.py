"""Recommend skills from the ecosystem based on project tech stack.

Maps detected dependencies and frameworks to curated skill sources.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from opsward.base import ScanResult
from opsward.util import read_text_safe


@dataclass(frozen=True)
class SkillRecommendation:
    """A recommended skill from the ecosystem."""

    name: str
    reason: str
    source: str  # URL or repo reference


# ---------------------------------------------------------------------------
# Curated mapping: dependency signals -> skill recommendations
# ---------------------------------------------------------------------------

# Each entry: (signal_keywords, SkillRecommendation)
# signal_keywords are checked against pyproject.toml/package.json content
_RECOMMENDATIONS: list[tuple[tuple[str, ...], SkillRecommendation]] = [
    (
        ("supabase",),
        SkillRecommendation(
            name="supabase",
            reason="Supabase dependency detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("stripe",),
        SkillRecommendation(
            name="stripe",
            reason="Stripe dependency detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("cloudflare", "wrangler"),
        SkillRecommendation(
            name="cloudflare-workers",
            reason="Cloudflare dependency detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("firebase", "firestore"),
        SkillRecommendation(
            name="firebase",
            reason="Firebase dependency detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("prisma",),
        SkillRecommendation(
            name="prisma",
            reason="Prisma ORM detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("docker", "Dockerfile"),
        SkillRecommendation(
            name="docker",
            reason="Docker usage detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("terraform",),
        SkillRecommendation(
            name="terraform",
            reason="Terraform dependency detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("fastapi",),
        SkillRecommendation(
            name="fastapi",
            reason="FastAPI framework detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("django",),
        SkillRecommendation(
            name="django",
            reason="Django framework detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("flask",),
        SkillRecommendation(
            name="flask",
            reason="Flask framework detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("react", "next", "nextjs"),
        SkillRecommendation(
            name="nextjs",
            reason="React/Next.js dependency detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("tailwindcss", "tailwind"),
        SkillRecommendation(
            name="tailwindcss",
            reason="Tailwind CSS detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("vercel",),
        SkillRecommendation(
            name="vercel",
            reason="Vercel deployment detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("netlify",),
        SkillRecommendation(
            name="netlify",
            reason="Netlify deployment detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
    (
        ("anthropic", "claude"),
        SkillRecommendation(
            name="anthropic-sdk",
            reason="Anthropic/Claude dependency detected",
            source="https://github.com/VoltAgent/awesome-agent-skills",
        ),
    ),
]


def recommend_skills(scan_result: ScanResult) -> list[SkillRecommendation]:
    """Recommend ecosystem skills based on detected tech stack.

    >>> from pathlib import Path
    >>> from opsward.base import ScanResult
    >>> recommend_skills(ScanResult(project_root=Path('/tmp/empty')))
    []
    """
    return list(_iter_recommendations(scan_result))


def _iter_recommendations(sr: ScanResult) -> Iterable[SkillRecommendation]:
    """Yield skill recommendations matching the project's dependency signals."""
    corpus = _build_signal_corpus(sr)
    if not corpus:
        return

    existing_skills = {s.name for s in sr.skills}
    seen_names: set[str] = set()

    for signals, rec in _RECOMMENDATIONS:
        if rec.name in existing_skills or rec.name in seen_names:
            continue
        if any(signal in corpus for signal in signals):
            seen_names.add(rec.name)
            yield rec


def _build_signal_corpus(sr: ScanResult) -> str:
    """Build a lowercase text corpus from dependency files for signal matching."""
    root = sr.project_root
    parts: list[str] = []
    for name in (
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "package.json",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
    ):
        text = read_text_safe(root / name)
        if text:
            parts.append(text.lower())
    return "\n".join(parts)
