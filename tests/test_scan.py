"""Tests for opsward.scan."""

from pathlib import Path

import pytest

from opsward.base import ProjectType
from opsward.scan import scan

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture
def python_project():
    return FIXTURES / 'python_project'


@pytest.fixture
def jsts_project():
    return FIXTURES / 'jsts_project'


@pytest.fixture
def bare_project():
    return FIXTURES / 'bare_project'


# -- Project type detection --


def test_detect_python(python_project):
    result = scan(python_project)
    assert result.project_type is ProjectType.python


def test_detect_jsts(jsts_project):
    result = scan(jsts_project)
    assert result.project_type is ProjectType.jsts


def test_detect_unknown(bare_project):
    result = scan(bare_project)
    assert result.project_type is ProjectType.unknown


# -- CLAUDE.md --


def test_claude_md_found(python_project):
    result = scan(python_project)
    assert result.claude_md_path is not None
    assert result.claude_md_path.name == 'CLAUDE.md'
    assert 'Python expert' in result.claude_md_content


def test_claude_md_missing(bare_project):
    result = scan(bare_project)
    assert result.claude_md_path is None
    assert result.claude_md_content == ''


# -- Skills --


def test_skills_inventory(python_project):
    result = scan(python_project)
    assert len(result.skills) == 1
    skill = result.skills[0]
    assert skill.name == 'my-skill'
    assert skill.has_skill_md is True
    assert 'testing purposes' in skill.description


# -- Agents --


def test_agents_inventory(python_project):
    result = scan(python_project)
    assert len(result.agents) == 1
    assert result.agents[0].name == 'code-reviewer'


# -- Rules --


def test_rules_inventory(python_project):
    result = scan(python_project)
    assert len(result.rules) == 1
    assert result.rules[0].name == 'no-print'
    assert 'logging module' in result.rules[0].content


# -- Hooks --


def test_hooks_found(python_project):
    result = scan(python_project)
    assert result.hooks_path is not None
    assert result.hooks_config is not None
    assert 'pre_commit' in result.hooks_config


def test_hooks_missing(bare_project):
    result = scan(bare_project)
    assert result.hooks_path is None
    assert result.hooks_config is None


# -- Docs --


def test_docs_inventory(python_project):
    result = scan(python_project)
    assert len(result.docs) == 2
    names = {d.name for d in result.docs}
    assert 'architecture' in names
    assert 'docs_guide' in names


def test_docs_guide_detected(python_project):
    result = scan(python_project)
    assert result.has_docs_guide is True
    assert result.docs_guide_path is not None


def test_no_docs(bare_project):
    result = scan(bare_project)
    assert result.docs == []
    assert result.has_docs_guide is False


# -- Bare project returns sensible defaults --


def test_bare_project_defaults(bare_project):
    result = scan(bare_project)
    assert result.skills == []
    assert result.agents == []
    assert result.rules == []
    assert result.docs == []
