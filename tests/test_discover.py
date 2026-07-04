"""Tests for opsward's optional toolery-backed asset discovery.

Skipped entirely when ``toolery`` (the ``opsward[discovery]`` extra) is not installed.
"""

import pytest

pytest.importorskip("toolery")

from opsward.discover import find_assets  # noqa: E402


def _make_repo(root):
    skills = root / ".claude" / "skills" / "diagnose-thing"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text(
        "---\nname: diagnose-thing\ndescription: diagnose the health of a project\n---\n"
    )
    agents = root / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "auditor.md").write_text(
        "---\nname: auditor\ndescription: audits a project for issues\n---\n"
    )
    return root


def test_find_assets_across_kinds(tmp_path):
    repo = _make_repo(tmp_path)
    hits = find_assets(str(repo), query="diagnose project health", kinds="skill,agent")
    assert "diagnose-thing" in [c.name for c, _ in hits]
    only_agents = find_assets(str(repo), query="project", kinds="agent")
    assert only_agents and all(c.kind == "agent" for c, _ in only_agents)


def test_find_assets_multi_root(tmp_path):
    r1 = _make_repo(tmp_path / "a")
    r2 = tmp_path / "b"
    s = r2 / ".claude" / "skills" / "other"
    s.mkdir(parents=True)
    (s / "SKILL.md").write_text("---\nname: other\ndescription: something else\n---\n")
    hits = find_assets(str(r1), str(r2), query="diagnose", kinds="skill")
    assert any(c.name == "diagnose-thing" for c, _ in hits)
