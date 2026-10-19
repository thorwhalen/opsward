# opsward.subagents

Reuse a skill as a subagent: declare it in the skill, generate the twin, check the sync.

A Claude Code subagent is a Markdown file under `.claude/agents/` whose frontmatter
can *preload* a skill (`skills: [name]` injects the full `SKILL.md` body). So a skill
that is also useful in its own context needs nothing but a thin twin that preloads it,
restricts tools, picks a model and states the reply contract. The single source of
truth stays in the skill: it opts in with spec-legal `metadata` keys (the Agent Skills
spec allows string pairs there, and other hosts ignore them). Quote the values so a
strict validator sees strings:

```default
---
name: fleet-sweep
description: ...
metadata:
  subagent: "true"
  subagent-tools: "Bash, Read, Grep"
  subagent-model: "sonnet"
  subagent-reply-lines: "5"
  subagent-name: "fleet-sweeper"
---
```

Only `subagent` is required; the defaults are `Read, Grep, Glob, Bash`, no model
(the host picks), 5 lines, and the skill’s own name. Three pure functions do the
work, so `generate` and `maintain` share one source: [`subagent_spec()`](#opsward.subagents.subagent_spec) reads
the declaration, [`render_subagent()`](#opsward.subagents.render_subagent) renders the twin (with a marker line
carrying a hash of what it was rendered from), and [`twin_status()`](#opsward.subagents.twin_status) classifies
every skill/agent pair in a scan. Decision record:
`misc/docs/decisions/0009-skills-declare-their-subagent-twin.md`.

### Functions

| [`check_subagent_twins`](#opsward.subagents.check_subagent_twins)(sr)                    | `maintain` check: every twin that is not generated and current.                       |
|----------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| [`render_subagent`](#opsward.subagents.render_subagent)(spec, \*, source)           | Render the twin agent file for *spec*; *source* is the skill's repo-relative path.    |
| [`subagent_files`](#opsward.subagents.subagent_files)(sr)                          | Yield the twin agent file for every validly declared skill (missing or not).          |
| [`subagent_spec`](#opsward.subagents.subagent_spec)(skill)                        | Return the twin a skill declares under `metadata`, or `None`.                         |
| [`twin_for_rendered_skill`](#opsward.subagents.twin_for_rendered_skill)(skill_md_text, ...) | The twin of a skill that is about to be written (so one `generate` run creates both). |
| [`twin_status`](#opsward.subagents.twin_status)(sr)                             | Classify every declared twin and every hand-written agent that preloads a skill.      |
| [`twin_summary`](#opsward.subagents.twin_summary)(sr)                            | Counts by state, for the diagnosis note.                                              |

### Classes

| [`SubagentSpec`](#opsward.subagents.SubagentSpec)(skill_name, name, description, ...)   | What a skill declared about its subagent twin, with defaults applied.                           |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| [`TwinStatus`](#opsward.subagents.TwinStatus)(skill, agent, state[, declared, ...])   | One skill/agent pair as [`twin_status()`](#opsward.subagents.twin_status) sees it. |

### *class* opsward.subagents.SubagentSpec(skill_name, name, description, tools, model, reply_lines)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

What a skill declared about its subagent twin, with defaults applied.

#### problems()

Why this declaration cannot be rendered (empty = fine).

```pycon
>>> SubagentSpec('s', '../x', '', 'Bash: all', None, 0).problems()
['no frontmatter description (the twin reuses it as its trigger)', 'subagent-name `../x` is not a valid agent name', 'subagent-reply-lines must be at least 1', 'subagent-tools must not contain `: `']
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

#### source_hash()

Hash of everything the rendered twin depends on, so drift is detectable.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* opsward.subagents.TwinStatus(skill, agent, state, declared=False, content='', detail='', path='')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One skill/agent pair as [`twin_status()`](#opsward.subagents.twin_status) sees it.

### opsward.subagents.check_subagent_twins(sr)

`maintain` check: every twin that is not generated and current.

* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`MaintenanceSuggestion`](opsward.base.html.md#opsward.base.MaintenanceSuggestion)]

### opsward.subagents.render_subagent(spec, , source)

Render the twin agent file for *spec*; *source* is the skill’s repo-relative path.

The body is deliberately short: the skill’s full content is preloaded by the host
through the `skills` field, so the twin only adds the context contract.

```pycon
>>> spec = SubagentSpec('sweep', 'sweep', 'Sweep and report.', 'Bash', 'haiku', 3)
>>> text = render_subagent(spec, source='.claude/skills/sweep/SKILL.md')
>>> text.splitlines()[1:4]
['name: sweep', 'description: Sweep and report.', 'tools: Bash']
>>> 'skills: [sweep]' in text and 'at most 3 lines' in text
True
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.subagents.subagent_files(sr)

Yield the twin agent file for every validly declared skill (missing or not).

Callers that must not overwrite (the CLI) skip existing targets; the marker in a
generated file is what [`twin_status()`](#opsward.subagents.twin_status) uses to tell a stale twin from a
hand-written one. Invalid and duplicate declarations yield nothing; `maintain`
reports them.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`GeneratedFile`](opsward.base.html.md#opsward.base.GeneratedFile)]

### opsward.subagents.subagent_spec(skill)

Return the twin a skill declares under `metadata`, or `None`.

```pycon
>>> from pathlib import Path
>>> from opsward.base import SkillInfo
>>> s = SkillInfo(name='sweep', path=Path('/x/sweep'), has_skill_md=True,
...     description='Sweep the fleet and report.',
...     frontmatter={'name': 'sweep', 'metadata': {'subagent': 'true', 'subagent-model': 'haiku'}})
>>> spec = subagent_spec(s)
>>> (spec.name, spec.tools, spec.model, spec.reply_lines)
('sweep', 'Read, Grep, Glob, Bash', 'haiku', 5)
>>> subagent_spec(SkillInfo(name='plain', path=Path('/x/plain'))) is None
True
```

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`SubagentSpec`](#opsward.subagents.SubagentSpec)]

### opsward.subagents.twin_for_rendered_skill(skill_md_text, skill_md_path, root)

The twin of a skill that is about to be written (so one `generate` run creates both).

```pycon
>>> from pathlib import Path
>>> text = '---\nname: s\ndescription: Do the thing.\nmetadata:\n  subagent: "true"\n---\nbody\n'
>>> gf = twin_for_rendered_skill(text, Path('/p/.claude/skills/s/SKILL.md'), Path('/p'))
>>> gf.target_path.as_posix(), 'skills: [s]' in gf.content
('/p/.claude/agents/s.md', True)
```

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`GeneratedFile`](opsward.base.html.md#opsward.base.GeneratedFile)]

### opsward.subagents.twin_status(sr)

Classify every declared twin and every hand-written agent that preloads a skill.

- `invalid`: the declaration cannot be rendered (see `SubagentSpec.problems`).
- `duplicate`: two skills declare the same twin name; the first wins, the rest are reported.
- `missing`: the skill declares a twin and no agent file exists.
- `stale`: the agent file was generated from a declaration that has since changed.
- `in_sync`: generated and current.
- `handwritten`: an agent opsward did not generate, either carrying the name a skill
  declares for its twin (`declared=True`), or sharing a non-declaring skill’s name or
  preloading it via `skills:` (`declared=False`).

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`TwinStatus`](#opsward.subagents.TwinStatus)]

### opsward.subagents.twin_summary(sr)

Counts by state, for the diagnosis note.

```pycon
>>> from pathlib import Path
>>> twin_summary(ScanResult(project_root=Path('/tmp/empty')))
{}
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`int`](https://docs.python.org/3/builtins/functions.html#int)]
