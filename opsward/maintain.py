"""Drift and staleness detection. ScanResult -> list[MaintenanceSuggestion].

Checks for stale paths, out-of-sync docs_guide, and other maintenance issues.
"""

import re
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Optional

from opsward.base import DiagnosisReport, MaintenanceSuggestion, ScanResult
from opsward.util import read_text_safe


def maintain(
    scan_result: ScanResult,
    *,
    previous_report: Optional[DiagnosisReport] = None,
) -> list[MaintenanceSuggestion]:
    """Detect maintenance issues and return suggestions.

    >>> from pathlib import Path
    >>> from opsward.base import ScanResult
    >>> maintain(ScanResult(project_root=Path('/tmp/empty')))
    []
    """
    suggestions: list[MaintenanceSuggestion] = []

    suggestions.extend(_check_stale_paths(scan_result))
    suggestions.extend(_check_docs_guide_sync(scan_result))
    suggestions.extend(_check_doc_freshness(scan_result))
    suggestions.extend(_check_skills_without_description(scan_result))
    suggestions.extend(_check_empty_docs(scan_result))

    return suggestions


# ---------------------------------------------------------------------------
# Stale paths in CLAUDE.md
# ---------------------------------------------------------------------------


def _check_stale_paths(sr: ScanResult) -> Iterable[MaintenanceSuggestion]:
    """Find file paths referenced in CLAUDE.md that don't exist on disk."""
    if not sr.claude_md_content:
        return

    paths = _extract_paths(sr.claude_md_content)
    for path_str in paths:
        full = sr.project_root / path_str
        if not full.exists():
            yield MaintenanceSuggestion(
                category="stale_path",
                description=(
                    f"CLAUDE.md references `{path_str}` but it does not exist"
                ),
            )


# ---------------------------------------------------------------------------
# docs_guide.md sync
# ---------------------------------------------------------------------------


def _check_docs_guide_sync(sr: ScanResult) -> Iterable[MaintenanceSuggestion]:
    """Check that docs_guide.md accurately reflects the actual docs directory."""
    if not sr.has_docs_guide or sr.docs_guide_path is None:
        return

    guide_content = read_text_safe(sr.docs_guide_path)
    if not guide_content:
        return

    docs_dir = sr.docs_guide_path.parent
    actual_docs = {
        d.name
        for d in sr.docs
        if d.name != "docs_guide"  # don't expect docs_guide to list itself
    }

    # Extract doc names referenced in docs_guide.md (look for .md links)
    referenced = set(_extract_doc_refs(guide_content))

    # Docs on disk but not listed in guide
    unlisted = actual_docs - referenced
    for name in sorted(unlisted):
        yield MaintenanceSuggestion(
            category="sync_issue",
            description=(
                f"`{name}.md` exists in docs/ but is not listed in docs_guide.md"
            ),
            diff=_suggest_guide_addition(name),
        )

    # Docs listed in guide but not on disk
    missing = referenced - actual_docs
    for name in sorted(missing):
        # Check the actual file doesn't exist (the ref might use a different stem)
        candidate = docs_dir / f"{name}.md"
        if not candidate.exists():
            yield MaintenanceSuggestion(
                category="sync_issue",
                description=(
                    f"docs_guide.md references `{name}.md` but the file does not exist"
                ),
            )


# ---------------------------------------------------------------------------
# Doc freshness (via git log if available)
# ---------------------------------------------------------------------------

_STALE_DAYS = 90


def _check_doc_freshness(sr: ScanResult) -> Iterable[MaintenanceSuggestion]:
    """Flag docs not updated in the last 90 days (if git is available)."""
    if not sr.docs:
        return

    git_dir = sr.project_root / ".git"
    if not git_dir.is_dir():
        return

    for doc in sr.docs:
        days = _days_since_last_commit(doc.path, sr.project_root)
        if days is not None and days > _STALE_DAYS:
            yield MaintenanceSuggestion(
                category="outdated_doc",
                description=(f"`{doc.name}.md` has not been updated in {days} days"),
            )


def _days_since_last_commit(file_path: Path, repo_root: Path) -> Optional[int]:
    """Return days since last git commit touching *file_path*, or None."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(file_path)],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        import time

        timestamp = int(result.stdout.strip())
        return int((time.time() - timestamp) / 86400)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


# ---------------------------------------------------------------------------
# Skills without descriptions
# ---------------------------------------------------------------------------


def _check_skills_without_description(
    sr: ScanResult,
) -> Iterable[MaintenanceSuggestion]:
    for skill in sr.skills:
        if not skill.has_skill_md:
            yield MaintenanceSuggestion(
                category="incomplete_skill",
                description=(
                    f"Skill `{skill.name}` has no SKILL.md — "
                    f"agents cannot discover when to use it"
                ),
            )
        elif not skill.description:
            yield MaintenanceSuggestion(
                category="incomplete_skill",
                description=(f"Skill `{skill.name}` SKILL.md has no description line"),
            )


# ---------------------------------------------------------------------------
# Empty docs
# ---------------------------------------------------------------------------

_MIN_DOC_BYTES = 50


def _check_empty_docs(sr: ScanResult) -> Iterable[MaintenanceSuggestion]:
    for doc in sr.docs:
        if doc.size_bytes < _MIN_DOC_BYTES:
            yield MaintenanceSuggestion(
                category="empty_doc",
                description=(
                    f"`{doc.name}.md` appears to be an empty stub "
                    f"({doc.size_bytes} bytes)"
                ),
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_paths(content: str) -> list[str]:
    """Extract plausible file/directory paths from markdown content."""
    pattern = re.compile(r"(?:^|[\s`(])(\./)?(\w[\w\-.]*/[\w\-./]+\.\w+)", re.MULTILINE)
    paths = []
    for m in pattern.finditer(content):
        path = (m.group(1) or "") + m.group(2)
        if "://" not in path and not path.startswith("http"):
            paths.append(path)
    return paths


def _extract_doc_refs(guide_content: str) -> Iterable[str]:
    """Extract doc names referenced in a docs_guide.md.

    Matches both markdown links ``[text](name.md)`` and backtick references
    `` `name.md` ``.
    """
    seen = set()
    # Markdown links: [anything](something.md)
    for m in re.finditer(r"\[.*?\]\((\w[\w\-]*)\.md[^)]*\)", guide_content):
        name = m.group(1)
        if name != "docs_guide" and name not in seen:
            seen.add(name)
            yield name
    # Backtick references: `something.md`
    for m in re.finditer(r"`(\w[\w\-]*)\.md`", guide_content):
        name = m.group(1)
        if name != "docs_guide" and name not in seen:
            seen.add(name)
            yield name


def _suggest_guide_addition(doc_name: str) -> str:
    """Return a diff-like suggestion for adding a doc to docs_guide.md."""
    return f"+ | [{doc_name}.md]({doc_name}.md) | <!-- add description --> |"
