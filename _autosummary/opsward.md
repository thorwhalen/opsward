# opsward

Diagnose, generate, and maintain the AI agent setup of your projects.

### Modules

| [`base`](opsward.base.md#module-opsward.base)                                       | All dataclasses and type definitions for opsward.                                                |
|-----------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [`cli`](opsward.cli.md#module-opsward.cli)                                         | CLI dispatch for opsward.                                                                        |
| [`data`](opsward.data.md#module-opsward.data)                                       | Bundled package resources for opsward, accessed via `importlib.resources.files("opsward.data")`. |
| [`discover`](opsward.discover.md#module-opsward.discover)                               | Optional cross-repo asset discovery, delegating to the `toolery` package.                        |
| [`generate`](opsward.generate.md#opsward.generate)(scan_result, \*[, agents_md, hooks]) | Determine which artifacts are missing, render templates, return files to create.                 |
| [`maintain`](opsward.maintain.md#opsward.maintain)(scan_result, \*[, previous_report])  | Detect maintenance issues and return suggestions.                                                |
| [`recommend`](opsward.recommend.md#module-opsward.recommend)                             | Recommend skills from the ecosystem based on project tech stack.                                 |
| [`scan`](opsward.scan.md#opsward.scan)(project_root)                                | Scan *project_root* and return a ScanResult.                                                     |
| [`score`](opsward.score.md#module-opsward.score)                                     | Pure scoring functions.                                                                          |
| [`util`](opsward.util.md#module-opsward.util)                                       | Shared helpers for opsward.                                                                      |
