# Research: meta-tooling for a large personal AI-asset ecosystem

Deep-research reports backing the meta-tooling Epic ([#19](https://github.com/thorwhalen/opsward/issues/19)).
Each is web-researched (2024–2026 state of the art), Vancouver-referenced, and grounded in the
existing package ecosystem (`ir`, `imbed`, `grub`, `skill`, `raglab`, `aw`, `py2mcp`, `opsward`, …).
These reports are the **durable rationale**; the Epic and its sub-issues are the actionable work.

| Report | Covers | Seeds issue |
|---|---|---|
| [`discovery_and_dispatch.md`](discovery_and_dispatch.md) | Search tools vs. search agents (lexical/semantic/agentic); progressive tool disclosure ("one search tool, not fifty"); router/orchestrator-dispatcher patterns; asset registries; maintained capability discovery. | [#12](https://github.com/thorwhalen/opsward/issues/12), [#13](https://github.com/thorwhalen/opsward/issues/13), [#14](https://github.com/thorwhalen/opsward/issues/14) |
| [`multiplatform_config.md`](multiplatform_config.md) | Host config formats (Claude/Cursor/Copilot/Windsurf/Gemini); the AGENTS.md / MCP / SKILL.md convergence; author-once-emit-many portability and drift. | [#15](https://github.com/thorwhalen/opsward/issues/15) |
| [`adr_and_home_finding.md`](adr_and_home_finding.md) | Decision-record standards (Nygard / MADR / Y-statements / Tyree-Akerman); where to store decisions; AI-era rationale capture; package-boundary heuristics and reuse discovery. | [#16](https://github.com/thorwhalen/opsward/issues/16) |
| [`lifecycle_agentops.md`](lifecycle_agentops.md) | "AgentOps" as a discipline; code-vs-best-practice drift; eval of agent setups; validation/linting; versioned self-renewing rulesets; governance. | [#17](https://github.com/thorwhalen/opsward/issues/17) |

## The core finding

Almost all the machinery already exists across the ecosystem — the work is **compose/extend, not greenfield**,
with exactly **one genuinely new (thin) package**: an asset-catalog / ingestion layer ([#12](https://github.com/thorwhalen/opsward/issues/12))
that harvests every asset kind into one normalized corpus and keeps it indexed. See Epic [#19](https://github.com/thorwhalen/opsward/issues/19) for the layered architecture.
