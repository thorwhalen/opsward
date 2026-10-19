# Architecture

## Core Abstraction

Opsward models a project's AI setup as a collection of **components**, each with a known location, expected structure, and quality score. The three top-level operations — diagnose, generate, maintain — are pure transformations over this model.

```
Target Project ──► scan.py ──► ScanResult ──► score.py ──► DiagnosisReport
                                   │
                                   ▼
                              generate.py ──► list of (path, content) pairs
                                   │
                                   ▼
                              maintain.py ──► list of MaintenanceSuggestion
```

## Data Flow

### Diagnose

1. `scan.py` walks the target project, collecting:
   - Project type (Python / JS/TS / mixed)
   - CLAUDE.md content and location
   - `.claude/skills/`, `.claude/agents/` (subfolders included, agents identified by their `name:`), `.claude/rules/` inventories (each skill entry also records whether it is a symlink bridge and whether a canonical `skills/<name>` or `<pkg>/data/skills/<name>` twin exists)
   - The user's global skill scope (`$CLAUDE_CONFIG_DIR/skills`, default `~/.claude/skills`), through the `claude_config_dir` keyword seam; `None` reads nothing outside the target
   - Hooks configuration (`.claude/hooks.json` or `settings.local.json`)
   - Docs directory contents and `docs_guide.md` if present
2. `score.py` evaluates the scan results against rubrics:
   - CLAUDE.md quality (6 dimensions, 0-100)
   - Skill validity (frontmatter against agentskills.io spec, size ≤500 lines, description quality)
   - Doc completeness (which docs exist vs. recommended set)
   - Cross-reference integrity (do paths in CLAUDE.md actually exist?)
3. Output: `DiagnosisReport` dataclass with component scores, missing items, and prioritized suggestions.

### Generate

1. Takes a `ScanResult` (or runs a scan if needed).
2. Determines which artifacts are missing and would be useful.
3. Loads templates from `opsward/data/templates/{project_type}/` and `shared/`.
4. Substitutes variables from scan results (project name, detected tech stack, module paths).
5. Returns `list[GeneratedFile]` — each is a `(target_path, content, overwrite_policy)` tuple.
6. CLI presents diffs and asks for confirmation before writing.

Generated artifacts include CLAUDE.md, docs, skills, agents, and rules, plus optional AGENTS.md (cross-platform agent instructions — `--agents-md` flag, shipped; see `ai_setup_meta_tooling.md` Section 1.5).

### Recommend

1. Takes a `ScanResult`; reads the dependency files at its root (`pyproject.toml`, `package.json`, …).
2. Matches them against the curated `_RECOMMENDATIONS` table and skips skills already installed.
3. Returns `list[SkillRecommendation]`. Advisory only: not part of the diagnosis score. Full design, heuristics and limits: `recommend_design.md`.

### Maintain

1. Takes a `ScanResult` and optionally a previous `DiagnosisReport`.
2. Runs one `_check_*` generator per kind of drift (in `def maintain`, `maintain.py`):
   - `stale_path`: paths referenced in CLAUDE.md that no longer exist
   - `claude_md_size`: CLAUDE.md over the size budget (the same finding `diagnose` scores)
   - `sync_issue`: `docs_guide.md` out of sync with the actual docs directory contents
   - `outdated_doc`: docs with no git commit in the last 90 days (skipped outside a git repo)
   - `incomplete_skill`: skills with no SKILL.md or no description
   - `empty_doc`: docs under 50 bytes (stubs)
   - `subagent_twin`: a skill's declared subagent twin is missing or stale, or a hand-written agent duplicates a skill (`subagents.py`, ADR 0009)
   - `stale_adr`: a decision record cites a path that no longer exists, or has no Status (`decisions.py`, ADR 0010)
3. Returns `list[MaintenanceSuggestion]` — each with a category, description, and optional diff.

## Module Responsibilities

| Module | Responsibility | I/O |
|--------|---------------|-----|
| `scan.py` | Read-only filesystem inspection (the target, plus the user's global skill scope through the `claude_config_dir` seam) | `Path → ScanResult` |
| `score.py` | Pure scoring logic | `ScanResult → DiagnosisReport` |
| `decisions.py` | Decision capture: next ADR, Y-statement log, ADR drift | `Path → GeneratedFile`, `ScanResult → MaintenanceSuggestion` |
| `subagents.py` | Skill-declared subagent twins: spec, render, sync state | `SkillInfo → SubagentSpec`, `ScanResult → GeneratedFile / MaintenanceSuggestion` |
| `generate.py` | Template loading + rendering | `ScanResult → list[GeneratedFile]` |
| `maintain.py` | Drift/staleness detection | `ScanResult → list[MaintenanceSuggestion]` |
| `recommend.py` | Maps detected dependencies/frameworks to curated ecosystem skills (design: `recommend_design.md`) | `ScanResult → list[SkillRecommendation]` |
| `base.py` | All dataclasses and type definitions | (no I/O) |
| `cli.py` | command functions + pretty-printing | stdin/stdout |
| `util.py` | Shared helpers | (internal) |

## Key Invariants

The rationale and evidence for these live in `decisions/` (indexed by `decisions/README.md`).

- `scan.py` NEVER writes to the target project. It is purely read-only.
- `generate.py` NEVER overwrites existing files without explicit policy.
- All scoring functions are pure: same input always produces same output.
- Templates are loaded via `importlib.resources` — never via hardcoded paths.

## Shipped (previously listed here as future extension points)

- **AGENTS.md output**: `generate.py` emits AGENTS.md (cross-platform agent instructions) alongside CLAUDE.md, behind the `--agents-md` flag.
- **Skill spec validation**: `score.py::validate_skill_spec` validates skills against the agentskills.io specification (name format, frontmatter fields, size limits) and feeds both `diagnose` and the Skills score.

## Extension Points

- **Custom templates**: Users can point to a directory of custom templates that override built-in ones.
- **Project type plugins**: The detection logic in `scan.py` uses a registry pattern — new project types can be added by registering detection functions and doc-path conventions.

Note: the rubric in `score.py` is hardcoded module constants, not an external override file — see `.claude/rules/scoring-invariants.md`. There is no "custom rubric" extension point.
