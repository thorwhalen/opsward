"""Assert opsward's command line has not moved since it was recorded.

``misc/cli_golden.json`` was recorded from the argh-based CLI *before* the migration to
``cw``; ``misc/cli_cases.txt`` is the corpus it was recorded from. This test replays it
against whatever dispatcher is installed now, so neither a refactor here nor a new ``cw``
release can change what a shell sees without a test going red.

Two tiers are asserted (see :mod:`cw.testing`):

* every case's exit code, stdout and stderr, verbatim; and
* the normalised ``usage:`` line of every ``--help`` case -- which names every option a
  parser has, so a lost flag or a changed ``nargs`` shows up here.

The full ``--help`` *body* is asserted only when the running CPython matches the one that
recorded the golden. CPython rewrites its own help rendering between versions (3.13 emits
``-f, --format FORMAT`` where 3.12 emits ``-f FORMAT, --format FORMAT``), and a golden
replayed across a version matrix would otherwise fail for something nobody caused.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN = REPO_ROOT / "misc" / "cli_golden.json"


def _console_script() -> str:
    """The installed ``opsward`` executable, however this environment lays it out."""
    found = shutil.which("opsward")
    if found:
        return found
    # A venv whose bin/ is not on PATH -- common under `uv run` and tox.
    for name in ("opsward", "opsward.exe"):
        candidate = Path(sys.executable).parent / name
        if candidate.exists():
            return str(candidate)
    pytest.fail(
        "the `opsward` console script is not installed; CLI parity cannot be checked. "
        "Install the package (`pip install -e .`) before running this test."
    )


def _recorded_python() -> tuple:
    """``(major, minor)`` of the CPython that recorded the golden."""
    recorded = json.loads(GOLDEN.read_text(encoding="utf-8"))["recorded_with"]["python"]
    return tuple(int(part) for part in recorded.split(".")[:2])


def test_cli_surface_is_unchanged():
    """Every recorded argv still produces the same exit code, stdout and stderr."""
    cw_testing = pytest.importorskip("cw.testing")
    cw_testing.assert_replay(
        GOLDEN,
        prog=[_console_script()],
        cwd=str(REPO_ROOT),
        strict_help=_recorded_python() == sys.version_info[:2],
    )
