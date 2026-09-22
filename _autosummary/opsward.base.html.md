# opsward.base

All dataclasses and type definitions for opsward.

### Classes

| [`AgentInfo`](#opsward.base.AgentInfo)(name, path[, description])            | An agent found in .claude/agents/.                                 |
|--------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`ComponentScore`](#opsward.base.ComponentScore)(name, score[, max_score, notes]) | Score for a single component (0–100) with optional notes.          |
| [`DiagnosisReport`](#opsward.base.DiagnosisReport)(project_root, project_type)     | Report card produced by scoring a ScanResult.                      |
| [`DocSpec`](#opsward.base.DocSpec)(name, path[, size_bytes])               | A document found in the docs directory.                            |
| [`GeneratedFile`](#opsward.base.GeneratedFile)(target_path, content[, ...])      | A file to be written by the generate step.                         |
| [`MaintenanceSuggestion`](#opsward.base.MaintenanceSuggestion)(category, description)    | A single maintenance action proposed by maintain.py.               |
| [`ProjectType`](#opsward.base.ProjectType)(\*values)                           | Detected project type.                                             |
| [`RuleInfo`](#opsward.base.RuleInfo)(name, path[, content])                 | A rule found in .claude/rules/.                                    |
| [`ScanResult`](#opsward.base.ScanResult)(project_root[, project_type, ...])   | Everything we learned by reading (never writing) a target project. |
| [`SkillInfo`](#opsward.base.SkillInfo)(name, path[, has_skill_md, ...])      | A skill found in .claude/skills/.                                  |

### *class* opsward.base.AgentInfo(name, path, description='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

An agent found in .claude/agents/.

### *class* opsward.base.ComponentScore(name, score, max_score=100, notes=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Score for a single component (0–100) with optional notes.

### *class* opsward.base.DiagnosisReport(project_root, project_type, scores=<factory>, missing_items=<factory>, suggestions=<factory>, weighted_score=0.0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Report card produced by scoring a ScanResult.

#### *property* grade *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

A (90-100), B (80-89), C (70-79), D (60-69), F (<60).

* **Type:**
  Letter grade

#### *property* overall_score *: [float](https://docs.python.org/3/builtins/functions.html#float)*

Weighted score if set, else simple average.

### *class* opsward.base.DocSpec(name, path, size_bytes=0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A document found in the docs directory.

### *class* opsward.base.GeneratedFile(target_path, content, overwrite_policy='skip')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A file to be written by the generate step.

### *class* opsward.base.MaintenanceSuggestion(category, description, diff='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A single maintenance action proposed by maintain.py.

### *class* opsward.base.ProjectType(\*values)

Bases: [`Enum`](https://docs.python.org/3/library/enum.html#enum.Enum)

Detected project type.

### *class* opsward.base.RuleInfo(name, path, content='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A rule found in .claude/rules/.

### *class* opsward.base.ScanResult(project_root, project_type=ProjectType.unknown, claude_md_path=None, claude_md_content='', skills=<factory>, agents=<factory>, rules=<factory>, hooks_path=None, hooks_config=None, docs=<factory>, has_docs_guide=False, docs_guide_path=None, agents_md_path=None, agents_md_content='', is_monorepo=False, monorepo_packages=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Everything we learned by reading (never writing) a target project.

### *class* opsward.base.SkillInfo(name, path, has_skill_md=False, description='', frontmatter=<factory>, line_count=0)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A skill found in .claude/skills/.
