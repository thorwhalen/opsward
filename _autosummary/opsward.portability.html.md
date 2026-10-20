# opsward.portability

Multi-host portability: which agent hosts a repo satisfies, and canonical↔render drift.

The canonical project brief is `AGENTS.md` (opsward#15). Every other host’s instruction
file (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, …) is a *render*
of it, related to it in one of three ways:

* `symlink` — the file is a symlink to `AGENTS.md`: byte-identical, cannot drift;
* `import` — the file imports it (`@AGENTS.md`) and adds host-only deltas: the
  recommended shape for hosts with an import syntax (Claude Code, Gemini CLI);
* `copy` — a separate file: everything in it can drift from the canonical.

The check is a *linter*: the canonical is authoritative and drift in a render is
reported, never merged back. Three finding kinds, matched section by section (by
normalised heading):

* `stale` — a canonical section is missing from a copy;
* `diverged` — a section is in both, with different bodies (a stale render or a hand
  edit in the render: the files alone cannot say which);
* `host_only` — a section only the render has: promote it to `AGENTS.md` if it is
  portable, or keep it as a host delta (after an `@AGENTS.md` import).

Scoped-rule folders (`.cursor/rules/`, `.windsurf/rules/`, `.clinerules/`) count
towards coverage but are not compared: they are not renders of one brief.

Files that are only coverage signals (`CONVENTIONS.md` is often a contributor doc, not a
render) are compared only when they import or link the canonical.

`read_host_files` is read-only (it backs `scan`); `analyze` is pure.

```pycon
>>> report = analyze(
...     "# P\n\n## Build\n\npytest\n",
...     {"CLAUDE.md": HostFile("CLAUDE.md", "## Build\n\npytest -x\n## Claude\n\nx\n")},
... )
>>> report.coverage["claude"], report.coverage["codex"]
('copy', 'native')
>>> sorted((f.kind, f.section) for f in report.findings)
[('diverged', 'build'), ('host_only', 'claude')]
```

### Module Attributes

| [`DRIFT_KINDS`](#opsward.portability.DRIFT_KINDS)   | The drift finding kinds, in report order (see the module docstring).   |
|----------------------------------------------------------------|------------------------------------------------------------------------|

### Functions

| [`analyze`](#opsward.portability.analyze)(canonical, host_files, \*[, hosts])   | Coverage and drift of *host_files* against the *canonical* `AGENTS.md` text.   |
|------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`as_read`](#opsward.portability.as_read)(render, canonical)                    | *render* as its host reads it: an `@AGENTS.md` import replaced by *canonical*. |
| [`check_portability`](#opsward.portability.check_portability)(root, \*[, hosts])          | `analyze` over what is on disk under *root*: the library entry point.          |
| [`has_canonical`](#opsward.portability.has_canonical)(canonical)                      | Whether an `AGENTS.md` text says anything (a BOM or whitespace does not).      |
| [`read_host_files`](#opsward.portability.read_host_files)(root, \*[, hosts])            | Every host instruction file and rule folder present under *root*.              |
| [`summarize`](#opsward.portability.summarize)(report)                             | One diagnose suggestion per drifting render.                                   |

### Classes

| [`DriftFinding`](#opsward.portability.DriftFinding)(kind, path, section)        | One section that differs between `AGENTS.md` and a render.                        |
|-------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| [`HostFile`](#opsward.portability.HostFile)(path[, content, ...])           | One host instruction file (or rule folder) as found on disk.                      |
| [`HostSpec`](#opsward.portability.HostSpec)(name[, instruction_files, ...]) | Where one agent host looks for project instructions (research table, opsward#15). |
| [`PortabilityReport`](#opsward.portability.PortabilityReport)([coverage, findings])  | Host coverage (host -> relation, `native` or `none`) and drift findings.          |

### opsward.portability.DRIFT_KINDS *= ('stale', 'diverged', 'host_only')*

The drift finding kinds, in report order (see the module docstring).

### *class* opsward.portability.DriftFinding(kind, path, section)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One section that differs between `AGENTS.md` and a render.

### *class* opsward.portability.HostFile(path, content='', links_to_canonical=False, is_dir=False, compared=True)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One host instruction file (or rule folder) as found on disk.

#### *property* relation *: [str](https://docs.python.org/3/builtins/stdtypes.html#str)*

`symlink`, `import`, `rules` or `copy` (see the module docstring).

### *class* opsward.portability.HostSpec(name, instruction_files=(), rule_dirs=(), reads_agents_md=False, compared=True)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Where one agent host looks for project instructions (research table, opsward#15).

### *class* opsward.portability.PortabilityReport(coverage=dict(), findings=list())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Host coverage (host -> relation, `native` or `none`) and drift findings.

#### *property* covered *: [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]*

Hosts that find project instructions, in `AGENT_HOSTS` order.

### opsward.portability.analyze(canonical, host_files, , hosts={'aider': HostSpec(name='aider', instruction_files=('CONVENTIONS.md',), rule_dirs=(), reads_agents_md=False, compared=False), 'claude': HostSpec(name='claude', instruction_files=('CLAUDE.md', '.claude/CLAUDE.md'), rule_dirs=('.claude/rules',), reads_agents_md=False, compared=True), 'cline': HostSpec(name='cline', instruction_files=('.clinerules',), rule_dirs=('.clinerules',), reads_agents_md=True, compared=True), 'codex': HostSpec(name='codex', instruction_files=(), rule_dirs=(), reads_agents_md=True, compared=True), 'copilot': HostSpec(name='copilot', instruction_files=('.github/copilot-instructions.md',), rule_dirs=('.github/instructions',), reads_agents_md=True, compared=True), 'cursor': HostSpec(name='cursor', instruction_files=('.cursorrules',), rule_dirs=('.cursor/rules',), reads_agents_md=True, compared=True), 'gemini': HostSpec(name='gemini', instruction_files=('GEMINI.md',), rule_dirs=(), reads_agents_md=False, compared=True), 'windsurf': HostSpec(name='windsurf', instruction_files=('.windsurfrules', '.windsurfrules.md'), rule_dirs=('.windsurf/rules',), reads_agents_md=False, compared=True), 'zed': HostSpec(name='zed', instruction_files=('.rules',), rule_dirs=(), reads_agents_md=True, compared=True)})

Coverage and drift of *host_files* against the *canonical* `AGENTS.md` text. Pure.

A blank canonical (empty, whitespace or a BOM) counts as absent.

* **Return type:**
  [`PortabilityReport`](#opsward.portability.PortabilityReport)

### opsward.portability.as_read(render, canonical)

*render* as its host reads it: an `@AGENTS.md` import replaced by *canonical*.

A line that is only the import is replaced in place; an import inside a sentence
appends the canonical at the end. A copy (no import) comes back unchanged, so
scoring a shim judges what the agent actually sees, not the three-line file.

```pycon
>>> as_read("@AGENTS.md\n\n## Claude\n\nx", "## Build\n\npytest\n")
'## Build\n\npytest\n\n## Claude\n\nx'
>>> as_read("Read @AGENTS.md first.", "## Build")
'Read @AGENTS.md first.\n\n## Build'
>>> as_read("## Build\n\npytest", "## Other")
'## Build\n\npytest'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.portability.check_portability(root, , hosts={'aider': HostSpec(name='aider', instruction_files=('CONVENTIONS.md',), rule_dirs=(), reads_agents_md=False, compared=False), 'claude': HostSpec(name='claude', instruction_files=('CLAUDE.md', '.claude/CLAUDE.md'), rule_dirs=('.claude/rules',), reads_agents_md=False, compared=True), 'cline': HostSpec(name='cline', instruction_files=('.clinerules',), rule_dirs=('.clinerules',), reads_agents_md=True, compared=True), 'codex': HostSpec(name='codex', instruction_files=(), rule_dirs=(), reads_agents_md=True, compared=True), 'copilot': HostSpec(name='copilot', instruction_files=('.github/copilot-instructions.md',), rule_dirs=('.github/instructions',), reads_agents_md=True, compared=True), 'cursor': HostSpec(name='cursor', instruction_files=('.cursorrules',), rule_dirs=('.cursor/rules',), reads_agents_md=True, compared=True), 'gemini': HostSpec(name='gemini', instruction_files=('GEMINI.md',), rule_dirs=(), reads_agents_md=False, compared=True), 'windsurf': HostSpec(name='windsurf', instruction_files=('.windsurfrules', '.windsurfrules.md'), rule_dirs=('.windsurf/rules',), reads_agents_md=False, compared=True), 'zed': HostSpec(name='zed', instruction_files=('.rules',), rule_dirs=(), reads_agents_md=True, compared=True)})

`analyze` over what is on disk under *root*: the library entry point.

* **Return type:**
  [`PortabilityReport`](#opsward.portability.PortabilityReport)

### opsward.portability.has_canonical(canonical)

Whether an `AGENTS.md` text says anything (a BOM or whitespace does not).

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### opsward.portability.read_host_files(root, , hosts={'aider': HostSpec(name='aider', instruction_files=('CONVENTIONS.md',), rule_dirs=(), reads_agents_md=False, compared=False), 'claude': HostSpec(name='claude', instruction_files=('CLAUDE.md', '.claude/CLAUDE.md'), rule_dirs=('.claude/rules',), reads_agents_md=False, compared=True), 'cline': HostSpec(name='cline', instruction_files=('.clinerules',), rule_dirs=('.clinerules',), reads_agents_md=True, compared=True), 'codex': HostSpec(name='codex', instruction_files=(), rule_dirs=(), reads_agents_md=True, compared=True), 'copilot': HostSpec(name='copilot', instruction_files=('.github/copilot-instructions.md',), rule_dirs=('.github/instructions',), reads_agents_md=True, compared=True), 'cursor': HostSpec(name='cursor', instruction_files=('.cursorrules',), rule_dirs=('.cursor/rules',), reads_agents_md=True, compared=True), 'gemini': HostSpec(name='gemini', instruction_files=('GEMINI.md',), rule_dirs=(), reads_agents_md=False, compared=True), 'windsurf': HostSpec(name='windsurf', instruction_files=('.windsurfrules', '.windsurfrules.md'), rule_dirs=('.windsurf/rules',), reads_agents_md=False, compared=True), 'zed': HostSpec(name='zed', instruction_files=('.rules',), rule_dirs=(), reads_agents_md=True, compared=True)})

Every host instruction file and rule folder present under *root*. Read-only.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### opsward.portability.summarize(report)

One diagnose suggestion per drifting render.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
