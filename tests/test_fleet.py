"""Fleet mode (opsward#17, gap 1): diagnose many roots, roll up, never die on one."""

import json
import subprocess
import sys
from pathlib import Path

from opsward import fleet, git_roots_under
from opsward.fleet import manifest_roots

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


# -- the `opsward fleet` command (#49) --


def _fleet_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "opsward", "fleet", *args],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )


def test_fleet_cli_rolls_up_the_given_roots():
    done = _fleet_cli(str(FIXTURES / "bare_project"), str(FIXTURES / "python_project"))
    assert done.returncode == 0, done.stderr
    assert "Fleet report: 2 repo(s)" in done.stdout and "bare_project" in done.stdout
    assert str(FIXTURES) not in done.stdout


def test_fleet_cli_json_is_the_name_keyed_summary():
    done = _fleet_cli(str(FIXTURES / "bare_project"), "--format", "json")
    data = json.loads(done.stdout)
    assert list(data["repos"]) == ["bare_project"] and str(FIXTURES) not in done.stdout


def test_fleet_cli_under_finds_git_repos(tmp_path):
    for name in ("one", "two"):
        (tmp_path / name / ".git").mkdir(parents=True)
    done = _fleet_cli("--under", str(tmp_path), "--format", "json")
    assert sorted(json.loads(done.stdout)["repos"]) == ["one", "two"]


def test_fleet_cli_manifest_remembers_the_roots(tmp_path):
    manifest = tmp_path / "state" / "fleet.json"
    first = _fleet_cli(str(FIXTURES / "bare_project"), "--manifest", str(manifest))
    assert first.returncode == 0, first.stderr
    record = json.loads(manifest.read_text())
    assert record["roots"] == [str((FIXTURES / "bare_project").resolve())]
    assert list(record["report"]["repos"]) == ["bare_project"]
    again = _fleet_cli("--manifest", str(manifest))  # no roots given: the manifest's
    assert again.returncode == 0 and "Fleet report: 1 repo(s)" in again.stdout


def test_fleet_cli_rejects_a_file_that_is_not_a_manifest(tmp_path):
    bogus = tmp_path / "x.json"
    bogus.write_text("[1, 2]")
    done = _fleet_cli("--manifest", str(bogus))
    assert done.returncode == 2 and "not an opsward fleet manifest" in done.stderr


def test_fleet_cli_needs_some_roots():
    done = _fleet_cli()
    assert done.returncode == 2 and "no roots" in done.stderr


def test_manifest_roots_of_a_missing_file_is_empty(tmp_path):
    assert manifest_roots(tmp_path / "absent.json") == []
