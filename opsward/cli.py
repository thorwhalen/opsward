"""CLI dispatch for opsward."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

from opsward.base import DiagnosisReport
from opsward.generate import generate as _generate, generate_skills as _generate_skills
from opsward.maintain import maintain as _maintain
from opsward.recommend import recommend_skills as _recommend_skills
from opsward.scan import scan
from opsward.score import diagnose as _diagnose


def _serialize_report(report: DiagnosisReport) -> dict:
    """Convert a DiagnosisReport to a JSON-serialisable dict."""
    d = asdict(report)
    d["project_root"] = str(report.project_root)
    d["project_type"] = report.project_type.value
    d["overall_score"] = report.overall_score
    d["grade"] = report.grade
    return d


def diagnose(
    *project_roots: str,
    format: str = "text",
    verbose: bool = False,
    min_score: int = 80,
):
    """Diagnose the AI agent setup of one or more projects.

    :param project_roots: one or more paths to project directories
    :param format: output format — 'text' or 'json'
    :param verbose: show additional detail in text output
    :param min_score: minimum overall score to pass (exit 0); below this exits 1
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
        report = _diagnose(sr)
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
    sys.exit(0 if worst >= min_score else 1)


def generate(
    *project_roots: str,
    write: bool = False,
    format: str = "text",
    agents_md: bool = False,
    hooks: bool = False,
):
    """Generate missing AI setup artifacts for one or more projects.

    By default, shows what would be created (dry run). Use --write to
    actually write files. Existing files are never overwritten.

    :param project_roots: one or more paths to project directories
    :param write: actually write files (default: dry run)
    :param format: output format — 'text' or 'json'
    :param agents_md: also generate AGENTS.md (cross-platform agent instructions)
    :param hooks: also generate starter hook scripts
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
        files = _generate(sr, agents_md=agents_md, hooks=hooks)
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


def maintain(
    *project_roots: str,
    format: str = "text",
):
    """Check for stale references, out-of-sync docs, and other drift.

    Each finding carries a recommended triage: align (update the config to match the
    code), revert (restore the code the config describes) or ignore (a legitimately
    volatile reference: put `opsward: ignore-path` on its line).

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
        suggestions = _maintain(sr)
        all_suggestions.extend(suggestions)

        if format == "json":
            continue

        if not suggestions:
            print(f"{root.name}: no maintenance issues found")
            continue

        print(f"{root.name}: {len(suggestions)} issue(s)\n")
        for ms in suggestions:
            print(f"  [{ms.category} → {ms.triage}] {ms.description}")
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
                "triage": ms.triage,
            }
            for ms in all_suggestions
        ]
        print(json.dumps(data, indent=2))

    sys.exit(0 if not all_suggestions else 1)


def _relative_path(path: Path, base: Path) -> str:
    """Return path relative to base, or absolute if not under base.

    Rendered with forward slashes regardless of host OS (#21): this is display
    text, not a filesystem path, and a Windows-separated path leaking into
    printed output (or into generated doc content) is not portable.
    """
    try:
        return path.relative_to(base).as_posix()
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


def install_skills(
    target: str = ".",
    *,
    global_install: bool = False,
    agents: bool = True,
    write: bool = False,
):
    """Install opsward's Claude Code skills (and agents) into a project or globally.

    By default, shows what would be created (dry run). Use --write to
    actually write files. Existing files are never overwritten.

    :param target: project directory (ignored when --global is set)
    :param global_install: install into ~/.claude/ instead of the project
    :param agents: also install agent definitions (default: True)
    :param write: actually write files (default: dry run)
    """
    if global_install:
        target_dir = Path.home() / ".claude"
    else:
        target_dir = Path(target).resolve() / ".claude"

    # Optionally scan the project for variable substitution
    sr = None
    if not global_install:
        project_root = Path(target).resolve()
        if project_root.is_dir():
            sr = scan(project_root)

    files = _generate_skills(
        target_dir,
        scan_result=sr,
        include_agents=agents,
    )

    if not files:
        print("Nothing to install — all skills already present.")
        return

    action = "Installing" if write else "Would install"
    print(f"{action} into {target_dir}/\n")

    for gf in files:
        rel = _relative_path(gf.target_path, target_dir)
        exists = gf.target_path.exists()
        if exists:
            print(f"  SKIP {rel}  (already exists)")
        else:
            print(f"  {action} {rel}")

        if write and not exists:
            gf.target_path.parent.mkdir(parents=True, exist_ok=True)
            gf.target_path.write_text(gf.content, encoding="utf-8")

    if not write:
        print("\nDry run — pass --write to install files.")


def recommend(
    *project_roots: str,
    format: str = "text",
):
    """Recommend ecosystem skills based on the project's tech stack.

    Analyzes dependencies and suggests skills from the community catalog.

    :param project_roots: one or more paths to project directories
    :param format: output format — 'text' or 'json'
    """
    if not project_roots:
        project_roots = (".",)

    all_recs = []
    for root_str in project_roots:
        root = Path(root_str).resolve()
        if not root.is_dir():
            print(f"Error: {root_str} is not a directory", file=sys.stderr)
            sys.exit(2)

        sr = scan(root)
        recs = _recommend_skills(sr)
        all_recs.extend(recs)

        if format != "json":
            if not recs:
                print(f"{root.name}: no skill recommendations")
            else:
                print(f"{root.name}: {len(recs)} recommended skill(s)\n")
                for rec in recs:
                    print(f"  {rec.name}")
                    print(f"    Reason: {rec.reason}")
                    print(f"    Source: {rec.source}")
                print()

    if format == "json":
        data = [
            {"name": r.name, "reason": r.reason, "source": r.source} for r in all_recs
        ]
        print(json.dumps(data, indent=2))


def find(
    query: str,
    *project_roots: str,
    kinds: str = "skill,agent",
    semantic: bool = False,
    limit: int = 10,
):
    """Find assets (skills, agents, docs) across one or more projects by QUERY.

    Cross-repo asset discovery via the toolery package
    (install with: pip install 'opsward[discovery]').

    :param query: search query
    :param project_roots: one or more project directories (default: current dir)
    :param kinds: comma-separated asset kinds — skill, agent, doc
    :param semantic: use toolery's ir semantic backend (needs toolery[ir])
    :param limit: max results to show
    """
    from opsward.discover import find_assets

    roots = project_roots or (".",)
    try:
        hits = find_assets(
            *roots, query=query, kinds=kinds, semantic=semantic, limit=limit
        )
    except ImportError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    if not hits:
        print(f"No assets matching {query!r} in {', '.join(roots)}.")
        return
    for card, score in hits:
        print(f"{score:6.2f}  [{card.kind}] {card.name}")
        if card.source_uri:
            print(f"          {card.source_uri}")


def fleet(
    *project_roots: str,
    under: str = "",
    depth: int = 1,
    format: str = "text",
    manifest: str = "",
):
    """Diagnose many projects at once and roll the results up into one fleet report.

    The fleet is the given roots, plus the git repos found under --under. With --manifest
    the fleet is remembered: the roots and the latest summary are written to that JSON
    file, and a later run with only --manifest re-diagnoses the same roots (given roots or
    --under replace them). The manifest holds this machine's absolute paths, so keep it
    out of version control. Exits 1 when any root could not be diagnosed.

    :param project_roots: project directories to diagnose
    :param under: also diagnose every git repo found under this directory
    :param depth: how many levels below --under to look for git repos
    :param format: output format — 'text' or 'json' (the name-keyed summary)
    :param manifest: JSON file that remembers the fleet's roots and its latest summary
    """
    from opsward.fleet import (
        fleet as _fleet,
        git_roots_under,
        manifest_roots,
        write_manifest,
    )

    roots = [str(Path(r).resolve()) for r in project_roots]
    if under:
        parent = Path(under)
        if not parent.is_dir():
            print(f"Error: {under} is not a directory", file=sys.stderr)
            sys.exit(2)
        roots += [str(p.resolve()) for p in git_roots_under(parent, depth=depth)]
        if not roots:
            print(f"Error: no git repos under {under}", file=sys.stderr)
            sys.exit(2)
    if manifest and not project_roots and not under:
        try:
            roots = manifest_roots(manifest)
        except (ValueError, OSError) as e:  # JSONDecodeError is a ValueError
            print(f"Error: cannot read the manifest: {e}", file=sys.stderr)
            sys.exit(2)
    if not roots:
        print(
            "Error: no roots — give project directories, --under DIR, "
            "or an existing --manifest",
            file=sys.stderr,
        )
        sys.exit(2)

    roots = list(dict.fromkeys(roots))
    report = _fleet(roots)
    if format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report)
    if manifest:
        # A typo'd root is not a fleet member: remember only roots that exist.
        members = [r for r in roots if report.errors.get(r) != "not a directory"]
        try:
            path = write_manifest(manifest, members, report)
        except OSError as e:
            print(f"Error: cannot write the manifest: {e}", file=sys.stderr)
            sys.exit(2)
        if _not_ignored_in_a_repo(path):
            print(
                f"Warning: {path.name} is inside a git work tree and not ignored; "
                "it holds this machine's paths, so add it to .gitignore",
                file=sys.stderr,
            )
    sys.exit(1 if report.errors else 0)


def lint(
    *project_roots: str,
    validators: str = "auto",
    format: str = "text",
):
    """Check skill specs and the hooks config: pass or fail, no score (exit 1 on any finding).

    The strict counterpart of `diagnose --min-score`, for CI and pre-commit. Validators:
    opsward (its own agentskills.io check, always there) and skill (the skill package's
    validate(); pip install 'opsward[lint]'). auto runs every one that is installed.

    :param project_roots: one or more project directories (default: current dir)
    :param validators: 'auto', or a comma list of: opsward, skill
    :param format: output format — 'text' or 'json'
    """
    from opsward.lint import lint as _lint, resolve_validators

    if format not in ("text", "json"):
        print("Error: format must be 'text' or 'json'", file=sys.stderr)
        sys.exit(2)
    try:
        chosen = resolve_validators(validators)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    findings = []
    for root_str in project_roots or (".",):
        root = Path(root_str).resolve()
        if not root.is_dir():
            print(f"Error: {root_str} is not a directory", file=sys.stderr)
            sys.exit(2)
        found = list(_lint(scan(root, claude_config_dir=None), validators=chosen))
        findings += [{"project": root.name, **f.to_dict()} for f in found]
        if format == "json":
            continue
        if not found:
            print(f"{root.name}: clean ({', '.join(chosen)})")
            continue
        print(f"{root.name}: {len(found)} finding(s) ({', '.join(chosen)})")
        for f in found:
            print(f"  {f}")
    if format == "json":
        print(json.dumps(findings, indent=2))
    sys.exit(1 if findings else 0)


def _not_ignored_in_a_repo(path: Path) -> bool:
    """True when ``path`` lies in a git work tree and is not ignored (no git: False)."""
    import subprocess

    try:
        done = subprocess.run(
            ["git", "check-ignore", "-q", path.name],
            cwd=path.parent,
            capture_output=True,
        )
    except OSError:
        return False
    return done.returncode == 1  # 0: ignored, 1: not ignored, 128: not a repo


def new(
    title: str,
    write: bool = False,
    project_root: str = ".",
    status: str = "Proposed",
    evidence: str = "",
):
    """Allocate the next numbered ADR for TITLE (dry run unless --write; never overwrites).

    :param title: the decision's title; the file name is derived from it
    :param write: actually write the file (default: dry run)
    :param project_root: the project directory (default: current dir)
    :param status: initial status — Proposed (default), or Accepted when the human has accepted it
    :param evidence: the issue, discussion or PR this rests on (a URL or #N)
    """
    from opsward.decisions import clean_title, new_adr

    if not clean_title(title):
        print("Error: the title is empty", file=sys.stderr)
        sys.exit(2)
    if status not in _ADR_STATUSES:
        print(
            f"Error: status must be one of {', '.join(_ADR_STATUSES)}", file=sys.stderr
        )
        sys.exit(2)
    root, decisions_dir = _decisions_dir(project_root)
    gf = new_adr(decisions_dir, title, status=status, evidence=evidence)
    rel = _relative_path(gf.target_path, root)
    if gf.target_path.exists():
        print(f"SKIP {rel}  (already exists)")
        sys.exit(1)
    if write:
        gf.target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(
            gf.target_path, "x", encoding="utf-8"
        ) as fh:  # exclusive: never over a file
            fh.write(gf.content)
        print(f"Created {rel}")
    else:
        print(f"Would create {rel}\n\nDry run — pass --write to create it.")


def note(text: str, write: bool = False, project_root: str = "."):
    """Append TEXT as a dated one-line decision (a Y-statement) to decisions/log.md (dry run unless --write).

    :param text: the decision: "In the context of …, facing …, we decided for …, because …"
    :param write: actually append (default: dry run); the log is created from its template when missing
    :param project_root: the project directory (default: current dir)
    """
    from opsward.decisions import log_append

    if not " ".join(text.split()):
        print("Error: the text is empty", file=sys.stderr)
        sys.exit(2)
    root, decisions_dir = _decisions_dir(project_root)
    try:
        path, content = log_append(decisions_dir, text)
    except (OSError, UnicodeDecodeError) as e:
        print(
            f"Error: cannot read the existing log, nothing written: {e}",
            file=sys.stderr,
        )
        sys.exit(2)
    rel = _relative_path(path, root)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Appended to {rel}")
    else:
        verb = "append to" if path.exists() else "create"
        print(
            f"Would {verb} {rel} a dated entry: {' '.join(text.split())}\n\nDry run — pass --write to do it."
        )


#: The statuses `decision new` will stamp. Accepting is the operator's act: pass
#: `--status Accepted` only when the human has said so (ADR 0010 §2).
_ADR_STATUSES = ("Proposed", "Accepted")


def _decisions_dir(project_root: str) -> tuple[Path, Path]:
    """(root, root/<docs>/decisions), by the same resolver `scan` uses to find ADRs."""
    from opsward.scan import docs_dir_for

    root = Path(project_root).resolve()
    if not root.is_dir():
        print(f"Error: {project_root} is not a directory", file=sys.stderr)
        sys.exit(2)
    sr = scan(root, claude_config_dir=None)
    return root, docs_dir_for(root, sr.project_type, sr.docs_guide_path) / "decisions"


# The SSOT of the CLI surface: a name -> command mapping, with one nested group.
_dispatch_funcs = {
    "diagnose": diagnose,
    "generate": generate,
    "maintain": maintain,
    "recommend": recommend,
    "install-skills": install_skills,
    "find": find,
    "fleet": fleet,
    "lint": lint,
    "decision": [new, note],
}
