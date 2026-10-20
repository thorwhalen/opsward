# opsward.cli

CLI dispatch for opsward.

### Functions

| [`diagnose`](#opsward.cli.diagnose)(\*project_roots[, format, verbose, ...])   | Diagnose the AI agent setup of one or more projects.                                                   |
|------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| [`eval_`](#opsward.cli.eval_)(project_root, \*[, judge, samples, ...])      | Report-only evals of a project's agent setup: an LLM judge of CLAUDE.md, and golden tasks.             |
| [`find`](#opsward.cli.find)(query, \*project_roots[, kinds, ...])          | Find assets (skills, agents, docs) across one or more projects by QUERY.                               |
| [`fleet`](#opsward.cli.fleet)(\*project_roots[, under, depth, ...])         | Diagnose many projects at once and roll the results up into one fleet report.                          |
| [`generate`](#opsward.cli.generate)(\*project_roots[, write, format, ...])     | Generate missing AI setup artifacts for one or more projects.                                          |
| [`install_skills`](#opsward.cli.install_skills)([target, global_install, ...])       | Install opsward's Claude Code skills (and agents) into a project or globally.                          |
| [`lint`](#opsward.cli.lint)(\*project_roots[, validators, format])         | Check skill specs and the hooks config: pass or fail, no score (exit 1 on any finding).                |
| [`maintain`](#opsward.cli.maintain)(\*project_roots[, format])                 | Check for stale references, out-of-sync docs, and other drift.                                         |
| [`new`](#opsward.cli.new)(title[, write, project_root, status, ...])      | Allocate the next numbered ADR for TITLE (dry run unless --write; never overwrites).                   |
| [`note`](#opsward.cli.note)(text[, write, project_root])                   | Append TEXT as a dated one-line decision (a Y-statement) to decisions/log.md (dry run unless --write). |
| [`portability`](#opsward.cli.portability)(\*project_roots[, format])              | Show which agent hosts find project instructions, and how renders drift from AGENTS.md.                |
| [`recommend`](#opsward.cli.recommend)(\*project_roots[, format])                | Recommend ecosystem skills based on the project's tech stack.                                          |

### opsward.cli.diagnose(\*project_roots, format='text', verbose=False, min_score=80)

Diagnose the AI agent setup of one or more projects.

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more paths to project directories
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’
  * **verbose** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – show additional detail in text output
  * **min_score** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – minimum overall score to pass (exit 0); below this exits 1

### opsward.cli.eval_(project_root, , judge='rubric', samples=1, tasks='', runs=1, format='text')

Report-only evals of a project’s agent setup: an LLM judge of CLAUDE.md, and golden tasks.

The judge scores CLAUDE.md’s subjective dimensions next to the rubric’s own score. The
golden tasks (a JSON list of {name, prompt, expect, forbid}, by default
<docs>/evals/golden_tasks.json) run with and without CLAUDE.md and report the pass-rate
delta. –judge rubric is free and deterministic (the rubric judge and an agent that
quotes the config: it checks the harness, not a model); –judge anthropic makes paid
calls (pip install ‘opsward[eval]’). Exits 0 whenever it ran (a report, never a gate);
2 only on a usage error.

* **Parameters:**
  * **project_root** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the project directory
  * **judge** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – ‘rubric’ (free) or ‘anthropic’ (paid model calls)
  * **samples** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – judge samples per dimension (the median is reported)
  * **tasks** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – golden-tasks JSON file (default: <docs>/evals/golden_tasks.json, if present)
  * **runs** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – runs per golden task and arm
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’

### opsward.cli.find(query, \*project_roots, kinds='skill,agent', semantic=False, limit=10)

Find assets (skills, agents, docs) across one or more projects by QUERY.

Cross-repo asset discovery via the toolery package
(install with: pip install ‘opsward[discovery]’).

* **Parameters:**
  * **query** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – search query
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more project directories (default: current dir)
  * **kinds** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – comma-separated asset kinds — skill, agent, doc
  * **semantic** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – use toolery’s ir semantic backend (needs toolery[ir])
  * **limit** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – max results to show

### opsward.cli.fleet(\*project_roots, under='', depth=1, format='text', manifest='')

Diagnose many projects at once and roll the results up into one fleet report.

The fleet is the given roots, plus the git repos found under –under. With –manifest
the fleet is remembered: the roots and the latest summary are written to that JSON
file, and a later run with only –manifest re-diagnoses the same roots (given roots or
–under replace them). The manifest holds this machine’s absolute paths, so keep it
out of version control. Exits 1 when any root could not be diagnosed.

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – project directories to diagnose
  * **under** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – also diagnose every git repo found under this directory
  * **depth** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – how many levels below –under to look for git repos
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’ (the name-keyed summary)
  * **manifest** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – JSON file that remembers the fleet’s roots and its latest summary

### opsward.cli.generate(\*project_roots, write=False, format='text', agents_md=False, hooks=False)

Generate missing AI setup artifacts for one or more projects.

By default, shows what would be created (dry run). Use –write to
actually write files. Existing files are never overwritten.

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more paths to project directories
  * **write** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – actually write files (default: dry run)
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’
  * **agents_md** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – also generate AGENTS.md (cross-platform agent instructions)
  * **hooks** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – also generate starter hook scripts

### opsward.cli.install_skills(target='.', , global_install=False, agents=True, write=False)

Install opsward’s Claude Code skills (and agents) into a project or globally.

By default, shows what would be created (dry run). Use –write to
actually write files. Existing files are never overwritten.

* **Parameters:**
  * **target** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – project directory (ignored when –global is set)
  * **global_install** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – install into ~/.claude/ instead of the project
  * **agents** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – also install agent definitions (default: True)
  * **write** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – actually write files (default: dry run)

### opsward.cli.lint(\*project_roots, validators='auto', format='text')

Check skill specs and the hooks config: pass or fail, no score (exit 1 on any finding).

The strict counterpart of `diagnose --min-score`, for CI and pre-commit. Validators:
opsward (its own agentskills.io check, always there), skill (the skill package’s
validate(); pip install ‘opsward[lint]’), and the external agnix and skillcheck
linters (opt-in by name). auto runs opsward and skill, each when installed.

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more project directories (default: current dir)
  * **validators** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – ‘auto’, or a comma list of: opsward, skill, agnix, skillcheck
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’

### opsward.cli.maintain(\*project_roots, format='text')

Check for stale references, out-of-sync docs, and other drift.

Each finding carries a recommended triage: align (update the config to match the
code), revert (restore the code the config describes) or ignore (a legitimately
volatile reference: put `opsward: ignore-path` on its line).

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more paths to project directories
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’

### opsward.cli.new(title, write=False, project_root='.', status='Proposed', evidence='')

Allocate the next numbered ADR for TITLE (dry run unless –write; never overwrites).

* **Parameters:**
  * **title** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the decision’s title; the file name is derived from it
  * **write** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – actually write the file (default: dry run)
  * **project_root** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the project directory (default: current dir)
  * **status** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – initial status — Proposed (default), or Accepted when the human has accepted it
  * **evidence** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the issue, discussion or PR this rests on (a URL or #N)

### opsward.cli.note(text, write=False, project_root='.')

Append TEXT as a dated one-line decision (a Y-statement) to decisions/log.md (dry run unless –write).

* **Parameters:**
  * **text** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the decision: “In the context of …, facing …, we decided for …, because …”
  * **write** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – actually append (default: dry run); the log is created from its template when missing
  * **project_root** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – the project directory (default: current dir)

### opsward.cli.portability(\*project_roots, format='text')

Show which agent hosts find project instructions, and how renders drift from AGENTS.md.

One row per host (claude, codex, copilot, cursor, …) with how it is covered:
symlink, import (an @AGENTS.md shim), native (reads AGENTS.md itself), copy, rules,
or none. Then every section where a render differs from AGENTS.md, and (with
opsward[lint]) every project skill whose render drops fields. Report-only.

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more project directories (default: current dir)
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’

### opsward.cli.recommend(\*project_roots, format='text')

Recommend ecosystem skills based on the project’s tech stack.

Analyzes dependencies and suggests skills from the community catalog.

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more paths to project directories
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’
