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
    stdout, _, _ = _run_cli('diagnose', str(FIXTURES / 'python_project'))
    assert 'Diagnosis Report' in stdout
    assert 'CLAUDE.md quality' in stdout
    assert 'Grade:' in stdout


def test_text_output_bare_project():
    stdout, _, rc = _run_cli('diagnose', str(FIXTURES / 'bare_project'))
    assert 'Grade: F' in stdout
    assert rc == 1  # issues found


# -- JSON output --


def test_json_output_valid():
    stdout, _, _ = _run_cli(
        'diagnose', str(FIXTURES / 'python_project'), '--format', 'json'
    )
    data = json.loads(stdout)
    assert 'overall_score' in data
    assert 'grade' in data
    assert 'scores' in data
    assert isinstance(data['scores'], list)


def test_json_output_has_all_fields():
    stdout, _, _ = _run_cli(
        'diagnose', str(FIXTURES / 'python_project'), '--format', 'json'
    )
    data = json.loads(stdout)
    assert data['project_type'] == 'python'
    score_names = {s['name'] for s in data['scores']}
    assert 'CLAUDE.md quality' in score_names


# -- Error handling --


def test_nonexistent_path():
    _, stderr, rc = _run_cli('diagnose', '/nonexistent/path/12345')
    assert rc == 2
    assert 'not a directory' in stderr.lower() or 'error' in stderr.lower()


# -- eval (report-only; only the free rubric judge is exercised) --


def test_eval_finds_golden_tasks_in_the_docs_folder(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('')
    (tmp_path / 'CLAUDE.md').write_text('# P\n\nAlways run `pytest -x`.\n')
    tasks_file = tmp_path / 'misc' / 'docs' / 'evals' / 'golden_tasks.json'
    tasks_file.parent.mkdir(parents=True)
    tasks_file.write_text(
        json.dumps([{'name': 't', 'prompt': 'Test it.', 'expect': ['pytest -x']}])
    )
    stdout, _, _ = _run_cli('eval', str(tmp_path), '-f', 'json', expect_rc=0)
    out = json.loads(stdout)
    assert out['judge']['judge'] == 'rubric'
    assert out['golden']['delta'] == 1.0


def test_eval_without_claude_md_or_tasks_still_exits_0():
    stdout, _, _ = _run_cli(
        'eval', str(FIXTURES / 'bare_project'), '-f', 'json', expect_rc=0
    )
    assert json.loads(stdout) == {
        'project': 'bare_project',
        'judge': None,
        'golden': None,
    }


@pytest.mark.parametrize(
    'args, message',
    [
        (['--judge', 'nope'], 'judge must be'),
        (['--samples', '0'], 'at least 1'),
        (['--tasks', 'no/such/tasks.json'], 'is not a file'),
    ],
)
def test_eval_usage_errors_exit_2(args, message):
    _, stderr, _ = _run_cli(
        'eval', str(FIXTURES / 'python_project'), *args, expect_rc=2
    )
    assert message in stderr


def test_eval_reports_a_malformed_tasks_file(tmp_path):
    bad = tmp_path / 'tasks.json'
    bad.write_text('{"not": "a list"}')
    _, stderr, _ = _run_cli(
        'eval', str(FIXTURES / 'python_project'), '--tasks', str(bad), expect_rc=2
    )
    assert 'cannot read the golden tasks' in stderr


def test_eval_reports_duplicate_task_names(tmp_path):
    dupes = tmp_path / 'tasks.json'
    dupes.write_text(json.dumps([{'name': 'a', 'prompt': 'x'}] * 2))
    _, stderr, _ = _run_cli(
        'eval', str(FIXTURES / 'python_project'), '--tasks', str(dupes), expect_rc=2
    )
    assert 'must be unique' in stderr
