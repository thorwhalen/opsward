"""Tests for the skill reachability findings (opsward#35): shadowing, unmigrated bridges, listing budget."""

import os
import tempfile
from pathlib import Path

import pytest

from opsward.scan import default_claude_config_dir, scan
from opsward.score import _LISTING_BUDGET_CHARS, diagnose, skill_reachability_findings


def _skill(root: Path, rel: str, name: str, description: str = "Does the thing. Use when asked.") -> Path:
    d = root / rel / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n---\n\nBody.\n")
    return d


def _symlink(target, link) -> None:
    """Create a symlink, or skip the test where the platform refuses (Windows without the privilege)."""
    try:
        os.symlink(target, link, target_is_directory=True)  # Windows needs the kind stated
    except (OSError, NotImplementedError) as exc:  # pragma: no cover - platform dependent
        pytest.skip(f"symlinks not available here: {exc}")


def _skills_component(report):
    return next(c for c in report.scores if c.name == "Skills")


def test_scan_reads_the_global_scope_through_the_seam():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj, cfg = tmp / "proj", tmp / "cfg"
        _skill(proj, ".claude/skills", "lint")
        _skill(cfg, "skills", "lint")
        _skill(cfg, "skills", "other")
        sr = scan(proj, claude_config_dir=cfg)
        assert sorted(g.name for g in sr.global_skills) == ["lint", "other"]
        assert sr.global_skills_dir == cfg / "skills"
        assert scan(proj, claude_config_dir=None).global_skills == []
        assert scan(proj, claude_config_dir=tmp / "missing").global_skills == []


def test_default_config_dir_honours_the_env_var(monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/tmp/elsewhere")
    assert default_claude_config_dir() == Path("/tmp/elsewhere")
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    assert default_claude_config_dir() == Path.home() / ".claude"


def test_shadowed_project_skill_is_reported_unless_it_is_the_same_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj, cfg = tmp / "proj", tmp / "cfg"
        _skill(proj, ".claude/skills", "lint")
        _skill(cfg, "skills", "lint")
        sr = scan(proj, claude_config_dir=cfg)
        suggestions: list[str] = []
        notes = skill_reachability_findings(sr, suggestions=suggestions)
        assert any('Skill "lint": shadowed by the global skill' in n for n in notes)
        assert len(suggestions) == 1 and "lint" in suggestions[0]
        # a global link to this very project copy is not shadowing
        os.remove(cfg / "skills" / "lint" / "SKILL.md")
        os.rmdir(cfg / "skills" / "lint")
        _symlink(proj / ".claude" / "skills" / "lint", cfg / "skills" / "lint")
        sr = scan(proj, claude_config_dir=cfg)
        assert skill_reachability_findings(sr, suggestions=[]) == []


def test_unmigrated_bridge_is_reported_and_a_symlink_bridge_is_not():
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "proj"
        _skill(proj, ".claude/skills", "lint")
        _skill(proj, "skills", "lint")  # the canonical location also exists
        sr = scan(proj, claude_config_dir=None)
        (s,) = sr.skills
        assert not s.is_link and s.canonical_path.resolve() == (proj / "skills" / "lint").resolve()
        notes = skill_reachability_findings(sr, suggestions=[])
        assert any("is a real directory while `skills/lint` also exists" in n for n in notes)
        # pip-shipped layout: <pkg>/data/skills/<name>, where <pkg> is a package; tests/data is not one
        _skill(proj, "mypkg/data/skills", "fmt")
        (proj / "mypkg" / "__init__.py").write_text("")
        _skill(proj, ".claude/skills", "fmt")
        _skill(proj, "tests/data/skills", "fixture-only")
        _skill(proj, ".claude/skills", "fixture-only")
        sr = scan(proj, claude_config_dir=None)
        assert {s.name: bool(s.canonical_path) for s in sr.skills} == {"lint": True, "fmt": True, "fixture-only": False}
        # replace one real dir by the canonical bridge
        import shutil

        shutil.rmtree(proj / ".claude" / "skills" / "lint")
        # an absolute target: a relative one with "/" separators is not followed on Windows
        _symlink(proj / "skills" / "lint", proj / ".claude" / "skills" / "lint")
        sr = scan(proj, claude_config_dir=None)
        lint = next(s for s in sr.skills if s.name == "lint")
        assert lint.is_link and lint.canonical_path is None


def test_global_dir_without_skill_md_does_not_shadow():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj, cfg = tmp / "proj", tmp / "cfg"
        _skill(proj, ".claude/skills", "lint")
        (cfg / "skills" / "lint").mkdir(parents=True)  # a bare directory: the host loads nothing from it
        assert skill_reachability_findings(scan(proj, claude_config_dir=cfg), suggestions=[]) == []


def test_listing_chars_follow_the_host_rules():
    from opsward.base import SkillInfo
    from opsward.score import _LISTING_ENTRY_DESC_CAP, _listing_chars

    long = "x" * 1000
    capped = SkillInfo(name="a", path=Path("/a"), has_skill_md=True, description=long, frontmatter={"when_to_use": long})
    hidden = SkillInfo(name="b", path=Path("/b"), has_skill_md=True, description=long, frontmatter={"disable-model-invocation": "true"})
    no_md = SkillInfo(name="c", path=Path("/c"), has_skill_md=False, description=long)
    assert _listing_chars([capped]) == len("a") + 3 + _LISTING_ENTRY_DESC_CAP + 1
    assert _listing_chars([hidden, no_md]) == 0


def test_listing_budget_note_only_when_global_plus_project_exceeds_it():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj, cfg = tmp / "proj", tmp / "cfg"
        _skill(proj, ".claude/skills", "lint")
        _skill(cfg, "skills", "small", "Short.")
        sr = scan(proj, claude_config_dir=cfg)
        assert not [n for n in skill_reachability_findings(sr, suggestions=[]) if n.startswith("Listing budget")]
        long = "x" * 1000
        for i in range(_LISTING_BUDGET_CHARS // 1000 + 1):
            _skill(cfg, "skills", f"big-{i}", long)
        sr = scan(proj, claude_config_dir=cfg)
        suggestions: list[str] = []
        (note,) = [n for n in skill_reachability_findings(sr, suggestions=suggestions) if n.startswith("Listing budget")]
        assert "this project's 1 skill(s) are at risk" in note and "1M-token window" in note and suggestions
        # the budget is a seam
        assert not skill_reachability_findings(sr, suggestions=[], listing_budget_chars=10**9)


def test_findings_are_notes_not_points():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        proj, cfg = tmp / "proj", tmp / "cfg"
        _skill(proj, ".claude/skills", "lint")
        clean = _skills_component(diagnose(scan(proj, claude_config_dir=None)))
        _skill(cfg, "skills", "lint")
        shadowed = _skills_component(diagnose(scan(proj, claude_config_dir=cfg)))
        assert shadowed.score == clean.score
        assert any("shadowed" in n for n in shadowed.notes) and not any("shadowed" in n for n in clean.notes)
