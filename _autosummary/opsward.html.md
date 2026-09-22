# opsward

Diagnose, generate, and maintain the AI agent setup of your projects.

### Modules

| [`base`](opsward.base.html.md#module-opsward.base)                                       | All dataclasses and type definitions for opsward.                                                |
|-----------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| [`cli`](opsward.cli.html.md#module-opsward.cli)                                         | CLI dispatch for opsward.                                                                        |
| [`data`](opsward.data.html.md#module-opsward.data)                                       | Bundled package resources for opsward, accessed via `importlib.resources.files("opsward.data")`. |
| [`discover`](opsward.discover.html.md#module-opsward.discover)                               | Optional cross-repo asset discovery, delegating to the `toolery` package.                        |
| [`generate`](opsward.generate.html.md#opsward.generate)(scan_result, \*[, agents_md, hooks]) | Determine which artifacts are missing, render templates, return files to create.                 |
| [`maintain`](opsward.maintain.html.md#opsward.maintain)(scan_result, \*[, previous_report])  | Detect maintenance issues and return suggestions.                                                |
| [`recommend`](opsward.recommend.html.md#module-opsward.recommend)                             | Recommend skills from the ecosystem based on project tech stack.                                 |
| [`scan`](opsward.scan.html.md#opsward.scan)(project_root)                                | Scan *project_root* and return a ScanResult.                                                     |
| [`score`](opsward.score.html.md#module-opsward.score)                                     | Pure scoring functions.                                                                          |
| [`util`](opsward.util.html.md#module-opsward.util)                                       | Shared helpers for opsward.                                                                      |
