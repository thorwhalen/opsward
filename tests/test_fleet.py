"""Fleet mode (opsward#17, gap 1): diagnose many roots, roll up, never die on one."""

import json
from pathlib import Path

from opsward import fleet, git_roots_under

FIXTURES = Path(__file__).parent / "fixtures"


def test_fleet_over_the_fixture_projects_rolls_up_missing_items_and_grades():
    roots = sorted(p for p in FIXTURES.iterdir() if p.is_dir())
    report = fleet([*roots, FIXTURES / "nope"])
    assert len(report.reports) == len(roots)
    assert report.errors == {str(FIXTURES / "nope"): "not a directory"}
    assert sum(report.grade_counts().values()) == len(roots)
    assert report.missing_rollup().get("CLAUDE.md", 0) >= 1  # bare_project has none
    assert all(c["repos"] <= len(roots) for c in report.component_rollup().values())
    text = str(report)
    assert "Fleet report" in text and "Could not diagnose" in text


def test_the_summary_names_repos_never_absolute_paths():
    report = fleet(sorted(p for p in FIXTURES.iterdir() if p.is_dir()))
    dumped = json.dumps(report.to_dict())
    assert str(FIXTURES) not in dumped and "bare_project" in dumped


def test_a_root_that_raises_is_recorded_not_fatal(tmp_path):
    def boom(root):
        raise RuntimeError("bad repo")

    report = fleet([tmp_path], diagnose_root=boom)
    assert report.reports == [] and "RuntimeError: bad repo" in report.errors[str(tmp_path)]


def test_git_roots_under_finds_repos_one_level_down(tmp_path):
    for name in ("a", "b", "notrepo"):
        (tmp_path / name).mkdir()
    (tmp_path / "a" / ".git").mkdir()
    (tmp_path / "b" / ".git").write_text("gitdir: elsewhere")
    assert [p.name for p in git_roots_under(tmp_path)] == ["a", "b"]
