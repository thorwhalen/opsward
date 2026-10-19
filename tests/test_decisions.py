"""Tests for opsward.decisions and the `decision` command group (opsward#16)."""

import contextlib
import datetime as dt
import io
import tempfile
from pathlib import Path

import cw

from opsward.cli import _dispatch_funcs
from opsward.decisions import (
    adr_files,
    check_decisions,
    log_append,
    log_entry,
    new_adr,
    next_number,
    slugify,
)
from opsward.maintain import maintain
from opsward.scan import scan


def _run(argv: list[str]) -> tuple[int, str, str]:
    """Dispatch in-process; the commands print to sys.stdout, so capture that."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = cw.dispatch(_dispatch_funcs, argv, out=out, err=err)
        except SystemExit as e:  # the commands call sys.exit on their own exits
            rc = e.code
    return rc, out.getvalue(), err.getvalue()


def test_numbering_skips_the_template_and_never_collides():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "0000-template.md").write_text("# NNNN — template\n")
        assert next_number(d) == 1
        (d / "0007-seven.md").write_text("# 0007 — Seven\n\n## Status\n\nAccepted\n")
        (d / "0003-three.md").write_text("# 0003 — Three\n\n## Status\n\nAccepted\n")
        assert [p.name for p in adr_files(d)] == ["0003-three.md", "0007-seven.md"]
        assert next_number(d) == 8
        gf = new_adr(d, "Eight: the next one!", date=dt.date(2026, 10, 19), evidence="#16")
        assert gf.target_path.name == "0008-eight-the-next-one.md"
        assert "## Status\n\nProposed (2026-10-19)" in gf.content and "\n#16\n" in gf.content
        assert slugify("  Ünïcode & spaces  ") == "n-code-spaces"


def test_log_append_creates_from_template_then_appends():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        path, content = log_append(d, "In the context of X, facing Y, we decided Z.", date=dt.date(2026, 10, 19))
        assert path == d / "log.md" and content.startswith("# Decision log")
        assert content.endswith("- 2026-10-19 — In the context of X, facing Y, we decided Z.\n")
        path.write_text(content)
        _, content2 = log_append(d, "second", date=dt.date(2026, 10, 20))
        assert content2.count("\n- ") == 2 and content2.endswith("- 2026-10-20 — second\n")
        assert log_entry("  spaced   out ", date=dt.date(2026, 1, 1)) == "- 2026-01-01 — spaced out"


def test_maintain_reports_stale_paths_and_missing_status_in_adrs():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        d = root / "misc" / "docs" / "decisions"
        d.mkdir(parents=True)
        (root / "misc" / "docs" / "docs_guide.md").write_text("# Guide\n\n| doc | when |\n|---|---|\n")
        (root / "pkg").mkdir()
        (root / "pkg" / "real.py").write_text("")
        (d / "0001-good.md").write_text("# 0001 — Good\n\n## Status\n\nAccepted\n\n## Decision\n\nSee `pkg/real.py` and the sibling `decisions/README.md`.\n")
        (d / "README.md").write_text("# Decisions\n")
        (d / "0002-rotten.md").write_text("# 0002 — Rotten\n\n## Status\n\nAccepted\n\n## Decision\n\nSee `pkg/gone.py` and `old/dir/thing.md`.\n")
        (d / "0003-nostatus.md").write_text("# 0003 — No status\n\n## Decision\n\nWhatever.\n")
        (d / "0000-template.md").write_text("# NNNN — Title\n\n## Status\n\nSee `nothing/here.md`\n")
        sr = scan(root, claude_config_dir=None)
        assert {x.name for x in sr.decisions} >= {"0001-good", "0002-rotten", "0003-nostatus"}
        findings = list(check_decisions(sr))
        assert [f.category for f in findings] == ["stale_adr", "stale_adr"]
        assert any("0002-rotten.md" in f.description and "`pkg/gone.py`" in f.description for f in findings)
        assert any("0003-nostatus.md" in f.description and "no `## Status`" in f.description for f in findings)
        assert not any("0000-template" in f.description for f in findings)
        assert [s.category for s in maintain(sr) if s.category == "stale_adr"] == ["stale_adr", "stale_adr"]


def test_decision_commands_dry_run_then_write():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pyproject.toml").write_text("[project]\nname='x'\n")
        rc, out, _ = _run(["decision", "new", "Pin the thing", "--project-root", str(root)])
        assert rc == 0 and "Would create misc/docs/decisions/0001-pin-the-thing.md" in out
        assert not (root / "misc" / "docs" / "decisions").exists()
        rc, out, _ = _run(["decision", "new", "Pin the thing", "-p", str(root), "--write", "--evidence", "#16"])
        assert rc == 0 and "Created misc/docs/decisions/0001-pin-the-thing.md" in out
        text = (root / "misc" / "docs" / "decisions" / "0001-pin-the-thing.md").read_text()
        assert text.startswith("# 0001 — Pin the thing") and "\n#16\n" in text
        rc, out, _ = _run(["decision", "new", "Second", "-p", str(root), "--write"])
        assert rc == 0 and "0002-second.md" in out
        rc, out, _ = _run(["decision", "note", "In the context of tests, we wrote one.", "-p", str(root)])
        assert rc == 0 and "Would create misc/docs/decisions/log.md a dated entry" in out
        rc, out, _ = _run(["decision", "note", "In the context of tests, we wrote one.", "-p", str(root), "--write"])
        assert rc == 0 and "Appended to misc/docs/decisions/log.md" in out
        log = (root / "misc" / "docs" / "decisions" / "log.md").read_text()
        assert log.startswith("# Decision log") and log.rstrip().endswith("we wrote one.")


def test_decision_new_never_overwrites():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        d = root / "docs" / "decisions"
        d.mkdir(parents=True)
        (root / "package.json").write_text("{}")
        rc, out, _ = _run(["decision", "new", "Thing", "-p", str(root), "--write"])
        assert rc == 0 and (d / "0001-thing.md").exists()
        before = (d / "0001-thing.md").read_text()
        # a hand-made file at the next number is never touched: numbering moves past it
        (d / "0002-thing.md").write_text("mine\n")
        rc, out, _ = _run(["decision", "new", "Thing", "-p", str(root), "--write"])
        assert rc == 0 and "docs/decisions/0003-thing.md" in out
        assert (d / "0002-thing.md").read_text() == "mine\n" and (d / "0001-thing.md").read_text() == before
