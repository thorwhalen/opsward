"""Tests for opsward.base dataclasses."""

from pathlib import Path

from opsward.base import (
    ComponentScore,
    DiagnosisReport,
    ProjectType,
    _score_bar,
)


def test_project_type_values():
    assert ProjectType.python.value == 'python'
    assert ProjectType.jsts.value == 'jsts'
    assert ProjectType.mixed.value == 'mixed'
    assert ProjectType.unknown.value == 'unknown'


def test_score_bar():
    assert _score_bar(100, 100) == '[' + '#' * 20 + ']'
    assert _score_bar(0, 100) == '[' + '.' * 20 + ']'
    assert _score_bar(50, 100) == '[' + '#' * 10 + '.' * 10 + ']'


def test_diagnosis_report_weighted_score():
    report = DiagnosisReport(
        project_root=Path('/tmp/test'),
        project_type=ProjectType.python,
        scores=[
            ComponentScore(name='a', score=80),
            ComponentScore(name='b', score=60),
        ],
        weighted_score=75.0,
    )
    assert report.overall_score == 75.0


def test_diagnosis_report_fallback_average():
    report = DiagnosisReport(
        project_root=Path('/tmp/test'),
        project_type=ProjectType.python,
        scores=[
            ComponentScore(name='a', score=80),
            ComponentScore(name='b', score=60),
        ],
    )
    # weighted_score defaults to 0.0 (falsy), so falls back to average
    assert report.overall_score == 70.0


def test_diagnosis_report_overall_score_empty():
    report = DiagnosisReport(
        project_root=Path('/tmp/test'),
        project_type=ProjectType.python,
    )
    assert report.overall_score == 0.0


def test_diagnosis_report_grades():
    for score, expected_grade in [(95, 'A'), (85, 'B'), (75, 'C'), (65, 'D'), (50, 'F')]:
        report = DiagnosisReport(
            project_root=Path('/tmp/test'),
            project_type=ProjectType.python,
            weighted_score=float(score),
        )
        assert report.grade == expected_grade, f'{score} -> {report.grade}'


def test_diagnosis_report_str():
    report = DiagnosisReport(
        project_root=Path('/tmp/test'),
        project_type=ProjectType.python,
        scores=[ComponentScore(name='CLAUDE.md', score=75, notes=['Missing skills section'])],
        missing_items=['docs_guide.md'],
        suggestions=['Add a docs_guide.md to index your docs'],
        weighted_score=75.0,
    )
    text = str(report)
    assert 'Diagnosis Report: test' in text
    assert 'CLAUDE.md' in text
    assert '75/100' in text
    assert 'Grade: C' in text
    assert 'Missing skills section' in text
    assert '[ ] docs_guide.md' in text
    assert 'Add a docs_guide.md' in text
