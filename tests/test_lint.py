"""`opsward lint` (opsward#50): skill specs and hooks config, pass or fail."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from opsward.base import ScanResult, SkillInfo
from opsward.lint import lint, opsward_validator, resolve_validators
from opsward.scan import scan

REPO = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


def _lint_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "opsward", "lint", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )


def _findings(name, **kw):
    return list(lint(scan(FIXTURES / name, claude_config_dir=None), **kw))


def test_a_clean_project_has_no_findings():
    assert _findings("bare_project") == []


def test_spec_and_hooks_violations_are_found_with_repo_relative_paths():
    found = _findings("python_project", validators="opsward")
    paths = {f.path for f in found}
    assert paths == {".claude/skills/my-skill", ".claude/hooks.json"}
    assert all(f.source == "opsward" for f in found)


def test_a_validator_that_raises_is_a_finding_not_a_crash():
    def boom(skill):
        raise RuntimeError("nope")

    found = _findings("python_project", validators={"boom": boom})
    assert any("validator failed: RuntimeError: nope" in f.message for f in found)


def test_a_skill_dir_without_skill_md_is_a_finding():
    sr = ScanResult(Path("r"), skills=[SkillInfo("x", Path("r/.claude/skills/x"))])
    assert [f.message for f in lint(sr, validators="opsward")] == ["no SKILL.md"]
    assert opsward_validator(SkillInfo("x", Path("x"))) == ["no SKILL.md"]


def test_unknown_or_uninstalled_validators_are_refused(monkeypatch):
    with pytest.raises(ValueError, match="unknown validator"):
        resolve_validators("opsward,nope")
    import opsward.lint as mod

    for name in ("skill", "agnix", "skillcheck"):
        validator, _ = mod.VALIDATORS[name]
        monkeypatch.setitem(mod.VALIDATORS, name, (validator, lambda: False))
    with pytest.raises(ValueError, match="not installed"):
        resolve_validators("skill")
    with pytest.raises(ValueError, match="npm install -g agnix"):
        resolve_validators("agnix")
    assert list(resolve_validators("auto")) == ["opsward"]


def _fake_run(stdout, *, calls=None):
    import subprocess

    def run(argv, **kwargs):
        if calls is not None:
            calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, stdout=stdout, stderr="boom")

    return run


def test_agnix_and_skillcheck_json_become_findings(monkeypatch, tmp_path):
    import json

    import opsward.lint as mod

    skill = SkillInfo("s", tmp_path / "s", has_skill_md=True)
    calls = []
    agnix_out = {
        "diagnostics": [
            {"level": "error", "rule": "AS-004", "message": "bad name", "line": 2},
            {"level": "warning", "rule": "AS-010", "message": "vague"},
            {"level": "info", "rule": "VER-001", "message": "versions"},
        ]
    }
    monkeypatch.setattr(mod.subprocess, "run", _fake_run(json.dumps(agnix_out), calls=calls))
    assert mod.agnix_validator(skill) == ["AS-004: bad name (line 2)", "AS-010: vague"]
    assert calls[0][:3] == ["agnix", "--format", "json"]
    check_out = {
        "results": [
            {"diagnostics": [{"severity": "error", "rule": "r", "message": "m", "line": None},
                             {"severity": "info", "rule": "i", "message": "x"}]}
        ]
    }
    monkeypatch.setattr(mod.subprocess, "run", _fake_run(json.dumps(check_out)))
    assert mod.skillcheck_validator(skill) == ["r: m"]
    assert mod.agnix_validator(SkillInfo("x", tmp_path / "x")) == []  # no SKILL.md


def test_an_external_linter_without_json_is_a_validator_failure(monkeypatch):
    import opsward.lint as mod

    monkeypatch.setattr(mod.subprocess, "run", _fake_run("not json"))
    sr = ScanResult(Path("r"), skills=[SkillInfo("s", Path("r/.claude/skills/s"), has_skill_md=True)])
    [finding] = lint(sr, validators={"agnix": mod.agnix_validator})
    assert "validator failed" in finding.message and "boom" in finding.message


@pytest.mark.parametrize("name", ["agnix", "skillcheck"])
def test_the_real_external_linter_flags_a_bad_skill(name, tmp_path):
    import shutil

    import opsward.lint as mod

    if shutil.which(name) is None:
        pytest.skip(f"{name} is not on PATH")
    (tmp_path / "Bad_Skill").mkdir()
    (tmp_path / "Bad_Skill" / "SKILL.md").write_text("---\nname: Bad_Name\n---\nbody\n")
    validator, _ = mod.VALIDATORS[name]
    assert validator(SkillInfo("Bad_Skill", tmp_path / "Bad_Skill", has_skill_md=True))


def test_the_skill_package_validator_composes_skill_validate():
    pytest.importorskip("skill")
    found = _findings("python_project", validators="skill")
    on_skills = [f for f in found if f.path.startswith(".claude/skills/")]
    assert on_skills and all(f.source == "skill" for f in on_skills)


def test_lint_cli_exits_1_on_findings_and_0_when_clean():
    bad = _lint_cli("tests/fixtures/python_project", "--validators", "opsward")
    assert bad.returncode == 1 and ".claude/skills/my-skill" in bad.stdout
    good = _lint_cli("tests/fixtures/bare_project")
    assert good.returncode == 0 and "clean" in good.stdout


def test_lint_cli_json_names_projects_not_paths():
    done = _lint_cli("tests/fixtures/python_project", "-v", "opsward", "--format", "json")
    data = json.loads(done.stdout)
    assert {d["project"] for d in data} == {"python_project"}
    assert str(FIXTURES) not in done.stdout


def test_lint_cli_rejects_an_unknown_validator():
    done = _lint_cli("tests/fixtures/bare_project", "--validators", "nope")
    assert done.returncode == 2 and "unknown validator" in done.stderr


def test_every_hooks_file_is_linted_even_unparseable_or_shadowed(tmp_path):
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "hooks.json").write_text("{bad")
    (claude / "settings.json").write_text('{"hooks": {"PreToolUse": "x"}}')
    (claude / "settings.local.json").write_text('{"model": "m"}')  # no hooks: skipped
    found = list(lint(scan(tmp_path, claude_config_dir=None), validators="opsward"))
    by_path = {f.path for f in found}
    assert by_path == {".claude/hooks.json", ".claude/settings.json"}
    assert any("not valid JSON" in f.message for f in found)


def test_an_empty_validator_selection_is_refused():
    for spec in (",", "", {}):
        with pytest.raises(ValueError, match="no validators selected"):
            resolve_validators(spec)


def test_lint_cli_rejects_an_unknown_format():
    done = _lint_cli("tests/fixtures/bare_project", "--format", "xml")
    assert done.returncode == 2 and "format must be" in done.stderr


def test_the_shipped_pre_commit_hooks_and_action_parse():
    yaml = pytest.importorskip("yaml")
    hooks = yaml.safe_load((REPO / ".pre-commit-hooks.yaml").read_text())
    assert {h["id"] for h in hooks} == {"opsward-lint", "opsward-diagnose"}
    assert all(h["entry"].startswith("opsward ") for h in hooks)
    action = yaml.safe_load((REPO / "action.yml").read_text())
    assert action["runs"]["using"] == "composite"
    run_lines = [s.get("run", "") for s in action["runs"]["steps"]]
    assert not any("${{" in line for line in run_lines)  # inputs only via env
