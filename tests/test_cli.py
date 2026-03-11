"""Tests for opsward.cli output."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / 'fixtures'


def _run_cli(*args, expect_rc=None):
    """Run opsward CLI and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        [sys.executable, '-m', 'opsward', *args],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    if expect_rc is not None:
        assert result.returncode == expect_rc, (
            f'Expected rc={expect_rc}, got {result.returncode}\n'
            f'stderr: {result.stderr}'
        )
    return result.stdout, result.stderr, result.returncode


# -- Text output --


def test_text_output_contains_report():
    stdout, _, _ = _run_cli('diagnose-cmd', str(FIXTURES / 'python_project'))
    assert 'Diagnosis Report' in stdout
    assert 'CLAUDE.md quality' in stdout
    assert 'Grade:' in stdout


def test_text_output_bare_project():
    stdout, _, rc = _run_cli('diagnose-cmd', str(FIXTURES / 'bare_project'))
    assert 'Grade: F' in stdout
    assert rc == 1  # issues found


# -- JSON output --


def test_json_output_valid():
    stdout, _, _ = _run_cli(
        'diagnose-cmd', str(FIXTURES / 'python_project'), '--format', 'json'
    )
    data = json.loads(stdout)
    assert 'overall_score' in data
    assert 'grade' in data
    assert 'scores' in data
    assert isinstance(data['scores'], list)


def test_json_output_has_all_fields():
    stdout, _, _ = _run_cli(
        'diagnose-cmd', str(FIXTURES / 'python_project'), '--format', 'json'
    )
    data = json.loads(stdout)
    assert data['project_type'] == 'python'
    score_names = {s['name'] for s in data['scores']}
    assert 'CLAUDE.md quality' in score_names


# -- Error handling --


def test_nonexistent_path():
    _, stderr, rc = _run_cli('diagnose-cmd', '/nonexistent/path/12345')
    assert rc == 2
    assert 'not a directory' in stderr.lower() or 'error' in stderr.lower()
