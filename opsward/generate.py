"""Template loading and generation. ScanResult -> list[GeneratedFile].

Never overwrites existing files (overwrite_policy='skip' by default).
"""

import importlib.resources
from pathlib import Path
from string import Template

from opsward.base import GeneratedFile, ProjectType, ScanResult
from opsward.util import read_text_safe

# Skills that opsward installs — each maps to shared/<name>/SKILL.md template
_SKILL_NAMES = (
    "opsward",
    "opsward-diagnose",
    "opsward-generate",
    "opsward-maintain",
)

# Agent definitions that opsward installs
_AGENT_NAMES = ("setup-auditor",)


def generate(scan_result: ScanResult) -> list[GeneratedFile]:
    """Determine which artifacts are missing, render templates, return files to create.

    >>> from pathlib import Path
    >>> from opsward.base import ScanResult
    >>> files = generate(ScanResult(project_root=Path('/tmp/empty')))
    >>> any(f.target_path.name == 'CLAUDE.md' for f in files)
    True
    """
    sr = scan_result
    variables = _build_variables(sr)
    docs_path = _docs_path(sr.project_type)
    existing_docs = {d.name for d in sr.docs}
    existing_skills = {s.name for s in sr.skills}
    existing_agents = {a.name for a in sr.agents}

    files: list[GeneratedFile] = []

    # ---- CLAUDE.md ----
    if sr.claude_md_path is None:
        files.append(
            _render(
                "shared/claude_md.md",
                sr.project_root / "CLAUDE.md",
                variables,
            )
        )

    # ---- Documentation layer ----
    # Always-generated docs
    for doc_name in ("docs_guide", "architecture", "known_issues", "conventions"):
        if doc_name not in existing_docs:
            template_name = _template_for_doc(doc_name, sr.project_type)
            target = sr.project_root / docs_path / f"{doc_name}.md"
            files.append(_render(template_name, target, variables))

    # Conditional docs
    if _has_tests(sr) and "testing" not in existing_docs:
        template_name = _template_for_doc("testing", sr.project_type)
        target = sr.project_root / docs_path / "testing.md"
        files.append(_render(template_name, target, variables))

    if _has_deploy_artifacts(sr) and "deployment" not in existing_docs:
        target = sr.project_root / docs_path / "deployment.md"
        files.append(_render("shared/deployment.md", target, variables))

    # Offered docs (always generated if missing, low priority)
    if "roadmap" not in existing_docs:
        target = sr.project_root / docs_path / "roadmap.md"
        files.append(_render("shared/roadmap.md", target, variables))

    # Decisions template
    decisions_dir = sr.project_root / docs_path / "decisions"
    template_target = decisions_dir / "0000-template.md"
    if not template_target.exists():
        files.append(
            _render(
                "shared/decisions/0000-template.md",
                template_target,
                variables,
            )
        )

    # ---- AI configuration layer ----
    # setup-auditor agent
    if "setup-auditor" not in existing_agents:
        target = sr.project_root / ".claude" / "agents" / "setup-auditor.md"
        files.append(_render("shared/setup-auditor.md", target, variables))

    # AI-enhanced skills (invoke opsward CLI + Claude interpretation)
    for skill_name in _SKILL_NAMES:
        if skill_name not in existing_skills:
            target = sr.project_root / ".claude" / "skills" / skill_name / "SKILL.md"
            files.append(
                _render(
                    f"shared/{skill_name}/SKILL.md",
                    target,
                    variables,
                )
            )

    return files


# ---------------------------------------------------------------------------
# Template loading via importlib.resources
# ---------------------------------------------------------------------------


def _load_template(name: str) -> str:
    """Load a template file from opsward.data.templates."""
    templates = importlib.resources.files("opsward.data.templates")
    return (templates / name).read_text(encoding="utf-8")


def _render(
    template_name: str,
    target_path: Path,
    variables: dict[str, str],
) -> GeneratedFile:
    """Load template, substitute variables, return a GeneratedFile."""
    raw = _load_template(template_name)
    # Use safe_substitute so unset variables remain as ${name} (valid markdown)
    content = Template(raw).safe_substitute(variables)
    return GeneratedFile(target_path=target_path, content=content)


# ---------------------------------------------------------------------------
# Targeted skill/agent generation (for install-skills command)
# ---------------------------------------------------------------------------


def generate_skills(
    target_dir: Path,
    *,
    scan_result: ScanResult | None = None,
    include_agents: bool = True,
) -> list[GeneratedFile]:
    """Generate only the opsward skill and agent files for *target_dir*.

    If *scan_result* is provided, template variables are substituted from the
    scan.  Otherwise templates are rendered without project-specific
    substitution (suitable for global ``~/.claude/`` installation).

    >>> from pathlib import Path
    >>> files = generate_skills(Path('/tmp/test'))
    >>> any('opsward-diagnose' in str(f.target_path) for f in files)
    True
    """
    variables = _build_variables(scan_result) if scan_result is not None else {}
    files: list[GeneratedFile] = []

    for skill_name in _SKILL_NAMES:
        target = target_dir / "skills" / skill_name / "SKILL.md"
        files.append(_render(f"shared/{skill_name}/SKILL.md", target, variables))

    if include_agents:
        for agent_name in _AGENT_NAMES:
            target = target_dir / "agents" / f"{agent_name}.md"
            files.append(_render(f"shared/{agent_name}.md", target, variables))

    return files


# ---------------------------------------------------------------------------
# Variable extraction from ScanResult
# ---------------------------------------------------------------------------


def _build_variables(sr: ScanResult) -> dict[str, str]:
    """Extract template variables from a ScanResult."""
    root = sr.project_root
    project_name = _detect_project_name(sr)
    project_description = _detect_description(sr)
    docs_path = _docs_path(sr.project_type)

    return {
        "project_name": project_name,
        "project_description": project_description,
        "project_type": sr.project_type.value,
        "docs_path": docs_path,
        "tech_stack": _detect_tech_stack(sr),
        "module_map": _detect_module_map(sr),
        "commands": _detect_commands(sr),
        "conventions": _detect_conventions_summary(sr),
        "package_manager": _detect_package_manager(sr),
        "formatter": _detect_formatter(sr),
        "linter": _detect_linter(sr),
        "line_length": _detect_line_length(sr),
        "test_framework": _detect_test_framework(sr),
        "test_command": _detect_test_command(sr),
        "test_dir": _detect_test_dir(sr),
        "coverage_command": _detect_coverage_command(sr),
        "additional_docs_table": _build_additional_docs_table(sr),
        "glossary_entries": "| <!-- Add terms here --> | |",
        "env_vars_table": "| <!-- Add variables here --> | | |",
    }


def _docs_path(project_type: ProjectType) -> str:
    if project_type == ProjectType.jsts:
        return "docs"
    return "misc/docs"


def _detect_project_name(sr: ScanResult) -> str:
    root = sr.project_root
    # Try pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        for line in read_text_safe(pyproject).splitlines():
            if line.strip().startswith("name"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    return parts[1].strip().strip('"').strip("'")
    # Try package.json
    import json

    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(read_text_safe(pkg))
            if "name" in data:
                return data["name"]
        except (json.JSONDecodeError, ValueError):
            pass
    return root.name


def _detect_description(sr: ScanResult) -> str:
    root = sr.project_root
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        for line in read_text_safe(pyproject).splitlines():
            if line.strip().startswith("description"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    return parts[1].strip().strip('"').strip("'")
    import json

    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(read_text_safe(pkg))
            if "description" in data:
                return data["description"]
        except (json.JSONDecodeError, ValueError):
            pass
    return f"A {sr.project_type.value} project"


def _detect_tech_stack(sr: ScanResult) -> str:
    parts = []
    root = sr.project_root
    if sr.project_type in (ProjectType.python, ProjectType.mixed):
        parts.append("Python")
    if sr.project_type in (ProjectType.jsts, ProjectType.mixed):
        if (root / "tsconfig.json").exists():
            parts.append("TypeScript")
        else:
            parts.append("JavaScript")
    if not parts:
        parts.append(sr.project_type.value)
    return ", ".join(parts)


def _detect_module_map(sr: ScanResult) -> str:
    root = sr.project_root
    if not root.is_dir():
        return "<!-- Add module descriptions -->"
    lines = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        if child.name in ("node_modules", "__pycache__", ".git", "dist", "build"):
            continue
        if child.is_dir():
            lines.append(f"- `{child.name}/` — ")
        elif child.suffix in (".py", ".ts", ".js", ".json", ".toml", ".yaml", ".yml"):
            lines.append(f"- `{child.name}` — ")
    return "\n".join(lines) if lines else "<!-- Add module descriptions -->"


def _detect_commands(sr: ScanResult) -> str:
    root = sr.project_root
    commands = []
    if sr.project_type in (ProjectType.python, ProjectType.mixed):
        if (root / "pyproject.toml").exists():
            commands.append('```bash\npip install -e ".[dev]"\npytest\n```')
    if sr.project_type in (ProjectType.jsts, ProjectType.mixed):
        pm = _detect_package_manager(sr)
        commands.append(f"```bash\n{pm} install\n{pm} run build\n{pm} test\n```")
    return "\n".join(commands) if commands else "<!-- Add build/test/run commands -->"


def _detect_package_manager(sr: ScanResult) -> str:
    root = sr.project_root
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists():
        return "bun"
    if (root / "package-lock.json").exists():
        return "npm"
    if sr.project_type in (ProjectType.jsts, ProjectType.mixed):
        return "npm"
    return "pip"


def _detect_formatter(sr: ScanResult) -> str:
    root = sr.project_root
    pyproject_text = read_text_safe(root / "pyproject.toml")
    if "ruff" in pyproject_text:
        return "ruff format"
    if "black" in pyproject_text:
        return "black"
    if (root / ".prettierrc").exists() or (root / ".prettierrc.json").exists():
        return "prettier"
    if (root / "biome.json").exists():
        return "biome"
    return "not configured"


def _detect_linter(sr: ScanResult) -> str:
    root = sr.project_root
    pyproject_text = read_text_safe(root / "pyproject.toml")
    if "ruff" in pyproject_text:
        return "ruff"
    if "pylint" in pyproject_text:
        return "pylint"
    if (root / ".eslintrc.json").exists() or (root / ".eslintrc.js").exists():
        return "eslint"
    if (root / "biome.json").exists():
        return "biome"
    return "not configured"


def _detect_line_length(sr: ScanResult) -> str:
    pyproject_text = read_text_safe(sr.project_root / "pyproject.toml")
    for line in pyproject_text.splitlines():
        if "line-length" in line or "line_length" in line:
            parts = line.split("=", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return "88"


def _detect_test_framework(sr: ScanResult) -> str:
    root = sr.project_root
    pyproject_text = read_text_safe(root / "pyproject.toml")
    if "pytest" in pyproject_text:
        return "pytest"
    if (root / "vitest.config.ts").exists():
        return "vitest"
    if (root / "jest.config.js").exists() or (root / "jest.config.ts").exists():
        return "jest"
    return "not detected"


def _detect_test_command(sr: ScanResult) -> str:
    fw = _detect_test_framework(sr)
    if fw == "pytest":
        return "pytest"
    if fw == "vitest":
        pm = _detect_package_manager(sr)
        return f"{pm} run test"
    if fw == "jest":
        pm = _detect_package_manager(sr)
        return f"{pm} test"
    return "# configure test command"


def _detect_test_dir(sr: ScanResult) -> str:
    root = sr.project_root
    if (root / "tests").is_dir():
        return "tests"
    if (root / "test").is_dir():
        return "test"
    if (root / "__tests__").is_dir():
        return "__tests__"
    if (root / "src" / "__tests__").is_dir():
        return "src/__tests__"
    return "tests"


def _detect_coverage_command(sr: ScanResult) -> str:
    fw = _detect_test_framework(sr)
    if fw == "pytest":
        return "pytest --cov"
    if fw in ("vitest", "jest"):
        pm = _detect_package_manager(sr)
        return f"{pm} run test -- --coverage"
    return "# configure coverage command"


def _detect_conventions_summary(sr: ScanResult) -> str:
    parts = []
    formatter = _detect_formatter(sr)
    linter = _detect_linter(sr)
    if formatter != "not configured":
        parts.append(f"- Use `{formatter}` for formatting")
    if linter != "not configured":
        parts.append(f"- Use `{linter}` for linting")
    return "\n".join(parts) if parts else "<!-- Add project conventions -->"


def _build_additional_docs_table(sr: ScanResult) -> str:
    """Build markdown table rows for docs beyond the core three."""
    core = {"architecture", "conventions", "known_issues", "docs_guide"}
    lines = []
    for doc in sr.docs:
        if doc.name not in core:
            lines.append(f"| [{doc.name}.md]({doc.name}.md) | | |")
    return "\n".join(lines) if lines else "| *No additional docs yet* | | |"


# ---------------------------------------------------------------------------
# Selective generation helpers
# ---------------------------------------------------------------------------


def _template_for_doc(doc_name: str, project_type: ProjectType) -> str:
    """Return the best template path for a doc, preferring type-specific."""
    type_key = "python" if project_type != ProjectType.jsts else "jsts"
    type_specific = f"{type_key}/{doc_name}.md"

    # Check if type-specific template exists
    try:
        _load_template(type_specific)
        return type_specific
    except (FileNotFoundError, TypeError, OSError):
        return f"shared/{doc_name}.md"


def _has_tests(sr: ScanResult) -> bool:
    root = sr.project_root
    return (
        (root / "tests").is_dir()
        or (root / "test").is_dir()
        or (root / "__tests__").is_dir()
        or _detect_test_framework(sr) != "not detected"
    )


def _has_deploy_artifacts(sr: ScanResult) -> bool:
    root = sr.project_root
    return (
        (root / "Dockerfile").exists()
        or (root / "docker-compose.yml").exists()
        or (root / "docker-compose.yaml").exists()
        or (root / ".github" / "workflows").is_dir()
        or (root / "Procfile").exists()
        or (root / "fly.toml").exists()
        or (root / "render.yaml").exists()
    )
