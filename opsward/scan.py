"""Read-only scanner: inspect a project and return a ScanResult.

This module NEVER writes to the target project.
"""

import json
import os
from pathlib import Path
from typing import Optional

from opsward.base import (
    AgentInfo,
    DocSpec,
    ProjectType,
    RuleInfo,
    ScanResult,
    SkillInfo,
)
from opsward.util import iter_files, iter_subdirs, read_json_safe, read_text_safe


_USER_CONFIG = object()  # sentinel: "the user's Claude config dir", resolved at call time


def default_claude_config_dir() -> Path:
    """``$CLAUDE_CONFIG_DIR`` if set, else ``~/.claude`` (what Claude Code itself uses)."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def scan(project_root: Path, *, claude_config_dir: object = _USER_CONFIG) -> ScanResult:
    """Scan *project_root* and return a ScanResult.

    ``claude_config_dir`` is the user's Claude Code config dir, whose ``skills/`` is
    the global scope a project skill competes with (shadowing, listing budget). It
    defaults to :func:`default_claude_config_dir`; pass ``None`` to read nothing
    outside the project (tests, portable goldens). Reading it is still read-only.

    >>> import tempfile, pathlib
    >>> r = scan(pathlib.Path(tempfile.mkdtemp()), claude_config_dir=None)
    >>> r.project_type, r.global_skills
    (<ProjectType.unknown: 'unknown'>, [])
    """
    project_root = Path(project_root).resolve()
    result = ScanResult(project_root=project_root)

    result.project_type = _detect_project_type(project_root)

    # CLAUDE.md — check root, then .claude/
    result.claude_md_path, result.claude_md_content = _find_claude_md(project_root)

    # .claude/ sub-directories
    claude_dir = project_root / ".claude"
    result.skills = list(_scan_skills(claude_dir / "skills", project_root=project_root))

    # The user's global skill scope
    cfg = default_claude_config_dir() if claude_config_dir is _USER_CONFIG else claude_config_dir
    if cfg is not None and (Path(cfg) / "skills").is_dir():
        result.global_skills_dir = Path(cfg) / "skills"
        result.global_skills = list(_scan_skills(result.global_skills_dir))
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


def _content_size(path: Path) -> int:
    """Byte size of *path* with line endings normalized to LF.

    The size feeds stub heuristics (``maintain``'s ``_MIN_DOC_BYTES``, ``score``'s
    empty-doc check) and is printed by ``diagnose -v``. Using the raw on-disk size
    made those host-dependent: Git for Windows defaults to ``core.autocrlf=true``,
    so the same doc measured larger there and could stop being flagged as a stub.

    >>> import tempfile, pathlib
    >>> d = pathlib.Path(tempfile.mkdtemp())
    >>> _ = (d / 'a.md').write_bytes(b'a\\r\\nb\\r\\n')
    >>> _content_size(d / 'a.md')
    4
    """
    return len(path.read_bytes().replace(b"\r\n", b"\n"))


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


def _scan_skills(skills_dir: Path, *, project_root: Optional[Path] = None):
    """Skills under *skills_dir*; with *project_root*, also where each entry's canonical twin would be."""
    for skill_path in iter_subdirs(skills_dir):
        skill_md = skill_path / "SKILL.md"
        has_skill_md = skill_md.is_file()
        description = ""
        frontmatter: dict = {}
        line_count = 0
        if has_skill_md:
            content = read_text_safe(skill_md)
            line_count = len(content.splitlines())
            frontmatter = _parse_frontmatter(content)
            description = _description_of(content, frontmatter)
        is_link = skill_path.is_symlink()
        try:
            real_path = skill_path.resolve()
        except OSError:
            real_path = None
        canonical = None
        if project_root is not None and not is_link:
            canonical = _canonical_skill_location(project_root, skill_path.name, skill_path)
        yield SkillInfo(
            name=skill_path.name,
            path=skill_path,
            has_skill_md=has_skill_md,
            description=description,
            frontmatter=frontmatter,
            line_count=line_count,
            is_link=is_link,
            real_path=real_path,
            canonical_path=canonical,
        )


def _canonical_skill_location(project_root: Path, name: str, exclude: Path) -> Optional[Path]:
    """``skills/<name>`` or ``<pkg>/data/skills/<name>`` holding a SKILL.md, other than *exclude*.

    These are the two real locations skill-package-setup allows; a real directory
    under ``.claude/skills`` next to one of them is the unmigrated state.
    """
    candidates = [project_root / "skills" / name]
    try:
        for child in project_root.iterdir():
            if child.is_dir() and not child.name.startswith(".") and child.name not in ("node_modules", "skills"):
                candidates.append(child / "data" / "skills" / name)
    except OSError:
        return None
    for cand in candidates:
        try:
            if (cand / "SKILL.md").is_file() and cand.resolve() != exclude.resolve():
                return cand
        except OSError:
            continue
    return None


def _scan_agents(agents_dir: Path):
    for agent_file in iter_files(agents_dir, suffix=".md"):
        content = read_text_safe(agent_file)
        frontmatter = _parse_frontmatter(content)
        name = str(frontmatter.get("name") or "").strip() or agent_file.stem
        yield AgentInfo(
            name=name,
            path=agent_file,
            description=_description_of(content, frontmatter),
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
        docs.append(DocSpec(name=f.stem, path=f, size_bytes=_content_size(f)))
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


def _strip_inline_comment(value: str) -> str:
    r"""Drop a trailing ``# comment`` from a YAML scalar, quoted or not.

    >>> _strip_inline_comment('plain  # c'), _strip_inline_comment('"q # not" # c'), _strip_inline_comment("'a''b'  # c")
    ('plain', '"q # not"', "'a''b'")
    """
    value = value.strip()
    if value[:1] in ("'", '"'):
        q = value[0]
        i = 1
        while i < len(value):
            if q == "'" and value[i] == "'" and value[i + 1 : i + 2] == "'":
                i += 2
                continue
            if q == '"' and value[i] == "\\":
                i += 2
                continue
            if value[i] == q:
                return value[: i + 1]
            i += 1
        return value
    cut = value.find(" #")
    return value[:cut].rstrip() if cut >= 0 else value


def _unquote(value: str) -> str:
    r"""Strip a comment, then quotes, decoding the escapes each quoting style allows.

    >>> _unquote('"a \\"b\\" \\u2014 c"  # x'), _unquote("'it''s'"), _unquote("bare  # x")
    ('a "b" — c', "it's", 'bare')
    """
    value = _strip_inline_comment(value)
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return str(json.loads(value))
        except ValueError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def _parse_flow_map(value: str) -> dict:
    """``{a: 1, b: two}`` -> ``{'a': '1', 'b': 'two'}`` (one level, no nesting)."""
    out: dict = {}
    for part in value.strip()[1:-1].split(","):
        if ":" in part:
            k, _, v = part.partition(":")
            out[k.strip()] = _unquote(v)
    return out


_BLOCK_SCALARS = frozenset({">", ">-", ">+", "|", "|-", "|+"})


def _parse_frontmatter(text: str) -> dict:
    r"""Extract YAML frontmatter from a SKILL.md file as a simple dict.

    Handles the subset of YAML used in agentskills.io spec frontmatter
    without requiring a YAML library: scalars (with ``# comments`` stripped),
    one level of nested keys (``metadata:``), inline flow maps
    (``metadata: {subagent: true}``), and folded/literal block scalars
    (``description: >-`` followed by indented lines).

    >>> _parse_frontmatter('---\nname: x\ndescription: >-\n  Line one,\n  line two: with colon.\nmetadata:\n  subagent: true  # opt in\n---\n')
    {'name': 'x', 'description': 'Line one, line two: with colon.', 'metadata': {'subagent': 'true'}}
    >>> _parse_frontmatter('---\nmetadata: {subagent: "true", subagent-model: haiku}\n---\n')['metadata']
    {'subagent': 'true', 'subagent-model': 'haiku'}
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
    block: list[str] | None = None  # continuation lines of a block scalar
    block_style = ""
    for line in lines[1:end]:
        stripped = line.strip()
        indented = bool(line) and line[0] in (" ", "\t")
        if block is not None and (indented or not stripped):
            block.append(stripped)
            continue
        if block is not None:
            result[current_key] = _join_block(block, block_style)
            block = None
        if not stripped or stripped.startswith("#"):
            continue
        if indented and current_key is not None:
            # Indented line = continuation of previous key (nested YAML)
            current = result.get(current_key)
            if ":" in stripped and not (isinstance(current, str) and current):
                k, _, v = stripped.partition(":")
                if not isinstance(current, dict):
                    result[current_key] = {}
                result[current_key][k.strip()] = _unquote(v)
            elif isinstance(current, str):
                # plain multi-line scalar
                result[current_key] = (result[current_key] + " " + _unquote(stripped)).strip()
            continue
        if ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = _strip_inline_comment(v.strip())
            current_key = k
            if v in _BLOCK_SCALARS:
                block, block_style = [], v
                result[k] = ""
            elif v.startswith("{") and v.endswith("}"):
                result[k] = _parse_flow_map(v)
            else:
                result[k] = _unquote(v)
    if block is not None and current_key is not None:
        result[current_key] = _join_block(block, block_style)
    return result


def _join_block(lines: list, style: str) -> str:
    """Join a block scalar's lines: folded (``>``) with spaces, literal (``|``) with newlines."""
    while lines and not lines[-1]:
        lines.pop()
    sep = "\n" if style.startswith("|") else " "
    return sep.join(lines).strip()


def _description_of(content: str, frontmatter: dict) -> str:
    """The frontmatter ``description`` if it is a usable string, else the body's first line."""
    desc = frontmatter.get("description")
    if isinstance(desc, str) and desc.strip():
        return " ".join(desc.split())
    body = content
    if content.startswith("---"):
        fence = content.find("\n---", 3)
        if fence > 0:
            body = content[fence + 4 :]
    return _first_line(body)


def _first_line(text: str) -> str:
    """Return the first non-empty, non-heading line of *text*."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""
