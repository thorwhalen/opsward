# opsward

Diagnose, generate, and maintain the AI agent setup of your projects.

### Modules

| [`base`](opsward.base.html.md#module-opsward.base)                                           | All dataclasses and type definitions for opsward.                                                |
|---------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [`cli`](opsward.cli.html.md#module-opsward.cli)                                             | CLI dispatch for opsward.                                                                        |
| [`data`](opsward.data.html.md#module-opsward.data)                                           | Bundled package resources for opsward, accessed via `importlib.resources.files("opsward.data")`. |
| [`decisions`](opsward.decisions.html.md#module-opsward.decisions)                                 | Decision capture: numbered ADRs, the one-line decision log, and their drift.                     |
| [`discover`](opsward.discover.html.md#module-opsward.discover)                                   | Optional cross-repo asset discovery, delegating to the `toolery` package.                        |
| [`evals`](opsward.evals.html.md#module-opsward.evals)                                         | Eval harness (opsward#17, gap 3): opt-in, report-only quality signals beyond the rubric.         |
| [`fleet`](opsward.fleet.html.md#opsward.fleet)(roots, \*[, diagnose_root, check_dirs])        | Diagnose every root and aggregate.                                                               |
| [`generate`](opsward.generate.html.md#opsward.generate)(scan_result, \*[, agents_md, hooks])     | Determine which artifacts are missing, render templates, return files to create.                 |
| [`lint`](opsward.lint.html.md#module-opsward.lint)                                           | Schema lint (opsward#17, gap 2): spec and config violations, pass or fail, no score.             |
| [`maintain`](opsward.maintain.html.md#opsward.maintain)(scan_result, \*[, previous_report, ...]) | Detect maintenance issues and return suggestions.                                                |
| [`recommend`](opsward.recommend.html.md#module-opsward.recommend)                                 | Recommend skills from the ecosystem based on project tech stack.                                 |
| [`scan`](opsward.scan.html.md#opsward.scan)(project_root, \*[, claude_config_dir])           | Scan *project_root* and return a ScanResult.                                                     |
| [`score`](opsward.score.html.md#module-opsward.score)                                         | Pure scoring functions.                                                                          |
| [`security`](opsward.security.html.md#module-opsward.security)                                   | Security advisories (opsward#17, gap 5): "valid" is not "safe to ship".                          |
| [`subagents`](opsward.subagents.html.md#module-opsward.subagents)                                 | Reuse a skill as a subagent: declare it in the skill, generate the twin, check the sync.         |
| [`util`](opsward.util.html.md#module-opsward.util)                                           | Shared helpers for opsward.                                                                      |
