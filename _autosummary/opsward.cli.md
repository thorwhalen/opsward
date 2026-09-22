# opsward.cli

CLI dispatch for opsward.

### Functions

| [`diagnose`](#opsward.cli.diagnose)(\*project_roots[, format, verbose, ...])   | Diagnose the AI agent setup of one or more projects.                          |
|------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`find`](#opsward.cli.find)(query, \*project_roots[, kinds, ...])          | Find assets (skills, agents, docs) across one or more projects by QUERY.      |
| [`generate`](#opsward.cli.generate)(\*project_roots[, write, format, ...])     | Generate missing AI setup artifacts for one or more projects.                 |
| [`install_skills`](#opsward.cli.install_skills)([target, global_install, ...])       | Install opsward's Claude Code skills (and agents) into a project or globally. |
| [`maintain`](#opsward.cli.maintain)(\*project_roots[, format])                 | Check for stale references, out-of-sync docs, and other drift.                |
| [`recommend`](#opsward.cli.recommend)(\*project_roots[, format])                | Recommend ecosystem skills based on the project's tech stack.                 |

### opsward.cli.diagnose(\*project_roots, format='text', verbose=False, min_score=80)

Diagnose the AI agent setup of one or more projects.

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more paths to project directories
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’
  * **verbose** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – show additional detail in text output
  * **min_score** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – minimum overall score to pass (exit 0); below this exits 1

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

### opsward.cli.maintain(\*project_roots, format='text')

Check for stale references, out-of-sync docs, and other drift.

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more paths to project directories
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’

### opsward.cli.recommend(\*project_roots, format='text')

Recommend ecosystem skills based on the project’s tech stack.

Analyzes dependencies and suggests skills from the community catalog.

* **Parameters:**
  * **project_roots** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – one or more paths to project directories
  * **format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – output format — ‘text’ or ‘json’
