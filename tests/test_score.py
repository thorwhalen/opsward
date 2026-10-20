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
    assert len(report.scores) == 6  # 6 components


def test_score_names(python_scan):
    report = diagnose(python_scan)
    names = {s.name for s in report.scores}
    assert names == {
        "CLAUDE.md quality",
        "Documentation",
        "Skills",
        "Setup (rules/agents/hooks)",
        "Cross-references",
        "Portability",
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


# ---------------------------------------------------------------------------
# CLAUDE.md size signal (thorwhalen/opsward#30)
# ---------------------------------------------------------------------------


def _sized_claude_md(total_chars: int) -> str:
    """A short-line CLAUDE.md of roughly *total_chars*, three unequal H2 sections + a small one."""
    line = "narrative line " * 6 + "\n"
    sections = {"Big": 5, "Medium": 3, "Smaller": 2, "Tiny": 0}
    unit = max(1, (total_chars - 200) // (10 * len(line)))
    body = "# P\n\n"
    for title, weight in sections.items():
        body += f"## {title}\n" + line * (unit * weight + 1)
    return body


def _component_with(scan_result: ScanResult, **kwargs):
    """The CLAUDE.md quality ComponentScore with diagnose() keyword overrides."""
    report = diagnose(scan_result, **kwargs)
    return next(s for s in report.scores if s.name == "CLAUDE.md quality")


def _conciseness_note(cs) -> str:
    return next((n for n in cs.notes if n.startswith("Conciseness: CLAUDE.md is")), "")


def test_oversized_claude_md_deducts_and_names_longest_sections():
    content = _sized_claude_md(30_000)
    assert len(content) > 10_000
    cs = _component(_claude(content), "CLAUDE.md quality")
    note = _conciseness_note(cs)
    assert note and FIX_ARROW in note
    # the three longest sections, longest first, each with its target docs path
    assert note.index('"Big"') < note.index('"Medium"') < note.index('"Smaller"')
    assert '"Tiny"' not in note
    assert "`misc/docs/big.md`" in note
    # points were actually lost relative to the same file with the check disabled
    off = _component_with(_claude(content), claude_md_max_chars=10**9)
    assert cs.score < off.score


def test_small_claude_md_loses_nothing():
    content = _sized_claude_md(7_000)
    assert len(content) < 10_000
    cs = _component(_claude(content), "CLAUDE.md quality")
    assert not _conciseness_note(cs)
    off = _component_with(_claude(content), claude_md_max_chars=10**9)
    assert cs.score == off.score


def test_size_threshold_is_keyword_argument_with_both_sides():
    content = _sized_claude_md(7_000)
    low = _component_with(_claude(content), claude_md_max_chars=5_000)
    high = _component_with(_claude(content), claude_md_max_chars=10_000)
    assert _conciseness_note(low) and not _conciseness_note(high)
    assert low.score < high.score


def test_size_penalty_is_proportional_to_overrun():
    from opsward.score import claude_md_size_overrun

    small = claude_md_size_overrun("x" * 11_000, max_chars=10_000)
    big = claude_md_size_overrun("x" * 30_000, max_chars=10_000)
    assert 1 <= small.penalty < big.penalty


def test_size_docs_dir_follows_project_type_and_existing_docs():
    content = _sized_claude_md(30_000)
    js = ScanResult(
        project_root=Path("/tmp/x"),
        project_type=ProjectType.jsts,
        claude_md_content=content,
    )
    assert "`docs/big.md`" in _conciseness_note(_component(js, "CLAUDE.md quality"))


def test_size_ignores_headings_inside_code_fences():
    from opsward.score import claude_md_size_overrun

    content = "## Real\n```\n## Fake\n```\n" + "x" * 100
    o = claude_md_size_overrun(content, max_chars=10)
    assert [t for t, _ in o.sections] == ["Real"]


def test_size_duplicate_h2_titles_are_merged():
    from opsward.score import claude_md_size_overrun

    content = "## Setup\n" + "a" * 50 + "\n## Other\n" + "b" * 40 + "\n## Setup\n" + "c" * 50 + "\n"
    o = claude_md_size_overrun(content, max_chars=10)
    titles = [t for t, _ in o.sections]
    assert titles == ["Setup", "Other"]
    assert o.sections[0][1] > 100


def test_size_without_h2_has_no_dangling_section_list():
    from opsward.score import claude_md_size_overrun

    o = claude_md_size_overrun("x" * 50, max_chars=10)
    assert o.sections == ()
    assert "Longest sections" not in o.describe()


def test_size_note_reports_points_actually_lost():
    # >500 lines: line-count rule already leaves only 2 points, so at most 2 can go
    content = "# P\n\n## Big\n" + "x\n" * 12000
    cs = _component(_claude(content), "CLAUDE.md quality")
    assert "(-2)" in _conciseness_note(cs)


def test_size_rejects_non_positive_threshold():
    from opsward.score import claude_md_size_overrun

    with pytest.raises(ValueError):
        claude_md_size_overrun("x", max_chars=0)


def test_size_fence_rules_and_heading_titles():
    from opsward.score import claude_md_size_overrun

    content = (
        "## C#\n````\n```\n## Fake\n```\n````\n"
        "~~~\n## AlsoFake\n```\n## StillFake\n~~~\n"
        "## Real ##\n" + "x" * 100
    )
    o = claude_md_size_overrun(content, max_chars=10)
    assert sorted(t for t, _ in o.sections) == ["C#", "Real"]


# opsward#32: setext (underlined) H2 headings name sections too.
def test_size_names_setext_h2_sections():
    from opsward.score import _h2_section_sizes, claude_md_size_overrun

    content = (
        "Intro paragraph.\n\n"
        "Setup\n-----\n" + "a" * 50 + "\n\n"
        "## Atx\n" + "b" * 20 + "\n\n"
        "Usage\n---\n" + "c" * 30 + "\n"
    )
    o = claude_md_size_overrun(content, max_chars=10)
    assert [t for t, _ in o.sections] == ["Setup", "Usage", "Atx"]
    sizes = dict(_h2_section_sizes(content))
    # every char from the first heading on belongs to exactly one section
    assert sum(sizes.values()) == len(content) - len("Intro paragraph.\n\n")


def test_size_dashes_that_are_not_setext_underlines():
    from opsward.score import _h2_section_sizes

    content = (
        "---\nname: x\n---\n"  # front matter: its closing --- is no underline
        "## Real\n"
        "- a list item\n---\n"  # a list item is no setext title
        "text\n\n---\n"  # after a blank line, --- is a thematic break
        "```\nFake\n---\n```\n"  # nor inside a fence
        "    indented code\n---\n"  # nor indented code
    )
    assert [t for t, _ in _h2_section_sizes(content)] == ["Real"]


def test_a_leading_rule_is_not_front_matter():
    """opsward#32 review: a doc opening with a decorative rule kept its ATX H2s."""
    from opsward.score import _h2_section_sizes

    content = "---\n\n## A\nxxx\n\n---\n\n## B\nyy\n"
    assert [t for t, _ in _h2_section_sizes(content)] == ["A", "B"]


def test_a_multi_line_paragraph_is_one_setext_title():
    from opsward.score import _h2_section_sizes

    content = "## A\nx\n\nLine one\nLine two\n---\nbody\n"
    sizes = _h2_section_sizes(content)
    assert [t for t, _ in sizes] == ["A", "Line one Line two"]
    assert sizes[0][1] == len("## A\nx\n\n")


@pytest.mark.parametrize(
    "block", ["<div>\nhi\n</div>\n", "<!-- c -->\n", "[foo]: /url\n", "\tcode\n"]
)
def test_html_link_definitions_and_tab_code_are_no_setext_titles(block):
    from opsward.score import _h2_section_sizes

    assert [t for t, _ in _h2_section_sizes("## Real\n" + block + "---\n")] == ["Real"]


def test_duplicate_agent_names_count_once_and_are_reported():
    import tempfile
    from pathlib import Path

    from opsward.scan import scan
    from opsward.score import diagnose

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        agents = root / ".claude" / "agents"
        (agents / "a").mkdir(parents=True)
        (agents / "b").mkdir()
        for d in ("a", "b"):
            (agents / d / "x.md").write_text("---\nname: same\ndescription: One agent, two files.\n---\n")
        report = diagnose(scan(root, claude_config_dir=None))
        setup = next(c for c in report.scores if c.name.startswith("Setup"))
        assert any('"same": defined 2 times' in n for n in setup.notes)
        assert any("duplicate agent definitions" in s for s in report.suggestions)
        (agents / "b" / "x.md").unlink()
        single = next(c for c in diagnose(scan(root, claude_config_dir=None)).scores if c.name.startswith("Setup"))
        assert single.score == setup.score  # the second file earned nothing


def test_overall_weights_sum_to_one_and_name_every_component():
    from opsward.score import _OVERALL_WEIGHTS

    assert abs(sum(_OVERALL_WEIGHTS.values()) - 1.0) < 1e-9
    report = diagnose(ScanResult(project_root=Path("/tmp/empty")))
    assert [s.name for s in report.scores] == list(_OVERALL_WEIGHTS)


def test_a_weighted_score_of_zero_is_not_replaced_by_the_average():
    report = diagnose(ScanResult(project_root=Path("/tmp/empty")))
    assert report.weighted_score == 0 and report.overall_score == 0
