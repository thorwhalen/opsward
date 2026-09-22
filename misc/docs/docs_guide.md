# Documentation Guide

This directory contains project knowledge documents for both human developers
and AI agents working on opsward. Consult this guide to find the right document
for your task.

| Document | When to Read | Description |
|----------|-------------|-------------|
| `ai_setup_meta_tooling.md` | Before any design work | Foundational research: what exists in the ecosystem, gap analysis, and the original design proposal |
| `architecture.md` | Before making structural changes | System design, module responsibilities, data flow, key abstractions |
| `conventions.md` | Before writing new code | Coding style, patterns, naming, and template authoring rules |
| `target_artifacts.md` | When working on the generator | Complete spec of every file opsward can generate for a target project |
| `scoring_rubric.md` | When working on the diagnostic | Detailed scoring criteria for CLAUDE.md, skills, docs, and overall setup health |
| `docs_catalog.md` | When adding/changing doc types | The canonical list of doc types opsward knows about, with naming rationale (SSOT — see note in `target_artifacts.md` and `ai_setup_meta_tooling.md` §2.1) |
| `known_issues.md` | Before investigating a bug | Known bugs, quirks, and workarounds |
| `roadmap.md` | Before proposing new work | Longer-term plans and feature ideas; check for a completed/archived banner before treating an item as still open |
| `testing.md` | Before writing or running tests | How to run opsward's own test suite, frameworks used, coverage expectations |
| `decisions/` | Before revisiting a past design choice | MADR-style architectural decision records, one file per decision |
| `research/` | Before scoping a new meta-tooling feature | Deep-research reports backing the AI-asset meta-tooling epic (thorwhalen/opsward#19) |
