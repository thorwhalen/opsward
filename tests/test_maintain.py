"""Tests for opsward.maintain."""

import tempfile
from pathlib import Path

import pytest

from opsward.maintain import maintain
from opsward.scan import scan

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture
def stale_scan():
    return scan(FIXTURES / 'stale_project')


@pytest.fixture
def python_scan():
    return scan(FIXTURES / 'python_project')


@pytest.fixture
def bare_scan():
    return scan(FIXTURES / 'bare_project')


# -- Stale paths in CLAUDE.md --


def test_detects_stale_paths(stale_scan):
    suggestions = maintain(stale_scan)
    stale = [s for s in suggestions if s.category == 'stale_path']
    assert len(stale) >= 2  # src/core.py and src/utils.py
    descriptions = ' '.join(s.description for s in stale)
    assert 'src/core.py' in descriptions
    assert 'src/utils.py' in descriptions


def test_no_stale_paths_when_no_claude_md(bare_scan):
    suggestions = maintain(bare_scan)
    stale = [s for s in suggestions if s.category == 'stale_path']
    assert stale == []


# -- docs_guide.md sync --


def test_detects_unlisted_doc(stale_scan):
    suggestions = maintain(stale_scan)
    sync = [s for s in suggestions if s.category == 'sync_issue']
    unlisted = [s for s in sync if 'unlisted_doc' in s.description]
    assert len(unlisted) == 1
    assert 'not listed in docs_guide.md' in unlisted[0].description


def test_detects_missing_referenced_doc(stale_scan):
    suggestions = maintain(stale_scan)
    sync = [s for s in suggestions if s.category == 'sync_issue']
    missing = [s for s in sync if 'deleted_doc' in s.description]
    assert len(missing) == 1
    assert 'does not exist' in missing[0].description


def test_sync_diff_provided_for_unlisted(stale_scan):
    suggestions = maintain(stale_scan)
    unlisted = [
        s for s in suggestions
        if s.category == 'sync_issue' and 'not listed' in s.description
    ]
    for s in unlisted:
        assert s.diff, f'Expected diff for: {s.description}'
        assert '+' in s.diff


def test_no_sync_issues_when_no_docs_guide(bare_scan):
    suggestions = maintain(bare_scan)
    sync = [s for s in suggestions if s.category == 'sync_issue']
    assert sync == []


# -- Clean project has no issues (or minimal) --


def test_clean_project_minimal_issues(python_scan):
    suggestions = maintain(python_scan)
    # The python fixture is reasonably clean; should have no stale paths
    stale = [s for s in suggestions if s.category == 'stale_path']
    assert stale == []


# -- Empty docs detection --


def test_detects_empty_docs():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        docs = root / 'docs'
        docs.mkdir()
        # Create a tiny stub doc
        (docs / 'stub.md').write_text('# S')
        # Create a real doc
        (docs / 'real.md').write_text('# Real\n\n' + 'Content ' * 20)

        sr = scan(root)
        suggestions = maintain(sr)
        empty = [s for s in suggestions if s.category == 'empty_doc']
        assert len(empty) == 1
        assert 'stub' in empty[0].description


# -- Skills without description --


def test_skill_without_skill_md():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        skill_dir = root / '.claude' / 'skills' / 'broken-skill'
        skill_dir.mkdir(parents=True)
        # No SKILL.md

        sr = scan(root)
        suggestions = maintain(sr)
        incomplete = [s for s in suggestions if s.category == 'incomplete_skill']
        assert len(incomplete) == 1
        assert 'broken-skill' in incomplete[0].description


# -- Integration: maintain returns list --


def test_maintain_returns_list(stale_scan):
    result = maintain(stale_scan)
    assert isinstance(result, list)
    for s in result:
        assert hasattr(s, 'category')
        assert hasattr(s, 'description')
        assert hasattr(s, 'diff')


# -- Categories are from a known set --


_KNOWN_CATEGORIES = {
    'stale_path', 'sync_issue', 'outdated_doc',
    'incomplete_skill', 'empty_doc',
}


def test_all_categories_known(stale_scan):
    suggestions = maintain(stale_scan)
    for s in suggestions:
        assert s.category in _KNOWN_CATEGORIES, (
            f'Unknown category: {s.category}'
        )
