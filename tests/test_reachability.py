"""Tests for the skill reachability findings (opsward#35): shadowing, unmigrated bridges, listing budget."""

import os
import tempfile
from pathlib import Path

from opsward.scan import default_claude_config_dir, scan
from opsward.score import _LISTING_BUDGET_CHARS, diagnose, skill_reachability_findings


def _skill(root: Path, rel: str, name: str, description: str = "Does the thing. Use when asked.") -> Path:
    d = root / rel / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n---\n\nBody.\n")
    return d


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
    monkeypatch.delenv("CLAUDE_CONFIG_DIR")
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
        os.symlink(proj / ".claude" / "skills" / "lint", cfg / "skills" / "lint")
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
        # pip-shipped layout: <pkg>/data/skills/<name>
        _skill(proj, "mypkg/data/skills", "fmt")
        _skill(proj, ".claude/skills", "fmt")
        sr = scan(proj, claude_config_dir=None)
        assert {s.name: bool(s.canonical_path) for s in sr.skills} == {"lint": True, "fmt": True}
        # replace one real dir by the canonical bridge
        import shutil

        shutil.rmtree(proj / ".claude" / "skills" / "lint")
        os.symlink("../../skills/lint", proj / ".claude" / "skills" / "lint")
        sr = scan(proj, claude_config_dir=None)
        lint = next(s for s in sr.skills if s.name == "lint")
        assert lint.is_link and lint.canonical_path is None


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
        assert "this project's 1 skill(s) are at risk" in note and suggestions


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
