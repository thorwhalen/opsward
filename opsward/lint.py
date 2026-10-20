"""Schema lint (opsward#17, gap 2): spec and config violations, pass or fail, no score.

``diagnose --min-score`` is the cheap scored gate; ``lint`` is the strict one. It runs
every *validator* over every project skill, and checks the hooks config, and reports each
violation with a repo-relative path. A validator is ``SkillInfo -> list[str]``:

* ``opsward`` -- opsward's own agentskills.io spec check (:func:`validate_skill_spec`),
  always available;
* ``skill`` -- the ``skill`` package's ``skill.validate()`` (``pip install 'opsward[lint]'``),
  which composes its own registered validators.

``"auto"`` (the default) is ``opsward`` plus ``skill`` when it is importable. A host can
pass any mapping of name to validator instead, which is the seam for external linters.

>>> from pathlib import Path
>>> from opsward.base import ScanResult, SkillInfo
>>> sr = ScanResult(Path("repo"), skills=[SkillInfo("Bad_Name", Path("repo/.claude/skills/Bad_Name"),
...                                                 has_skill_md=True, frontmatter={"name": "Bad_Name"})])
>>> findings = list(lint(sr, validators={"opsward": opsward_validator}))
>>> findings[0].path, findings[0].source
('.claude/skills/Bad_Name', 'opsward')
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
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
    """The ``skill`` package's ``validate()`` over the skill's directory."""
    import skill as skill_pkg  # optional: pip install 'opsward[lint]'

    return list(skill_pkg.validate(str(skill.path)))


def _skill_package_available() -> bool:
    from importlib.util import find_spec

    return find_spec("skill") is not None


#: Every known validator: name -> (validator, is-it-available).
VALIDATORS: dict[str, tuple[Validator, Callable[[], bool]]] = {
    "opsward": (opsward_validator, lambda: True),
    "skill": (skill_package_validator, _skill_package_available),
}


def resolve_validators(spec: str | Mapping[str, Validator] = DFLT_VALIDATORS) -> dict[str, Validator]:
    """Turn ``"auto"``, ``"opsward,skill"`` or a mapping into a name -> validator dict.

    :raises ValueError: an unknown name, or a named validator that is not installed.

    >>> list(resolve_validators("opsward"))
    ['opsward']
    >>> resolve_validators("nope")
    Traceback (most recent call last):
    ...
    ValueError: unknown validator 'nope' (known: opsward, skill)
    """
    if isinstance(spec, Mapping):
        return dict(spec)
    if spec == "auto":
        return {name: v for name, (v, available) in VALIDATORS.items() if available()}
    chosen = {}
    for name in filter(None, (s.strip() for s in spec.split(","))):
        if name not in VALIDATORS:
            raise ValueError(f"unknown validator {name!r} (known: {', '.join(VALIDATORS)})")
        validator, available = VALIDATORS[name]
        if not available():
            raise ValueError(
                f"validator {name!r} is not installed: pip install 'opsward[lint]'"
            )
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
    """Every spec/config violation in the scanned project, skills first, then hooks."""
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
    if scan_result.hooks_path is not None:
        where = _rel(scan_result.hooks_path, root)
        if scan_result.hooks_config is None:
            yield LintFinding(where, "opsward", "hooks config is not valid JSON")
        else:
            for message in validate_hooks_config(scan_result.hooks_config):
                yield LintFinding(where, "opsward", message)
