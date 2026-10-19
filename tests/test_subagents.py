"""Tests for opsward.subagents: declaration parsing, rendering, sync states, wiring."""

import tempfile
from pathlib import Path

from opsward.generate import generate
from opsward.maintain import maintain
from opsward.scan import scan
from opsward.score import diagnose
from opsward.subagents import (
    SubagentSpec,
    check_subagent_twins,
    render_subagent,
    subagent_files,
    subagent_spec,
    twin_status,
    twin_summary,
)

_SKILL = """---
name: fleet-sweep
description: "Sweep every repo and report what drifted. Use when asked for a fleet status."
metadata:
  subagent: true
  subagent-tools: Bash, Read
  subagent-model: haiku
  subagent-reply-lines: 3
---

# Fleet sweep

1. Run the sweep.
2. Report.
"""

_PLAIN_SKILL = """---
name: conventions
description: House style for this repo.
---

Follow the conventions.
"""


def _project(tmp: Path, *, skill: str = _SKILL, agent: str | None = None, agent_name: str = "fleet-sweep") -> Path:
    root = tmp / "proj"
    (root / ".claude" / "skills" / "fleet-sweep").mkdir(parents=True)
    (root / ".claude" / "skills" / "fleet-sweep" / "SKILL.md").write_text(skill)
    (root / ".claude" / "skills" / "conventions").mkdir()
    (root / ".claude" / "skills" / "conventions" / "SKILL.md").write_text(_PLAIN_SKILL)
    if agent is not None:
        (root / ".claude" / "agents").mkdir(parents=True)
        (root / ".claude" / "agents" / f"{agent_name}.md").write_text(agent)
    return root


def _write_twin(root: Path) -> Path:
    sr = scan(root)
    (gf,) = list(subagent_files(sr))
    gf.target_path.parent.mkdir(parents=True, exist_ok=True)
    gf.target_path.write_text(gf.content)
    return gf.target_path


def test_spec_reads_declaration_and_defaults():
    with tempfile.TemporaryDirectory() as tmp:
        sr = scan(_project(Path(tmp)))
        specs = {s.name: subagent_spec(s) for s in sr.skills}
        assert specs["conventions"] is None
        spec = specs["fleet-sweep"]
        assert spec == SubagentSpec(
            skill_name="fleet-sweep",
            name="fleet-sweep",
            description="Sweep every repo and report what drifted. Use when asked for a fleet status.",
            tools="Bash, Read",
            model="haiku",
            reply_lines=3,
        )


def test_render_preloads_skill_and_states_contract():
    spec = SubagentSpec("fleet-sweep", "sweeper", "Sweep: and report.", "Bash", None, 4)
    text = render_subagent(spec, source=".claude/skills/fleet-sweep/SKILL.md")
    head = text.split("---")[1]
    assert "name: sweeper" in head
    assert 'description: "Sweep: and report."' in head  # quoted: it contains a colon
    assert "skills: [fleet-sweep]" in head
    assert "model:" not in head
    assert "at most 4 lines" in text
    assert f"source-hash: {spec.source_hash()}" in text


def test_generate_emits_missing_twin_once():
    with tempfile.TemporaryDirectory() as tmp:
        root = _project(Path(tmp))
        files = generate(scan(root))
        twins = [f for f in files if f.target_path.parent.name == "agents" and f.target_path.name == "fleet-sweep.md"]
        assert len(twins) == 1
        twins[0].target_path.parent.mkdir(parents=True)
        twins[0].target_path.write_text(twins[0].content)
        files = generate(scan(root))
        assert not [f for f in files if f.target_path.name == "fleet-sweep.md"]


def test_twin_states_missing_in_sync_stale():
    with tempfile.TemporaryDirectory() as tmp:
        root = _project(Path(tmp))
        assert [t.state for t in twin_status(scan(root))] == ["missing"]
        assert [s.category for s in maintain(scan(root))] == ["subagent_twin"]
        _write_twin(root)
        assert [t.state for t in twin_status(scan(root))] == ["in_sync"]
        assert maintain(scan(root)) == []
        skill_md = root / ".claude" / "skills" / "fleet-sweep" / "SKILL.md"
        skill_md.write_text(skill_md.read_text().replace("subagent-model: haiku", "subagent-model: sonnet"))
        (status,) = list(twin_status(scan(root)))
        assert status.state == "stale" and "model: sonnet" in status.content
        (finding,) = list(check_subagent_twins(scan(root)))
        assert "out of date" in finding.description and "model: sonnet" in finding.diff


def test_handwritten_twin_is_reported_but_never_overwritten():
    handwritten = "---\nname: fleet-sweep\ndescription: My own sweeper.\n---\nDo it by hand.\n"
    with tempfile.TemporaryDirectory() as tmp:
        root = _project(Path(tmp), agent=handwritten)
        (status,) = list(twin_status(scan(root)))
        assert status.state == "handwritten"
        assert not [f for f in generate(scan(root)) if f.target_path.name == "fleet-sweep.md"]
        (finding,) = list(check_subagent_twins(scan(root)))
        assert "hand-written twin" in finding.description


def test_undeclared_skill_with_preloading_agent_is_a_handwritten_twin():
    agent = "---\nname: style-checker\ndescription: Checks style.\nskills: [conventions]\n---\nCheck.\n"
    with tempfile.TemporaryDirectory() as tmp:
        root = _project(Path(tmp), skill=_PLAIN_SKILL.replace("conventions", "fleet-sweep"), agent=agent, agent_name="style-checker")
        states = {(t.skill, t.agent): t.state for t in twin_status(scan(root))}
        assert states == {("conventions", "style-checker"): "handwritten"}


def test_diagnose_notes_twins_without_moving_the_score():
    with tempfile.TemporaryDirectory() as tmp:
        root = _project(Path(tmp))
        before = diagnose(scan(root))
        _write_twin(root)
        after = diagnose(scan(root))
        setup_before = next(c for c in before.scores if c.name.startswith("Setup"))
        setup_after = next(c for c in after.scores if c.name.startswith("Setup"))
        assert any("1 missing" in n for n in setup_before.notes)
        assert any("1 in_sync" in n for n in setup_after.notes)
        assert twin_summary(scan(root)) == {"in_sync": 1}
        # the generated twin is a described agent, so Setup credits it like any agent
        assert setup_after.score >= setup_before.score
