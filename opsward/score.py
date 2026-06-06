"""Pure scoring functions. ScanResult -> DiagnosisReport.

All functions are pure — same input, same output.
"""

import re
from collections.abc import Sequence
from pathlib import Path

from opsward.base import ComponentScore, DiagnosisReport, ScanResult, SkillInfo


# ---------------------------------------------------------------------------
# Weights for overall health score (from scoring_rubric.md)
# ---------------------------------------------------------------------------

_OVERALL_WEIGHTS: dict[str, float] = {
    "CLAUDE.md quality": 0.35,
    "Documentation": 0.25,
    "Skills": 0.20,
    "Setup (rules/agents/hooks)": 0.10,
    "Cross-references": 0.10,
}

# Core docs the rubric expects
_CORE_DOCS = {"architecture", "known_issues", "conventions"}


def diagnose(scan_result: ScanResult) -> DiagnosisReport:
    """Score a ScanResult and return a DiagnosisReport.

    >>> from pathlib import Path
    >>> from opsward.base import ScanResult
    >>> r = diagnose(ScanResult(project_root=Path('/tmp/empty')))
    >>> r.grade
    'F'
    """
    scores: list[ComponentScore] = []
    missing: list[str] = []
    suggestions: list[str] = []

    # 1. CLAUDE.md quality (max 100, 6 dimensions)
    claude_score = _score_claude_md(
        scan_result.claude_md_content,
        scan_result.project_root,
        missing=missing,
        suggestions=suggestions,
    )
    scores.append(claude_score)

    # 2. Documentation completeness (max 100)
    doc_score = _score_docs(scan_result, missing=missing, suggestions=suggestions)
    scores.append(doc_score)

    # 3. Skills (max 100)
    skills_score = _score_skills(scan_result, missing=missing, suggestions=suggestions)
    scores.append(skills_score)

    # 4. Setup: rules, agents, hooks (max 100)
    setup_score = _score_setup(scan_result, suggestions=suggestions)
    scores.append(setup_score)

    # 5. Cross-reference integrity (max 100)
    xref_score = _score_cross_references(scan_result, suggestions=suggestions)
    scores.append(xref_score)

    # 6. AGENTS.md cross-platform check (advisory, not scored)
    _check_agents_md(scan_result, suggestions=suggestions)

    # Weighted overall
    score_map = {s.name: s.score for s in scores}
    weighted = sum(
        score_map.get(name, 0) * weight for name, weight in _OVERALL_WEIGHTS.items()
    )

    return DiagnosisReport(
        project_root=scan_result.project_root,
        project_type=scan_result.project_type,
        scores=scores,
        missing_items=missing,
        suggestions=suggestions,
        weighted_score=weighted,
    )


# ---------------------------------------------------------------------------
# CLAUDE.md scoring — 6 dimensions, mapped to 0-100
# ---------------------------------------------------------------------------

# Dimension max scores (sum = 100)
_CMD_MAX = 20
_ARCH_MAX = 20
_CONV_MAX = 15
_CONCISE_MAX = 15
_CURRENCY_MAX = 15
_ACTION_MAX = 15


def _score_claude_md(
    content: str,
    project_root: Path,
    *,
    missing: list[str],
    suggestions: list[str],
) -> ComponentScore:
    if not content:
        missing.append("CLAUDE.md")
        suggestions.append("Create a CLAUDE.md at the project root")
        return ComponentScore(
            name="CLAUDE.md quality", score=0, notes=["No CLAUDE.md found"]
        )

    notes: list[str] = []
    total = 0

    total += _dim_commands(content, notes)
    total += _dim_architecture(content, notes)
    total += _dim_conventions(content, notes)
    total += _dim_conciseness(content, notes)
    total += _dim_currency(content, project_root, notes)
    total += _dim_actionability(content, notes)

    return ComponentScore(name="CLAUDE.md quality", score=total, notes=notes)


def _dim_commands(content: str, notes: list[str]) -> int:
    """Commands & Workflows (0-20)."""
    code_blocks = re.findall(r"```[\s\S]*?```", content)
    lower = content.lower()

    cmd_keywords = {"test", "build", "lint", "run", "dev", "start", "install"}
    found = {kw for kw in cmd_keywords if kw in lower}

    if not code_blocks:
        notes.append(
            "Commands: no code blocks found "
            "→ add a fenced code block with the build, test, and run commands"
        )
        return 0

    if len(found) >= 5:
        return _CMD_MAX
    if len(found) >= 3:
        notes.append(
            f"Commands: {len(found)} command keyword(s) found "
            "→ document the rest (build, test, lint, run, install) for full credit"
        )
        return 13
    if len(found) >= 1:
        notes.append(
            f"Commands: only {len(found)} command keyword(s) found "
            "→ document build, test, lint, run, and install commands"
        )
        return 7
    notes.append(
        "Commands: code blocks present but no build/test/lint keywords "
        "→ label the commands (build, test, run) so an agent knows what they do"
    )
    return 3


def _dim_architecture(content: str, notes: list[str]) -> int:
    """Architecture Clarity (0-20)."""
    section = _find_section(
        content, ("architecture", "module map", "structure", "project layout")
    )
    if not section:
        notes.append(
            "Architecture: no architecture/structure section found "
            "→ add a '## Architecture' section mapping key modules to one-line descriptions"
        )
        return 0

    # Check for descriptions alongside paths
    has_descriptions = bool(re.search(r"[/\w]+\.\w+.*[-–—:]", section))
    has_paths = bool(re.search(r"\w+/\w+", section))

    if has_descriptions and has_paths:
        return _ARCH_MAX
    if has_paths:
        notes.append(
            "Architecture: paths listed without descriptions "
            "→ add a one-line description after each module path (e.g. `path/ — what it does`)"
        )
        return 10
    notes.append(
        "Architecture: section has no module paths "
        "→ list the key modules by path with a one-line description each"
    )
    return 5


def _dim_conventions(content: str, notes: list[str]) -> int:
    """Conventions (0-15)."""
    section = _find_section(
        content, ("conventions", "style", "patterns", "coding", "rules")
    )
    if not section:
        notes.append(
            "Conventions: no conventions/style section found "
            "→ add a '## Conventions' section documenting non-obvious patterns"
        )
        return 0

    # Check for specificity indicators
    specific_indicators = 0
    for pattern in (
        r"`\w+`",  # inline code
        r"```",  # code blocks
        r"\.(py|ts|js|json|toml|yaml)\b",  # file extensions
        r"(ruff|black|eslint|prettier|mypy)\b",  # tool names
    ):
        if re.search(pattern, section, re.IGNORECASE):
            specific_indicators += 1

    if specific_indicators >= 3:
        return _CONV_MAX
    if specific_indicators >= 1:
        notes.append(
            "Conventions: low specificity "
            "→ name the tools (e.g. ruff), cite file extensions, and show code snippets"
        )
        return 9
    notes.append(
        "Conventions: section is vague "
        "→ replace generic advice with concrete patterns: tool names, file paths, code examples"
    )
    return 5


def _dim_conciseness(content: str, notes: list[str]) -> int:
    """Conciseness (0-15)."""
    line_count = len(content.splitlines())

    if line_count == 0:
        return 0
    if line_count <= 80:
        return _CONCISE_MAX
    if line_count <= 200:
        notes.append(
            f"Conciseness: {line_count} lines — healthy, but trimming "
            "→ move reference detail into docs/ to get under 80 lines for full marks"
        )
        return 11
    if line_count <= 500:
        notes.append(
            f"Conciseness: {line_count} lines "
            "→ move detail into docs/ and link it, keeping CLAUDE.md scannable"
        )
        return 6
    notes.append(
        f"Conciseness: {line_count} lines — likely too long "
        "→ extract sections into docs/ and reference them from a short CLAUDE.md"
    )
    return 2


def _dim_currency(content: str, project_root: Path, notes: list[str]) -> int:
    """Currency (0-15). Check that referenced paths actually exist."""
    paths = _extract_paths(content)
    if not paths:
        # No paths to validate — can't penalize, give moderate score
        return 10

    broken = [p for p in paths if not (project_root / p).exists()]
    ratio = (len(paths) - len(broken)) / len(paths)

    if ratio == 1.0:
        return _CURRENCY_MAX

    notes.append(
        f"Currency: {len(broken)} broken path reference(s) "
        f"({', '.join(broken[:3])}) → update or remove the stale paths"
    )
    return 3 if ratio < 0.5 else 9


def _dim_actionability(content: str, notes: list[str]) -> int:
    """Actionability (0-15)."""
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    if not lines:
        return 0

    # Count actionable indicators: imperative verbs, code refs, specifics
    actionable = 0
    vague = 0
    imperative_pattern = re.compile(
        r"^[-*]?\s*(use|run|add|create|prefer|avoid|always|never|ensure|set|call|import)\b",
        re.IGNORECASE,
    )
    vague_pattern = re.compile(
        r"\b(appropriate|as needed|consider|if possible|when necessary)\b",
        re.IGNORECASE,
    )

    for line in lines:
        if imperative_pattern.search(line):
            actionable += 1
        if vague_pattern.search(line):
            vague += 1

    if actionable == 0:
        notes.append(
            "Actionability: no imperative instructions found "
            "→ phrase guidance as commands (use/run/add/avoid/never/always …)"
        )
        return 3

    ratio = actionable / (actionable + vague) if (actionable + vague) else 0.5
    if ratio >= 0.8:
        return _ACTION_MAX
    if ratio >= 0.5:
        notes.append(
            "Actionability: some vague instructions "
            "→ replace hedges (appropriate, as needed, consider) with concrete directives"
        )
        return 10
    notes.append(
        "Actionability: many vague instructions "
        "→ replace hedges (appropriate, as needed, consider) with concrete directives"
    )
    return 5


# ---------------------------------------------------------------------------
# Documentation scoring (0-100)
# ---------------------------------------------------------------------------


def _score_docs(
    sr: ScanResult, *, missing: list[str], suggestions: list[str]
) -> ComponentScore:
    notes: list[str] = []
    total = 0

    # docs_guide.md exists (25 pts)
    if sr.has_docs_guide:
        total += 25
    else:
        missing.append("docs_guide.md")
        suggestions.append("Create a docs_guide.md to index your documentation")

    # Core docs present (30 pts, 10 each)
    doc_names = {d.name for d in sr.docs}
    for core in sorted(_CORE_DOCS):
        if core in doc_names:
            total += 10
        else:
            missing.append(f"docs/{core}.md")

    # Docs have content (20 pts) — check they're not tiny stubs
    if sr.docs:
        non_empty = sum(1 for d in sr.docs if d.size_bytes > 50)
        content_ratio = non_empty / len(sr.docs)
        content_pts = round(20 * content_ratio)
        total += content_pts
        if content_ratio < 1.0:
            stub_names = ", ".join(d.name for d in sr.docs if d.size_bytes <= 50)
            notes.append(
                f"{len(sr.docs) - non_empty} doc(s) appear to be empty stubs "
                f"({stub_names}) → flesh them out with real content or remove them"
            )
    else:
        notes.append(
            "No documentation files found "
            "→ run `opsward generate` to scaffold architecture/conventions docs"
        )

    # Cross-references (15 pts) — does CLAUDE.md mention docs_guide?
    if sr.claude_md_content and "docs_guide" in sr.claude_md_content:
        total += 15
    elif sr.claude_md_content:
        notes.append(
            "CLAUDE.md does not reference docs_guide.md "
            "→ link docs_guide.md from CLAUDE.md so agents discover the docs"
        )

    # Freshness (10 pts) — we can't check git dates in a pure function,
    # so award if docs exist at all
    if sr.docs:
        total += 10

    return ComponentScore(name="Documentation", score=min(total, 100), notes=notes)


# ---------------------------------------------------------------------------
# Skills scoring (0-100)
# ---------------------------------------------------------------------------


def _score_skills(
    sr: ScanResult, *, missing: list[str], suggestions: list[str]
) -> ComponentScore:
    notes: list[str] = []

    if not sr.skills:
        notes.append("No skills defined")
        suggestions.append(
            "Consider adding skills in .claude/skills/ for recurring tasks"
        )
        return ComponentScore(name="Skills", score=0, notes=notes)

    # Each skill earns a quality fraction in [0, 1]: 40% for a SKILL.md, 30% for
    # a description, 30% for spec compliance. We average across skills and scale
    # to 100, rounding once — so N perfect skills score a full 100 (an earlier
    # per-skill integer floor silently capped perfect setups below 100).
    quality = 0.0
    for skill in sr.skills:
        q = 0.0
        if skill.has_skill_md:
            q += 0.40
        else:
            notes.append(
                f'Skill "{skill.name}": missing SKILL.md '
                "→ add a SKILL.md with `name` and `description` frontmatter"
            )
        if skill.description:
            q += 0.30
        else:
            notes.append(
                f'Skill "{skill.name}": no description '
                "→ add a `description:` line to the frontmatter so the skill can be triggered"
            )
        violations = _validate_skill_spec(skill)
        if not violations:
            q += 0.30
        else:
            for v in violations:
                notes.append(f'Skill "{skill.name}": {v}')
        quality += q

    score = round(100 * quality / len(sr.skills))
    return ComponentScore(name="Skills", score=min(score, 100), notes=notes)


# ---------------------------------------------------------------------------
# agentskills.io spec validation
# ---------------------------------------------------------------------------


def validate_skill_spec(skill: SkillInfo) -> list[str]:
    """Validate a SkillInfo against the agentskills.io specification.

    Returns a list of human-readable violation strings (empty = compliant).

    >>> from pathlib import Path
    >>> from opsward.base import SkillInfo
    >>> s = SkillInfo(name='good-skill', path=Path('.'), has_skill_md=True,
    ...     frontmatter={'name': 'good-skill', 'description': 'Does X.'}, line_count=50)
    >>> validate_skill_spec(s)
    []
    """
    return _validate_skill_spec(skill)


_NAME_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
_MAX_SKILL_LINES = 500
_MAX_NAME_LEN = 64
_MAX_DESC_LEN = 1024
_MAX_COMPAT_LEN = 500


def _validate_skill_spec(skill) -> list[str]:
    """Validate a SkillInfo against the agentskills.io specification.

    Returns a list of human-readable violation strings (empty = compliant).
    """
    violations: list[str] = []
    if not skill.has_skill_md:
        return violations  # Can't validate without SKILL.md

    fm = skill.frontmatter

    # name field
    fm_name = fm.get("name", "")
    if not fm_name:
        violations.append("frontmatter missing required `name` field")
    else:
        if len(fm_name) > _MAX_NAME_LEN:
            violations.append(f"`name` exceeds {_MAX_NAME_LEN} chars")
        if not _NAME_PATTERN.match(fm_name):
            violations.append(
                "`name` must be lowercase alphanumeric + hyphens, "
                "no leading/trailing/consecutive hyphens"
            )
        if "--" in fm_name:
            violations.append("`name` contains consecutive hyphens")
        if fm_name != skill.name:
            violations.append(
                f"`name` field ({fm_name!r}) must match directory name ({skill.name!r})"
            )

    # description field
    fm_desc = fm.get("description", "")
    if not fm_desc:
        violations.append("frontmatter missing required `description` field")
    elif len(fm_desc) > _MAX_DESC_LEN:
        violations.append(f"`description` exceeds {_MAX_DESC_LEN} chars")

    # compatibility field length
    compat = fm.get("compatibility", "")
    if compat and len(compat) > _MAX_COMPAT_LEN:
        violations.append(f"`compatibility` exceeds {_MAX_COMPAT_LEN} chars")

    # SKILL.md size
    if skill.line_count > _MAX_SKILL_LINES:
        violations.append(
            f"SKILL.md has {skill.line_count} lines (max {_MAX_SKILL_LINES})"
        )

    return violations


# ---------------------------------------------------------------------------
# Setup scoring: rules, agents, hooks (0-100)
# ---------------------------------------------------------------------------


# Setup point budget (sums to 100): rules 35, agents 35, hooks 30
_SETUP_RULES_MAX = 35
_SETUP_AGENTS_MAX = 35
_SETUP_HOOKS_MAX = 30
_SETUP_PER_ARTIFACT = 15  # per rule / agent, capped at the section max

# A rule shorter than this (stripped) reads as a bare stub, not a real invariant.
_RULE_MIN_CHARS = 40

# Hook event names Claude Code recognizes (anything else silently never fires).
_KNOWN_HOOK_EVENTS = frozenset(
    {
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "Notification",
        "Stop",
        "SubagentStop",
        "SessionStart",
        "SessionEnd",
        "PreCompact",
    }
)


def validate_hooks_config(cfg: object) -> list[str]:
    """Validate a hooks config against Claude Code's expected shape.

    Returns a list of human-readable violation strings (empty = valid). Catches
    the silent-failure traps: a non-string ``matcher``, an unknown event name,
    or an entry with no runnable ``command`` hook — none of which Claude Code
    honors, so the hook never fires even though the file "looks" configured.

    >>> validate_hooks_config({'hooks': {'PostToolUse': [
    ...     {'matcher': 'Edit', 'hooks': [{'type': 'command', 'command': 'x'}]}]}})
    []
    >>> validate_hooks_config({'pre_commit': ['ruff']})
    ['no top-level `hooks` key']
    >>> 'matcher' in validate_hooks_config({'hooks': {'PostToolUse': [
    ...     {'matcher': {'tool_name': 'Edit'}, 'hooks': [
    ...         {'type': 'command', 'command': 'x'}]}]}})[0]
    True
    """
    return _validate_hooks_config(cfg)


def _validate_hooks_config(cfg: object) -> list[str]:
    violations: list[str] = []
    if not isinstance(cfg, dict):
        return ["hooks config is not a JSON object"]
    hooks = cfg.get("hooks")
    if hooks is None:
        return ["no top-level `hooks` key"]
    if not isinstance(hooks, dict):
        return ["`hooks` is not an object of event -> entries"]
    if not hooks:
        return ["`hooks` is empty"]

    for event, entries in hooks.items():
        if event not in _KNOWN_HOOK_EVENTS:
            violations.append(f"unknown hook event {event!r}")
        if not isinstance(entries, list):
            violations.append(f"event {event!r}: entries must be a list")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                violations.append(f"event {event!r}: entry is not an object")
                continue
            matcher = entry.get("matcher")
            if matcher is not None and not isinstance(matcher, str):
                violations.append(
                    f"event {event!r}: `matcher` must be a string regex, "
                    f"not {type(matcher).__name__} (Claude Code ignores a dict matcher)"
                )
            hook_list = entry.get("hooks")
            if not isinstance(hook_list, list) or not hook_list:
                violations.append(
                    f"event {event!r}: entry has no non-empty `hooks` list"
                )
                continue
            for h in hook_list:
                if (
                    not isinstance(h, dict)
                    or h.get("type") != "command"
                    or not h.get("command")
                ):
                    violations.append(
                        f"event {event!r}: each hook needs `type: command` and a `command`"
                    )
    return violations


def _score_setup(sr: ScanResult, *, suggestions: list[str]) -> ComponentScore:
    notes: list[str] = []
    total = 0

    # Rules (up to 35) — credit substantive rules, not bare stubs.
    if sr.rules:
        substantive = [r for r in sr.rules if len(r.content.strip()) >= _RULE_MIN_CHARS]
        stubs = [r for r in sr.rules if r not in substantive]
        total += min(_SETUP_RULES_MAX, _SETUP_PER_ARTIFACT * len(substantive))
        for r in stubs:
            notes.append(f'Rule "{r.name}": looks like a stub — add a real invariant')
        if stubs:
            suggestions.append(
                "Flesh out stub rule(s) in .claude/rules/ — a heading alone is not an invariant"
            )
    else:
        notes.append("No rules defined")

    # Agents (up to 35) — credit agents that at least carry a description.
    if sr.agents:
        described = [a for a in sr.agents if a.description.strip()]
        total += min(_SETUP_AGENTS_MAX, _SETUP_PER_ARTIFACT * len(described))
        for a in sr.agents:
            if not a.description.strip():
                notes.append(f'Agent "{a.name}": no description')
    else:
        notes.append("No agents defined")

    # Hooks (30) — score validity, not mere presence (issue #6).
    if sr.hooks_config:
        violations = _validate_hooks_config(sr.hooks_config)
        if not violations:
            total += _SETUP_HOOKS_MAX
        else:
            total += _SETUP_HOOKS_MAX // 3  # partial: configured but won't fire
            notes.append(f"Hooks config invalid: {violations[0]}")
            suggestions.append(
                "Fix the hooks config in .claude/hooks.json — "
                f"{violations[0]} (an invalid hook silently never fires)"
            )
    else:
        notes.append("No hooks configured")
        suggestions.append(
            "Add hooks in .claude/hooks.json — run `opsward generate --hooks` "
            "for starter templates (auto-format on PostToolUse, session context on SessionStart)"
        )

    return ComponentScore(
        name="Setup (rules/agents/hooks)", score=min(total, 100), notes=notes
    )


# ---------------------------------------------------------------------------
# Cross-reference integrity (0-100)
# ---------------------------------------------------------------------------


def _score_cross_references(
    sr: ScanResult, *, suggestions: list[str]
) -> ComponentScore:
    notes: list[str] = []

    if not sr.claude_md_content:
        return ComponentScore(name="Cross-references", score=0, notes=["No CLAUDE.md"])

    paths = _extract_paths(sr.claude_md_content)
    if not paths:
        notes.append("No file paths found in CLAUDE.md to validate")
        return ComponentScore(name="Cross-references", score=50, notes=notes)

    existing = 0
    broken = []
    for p in paths:
        if (sr.project_root / p).exists():
            existing += 1
        else:
            broken.append(p)

    if broken:
        notes.append(f"Broken references: {', '.join(broken[:5])}")
        suggestions.append("Fix broken path references in CLAUDE.md")

    ratio = existing / len(paths)
    score = round(100 * ratio)
    return ComponentScore(name="Cross-references", score=score, notes=notes)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_agents_md(sr: ScanResult, *, suggestions: list[str]) -> None:
    """Advisory check for AGENTS.md (cross-platform agent instructions)."""
    if not sr.agents_md_content:
        if sr.claude_md_content:
            suggestions.append(
                "No AGENTS.md found — run `opsward generate --agents-md` to create "
                "cross-platform agent instructions (supported by 60,000+ projects)"
            )
        return

    # If both exist, check for basic consistency
    if sr.claude_md_content and sr.agents_md_content:
        # Check that AGENTS.md has build/test commands if CLAUDE.md does
        claude_lower = sr.claude_md_content.lower()
        agents_lower = sr.agents_md_content.lower()
        if "```" in claude_lower and "```" not in agents_lower:
            suggestions.append(
                "AGENTS.md has no code blocks but CLAUDE.md does — "
                "consider syncing build/test commands"
            )


def _find_section(content: str, heading_keywords: Sequence[str]) -> str:
    """Extract the first section whose heading matches any keyword."""
    lines = content.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("#"):
            heading_lower = line.lstrip("#").strip().lower()
            if any(kw in heading_lower for kw in heading_keywords):
                start = i + 1
                continue
            if start is not None:
                # Hit next heading — return what we collected
                return "\n".join(lines[start:i])
    if start is not None:
        return "\n".join(lines[start:])
    return ""


def _extract_paths(content: str) -> list[str]:
    """Extract plausible file/directory paths from markdown content."""
    # Match things like src/foo.py, ./bar/baz.ts, docs/guide.md
    pattern = re.compile(r"(?:^|[\s`(])(\./)?(\w[\w\-.]*/[\w\-./]+\.\w+)", re.MULTILINE)
    paths = []
    for m in pattern.finditer(content):
        path = (m.group(1) or "") + m.group(2)
        # Filter out URLs
        if "://" not in path and not path.startswith("http"):
            paths.append(path)
    return paths
