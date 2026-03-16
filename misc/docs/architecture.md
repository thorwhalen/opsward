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
   - `.claude/skills/`, `.claude/agents/`, `.claude/rules/` inventories
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

Generated artifacts include CLAUDE.md, docs, skills, agents, and rules. Future: AGENTS.md generation (cross-platform agent instructions, see `ai_setup_meta_tooling.md` Section 1.5).

### Maintain

1. Takes a `ScanResult` and optionally a previous `DiagnosisReport`.
2. Checks for:
   - Stale paths in CLAUDE.md (referenced files that no longer exist)
   - Docs whose `Last Updated` date is old relative to code changes
   - Skills with descriptions that don't match current project state
   - `docs_guide.md` out of sync with actual docs directory contents
   - `known_issues.md` items that reference closed GitHub issues
3. Returns `list[MaintenanceSuggestion]` — each with a category, description, and optional diff.

## Module Responsibilities

| Module | Responsibility | I/O |
|--------|---------------|-----|
| `scan.py` | Read-only filesystem inspection | `Path → ScanResult` |
| `score.py` | Pure scoring logic | `ScanResult → DiagnosisReport` |
| `generate.py` | Template loading + rendering | `ScanResult → list[GeneratedFile]` |
| `maintain.py` | Drift/staleness detection | `ScanResult → list[MaintenanceSuggestion]` |
| `base.py` | All dataclasses and type definitions | (no I/O) |
| `cli.py` | argh dispatch + pretty-printing | stdin/stdout |
| `util.py` | Shared helpers | (internal) |

## Key Invariants

- `scan.py` NEVER writes to the target project. It is purely read-only.
- `generate.py` NEVER overwrites existing files without explicit policy.
- All scoring functions are pure: same input always produces same output.
- Templates are loaded via `importlib.resources` — never via hardcoded paths.

## Extension Points

- **Custom rubrics**: Users can provide a rubric override file (YAML) to adjust scoring weights.
- **Custom templates**: Users can point to a directory of custom templates that override built-in ones.
- **Project type plugins**: The detection logic in `scan.py` uses a registry pattern — new project types can be added by registering detection functions and doc-path conventions.
- **AGENTS.md output**: `generate.py` can be extended to emit AGENTS.md (cross-platform agent instructions) alongside CLAUDE.md.
- **Skill spec validation**: `score.py` can validate skills against the agentskills.io specification (name format, frontmatter fields, size limits, directory structure).
