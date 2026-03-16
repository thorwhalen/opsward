"""Tests for roadmap features: spec validation, AGENTS.md, hooks, recommend, monorepo."""

import json
import tempfile
from pathlib import Path

import pytest

from opsward.base import ProjectType, ScanResult, SkillInfo
from opsward.generate import generate
from opsward.recommend import recommend_skills
from opsward.scan import scan, _parse_frontmatter
from opsward.score import diagnose, validate_skill_spec

FIXTURES = Path(__file__).parent / 'fixtures'


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_simple_frontmatter(self):
        text = "---\nname: my-skill\ndescription: Does things.\n---\nBody."
        fm = _parse_frontmatter(text)
        assert fm["name"] == "my-skill"
        assert fm["description"] == "Does things."

    def test_no_frontmatter(self):
        assert _parse_frontmatter("# Just markdown") == {}

    def test_nested_metadata(self):
        text = "---\nname: x\nmetadata:\n  author: acme\n  version: 1.0\n---\n"
        fm = _parse_frontmatter(text)
        assert fm["name"] == "x"
        assert isinstance(fm["metadata"], dict)
        assert fm["metadata"]["author"] == "acme"

    def test_quoted_values(self):
        text = '---\nname: "my-skill"\ndescription: \'Does things.\'\n---\n'
        fm = _parse_frontmatter(text)
        assert fm["name"] == "my-skill"
        assert fm["description"] == "Does things."


# ---------------------------------------------------------------------------
# agentskills.io spec validation
# ---------------------------------------------------------------------------


class TestSkillSpecValidation:
    def _make_skill(self, **overrides):
        defaults = dict(
            name="good-skill",
            path=Path("."),
            has_skill_md=True,
            frontmatter={"name": "good-skill", "description": "Does X when Y."},
            line_count=50,
        )
        defaults.update(overrides)
        return SkillInfo(**defaults)

    def test_valid_skill(self):
        assert validate_skill_spec(self._make_skill()) == []

    def test_missing_name(self):
        s = self._make_skill(frontmatter={"description": "OK."})
        v = validate_skill_spec(s)
        assert any("name" in x for x in v)

    def test_name_mismatch(self):
        s = self._make_skill(
            frontmatter={"name": "wrong-name", "description": "OK."}
        )
        v = validate_skill_spec(s)
        assert any("must match directory" in x for x in v)

    def test_name_uppercase(self):
        s = self._make_skill(
            name="Bad-Skill",
            frontmatter={"name": "Bad-Skill", "description": "OK."},
        )
        v = validate_skill_spec(s)
        assert any("lowercase" in x for x in v)

    def test_name_consecutive_hyphens(self):
        s = self._make_skill(
            name="bad--skill",
            frontmatter={"name": "bad--skill", "description": "OK."},
        )
        v = validate_skill_spec(s)
        assert any("consecutive" in x for x in v)

    def test_missing_description(self):
        s = self._make_skill(frontmatter={"name": "good-skill"})
        v = validate_skill_spec(s)
        assert any("description" in x for x in v)

    def test_too_many_lines(self):
        s = self._make_skill(line_count=600)
        v = validate_skill_spec(s)
        assert any("600 lines" in x for x in v)

    def test_no_skill_md(self):
        s = self._make_skill(has_skill_md=False)
        assert validate_skill_spec(s) == []


# ---------------------------------------------------------------------------
# AGENTS.md generation
# ---------------------------------------------------------------------------


class TestAgentsMdGeneration:
    def test_agents_md_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = ScanResult(project_root=Path(tmpdir))
            files = generate(sr, agents_md=True)
            names = {f.target_path.name for f in files}
            assert "AGENTS.md" in names

    def test_agents_md_not_generated_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = ScanResult(project_root=Path(tmpdir))
            files = generate(sr)
            names = {f.target_path.name for f in files}
            assert "AGENTS.md" not in names

    def test_agents_md_skipped_if_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "AGENTS.md").write_text("# Existing")
            sr = scan(root)
            files = generate(sr, agents_md=True)
            names = {f.target_path.name for f in files}
            assert "AGENTS.md" not in names

    def test_agents_md_has_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text('[project]\nname = "testproj"\n')
            sr = scan(root)
            files = generate(sr, agents_md=True)
            agents_file = next(f for f in files if f.target_path.name == "AGENTS.md")
            assert "testproj" in agents_file.content
            assert "## Build & Test" in agents_file.content


# ---------------------------------------------------------------------------
# Hook generation
# ---------------------------------------------------------------------------


class TestHookGeneration:
    def test_hooks_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = ScanResult(project_root=Path(tmpdir))
            files = generate(sr, hooks=True)
            hook_files = [f for f in files if "hooks.json" in f.target_path.name]
            assert len(hook_files) == 1

    def test_hooks_not_generated_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = ScanResult(project_root=Path(tmpdir))
            files = generate(sr)
            hook_files = [f for f in files if "hooks.json" in f.target_path.name]
            assert len(hook_files) == 0

    def test_hooks_json_is_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = ScanResult(project_root=Path(tmpdir))
            files = generate(sr, hooks=True)
            hook_file = next(f for f in files if "hooks.json" in f.target_path.name)
            data = json.loads(hook_file.content)
            assert "hooks" in data
            assert "PostToolUse" in data["hooks"]
            assert "SessionStart" in data["hooks"]

    def test_hooks_skipped_if_already_configured(self):
        sr = ScanResult(
            project_root=Path("/tmp/x"),
            hooks_config={"hooks": {}},
        )
        files = generate(sr, hooks=True)
        hook_files = [f for f in files if "hooks.json" in f.target_path.name]
        assert len(hook_files) == 0


# ---------------------------------------------------------------------------
# AGENTS.md consistency check in diagnose
# ---------------------------------------------------------------------------


class TestAgentsMdDiagnosis:
    def test_suggests_agents_md_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "CLAUDE.md").write_text("# My Project\nUse `pytest` to test.")
            sr = scan(root)
            report = diagnose(sr)
            assert any("AGENTS.md" in s for s in report.suggestions)

    def test_no_agents_md_suggestion_when_no_claude_md(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = scan(Path(tmpdir))
            report = diagnose(sr)
            assert not any("AGENTS.md" in s for s in report.suggestions)


# ---------------------------------------------------------------------------
# Recommend skills
# ---------------------------------------------------------------------------


class TestRecommendSkills:
    def test_no_recommendations_bare_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = scan(Path(tmpdir))
            assert recommend_skills(sr) == []

    def test_fastapi_recommendation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\ndependencies = ["fastapi"]\n'
            )
            sr = scan(root)
            recs = recommend_skills(sr)
            names = {r.name for r in recs}
            assert "fastapi" in names

    def test_no_duplicate_recommendations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\ndependencies = ["stripe"]\n'
            )
            sr = scan(root)
            recs = recommend_skills(sr)
            assert len(recs) == len({r.name for r in recs})

    def test_skips_already_installed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\ndependencies = ["fastapi"]\n'
            )
            # Create the skill directory
            skill_dir = root / ".claude" / "skills" / "fastapi"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: fastapi\ndescription: FastAPI.\n---\nBody."
            )
            sr = scan(root)
            recs = recommend_skills(sr)
            assert not any(r.name == "fastapi" for r in recs)


# ---------------------------------------------------------------------------
# Monorepo detection
# ---------------------------------------------------------------------------


class TestMonorepoDetection:
    def test_not_monorepo_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = scan(Path(tmpdir))
            assert sr.is_monorepo is False
            assert sr.monorepo_packages == []

    def test_packages_dir_with_manifests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pkg1 = root / "packages" / "core"
            pkg1.mkdir(parents=True)
            (pkg1 / "package.json").write_text("{}")
            pkg2 = root / "packages" / "ui"
            pkg2.mkdir(parents=True)
            (pkg2 / "package.json").write_text("{}")
            sr = scan(root)
            assert sr.is_monorepo is True
            assert "packages/core" in sr.monorepo_packages
            assert "packages/ui" in sr.monorepo_packages

    def test_turbo_json_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "turbo.json").write_text("{}")
            sr = scan(root)
            assert sr.is_monorepo is True

    def test_packages_without_manifests_not_monorepo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "packages" / "empty").mkdir(parents=True)
            sr = scan(root)
            assert sr.is_monorepo is False


# ---------------------------------------------------------------------------
# Scan includes new fields
# ---------------------------------------------------------------------------


class TestScanNewFields:
    def test_agents_md_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "AGENTS.md").write_text("# Agents instructions")
            sr = scan(root)
            assert sr.agents_md_path is not None
            assert "Agents instructions" in sr.agents_md_content

    def test_skill_frontmatter_parsed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_dir = root / ".claude" / "skills" / "test-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: test-skill\ndescription: Does X.\n---\nBody."
            )
            sr = scan(root)
            assert len(sr.skills) == 1
            assert sr.skills[0].frontmatter["name"] == "test-skill"
            assert sr.skills[0].line_count > 0


# ---------------------------------------------------------------------------
# Score integration: spec violations appear in notes
# ---------------------------------------------------------------------------


class TestScoreSpecIntegration:
    def test_spec_violations_in_diagnosis(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_dir = root / ".claude" / "skills" / "Bad-Skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: Bad-Skill\ndescription: OK.\n---\nBody."
            )
            sr = scan(root)
            report = diagnose(sr)
            skills_score = next(s for s in report.scores if s.name == "Skills")
            assert any("lowercase" in n for n in skills_score.notes)

    def test_valid_skill_no_violations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill_dir = root / ".claude" / "skills" / "good-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: good-skill\ndescription: Does X when Y.\n---\nBody."
            )
            sr = scan(root)
            report = diagnose(sr)
            skills_score = next(s for s in report.scores if s.name == "Skills")
            # Should not have spec violation notes
            assert not any("frontmatter" in n for n in skills_score.notes)
