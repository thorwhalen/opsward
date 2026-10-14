# 0004 — Shipped skills wrap the deterministic CLI; judgment lives in the agent

## Status

Accepted (2026-03-11)

## Context

The first skill templates (`diagnose-setup`, `maintain-docs`) were instruction-only: they told an agent what to check, and the agent did the checking from scratch each time, inconsistently. opsward also has to stay usable without any model access, e.g. in CI.

## Decision

- opsward's own logic is deterministic Python exposed as a CLI (`diagnose`, `generate`, `maintain`, `recommend`) with machine-readable output (`--format json`).
- The skills it installs into projects (`opsward`, `opsward-diagnose`, `opsward-generate`, `opsward-maintain`, plus the read-only `setup-auditor` agent) run that CLI via Bash and then let the agent interpret the structured output, customise generated stubs with real content, and act on suggestions.
- opsward makes no model calls and needs no API key. Semantic judgment (is this convention actually useful? is this description accurate?) is left to the agent layer; the scorer stays heuristic and cheap.

## Consequences

- The same numbers come out in CI, in a terminal, and inside an agent session.
- The CLI's output format is a contract the shipped skills depend on; it is pinned by the CLI goldens (see [0008](0008-cli-surface-pinned-by-goldens.md)).
- Scores measure form, not effect: there is no LLM-as-judge or eval layer (a known gap, discussed in `misc/docs/research/lifecycle_agentops.md`).
- opsward dogfoods these skills on itself, alongside hand-written contributor skills (`opsward-dev`, `opsward-add-*`) that are a different artifact class.

## Evidence

- Instruction-only skills replaced by four CLI-invoking skills + `install-skills`: commit [138f95e](https://github.com/thorwhalen/opsward/commit/138f95e)
- `CLAUDE.md`: "These skills are AI-enhanced: they invoke opsward's deterministic CLI tools via Bash … No API keys needed."
- Shipped skills installed on opsward itself, contributor skills added: [PR #1](https://github.com/thorwhalen/opsward/pull/1)
