"""Schema lint (opsward#17, gap 2): spec and config violations, pass or fail, no score.

``diagnose --min-score`` is the cheap scored gate; ``lint`` is the strict one. It runs
every *validator* over every project skill, and checks the hooks config, and reports each
violation with a repo-relative path. A validator is ``SkillInfo -> list[str]``:

* ``opsward`` -- opsward's own agentskills.io spec check (:func:`validate_skill_spec`),
  always available;
* ``skill`` -- the ``skill`` package's ``skill.validate()`` (``pip install 'opsward[lint]'``),
  which composes its own registered validators;
* ``agnix`` and ``skillcheck`` -- external linters, run as subprocesses
  (``npm install -g agnix``, ``pip install skillcheck``); their JSON diagnostics of level
  ``error`` and ``warning`` become findings. opsward does not depend on either, and they
  are opt-in by name: their rule sets are wider and noisier than the spec check, so a
  gate on ``"auto"`` must not turn red because a machine happens to have one installed.

``"auto"`` (the default) is :data:`AUTO_VALIDATORS`, each when it is available. A host
can pass any mapping of name to validator instead.

>>> from pathlib import Path
>>> from opsward.base import ScanResult, SkillInfo
>>> sr = ScanResult(Path("repo"), skills=[SkillInfo("Bad_Name", Path("repo/.claude/skills/Bad_Name"),
...                                                 has_skill_md=True, frontmatter={"name": "Bad_Name"})])
>>> findings = list(lint(sr, validators={"opsward": opsward_validator}))
>>> findings[0].path, findings[0].source
('.claude/skills/Bad_Name', 'opsward')
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from opsward.base import ScanResult, SkillInfo
from opsward.score import validate_hooks_config, validate_skill_spec

Validator = Callable[[SkillInfo], list]

#: What ``validators="auto"`` means: these names, each when it is available.
DFLT_VALIDATORS = "auto"


@dataclass(frozen=True)
class LintFinding:
    """One violation: where (repo-relative), which validator said so, and what."""

    path: str
    source: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: [{self.source}] {self.message}"

    def to_dict(self) -> dict:
        return asdict(self)


def opsward_validator(skill: SkillInfo) -> list[str]:
    """opsward's own spec check; a skill directory without a SKILL.md is one violation."""
    if not skill.has_skill_md:
        return ["no SKILL.md"]
    return validate_skill_spec(skill)


def skill_package_validator(skill: SkillInfo) -> list[str]:
    """The ``skill`` package's ``validate()`` over the skill's directory.

    A directory with no SKILL.md is left to :func:`opsward_validator` (``skill`` would
    report it again, with an absolute path).
    """
    if not skill.has_skill_md:
        return []
    import skill as skill_pkg  # optional: pip install 'opsward[lint]'

    return list(skill_pkg.validate(str(skill.path)))


def _skill_package_available() -> bool:
    from importlib.util import find_spec

    return find_spec("skill") is not None


#: Diagnostic levels of an external linter that count as findings (``info`` does not).
EXTERNAL_FINDING_LEVELS = ("error", "warning")
#: Seconds an external linter may take on one skill.
DFLT_EXTERNAL_TIMEOUT = 120


def _run_json(argv: list[str], *, timeout: float = DFLT_EXTERNAL_TIMEOUT):
    """Run an external linter and parse its JSON stdout (its exit code is not the verdict)."""
    done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(done.stdout)
    except ValueError:
        lines = [ln.strip() for ln in (done.stderr or done.stdout).splitlines()]
        detail = next((ln for ln in lines if ln), "no output")
        raise RuntimeError(
            f"{argv[0]} exited {done.returncode} without JSON: {detail}"
        ) from None


def _messages(diagnostics: Iterable[Mapping], *, level_key: str) -> list[str]:
    """``rule: message (line N)`` for each diagnostic at a finding level.

    >>> _messages([{"rule": "AS-004", "level": "error", "message": "bad name", "line": 2},
    ...            {"rule": "VER-001", "level": "info", "message": "fyi"}], level_key="level")
    ['AS-004: bad name (line 2)']
    """
    return [
        f"{d.get('rule', '?')}: {d.get('message', '')}"
        + (f" (line {d['line']})" if d.get("line") else "")
        for d in diagnostics
        if d.get(level_key) in EXTERNAL_FINDING_LEVELS
    ]


def agnix_validator(skill: SkillInfo) -> list[str]:
    """`agnix <https://github.com/agent-sh/agnix>`_ over the skill's directory."""
    if not skill.has_skill_md:
        return []
    report = _run_json(["agnix", "--format", "json", str(skill.path)])
    return _messages(report.get("diagnostics", ()), level_key="level")


def skillcheck_validator(skill: SkillInfo) -> list[str]:
    """`skillcheck <https://pypi.org/project/skillcheck/>`_ over the skill's SKILL.md."""
    if not skill.has_skill_md:
        return []
    argv = [
        "skillcheck",
        "--format",
        "json",
        "--no-color",
        str(skill.path / "SKILL.md"),
    ]
    report = _run_json(argv)
    return [
        message
        for result in report.get("results", ())
        for message in _messages(result.get("diagnostics", ()), level_key="severity")
    ]


def _on_path(executable: str) -> Callable[[], bool]:
    return lambda: shutil.which(executable) is not None


#: Every known validator: name -> (validator, is-it-available).
VALIDATORS: dict[str, tuple[Validator, Callable[[], bool]]] = {
    "opsward": (opsward_validator, lambda: True),
    "skill": (skill_package_validator, _skill_package_available),
    "agnix": (agnix_validator, _on_path("agnix")),
    "skillcheck": (skillcheck_validator, _on_path("skillcheck")),
}

#: What ``"auto"`` runs (each when available): the same set on every machine.
AUTO_VALIDATORS = ("opsward", "skill")

#: How to install each optional validator (named in the "not installed" error).
INSTALL_HINTS = {
    "skill": "pip install 'opsward[lint]'",
    "agnix": "npm install -g agnix",
    "skillcheck": "pip install skillcheck",
}


def resolve_validators(
    spec: str | Mapping[str, Validator] = DFLT_VALIDATORS,
) -> dict[str, Validator]:
    """Turn ``"auto"``, ``"opsward,skill"`` or a mapping into a name -> validator dict.

    :raises ValueError: an unknown name, or a named validator that is not installed.

    >>> list(resolve_validators("opsward"))
    ['opsward']
    >>> resolve_validators("nope")
    Traceback (most recent call last):
    ...
    ValueError: unknown validator 'nope' (known: opsward, skill, agnix, skillcheck)
    """
    chosen = _resolve(spec)
    if not chosen:  # a gate that checks nothing must not pass
        raise ValueError(f"no validators selected (known: {', '.join(VALIDATORS)})")
    return chosen


def _resolve(spec) -> dict[str, Validator]:
    if isinstance(spec, Mapping):
        return dict(spec)
    if spec == "auto":
        return {
            name: v
            for name, (v, available) in VALIDATORS.items()
            if name in AUTO_VALIDATORS and available()
        }
    chosen = {}
    for name in filter(None, (s.strip() for s in spec.split(","))):
        if name not in VALIDATORS:
            raise ValueError(
                f"unknown validator {name!r} (known: {', '.join(VALIDATORS)})"
            )
        validator, available = VALIDATORS[name]
        if not available():
            hint = INSTALL_HINTS.get(name, "see opsward.lint")
            raise ValueError(f"validator {name!r} is not installed: {hint}")
        chosen[name] = validator
    return chosen


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def lint(
    scan_result: ScanResult,
    *,
    validators: str | Mapping[str, Validator] = DFLT_VALIDATORS,
) -> Iterator[LintFinding]:
    """Every spec/config violation in the scanned project, skills first, then hooks.

    Hooks are read from every file in :data:`HOOKS_FILES` that exists, not only the one
    ``scan`` picked, so an unparseable or shadowed hooks file is still reported.
    """
    root = scan_result.project_root
    chosen = resolve_validators(validators)
    for skill in scan_result.skills:
        where = _rel(skill.path, root)
        for name, validator in chosen.items():
            try:
                messages = validator(skill)
            except Exception as error:  # a broken validator is a finding, not a crash
                messages = [f"validator failed: {type(error).__name__}: {error}"]
            for message in messages:
                yield LintFinding(where, name, str(message))
    yield from _hooks_findings(root)


#: Where Claude Code reads hooks from; a settings file holds hooks only under ``hooks``.
HOOKS_FILES = ("hooks.json", "settings.json", "settings.local.json")


def _hooks_findings(root: Path) -> Iterator[LintFinding]:
    """Every hooks-bearing file under ``.claude/``: unparseable JSON, or a malformed ``hooks``."""
    import json

    for name in HOOKS_FILES:
        path = root / ".claude" / name
        if not path.is_file():
            continue
        where = _rel(path, root)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as error:
            yield LintFinding(where, "opsward", f"not valid JSON: {error}")
            continue
        if name != "hooks.json" and not (isinstance(data, dict) and "hooks" in data):
            continue  # a settings file without hooks is not a hooks config
        for message in validate_hooks_config(data):
            yield LintFinding(where, "opsward", message)
