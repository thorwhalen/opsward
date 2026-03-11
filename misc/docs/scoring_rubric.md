# Scoring Rubric

## CLAUDE.md Quality Score (0-100)

Six dimensions, each scored independently. Inspired by community best practices
(particularly the giuseppe-trisciuoglio claude-md-management skill and GitHub's
analysis of 2,500+ AGENTS.md files).

### 1. Commands & Workflows (0-20)

| Score | Criteria |
|-------|----------|
| 0-5 | No commands documented |
| 6-10 | Only install/build documented |
| 11-15 | Build, test, and run documented |
| 16-20 | Build, test, run, lint, and common workflows all documented with copy-pasteable commands |

**Detection:** Look for code blocks containing shell commands. Check if `test`, `build`, `dev`/`start`, `lint` commands are present.

### 2. Architecture Clarity (0-20)

| Score | Criteria |
|-------|----------|
| 0-5 | No module map or structure description |
| 6-10 | Basic directory listing without role annotations |
| 11-15 | Module map with role descriptions |
| 16-20 | Module map with roles, relationships, and data flow hints |

**Detection:** Look for a "Module Map" or "Architecture" or "Structure" section. Check if entries have descriptions (not just bare paths).

### 3. Conventions (0-15)

| Score | Criteria |
|-------|----------|
| 0-3 | No conventions section |
| 4-7 | Generic advice ("write clean code") |
| 8-11 | Project-specific conventions that differ from defaults |
| 12-15 | Specific, actionable conventions with examples or references to linter configs |

**Detection:** Look for a "Conventions" or "Style" or "Patterns" section. Check for specificity (mentions concrete tools, patterns, file names).

### 4. Conciseness (0-15)

| Score | Criteria |
|-------|----------|
| 0-3 | Over 500 lines, or mostly boilerplate |
| 4-7 | 200-500 lines, some bloat |
| 8-11 | 80-200 lines, mostly signal |
| 12-15 | Under 80 lines, dense and scannable |

**Detection:** Line count. Ratio of headings to content. Presence of long prose paragraphs (bad) vs. bullet points and code blocks (good).

### 5. Currency (0-15)

| Score | Criteria |
|-------|----------|
| 0-3 | Multiple referenced paths don't exist |
| 4-7 | Some stale references |
| 8-11 | All referenced paths exist, but some sections feel dated |
| 12-15 | All references valid, content matches current project state |

**Detection:** Extract all file paths from CLAUDE.md. Check each one exists in the project. Flag broken references.

### 6. Actionability (0-15)

| Score | Criteria |
|-------|----------|
| 0-3 | Vague instructions, agent would have to guess |
| 4-7 | Some actionable instructions mixed with vague ones |
| 8-11 | Most instructions are actionable |
| 12-15 | Every instruction is specific enough to act on without further context |

**Detection:** Heuristic — look for imperative verbs, code blocks, specific file references. Flag sentences that contain "appropriate", "as needed", "consider" without specifics.

## Skill Quality Score (0-100, per skill)

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Frontmatter valid | 20 | Has `name` and `description` in YAML frontmatter |
| Description quality | 20 | Description explains WHEN to use it, not just WHAT it does |
| Size | 15 | Under 500 lines (as recommended by Anthropic) |
| Instructions clarity | 20 | Steps are numbered or clearly structured |
| References present | 10 | Links to supporting files if skill is complex |
| Tool restrictions | 15 | Uses `allowed-tools` if skill should be read-only or limited |

## Documentation Completeness Score (0-100)

Based on which docs exist and their quality:

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| `docs_guide.md` exists | 25 | The entry-point document |
| Core docs present | 30 | `architecture.md`, `known_issues.md`, `conventions.md` |
| Docs have content | 20 | Not just empty templates — have actual project-specific info |
| Cross-references work | 15 | CLAUDE.md points to docs_guide, docs_guide lists all docs accurately |
| Freshness | 10 | Docs updated within last 90 days (if project has recent commits) |

## Overall Setup Health Score

Weighted combination:

| Component | Weight |
|-----------|--------|
| CLAUDE.md quality | 35% |
| Documentation completeness | 25% |
| Skills inventory | 20% |
| Rules/agents/hooks | 10% |
| Cross-reference integrity | 10% |

Letter grades: A (90-100), B (80-89), C (70-79), D (60-69), F (<60).
