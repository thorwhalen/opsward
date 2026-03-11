"""Tests for opsward.score."""

from pathlib import Path

import pytest

from opsward.base import ProjectType, ScanResult
from opsward.scan import scan
from opsward.score import diagnose

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture
def python_scan():
    return scan(FIXTURES / 'python_project')


@pytest.fixture
def bare_scan():
    return scan(FIXTURES / 'bare_project')


@pytest.fixture
def jsts_scan():
    return scan(FIXTURES / 'jsts_project')


# -- Basic report structure --


def test_diagnose_returns_report(python_scan):
    report = diagnose(python_scan)
    assert report.project_type is ProjectType.python
    assert len(report.scores) == 5  # 5 components


def test_score_names(python_scan):
    report = diagnose(python_scan)
    names = {s.name for s in report.scores}
    assert names == {
        'CLAUDE.md quality',
        'Documentation',
        'Skills',
        'Setup (rules/agents/hooks)',
        'Cross-references',
    }


# -- Scores are bounded --


def test_all_scores_bounded(python_scan):
    report = diagnose(python_scan)
    for cs in report.scores:
        assert 0 <= cs.score <= cs.max_score, f'{cs.name}: {cs.score}'


def test_overall_bounded(python_scan):
    report = diagnose(python_scan)
    assert 0 <= report.overall_score <= 100


# -- Bare project gets low scores --


def test_bare_project_low_score(bare_scan):
    report = diagnose(bare_scan)
    assert report.overall_score < 30
    assert report.grade == 'F'


def test_bare_project_missing_items(bare_scan):
    report = diagnose(bare_scan)
    assert 'CLAUDE.md' in report.missing_items


# -- Python project gets reasonable scores --


def test_python_project_has_claude_md_score(python_scan):
    report = diagnose(python_scan)
    claude_score = next(s for s in report.scores if s.name == 'CLAUDE.md quality')
    assert claude_score.score > 0, 'Should get some points for having CLAUDE.md'


def test_python_project_skills_scored(python_scan):
    report = diagnose(python_scan)
    skills_score = next(s for s in report.scores if s.name == 'Skills')
    assert skills_score.score > 0, 'Should get points for having a skill with SKILL.md'


def test_python_project_setup_scored(python_scan):
    report = diagnose(python_scan)
    setup_score = next(
        s for s in report.scores if s.name == 'Setup (rules/agents/hooks)'
    )
    assert setup_score.score > 0, 'Has rules, agents, and hooks'


def test_python_project_docs_scored(python_scan):
    report = diagnose(python_scan)
    doc_score = next(s for s in report.scores if s.name == 'Documentation')
    assert doc_score.score > 0, 'Has docs_guide.md and architecture.md'


# -- Grade boundaries --


def test_grade_boundaries():
    for weighted, expected in [(95, 'A'), (80, 'B'), (70, 'C'), (60, 'D'), (10, 'F')]:
        r = ScanResult(project_root=Path('/tmp/x'))
        report = diagnose(r)
        report.weighted_score = float(weighted)
        assert report.grade == expected


# -- Pure function invariant --


def test_diagnose_is_pure(python_scan):
    r1 = diagnose(python_scan)
    r2 = diagnose(python_scan)
    assert r1.overall_score == r2.overall_score
    assert len(r1.scores) == len(r2.scores)
    for s1, s2 in zip(r1.scores, r2.scores):
        assert s1.score == s2.score
