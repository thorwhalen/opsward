# 0007 — A dependency-light core; heavier capabilities are lazily-imported extras

## Status

Accepted (2026-03-11; CLI dependency replaced 2026-08-30; first optional extra 2026-07-04)

## Context

opsward is a diagnostic and scaffolding tool meant to be installed everywhere, including into CI and next to arbitrary projects. Every runtime dependency is install weight, a version-conflict risk with the project being diagnosed, and, for a copyleft dependency, a licensing question.

## Decision

- The core has one runtime dependency, the CLI dispatcher `cw` (MIT, zero runtime dependencies), which replaced `argh` (LGPL-3.0-or-later).
- Everything else is standard library: `string.Template` for templates ([0003](0003-string-template-not-jinja2.md)), a hand-written parser for the YAML subset used in SKILL.md frontmatter (`def _parse_frontmatter` in `scan.py`), substring matching instead of dependency-file parsing in `recommend.py`.
- A capability that needs a heavy dependency ships as an optional extra, imported lazily inside the function that needs it, with an `ImportError` that names the install command. The first is cross-repo asset discovery (`opsward find`, extra `opsward[discovery]` pulling in `toolery`).

## Consequences

- `pip install opsward` is small and conflict-unlikely; the extra only costs users who want it.
- Hand-rolled parsing is deliberately partial (the frontmatter parser handles the agentskills.io subset, not general YAML; `recommend` has known false positives, see `misc/docs/recommend_design.md`).
- Tests for an extra must skip cleanly when it is not installed.

## Evidence

- `CLAUDE.md` Tech Stack: "No heavy deps: This is a lightweight diagnostic/scaffolding tool."
- argh → cw for license and zero dependencies: [PR #25](https://github.com/thorwhalen/opsward/pull/25)
- `toolery` as a lazily-imported optional extra: commit [9d22c4f](https://github.com/thorwhalen/opsward/commit/9d22c4f)
