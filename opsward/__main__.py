"""CLI entry point: python -m opsward."""

import argh

from opsward.cli import _dispatch_funcs


def main():
    argh.dispatch_commands(_dispatch_funcs)


if __name__ == '__main__':
    main()
