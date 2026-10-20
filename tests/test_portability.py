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


# -- opsward#69: a shim is scored as read, the CLI command, the fleet rollup --


def test_a_shim_is_scored_with_its_import_inlined(tmp_path):
    body = "## Commands\n\n```bash\npytest\nruff check .\n```\n\n## Architecture\n\n- `src/` holds the code\n"
    _write(tmp_path, "AGENTS.md", "# P\n\n" + body)
    _write(tmp_path, "CLAUDE.md", "@AGENTS.md\n")
    shim = diagnose(scan(tmp_path, claude_config_dir=None))
    _write(tmp_path, "CLAUDE.md", "# P\n\n" + body)
    copy = diagnose(scan(tmp_path, claude_config_dir=None))
    assert shim.scores[0].score == copy.scores[0].score > 0
    assert shim.portability.coverage["claude"] == "import"
    assert copy.portability.coverage["claude"] == "copy"


def test_as_read_leaves_fenced_imports_and_copies_alone():
    from opsward.portability import as_read

    fenced = "```\n@AGENTS.md\n```\n"
    assert as_read(fenced, "## Build") == fenced
    assert as_read("@AGENTS.md", "") == "@AGENTS.md"


def test_portability_cli_prints_coverage_and_drift(tmp_path):
    import json
    import subprocess
    import sys

    _write(tmp_path, "AGENTS.md", CANONICAL)
    _write(tmp_path, "CLAUDE.md", "# P\n\n## Build\n\npytest -x\n")

    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "opsward", "portability", str(tmp_path), *args],
            capture_output=True,
            text=True,
        )

    text = run()
    assert text.returncode == 0, text.stderr
    assert "claude    copy" in text.stdout and "codex     native" in text.stdout
    assert "CLAUDE.md: section 'build' differs from AGENTS.md" in text.stdout
    data = json.loads(run("--format", "json").stdout)
    assert data[0]["project"] == tmp_path.name
    assert {"kind": "stale", "path": "CLAUDE.md", "section": "layout"} in data[0]["findings"]
    assert run("--format", "yaml").returncode == 2


def test_fleet_rolls_up_coverage_and_drift(tmp_path):
    from opsward import fleet

    for name, claude in [("shim", "@AGENTS.md\n"), ("copy", "# P\n\n## Build\n\nx\n")]:
        _write(tmp_path / name, "AGENTS.md", CANONICAL)
        _write(tmp_path / name, "CLAUDE.md", claude)
    (tmp_path / "bare").mkdir()
    report = fleet([tmp_path / n for n in ("shim", "copy", "bare")])
    rollup = report.portability_rollup()
    assert rollup["covered"]["claude"] == 2 and rollup["covered"]["codex"] == 2
    assert rollup["uncovered"] == 1 and rollup["drifting_repos"] == 1
    assert rollup["drift"] == {"stale": 1, "diverged": 1, "host_only": 0}
    assert report.to_dict()["portability_rollup"] == rollup
    assert "Host coverage (repos): claude 2" in str(report)
    assert "AGENTS.md drift: 1 repo(s) (stale 1, diverged 1)" in str(report)


def test_as_read_strips_a_bom_and_inlines_once():
    from opsward.portability import as_read

    assert as_read("﻿@AGENTS.md\n", "## Build") == "## Build"
    assert as_read("@AGENTS.md\n@AGENTS.md", "## Build") == "## Build\n@AGENTS.md"
    assert as_read("x\n\n    @AGENTS.md", "## B").endswith("    @AGENTS.md\n\n## B")



# -- opsward#73: an import resolves against the importing file's folder --


@pytest.mark.parametrize(
    "path, text, relation",
    [
        ("CLAUDE.md", "@AGENTS.md\n", "import"),
        ("CLAUDE.md", "@./AGENTS.md\n", "import"),
        ("CLAUDE.md", "@../AGENTS.md\n", "copy"),
        ("CLAUDE.md", "@docs/AGENTS.md\n", "copy"),
        (".claude/CLAUDE.md", "@AGENTS.md\n", "copy"),
        (".claude/CLAUDE.md", "See @AGENTS.md first.", "copy"),
        (".claude/CLAUDE.md", "@../AGENTS.md\n", "import"),
        (".claude/CLAUDE.md", "See @../AGENTS.md first.", "import"),
    ],
)
def test_relation_resolves_the_import_from_the_importer(path, text, relation):
    assert HostFile(path, text).relation == relation


def test_as_read_inlines_only_an_import_that_resolves():
    from opsward.portability import as_read

    shim = "@AGENTS.md\n\n## Claude\n\nx"
    assert as_read(shim, "## Build") == "## Build\n\n## Claude\n\nx"
    assert as_read(shim, "## Build", path="CLAUDE.md") == "## Build\n\n## Claude\n\nx"
    assert as_read(shim, "## Build", path=".claude/CLAUDE.md") == shim
    up = "@../AGENTS.md\n\n## Claude\n\nx"
    assert as_read(up, "## Build", path=".claude/CLAUDE.md") == (
        "## Build\n\n## Claude\n\nx"
    )
    assert as_read(up, "## Build") == up


def test_dot_claude_shim_is_credited_only_when_its_import_resolves(tmp_path):
    body = "## Commands\n\n```bash\npytest\n```\n"
    _write(tmp_path, "AGENTS.md", "# P\n\n" + body)
    _write(tmp_path, ".claude/CLAUDE.md", "@AGENTS.md\n")
    wrong = diagnose(scan(tmp_path, claude_config_dir=None))
    assert wrong.portability.coverage["claude"] == "copy"
    assert any("`@../AGENTS.md`" in s for s in wrong.suggestions)
    _write(tmp_path, ".claude/CLAUDE.md", "@../AGENTS.md\n")
    right = diagnose(scan(tmp_path, claude_config_dir=None))
    assert right.portability.coverage["claude"] == "import"
    assert right.scores[0].score > wrong.scores[0].score


# -- opsward#67: the scored Portability component (ADR 0012) --


def _portability(root):
    report = diagnose(scan(root, claude_config_dir=None))
    return next(s for s in report.scores if s.name == "Portability"), report


def test_portability_scores_drift_only(tmp_path):
    _write(tmp_path, "CLAUDE.md", "# P\n\n## Build\n\npytest\n")
    claude_only, before = _portability(tmp_path)
    assert claude_only.score == 100  # no AGENTS.md: a Claude-only repo is not penalised
    _write(tmp_path, "AGENTS.md", CANONICAL)
    drifting, _ = _portability(tmp_path)
    assert drifting.score == 100 - 10 * 2  # 1 diverged + 1 stale
    _write(tmp_path, "CLAUDE.md", "@AGENTS.md\n")
    shim, _ = _portability(tmp_path)
    assert shim.score == 100 and shim.notes == []


def test_without_agents_md_the_overall_score_is_unchanged(tmp_path):
    from opsward import score

    _write(tmp_path, "CLAUDE.md", "# P\n\n## Build\n\npytest\n")
    report = diagnose(scan(tmp_path, claude_config_dir=None))
    old = {**score._OVERALL_WEIGHTS, "CLAUDE.md quality": 0.35}
    del old["Portability"]
    by_name = {s.name: s.score for s in report.scores}
    assert report.weighted_score == pytest.approx(
        sum(by_name[k] * w for k, w in old.items())
    )


def test_a_blank_agents_md_counts_as_absent(tmp_path):
    _write(tmp_path, "AGENTS.md", "﻿   \n\n")
    _write(tmp_path, "CLAUDE.md", "# P\n\n## Build\n\npytest\n\n## Notes\n\nx\n")
    score, report = _portability(tmp_path)
    assert score.score == 100 and report.portability.findings == []
    assert report.portability.coverage["codex"] == "none"


# -- opsward#68: the lossy kind, fed by the skill package's registry --


def _needs_skill_losses():
    translate = pytest.importorskip("skill.translate", reason="needs opsward[lint]")
    if not hasattr(translate, "lost_fields"):
        pytest.skip("needs a skill release with translation_losses (thorwhalen/skill#14)")


def test_lossy_skill_renders_are_reported_not_scored(tmp_path):
    _needs_skill_losses()
    _write(
        tmp_path,
        ".claude/skills/greet/SKILL.md",
        "---\nname: greet\ndescription: Say hello\nlicense: MIT\nallowed-tools: Bash\n---\n\nHi.\n",
    )
    _write(tmp_path, ".cursor/rules/greet.mdc", "---\ndescription: Say hello\n---\nHi.\n")
    _write(tmp_path, ".windsurf/rules/other.md", "x")  # not this skill's render
    report = portability(tmp_path)
    lossy = [f for f in report.findings if f.kind == "lossy"]
    assert [(f.path, f.section) for f in lossy] == [(".cursor/rules/greet.mdc", "greet")]
    assert "allowed-tools" in lossy[0].lost and "license" in lossy[0].lost
    assert "loses allowed-tools" in str(lossy[0])
    assert report.to_dict()["findings"][0]["lost"] == list(lossy[0].lost)
    score, _ = _portability(tmp_path)
    assert score.score == 100


def test_hosts_and_the_skill_registry_are_joined_not_copied():
    _needs_skill_losses()
    from skill.install import agent_targets

    from opsward.portability import AGENT_HOSTS

    linked = {h.skill_target for h in AGENT_HOSTS.values() if h.skill_target}
    assert linked <= set(agent_targets), linked - set(agent_targets)
    # every host the skill package can install into is a host opsward knows
    assert set(agent_targets) <= linked, set(agent_targets) - linked


def test_lossy_review_cases(tmp_path):
    _needs_skill_losses()
    import subprocess
    import sys

    skill_md = "---\nname: {}\ndescription: d\nlicense: MIT\n---\n\nHi.\n"
    _write(tmp_path, ".claude/skills/greet/SKILL.md", skill_md.format("greet"))
    _write(tmp_path, ".claude/skills/evil/SKILL.md", skill_md.format("../../../outside"))
    _write(tmp_path, ".cursor/rules/greet.mdc", "x")
    _write(tmp_path, "outside.mdc", "x")
    _write(tmp_path, "AGENTS.md", "# A\n<!-- skill:greet -->\n")
    (tmp_path / "GEMINI.md").symlink_to("AGENTS.md")
    report = portability(tmp_path)
    assert [f.path for f in report.findings if f.kind == "lossy"] == [".cursor/rules/greet.mdc"]
    out = subprocess.run(
        [sys.executable, "-m", "opsward", "portability", str(tmp_path)],
        capture_output=True, text=True,
    ).stdout
    assert "Lossy skill renders (1):" in out and "AGENTS.md drift" not in out


def test_to_dict_keeps_an_empty_section():
    from opsward.portability import DriftFinding, PortabilityReport

    report = PortabilityReport(findings=[DriftFinding("host_only", "CLAUDE.md", "")])
    assert report.to_dict()["findings"] == [
        {"kind": "host_only", "path": "CLAUDE.md", "section": ""}
    ]
