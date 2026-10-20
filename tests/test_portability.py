"""Tests for opsward.portability: host coverage and canonical↔render drift (opsward#15)."""

import os
from pathlib import Path

import pytest

from opsward import check_portability as portability, diagnose, scan
from opsward.portability import HostFile, analyze

CANONICAL = "# P\n\n## Build\n\n```bash\npytest\n# not a heading\n```\n\n## Layout\n\n- src/\n"


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _kinds(report):
    return sorted((f.kind, f.path, f.section) for f in report.findings)


def test_copy_reports_stale_diverged_and_host_only(tmp_path):
    _write(tmp_path, "AGENTS.md", CANONICAL)
    _write(tmp_path, "GEMINI.md", "# G\n\n## Build\n\npytest -x\n\n## Gemini only\n\nx\n")
    report = portability(tmp_path)
    assert report.coverage["gemini"] == "copy"
    assert _kinds(report) == [
        ("diverged", "GEMINI.md", "build"),
        ("host_only", "GEMINI.md", "gemini only"),
        ("stale", "GEMINI.md", "layout"),
    ]


def test_import_shim_keeps_deltas_but_flags_diverged_duplicates(tmp_path):
    _write(tmp_path, "AGENTS.md", CANONICAL)
    _write(
        tmp_path,
        "CLAUDE.md",
        "# P\n\n@AGENTS.md\n\n## Claude only\n\nhooks\n\n## Layout\n\n- lib/\n",
    )
    report = portability(tmp_path)
    assert report.coverage["claude"] == "import"
    assert _kinds(report) == [("diverged", "CLAUDE.md", "layout")]


def test_identical_copy_has_no_findings(tmp_path):
    _write(tmp_path, "AGENTS.md", CANONICAL)
    _write(tmp_path, ".github/copilot-instructions.md", CANONICAL.replace("# P", "# Copilot"))
    report = portability(tmp_path)
    assert report.findings == []
    # Reading AGENTS.md natively outranks the host's own copy
    assert report.coverage["copilot"] == "native"


def test_symlink_cannot_drift(tmp_path):
    _write(tmp_path, "AGENTS.md", CANONICAL)
    try:
        os.symlink("AGENTS.md", tmp_path / "CLAUDE.md")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    report = portability(tmp_path)
    assert report.coverage["claude"] == "symlink"
    assert report.findings == []


def test_coverage_without_canonical(tmp_path):
    _write(tmp_path, "CLAUDE.md", "# P\n\n## Build\n\npytest\n")
    (tmp_path / ".cursor" / "rules").mkdir(parents=True)
    report = portability(tmp_path)
    assert report.coverage["claude"] == "copy"
    assert report.coverage["cursor"] == "rules"
    assert report.coverage["codex"] == "none"
    assert report.findings == []
    assert report.covered == ["claude", "cursor"]


def test_analyze_is_pure_over_host_files():
    report = analyze(CANONICAL, {"GEMINI.md": HostFile("GEMINI.md", CANONICAL)})
    assert report.findings == []
    assert report.to_dict()["coverage"]["gemini"] == "copy"


def test_scan_reads_host_files(tmp_path):
    _write(tmp_path, "GEMINI.md", "x")
    (tmp_path / ".clinerules").mkdir()
    sr = scan(tmp_path, claude_config_dir=None)
    assert set(sr.host_files) == {"GEMINI.md", ".clinerules"}
    assert sr.host_files[".clinerules"].relation == "rules"


def test_diagnose_suggests_shim_and_summarizes_drift(tmp_path):
    _write(tmp_path, "AGENTS.md", CANONICAL)
    _write(tmp_path, "CLAUDE.md", "# P\n\n## Build\n\npytest -x\n")
    suggestions = diagnose(scan(tmp_path, claude_config_dir=None)).suggestions
    assert any("does not import AGENTS.md" in s for s in suggestions)
    assert any(
        s.startswith("CLAUDE.md drifts from AGENTS.md (1 stale, 1 diverged") for s in suggestions
    )


def test_diagnose_quiet_for_a_clean_shim(tmp_path):
    _write(tmp_path, "AGENTS.md", CANONICAL)
    _write(tmp_path, "CLAUDE.md", "# P\n\n@AGENTS.md\n\n## Claude only\n\nhooks\n")
    suggestions = diagnose(scan(tmp_path, claude_config_dir=None)).suggestions
    assert not any("AGENTS.md" in s for s in suggestions)


# -- review cases: false drift and missed shims --


def test_reversed_symlink_or_hardlink_is_the_canonical(tmp_path):
    _write(tmp_path, "CLAUDE.md", CANONICAL)
    try:
        os.link(tmp_path / "CLAUDE.md", tmp_path / "AGENTS.md")
    except (OSError, NotImplementedError):
        pytest.skip("hard links unavailable")
    assert portability(tmp_path).coverage["claude"] == "symlink"


def test_inline_import_counts_but_fenced_or_code_span_does_not():
    assert HostFile("CLAUDE.md", "See @AGENTS.md for commands.").relation == "import"
    assert HostFile("CLAUDE.md", "```\n@AGENTS.md\n```").relation == "copy"
    assert HostFile("CLAUDE.md", "write `@AGENTS.md` to import").relation == "copy"


def test_headings_h1_setext_bom_and_fences():
    from opsward.portability import _sections

    assert _sections("# T\n\n# One\na\n# Two\nb") == {"one": "a", "two": "b"}
    assert _sections("﻿## A\nx".lstrip("﻿")) == {"a": "x"}
    assert _sections("Title\n=====\nBuild\n-----\npytest") == {"build": "pytest"}
    text = "# T\n## A\n````md\n```\n## inside\n```\n````\n## B\ny"
    assert set(_sections(text)) == {"a", "b"}
    assert "b" in _sections("# T\n## A\n```y``` z\n## B\ny")


def test_empty_render_and_conventions_doc_are_not_drift(tmp_path):
    _write(tmp_path, "AGENTS.md", CANONICAL)
    _write(tmp_path, "GEMINI.md", "")
    _write(tmp_path, "CONVENTIONS.md", "# Contributing\n\n## Style\n\nblack\n")
    report = portability(tmp_path)
    assert report.findings == []
    assert report.coverage["aider"] == "copy"


def test_clinerules_file_and_dot_claude_claude_md(tmp_path):
    _write(tmp_path, ".clinerules", "rules")
    _write(tmp_path, ".claude/CLAUDE.md", "# P\n")
    report = portability(tmp_path)
    assert report.coverage["cline"] == "copy"
    assert report.coverage["claude"] == "copy"
