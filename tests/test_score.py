"""Tests for opsward.score."""

from pathlib import Path

import pytest

from opsward.base import AgentInfo, ProjectType, RuleInfo, ScanResult
from opsward.scan import scan
from opsward.score import diagnose

FIXTURES = Path(__file__).parent / "fixtures"


def _setup_score(scan_result: ScanResult) -> int:
    """The 'Setup (rules/agents/hooks)' component score for a ScanResult."""
    report = diagnose(scan_result)
    return next(
        s.score for s in report.scores if s.name == "Setup (rules/agents/hooks)"
    )


# A structurally valid Claude Code hooks config (string matcher, command hook).
_VALID_HOOKS = {
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [{"type": "command", "command": "echo formatted"}],
            }
        ]
    }
}


@pytest.fixture
def python_scan():
    return scan(FIXTURES / "python_project")


@pytest.fixture
def bare_scan():
    return scan(FIXTURES / "bare_project")


@pytest.fixture
def jsts_scan():
    return scan(FIXTURES / "jsts_project")


# -- Basic report structure --


def test_diagnose_returns_report(python_scan):
    report = diagnose(python_scan)
    assert report.project_type is ProjectType.python
    assert len(report.scores) == 5  # 5 components


def test_score_names(python_scan):
    report = diagnose(python_scan)
    names = {s.name for s in report.scores}
    assert names == {
        "CLAUDE.md quality",
        "Documentation",
        "Skills",
        "Setup (rules/agents/hooks)",
        "Cross-references",
    }


# -- Scores are bounded --


def test_all_scores_bounded(python_scan):
    report = diagnose(python_scan)
    for cs in report.scores:
        assert 0 <= cs.score <= cs.max_score, f"{cs.name}: {cs.score}"


def test_overall_bounded(python_scan):
    report = diagnose(python_scan)
    assert 0 <= report.overall_score <= 100


# -- Bare project gets low scores --


def test_bare_project_low_score(bare_scan):
    report = diagnose(bare_scan)
    assert report.overall_score < 30
    assert report.grade == "F"


def test_bare_project_missing_items(bare_scan):
    report = diagnose(bare_scan)
    assert "CLAUDE.md" in report.missing_items


# -- Python project gets reasonable scores --


def test_python_project_has_claude_md_score(python_scan):
    report = diagnose(python_scan)
    claude_score = next(s for s in report.scores if s.name == "CLAUDE.md quality")
    assert claude_score.score > 0, "Should get some points for having CLAUDE.md"


def test_python_project_skills_scored(python_scan):
    report = diagnose(python_scan)
    skills_score = next(s for s in report.scores if s.name == "Skills")
    assert skills_score.score > 0, "Should get points for having a skill with SKILL.md"


def test_python_project_setup_scored(python_scan):
    report = diagnose(python_scan)
    setup_score = next(
        s for s in report.scores if s.name == "Setup (rules/agents/hooks)"
    )
    assert setup_score.score > 0, "Has rules, agents, and hooks"


def test_python_project_docs_scored(python_scan):
    report = diagnose(python_scan)
    doc_score = next(s for s in report.scores if s.name == "Documentation")
    assert doc_score.score > 0, "Has docs_guide.md and architecture.md"


# -- Grade boundaries --


def test_grade_boundaries():
    for weighted, expected in [(95, "A"), (80, "B"), (70, "C"), (60, "D"), (10, "F")]:
        r = ScanResult(project_root=Path("/tmp/x"))
        report = diagnose(r)
        report.weighted_score = float(weighted)
        assert report.grade == expected


# -- Validity-aware Setup scoring (issue #6) --


def test_setup_section_maxes_sum_to_100():
    """The Setup point budget (rules + agents + hooks) must total 100."""
    from opsward.score import _SETUP_AGENTS_MAX, _SETUP_HOOKS_MAX, _SETUP_RULES_MAX

    assert _SETUP_RULES_MAX + _SETUP_AGENTS_MAX + _SETUP_HOOKS_MAX == 100


def test_valid_hooks_earns_full_hook_credit():
    """A structurally valid hooks.json earns the full 30-point hooks slice."""
    r = ScanResult(project_root=Path("/tmp/x"), hooks_config=_VALID_HOOKS)
    assert _setup_score(r) == 30


def test_malformed_dict_matcher_hooks_loses_credit():
    """A dict `matcher` (the bug from #3) must NOT earn full hook credit."""
    bad = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": {"tool_name": "Edit"},  # invalid: must be a string
                    "hooks": [{"type": "command", "command": "echo hi"}],
                }
            ]
        }
    }
    r = ScanResult(project_root=Path("/tmp/x"), hooks_config=bad)
    assert _setup_score(r) < 30


def test_hooks_without_hooks_key_loses_credit():
    """A config with no top-level `hooks` key is not a valid hooks file."""
    r = ScanResult(project_root=Path("/tmp/x"), hooks_config={"pre_commit": ["x"]})
    assert _setup_score(r) < 30


def test_malformed_hooks_emit_suggestion():
    """A present-but-malformed hooks config produces an actionable suggestion."""
    bad = {"hooks": {"PostToolUse": [{"matcher": {"x": "y"}, "hooks": []}]}}
    r = ScanResult(project_root=Path("/tmp/x"), hooks_config=bad)
    report = diagnose(r)
    assert any("hook" in s.lower() for s in report.suggestions)


def test_stub_rule_scores_less_than_real_rule():
    """A bare-stub rule earns less Setup credit than a substantive one."""
    stub = ScanResult(
        project_root=Path("/tmp/x"),
        rules=[RuleInfo(name="x", path=Path("/tmp/x/x.md"), content="# x\n")],
    )
    real = ScanResult(
        project_root=Path("/tmp/x"),
        rules=[
            RuleInfo(
                name="x",
                path=Path("/tmp/x/x.md"),
                content="# Rule\n\nNever use print() for logging; use the logging module.",
            )
        ],
    )
    assert _setup_score(stub) < _setup_score(real)


def test_setup_score_bounded_with_everything():
    """Setup stays within [0, 100] even with many valid artifacts."""
    r = ScanResult(
        project_root=Path("/tmp/x"),
        rules=[
            RuleInfo(name=f"r{i}", path=Path("/tmp/x"), content="A real rule body." * 3)
            for i in range(5)
        ],
        agents=[
            AgentInfo(name=f"a{i}", path=Path("/tmp/x"), description="Does a thing.")
            for i in range(5)
        ],
        hooks_config=_VALID_HOOKS,
    )
    assert 0 <= _setup_score(r) <= 100


# -- Pure function invariant --


def test_diagnose_is_pure(python_scan):
    r1 = diagnose(python_scan)
    r2 = diagnose(python_scan)
    assert r1.overall_score == r2.overall_score
    assert len(r1.scores) == len(r2.scores)
    for s1, s2 in zip(r1.scores, r2.scores):
        assert s1.score == s2.score
