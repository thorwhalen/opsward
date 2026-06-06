"""Tests for opsward.score."""

from pathlib import Path

import pytest

from opsward.base import (
    AgentInfo,
    ProjectType,
    RuleInfo,
    ScanResult,
    SkillInfo,
    DocSpec,
)
from opsward.scan import scan
from opsward.score import diagnose

FIXTURES = Path(__file__).parent / "fixtures"

# The marker every explainable "why → how to fix" note carries.
FIX_ARROW = "→"


def _setup_score(scan_result: ScanResult) -> int:
    """The 'Setup (rules/agents/hooks)' component score for a ScanResult."""
    report = diagnose(scan_result)
    return next(
        s.score for s in report.scores if s.name == "Setup (rules/agents/hooks)"
    )


def _component(scan_result: ScanResult, name: str):
    """The ComponentScore with the given name for a ScanResult."""
    report = diagnose(scan_result)
    return next(s for s in report.scores if s.name == name)


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


# -- Explainable scores: every lost point says why → how to fix (issue #8) --


def _claude(content: str, root: Path = Path("/tmp/x")) -> ScanResult:
    return ScanResult(project_root=root, claude_md_content=content)


def test_weak_commands_emits_fix_note():
    """A CLAUDE.md with a code block but few command keywords explains the fix."""
    content = "# Project\n\n```\npython foo.py\n```\n\nUse run to start.\n"
    cs = _component(_claude(content), "CLAUDE.md quality")
    cmd_notes = [n for n in cs.notes if n.lower().startswith("commands")]
    assert cmd_notes, "weak commands dimension should leave a note"
    assert any(FIX_ARROW in n for n in cmd_notes)


def test_paths_only_architecture_emits_fix_note():
    """An architecture section with paths but no descriptions explains the fix."""
    content = "# Project\n\n## Architecture\n\n- src/foo/bar.py\n- src/foo/baz.py\n"
    cs = _component(_claude(content), "CLAUDE.md quality")
    arch_notes = [n for n in cs.notes if n.lower().startswith("architecture")]
    assert arch_notes, "paths-only architecture should leave a note"
    assert any(FIX_ARROW in n for n in arch_notes)


def test_low_specificity_conventions_emits_fix_note():
    """A vague conventions section (no tools/extensions) explains the fix."""
    content = "# Project\n\n## Conventions\n\nBe consistent and clean and tidy.\n"
    cs = _component(_claude(content), "CLAUDE.md quality")
    conv_notes = [n for n in cs.notes if n.lower().startswith("conventions")]
    assert conv_notes, "low-specificity conventions should leave a note"
    assert any(FIX_ARROW in n for n in conv_notes)


def test_vague_actionability_emits_fix_note():
    """Many vague instructions (appropriate/as needed) explains the fix."""
    content = (
        "# Project\n\n"
        "Use the appropriate tool as needed.\n"
        "Consider refactoring if possible.\n"
        "Handle errors when necessary.\n"
    )
    cs = _component(_claude(content), "CLAUDE.md quality")
    act_notes = [n for n in cs.notes if n.lower().startswith("actionability")]
    assert act_notes, "vague actionability should leave a note"
    assert any(FIX_ARROW in n for n in act_notes)


def test_broken_currency_emits_fix_note(tmp_path):
    """Broken path references explain how to fix (update/remove stale paths)."""
    content = "# Project\n\nSee src/missing/gone.py and docs/absent.md for details.\n"
    cs = _component(_claude(content, root=tmp_path), "CLAUDE.md quality")
    cur_notes = [n for n in cs.notes if n.lower().startswith("currency")]
    assert cur_notes, "broken currency should leave a note"
    assert any(FIX_ARROW in n for n in cur_notes)


def test_skill_missing_description_emits_fix_note():
    """A skill with SKILL.md but no description explains the fix."""
    skill = SkillInfo(
        name="my-skill",
        path=Path("/tmp/x/my-skill"),
        has_skill_md=True,
        description="",
        frontmatter={"name": "my-skill"},
        line_count=20,
    )
    cs = _component(ScanResult(project_root=Path("/tmp/x"), skills=[skill]), "Skills")
    desc_notes = [n for n in cs.notes if "description" in n.lower()]
    assert desc_notes, "missing skill description should leave a note"
    assert any(FIX_ARROW in n for n in desc_notes)


def test_stub_doc_emits_fix_note():
    """An empty-stub doc explains the fix (flesh out or remove)."""
    sr = ScanResult(
        project_root=Path("/tmp/x"),
        has_docs_guide=True,
        docs=[
            DocSpec(
                name="architecture", path=Path("/tmp/x/architecture.md"), size_bytes=500
            ),
            DocSpec(
                name="conventions", path=Path("/tmp/x/conventions.md"), size_bytes=5
            ),
        ],
    )
    cs = _component(sr, "Documentation")
    stub_notes = [n for n in cs.notes if "stub" in n.lower()]
    assert stub_notes, "stub docs should leave a note"
    assert any(FIX_ARROW in n for n in stub_notes)


def test_weak_claude_md_all_notes_carry_a_fix():
    """A deliberately weak (but present) CLAUDE.md: every note carries a fix arrow."""
    content = (
        "# Project\n\n"
        "## Architecture\n\n- src/a/b.py\n\n"
        "## Conventions\n\nBe nice.\n\n"
        "Use the appropriate approach as needed.\n"
    )
    cs = _component(_claude(content), "CLAUDE.md quality")
    assert cs.notes, "a weak CLAUDE.md should produce notes"
    assert all(FIX_ARROW in n for n in cs.notes), cs.notes


def test_explainability_does_not_change_scores():
    """Enriching notes is explanation-only — the numeric dimension values stand.

    Pins the per-dimension outcome for a known-weak CLAUDE.md so an accidental
    rebalance while editing the explanation text is caught:
    commands 0 + architecture 10 + conventions 5 + conciseness 15 +
    currency 3 + actionability 10 = 43.
    """
    content = (
        "# Project\n\n"
        "## Architecture\n\n- src/a/b.py\n\n"
        "## Conventions\n\nBe nice.\n\n"
        "Use the appropriate approach as needed.\n"
    )
    cs = _component(_claude(content), "CLAUDE.md quality")
    assert cs.score == 43


def _perfect_skill(name: str) -> SkillInfo:
    return SkillInfo(
        name=name,
        path=Path(f"/tmp/x/{name}"),
        has_skill_md=True,
        description="Does a thing.",
        frontmatter={"name": name, "description": "Does a thing."},
        line_count=30,
    )


def test_perfect_skills_score_full_100():
    """N fully-compliant skills score a full 100 (no integer-rounding cap)."""
    for n in (1, 3, 7, 8, 13):
        sr = ScanResult(
            project_root=Path("/tmp/x"),
            skills=[_perfect_skill(f"skill-{i}") for i in range(n)],
        )
        cs = _component(sr, "Skills")
        assert cs.score == 100, f"{n} perfect skills should score 100, got {cs.score}"
        assert cs.notes == [], f"{n} perfect skills should have no notes"


def test_skill_missing_description_partial_credit():
    """No description forfeits both the description (30) and spec (30) slices → 40."""
    skill = SkillInfo(
        name="s",
        path=Path("/tmp/x/s"),
        has_skill_md=True,
        description="",
        frontmatter={"name": "s"},
        line_count=20,
    )
    cs = _component(ScanResult(project_root=Path("/tmp/x"), skills=[skill]), "Skills")
    assert cs.score == 40


def test_full_architecture_section_reaches_max():
    """A path+description architecture section earns the full _ARCH_MAX (no silent cap)."""
    from opsward.score import _ARCH_MAX, _dim_architecture

    section = (
        "# Project\n\n## Architecture\n\n"
        "- `opsward/scan.py` — read-only filesystem scanning\n"
        "- `opsward/score.py` — pure scoring functions\n"
    )
    notes: list[str] = []
    assert _dim_architecture(section, notes) == _ARCH_MAX


def test_midlength_claude_md_explains_conciseness():
    """An 81-200 line CLAUDE.md gets a (gentle) conciseness note, not a silent loss."""
    content = "# Project\n\n" + "\n".join(f"- point {i}" for i in range(120))
    cs = _component(_claude(content), "CLAUDE.md quality")
    conc_notes = [n for n in cs.notes if n.lower().startswith("conciseness")]
    assert conc_notes
    assert any(FIX_ARROW in n for n in conc_notes)


def test_skill_spec_violation_only_partial_credit():
    """A described skill that violates only the spec earns 70 (40 + 30)."""
    skill = SkillInfo(
        name="Bad_Name",  # uppercase + underscore violates the name pattern
        path=Path("/tmp/x/Bad_Name"),
        has_skill_md=True,
        description="Does a thing.",
        frontmatter={"name": "Bad_Name", "description": "Does a thing."},
        line_count=20,
    )
    cs = _component(ScanResult(project_root=Path("/tmp/x"), skills=[skill]), "Skills")
    assert cs.score == 70


# -- Pure function invariant --


def test_diagnose_is_pure(python_scan):
    r1 = diagnose(python_scan)
    r2 = diagnose(python_scan)
    assert r1.overall_score == r2.overall_score
    assert len(r1.scores) == len(r2.scores)
    for s1, s2 in zip(r1.scores, r2.scores):
        assert s1.score == s2.score
