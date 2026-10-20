"""Governance vocabulary (opsward#53): triage on drift findings, the ignore-path marker."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from opsward.maintain import TRIAGE_ACTIONS, maintain
from opsward.scan import scan
from opsward.score import diagnose

FIXTURES = Path(__file__).parent / "fixtures"


def _project(tmp_path, claude_md):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'p'\n")
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "real.py").write_text("")
    (tmp_path / "CLAUDE.md").write_text(claude_md)
    return scan(tmp_path, claude_config_dir=None)


def _stale(sr):
    return [s.description for s in maintain(sr) if s.category == "stale_path"]


def test_every_finding_carries_a_triage_from_the_vocabulary():
    found = maintain(scan(FIXTURES / "stale_project", claude_config_dir=None))
    assert found and all(s.triage in TRIAGE_ACTIONS for s in found)


def test_an_inline_marker_silences_that_line_only(tmp_path):
    sr = _project(tmp_path, "- `src/gone.py` <!-- opsward: ignore-path -->\n- `src/also_gone.py`\n")
    assert _stale(sr) == ["CLAUDE.md references `src/also_gone.py` but it does not exist"]


def test_a_marker_alone_on_its_line_covers_the_next_line(tmp_path):
    sr = _project(tmp_path, "# opsward: ignore-path\n- `build/out.py` is generated\n- `src/real.py`\n")
    assert _stale(sr) == []


def test_the_marker_also_spares_the_currency_score(tmp_path):
    bad = diagnose(_project(tmp_path, "- `src/gone.py`\n- `src/real.py`\n"))
    ignored = diagnose(_project(tmp_path, "- `src/gone.py` <!-- opsward: ignore-path -->\n- `src/real.py`\n"))
    assert ignored.overall_score >= bad.overall_score
    claude = lambda r: next(s for s in r.scores if s.name.startswith("CLAUDE.md"))  # noqa: E731
    assert not any("src/gone.py" in n for n in claude(ignored).notes)


def test_maintain_cli_shows_the_triage_in_text_and_json():
    run = lambda *a: subprocess.run(  # noqa: E731
        [sys.executable, "-m", "opsward", "maintain", "tests/fixtures/stale_project", *a],
        capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
    )
    assert "[stale_path → align]" in run().stdout
    assert {d["triage"] for d in json.loads(run("--format", "json").stdout)} <= set(TRIAGE_ACTIONS)


# -- config changelog (#53, part 3) --


def _git(root, *args, date=None):
    env = dict(os.environ)
    if date:  # pinned, so commits in the same second still order
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=root, check=True, capture_output=True, env=env)


def _repo_with_changelog(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'p'\n")
    (tmp_path / "CLAUDE.md").write_text("# P\n")
    (tmp_path / "misc" / "docs").mkdir(parents=True)
    (tmp_path / "misc" / "docs" / "config_changelog.md").write_text("- 2026-01-01: initial CLAUDE.md\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "init", date="2026-01-01T00:00:00+00:00")
    return tmp_path


def _changelog_findings(root):
    return [s for s in maintain(scan(root, claude_config_dir=None)) if s.category == "config_changelog"]


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_a_config_commit_after_the_last_changelog_entry_is_flagged(tmp_path):
    root = _repo_with_changelog(tmp_path)
    assert _changelog_findings(root) == []
    (root / "CLAUDE.md").write_text("# P\n\nRun `pytest`.\n")
    _git(root, "commit", "-qam", "edit config", date="2026-02-01T00:00:00+00:00")
    (found,) = _changelog_findings(root)
    assert "misc/docs/config_changelog.md" in found.description and found.triage == "align"
    log = root / "misc" / "docs" / "config_changelog.md"
    log.write_text("- 2026-02-01: documented pytest\n" + log.read_text())
    _git(root, "commit", "-qam", "log it", date="2026-02-02T00:00:00+00:00")
    assert _changelog_findings(root) == []


def test_no_changelog_no_check():
    assert _changelog_findings(FIXTURES / "python_project") == []
