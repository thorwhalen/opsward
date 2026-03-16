"""Read-only scanner: inspect a project and return a ScanResult.

This module NEVER writes to the target project.
"""

from pathlib import Path

from opsward.base import (
    AgentInfo,
    DocSpec,
    ProjectType,
    RuleInfo,
    ScanResult,
    SkillInfo,
)
from opsward.util import iter_files, iter_subdirs, read_json_safe, read_text_safe


def scan(project_root: Path) -> ScanResult:
    """Scan *project_root* and return a ScanResult.

    >>> import tempfile, pathlib
    >>> r = scan(pathlib.Path(tempfile.mkdtemp()))
    >>> r.project_type
    <ProjectType.unknown: 'unknown'>
    """
    project_root = Path(project_root).resolve()
    result = ScanResult(project_root=project_root)

    result.project_type = _detect_project_type(project_root)

    # CLAUDE.md — check root, then .claude/
    result.claude_md_path, result.claude_md_content = _find_claude_md(project_root)

    # .claude/ sub-directories
    claude_dir = project_root / ".claude"
    result.skills = list(_scan_skills(claude_dir / "skills"))
    result.agents = list(_scan_agents(claude_dir / "agents"))
    result.rules = list(_scan_rules(claude_dir / "rules"))

    # Hooks config
    result.hooks_path, result.hooks_config = _find_hooks(claude_dir)

    # Docs directory
    result.docs, result.has_docs_guide, result.docs_guide_path = _scan_docs(
        project_root
    )

    # AGENTS.md
    agents_md = project_root / "AGENTS.md"
    if agents_md.is_file():
        result.agents_md_path = agents_md
        result.agents_md_content = read_text_safe(agents_md)

    # Monorepo detection
    result.is_monorepo, result.monorepo_packages = _detect_monorepo(project_root)

    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _detect_project_type(root: Path) -> ProjectType:
    has_python = (
        (root / "pyproject.toml").exists()
        or (root / "setup.py").exists()
        or (root / "setup.cfg").exists()
        or (root / "requirements.txt").exists()
    )
    has_jsts = (root / "package.json").exists() or (root / "tsconfig.json").exists()
    if has_python and has_jsts:
        return ProjectType.mixed
    if has_python:
        return ProjectType.python
    if has_jsts:
        return ProjectType.jsts
    return ProjectType.unknown


def _find_claude_md(root: Path) -> tuple[Path | None, str]:
    for candidate in (root / "CLAUDE.md", root / ".claude" / "CLAUDE.md"):
        if candidate.is_file():
            return candidate, read_text_safe(candidate)
    return None, ""


def _scan_skills(skills_dir: Path):
    for skill_path in iter_subdirs(skills_dir):
        skill_md = skill_path / "SKILL.md"
        has_skill_md = skill_md.is_file()
        description = ""
        frontmatter: dict = {}
        line_count = 0
        if has_skill_md:
            content = read_text_safe(skill_md)
            description = _first_line(content)
            line_count = len(content.splitlines())
            frontmatter = _parse_frontmatter(content)
            if not description and "description" in frontmatter:
                description = frontmatter["description"]
        yield SkillInfo(
            name=skill_path.name,
            path=skill_path,
            has_skill_md=has_skill_md,
            description=description,
            frontmatter=frontmatter,
            line_count=line_count,
        )


def _scan_agents(agents_dir: Path):
    for agent_file in iter_files(agents_dir, suffix=".md"):
        content = read_text_safe(agent_file)
        yield AgentInfo(
            name=agent_file.stem,
            path=agent_file,
            description=_first_line(content),
        )


def _scan_rules(rules_dir: Path):
    for rule_file in iter_files(rules_dir, suffix=".md"):
        content = read_text_safe(rule_file)
        yield RuleInfo(
            name=rule_file.stem,
            path=rule_file,
            content=content,
        )


def _find_hooks(claude_dir: Path) -> tuple[Path | None, dict | None]:
    # hooks.json takes priority, then settings.local.json
    for name in ("hooks.json", "settings.local.json"):
        candidate = claude_dir / name
        if candidate.is_file():
            data = read_json_safe(candidate)
            if data is not None:
                return candidate, data
    return None, None


def _scan_docs(root: Path) -> tuple[list[DocSpec], bool, Path | None]:
    docs_dir = root / "docs"
    if not docs_dir.is_dir():
        # Also check misc/docs
        docs_dir = root / "misc" / "docs"
    if not docs_dir.is_dir():
        return [], False, None

    docs = []
    docs_guide_path = None
    has_docs_guide = False

    for f in iter_files(docs_dir, suffix=".md"):
        docs.append(DocSpec(name=f.stem, path=f, size_bytes=f.stat().st_size))
        if f.name == "docs_guide.md":
            has_docs_guide = True
            docs_guide_path = f

    return docs, has_docs_guide, docs_guide_path


def _detect_monorepo(root: Path) -> tuple[bool, list[str]]:
    """Detect monorepo structures (packages/, apps/, workspaces).

    Returns (is_monorepo, list of package directory names).
    """
    packages: list[str] = []
    # Common monorepo container directories
    for container_name in ("packages", "apps", "libs", "modules", "services"):
        container = root / container_name
        if not container.is_dir():
            continue
        for child in sorted(container.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            # Check if sub-package has its own manifest
            if (
                (child / "package.json").exists()
                or (child / "pyproject.toml").exists()
                or (child / "setup.py").exists()
            ):
                packages.append(f"{container_name}/{child.name}")

    # Also check for pnpm-workspace.yaml or lerna.json
    if not packages:
        for signal in ("pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json"):
            if (root / signal).exists():
                # It's a monorepo but we couldn't enumerate packages
                return True, []

    return bool(packages), packages


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a SKILL.md file as a simple dict.

    Handles the subset of YAML used in agentskills.io spec frontmatter
    without requiring a YAML library.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}

    result: dict = {}
    current_key = None
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Indented line = continuation of previous key (nested YAML)
        if line[0] in (" ", "\t") and current_key is not None:
            # Simple nested key-value → store under parent as dict
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if not isinstance(result.get(current_key), dict):
                    result[current_key] = {}
                result[current_key][k] = v
            continue
        if ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            result[k] = v
            current_key = k
    return result


def _first_line(text: str) -> str:
    """Return the first non-empty, non-heading line of *text*."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""
