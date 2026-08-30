"""CLI entry point: ``python -m opsward`` and the ``opsward`` console script.

The command list is :data:`opsward.cli._dispatch_funcs` -- one SSOT, no per-command
registration here. :func:`cw.dispatch` turns it into an ``argparse`` parser and runs it,
reproducing the grammar this CLI has always had (pinned by ``misc/cli_golden_py*.json``
and asserted by ``tests/test_cli_parity.py``).

``prog`` is deliberately not passed: leaving it to ``argparse`` keeps the program name
derived from ``sys.argv[0]``, so ``python -m opsward`` still reports ``__main__.py`` and
the console script still reports ``opsward``, exactly as before.
"""

import cw

from opsward.cli import _dispatch_funcs


def main():
    """Parse ``sys.argv`` and run the command it names; return its exit code."""
    raise SystemExit(cw.dispatch(_dispatch_funcs))


if __name__ == "__main__":
    main()
