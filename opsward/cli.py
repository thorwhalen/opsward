"""CLI dispatch for opsward."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

from opsward.base import DiagnosisReport
from opsward.generate import generate
from opsward.maintain import maintain
from opsward.scan import scan
from opsward.score import diagnose


def _serialize_report(report: DiagnosisReport) -> dict:
    """Convert a DiagnosisReport to a JSON-serialisable dict."""
    d = asdict(report)
    d["project_root"] = str(report.project_root)
    d["project_type"] = report.project_type.value
    d["overall_score"] = report.overall_score
    d["grade"] = report.grade
    return d


def diagnose_cmd(
    *project_roots: str,
    format: str = "text",
    verbose: bool = False,
):
    """Diagnose the AI agent setup of one or more projects.

    :param project_roots: one or more paths to project directories
    :param format: output format — 'text' or 'json'
    :param verbose: show additional detail in text output
    """
    if not project_roots:
        project_roots = (".",)

    reports = []
    for root_str in project_roots:
        root = Path(root_str).resolve()
        if not root.is_dir():
            print(f"Error: {root_str} is not a directory", file=sys.stderr)
            sys.exit(2)

        sr = scan(root)
        report = diagnose(sr)
        reports.append(report)

    if format == "json":
        data = [_serialize_report(r) for r in reports]
        output = data[0] if len(data) == 1 else data
        print(json.dumps(output, indent=2, default=str))
    else:
        for i, report in enumerate(reports):
            if i > 0:
                print("\n" + "=" * 60 + "\n")
            print(report)
            if verbose:
                sr = scan(report.project_root)
                _print_verbose(sr)

    worst = min(r.overall_score for r in reports)
    sys.exit(0 if worst >= 80 else 1)


def generate_cmd(
    *project_roots: str,
    write: bool = False,
    format: str = "text",
):
    """Generate missing AI setup artifacts for one or more projects.

    By default, shows what would be created (dry run). Use --write to
    actually write files. Existing files are never overwritten.

    :param project_roots: one or more paths to project directories
    :param write: actually write files (default: dry run)
    :param format: output format — 'text' or 'json'
    """
    if not project_roots:
        project_roots = (".",)

    all_files = []
    for root_str in project_roots:
        root = Path(root_str).resolve()
        if not root.is_dir():
            print(f"Error: {root_str} is not a directory", file=sys.stderr)
            sys.exit(2)

        sr = scan(root)
        files = generate(sr)
        all_files.extend(files)

        if format == "json":
            continue

        # Text output
        if not files:
            print(f"{root.name}: nothing to generate — all artifacts present")
            continue

        action = "Creating" if write else "Would create"
        print(f"{root.name}: {len(files)} artifact(s)\n")
        for gf in files:
            rel = _relative_path(gf.target_path, root)
            exists = gf.target_path.exists()
            if exists:
                print(f"  SKIP {rel}  (already exists)")
            else:
                print(f"  {action} {rel}")

            if write and not exists:
                gf.target_path.parent.mkdir(parents=True, exist_ok=True)
                gf.target_path.write_text(gf.content, encoding="utf-8")

        if not write:
            print(f"\nDry run — pass --write to create files.")

    if format == "json":
        data = [
            {
                "target_path": str(gf.target_path),
                "exists": gf.target_path.exists(),
                "overwrite_policy": gf.overwrite_policy,
                "content_length": len(gf.content),
            }
            for gf in all_files
        ]
        print(json.dumps(data, indent=2))


def maintain_cmd(
    *project_roots: str,
    format: str = "text",
):
    """Check for stale references, out-of-sync docs, and other drift.

    :param project_roots: one or more paths to project directories
    :param format: output format — 'text' or 'json'
    """
    if not project_roots:
        project_roots = (".",)

    all_suggestions = []
    for root_str in project_roots:
        root = Path(root_str).resolve()
        if not root.is_dir():
            print(f"Error: {root_str} is not a directory", file=sys.stderr)
            sys.exit(2)

        sr = scan(root)
        suggestions = maintain(sr)
        all_suggestions.extend(suggestions)

        if format == "json":
            continue

        if not suggestions:
            print(f"{root.name}: no maintenance issues found")
            continue

        print(f"{root.name}: {len(suggestions)} issue(s)\n")
        for ms in suggestions:
            print(f"  [{ms.category}] {ms.description}")
            if ms.diff:
                for line in ms.diff.splitlines():
                    print(f"    {line}")
        print()

    if format == "json":
        data = [
            {
                "category": ms.category,
                "description": ms.description,
                "diff": ms.diff,
            }
            for ms in all_suggestions
        ]
        print(json.dumps(data, indent=2))

    sys.exit(0 if not all_suggestions else 1)


def _relative_path(path: Path, base: Path) -> str:
    """Return path relative to base, or absolute if not under base."""
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def _print_verbose(sr):
    """Print extra scan details."""
    print("\nDetailed inventory:")
    print(f"  Skills:  {len(sr.skills)}")
    for s in sr.skills:
        print(f"    - {s.name} (SKILL.md: {'yes' if s.has_skill_md else 'no'})")
    print(f"  Agents:  {len(sr.agents)}")
    for a in sr.agents:
        print(f"    - {a.name}")
    print(f"  Rules:   {len(sr.rules)}")
    for r in sr.rules:
        print(f"    - {r.name}")
    print(f"  Docs:    {len(sr.docs)}")
    for d in sr.docs:
        print(f"    - {d.name} ({d.size_bytes} bytes)")
    print(f"  Hooks:   {'yes' if sr.hooks_config else 'no'}")


_dispatch_funcs = [diagnose_cmd, generate_cmd, maintain_cmd]
