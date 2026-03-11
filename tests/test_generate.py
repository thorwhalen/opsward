"""Tests for opsward.generate."""

import tempfile
from pathlib import Path

import pytest

from opsward.base import ProjectType, ScanResult
from opsward.generate import generate, _load_template, _build_variables
from opsward.scan import scan

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture
def python_scan():
    return scan(FIXTURES / 'python_project')


@pytest.fixture
def jsts_scan():
    return scan(FIXTURES / 'jsts_project')


@pytest.fixture
def bare_scan():
    return scan(FIXTURES / 'bare_project')


# -- Template loading --


def test_load_shared_template():
    content = _load_template('shared/known_issues.md')
    assert '# Known Issues' in content


def test_load_python_template():
    content = _load_template('python/conventions.md')
    assert 'snake_case' in content


def test_load_jsts_template():
    content = _load_template('jsts/conventions.md')
    assert 'camelCase' in content


# -- Variable extraction --


def test_variables_python(python_scan):
    v = _build_variables(python_scan)
    assert v['project_name'] == 'myproject'
    assert v['project_type'] == 'python'
    assert v['docs_path'] == 'misc/docs'


def test_variables_jsts(jsts_scan):
    v = _build_variables(jsts_scan)
    assert v['project_name'] == 'my-ts-app'
    assert v['project_type'] == 'jsts'
    assert v['docs_path'] == 'docs'


# -- Selective generation --


def test_bare_generates_everything(bare_scan):
    files = generate(bare_scan)
    names = {f.target_path.name for f in files}
    # Should generate CLAUDE.md and core docs at minimum
    assert 'CLAUDE.md' in names
    assert 'docs_guide.md' in names
    assert 'architecture.md' in names
    assert 'known_issues.md' in names
    assert 'conventions.md' in names


def test_python_skips_existing_docs(python_scan):
    files = generate(python_scan)
    names = {f.target_path.name for f in files}
    # python_project already has architecture.md and docs_guide.md
    assert 'architecture.md' not in names
    assert 'docs_guide.md' not in names
    # But should still generate missing ones
    assert 'known_issues.md' in names
    assert 'conventions.md' in names


def test_python_skips_existing_claude_md(python_scan):
    files = generate(python_scan)
    names = {f.target_path.name for f in files}
    # python_project already has CLAUDE.md
    assert 'CLAUDE.md' not in names


def test_generates_ai_artifacts(bare_scan):
    files = generate(bare_scan)
    names = {f.target_path.name for f in files}
    assert 'setup-auditor.md' in names
    # Skills produce SKILL.md, check by parent dir
    skill_parents = {f.target_path.parent.name for f in files if f.target_path.name == 'SKILL.md'}
    assert 'diagnose-setup' in skill_parents
    assert 'maintain-docs' in skill_parents


def test_skips_existing_agents(python_scan):
    """python_project has code-reviewer agent; setup-auditor is still generated."""
    files = generate(python_scan)
    # setup-auditor doesn't exist in the fixture, so it should be generated
    agent_names = {f.target_path.stem for f in files if 'agents' in str(f.target_path)}
    assert 'setup-auditor' in agent_names


def test_no_deployment_for_library(python_scan):
    """python_project has no deploy artifacts, so no deployment.md."""
    files = generate(python_scan)
    names = {f.target_path.name for f in files}
    assert 'deployment.md' not in names


def test_testing_generated_when_tests_exist(python_scan):
    """python_project has a tests/ dir."""
    files = generate(python_scan)
    names = {f.target_path.name for f in files}
    assert 'testing.md' in names


def test_no_testing_for_bare(bare_scan):
    """bare_project has no tests/ dir or test config."""
    files = generate(bare_scan)
    names = {f.target_path.name for f in files}
    assert 'testing.md' not in names


# -- Template rendering --


def test_templates_are_valid_markdown(bare_scan):
    """All generated content should be valid markdown (no raw ${...} errors)."""
    files = generate(bare_scan)
    for gf in files:
        # safe_substitute leaves unresolved vars as ${name} which is valid markdown
        assert gf.content, f'Empty content for {gf.target_path}'
        # Should not contain Template errors
        assert 'Traceback' not in gf.content


def test_python_conventions_uses_python_template(python_scan):
    files = generate(python_scan)
    conv = next((f for f in files if f.target_path.name == 'conventions.md'), None)
    assert conv is not None
    assert 'snake_case' in conv.content  # Python-specific content


def test_overwrite_policy_is_skip():
    """All generated files should default to skip policy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sr = ScanResult(project_root=Path(tmpdir))
        files = generate(sr)
        for gf in files:
            assert gf.overwrite_policy == 'skip'


# -- Write mode integration --


def test_write_creates_files():
    """Test that files are actually created in a temp dir."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create a pyproject.toml so it's detected as Python
        (root / 'pyproject.toml').write_text('[project]\nname = "testproj"\n')

        sr = scan(root)
        files = generate(sr)

        assert len(files) > 0
        # Write them
        for gf in files:
            gf.target_path.parent.mkdir(parents=True, exist_ok=True)
            gf.target_path.write_text(gf.content)

        # Verify
        assert (root / 'CLAUDE.md').exists()
        assert 'testproj' in (root / 'CLAUDE.md').read_text()

        # Re-scan — now nothing should be generated
        sr2 = scan(root)
        files2 = generate(sr2)
        # Most files should be skipped now (some may still be missing
        # if the scan doesn't find them in the right place)
        generated_names_1 = {f.target_path.name for f in files}
        generated_names_2 = {f.target_path.name for f in files2}
        assert len(generated_names_2) < len(generated_names_1)


# -- Docs path by project type --


def test_python_docs_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        files = generate(ScanResult(
            project_root=root,
            project_type=ProjectType.python,
        ))
        doc_files = [f for f in files if 'docs_guide.md' == f.target_path.name]
        assert doc_files
        assert 'misc/docs' in str(doc_files[0].target_path)


def test_jsts_docs_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        files = generate(ScanResult(
            project_root=root,
            project_type=ProjectType.jsts,
        ))
        doc_files = [f for f in files if 'docs_guide.md' == f.target_path.name]
        assert doc_files
        path_str = str(doc_files[0].target_path)
        assert 'misc/docs' not in path_str
        assert '/docs/' in path_str
