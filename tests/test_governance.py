"""Governance vocabulary (opsward#53): triage on drift findings, the ignore-path marker."""

import json
import subprocess
import sys
from pathlib import Path

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
