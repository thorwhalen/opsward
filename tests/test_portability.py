"""Tests for opsward.portability: host coverage and canonical↔render drift (opsward#15)."""

import os
from pathlib import Path

import pytest

from opsward import diagnose, portability, scan
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
