# opsward

Diagnose, generate, and maintain the AI agent setup of your projects —
CLAUDE.md, skills, subagents, rules, and supporting docs.

## Install

```bash
pip install opsward
```

## Quick Start

### Diagnose

Score your project's AI setup health:

```bash
opsward diagnose-cmd .
```

```
Diagnosis Report: myproject
Project type: python
Overall score: 72/100  (Grade: C)

Components:
  CLAUDE.md quality         [################....] 81/100
  Documentation             [##############......] 70/100
  Skills                    [############........] 60/100
  Setup (rules/agents/hooks) [##########..........] 50/100
  Cross-references          [####################] 100/100

Missing:
  [ ] docs_guide.md
  [ ] docs/known_issues.md

Suggestions:
  1. Create a docs_guide.md to index your documentation
  2. Consider adding hooks in .claude/hooks.json
```

### Generate

Create missing artifacts (dry run by default):

```bash
opsward generate-cmd .
opsward generate-cmd . --write   # actually create files
```

Generates CLAUDE.md, docs (architecture, conventions, known_issues, etc.),
skills (diagnose-setup, maintain-docs), and agents (setup-auditor) —
only what's missing, never overwrites existing files.

### Maintain

Find stale references and drift:

```bash
opsward maintain-cmd .
```

```
myproject: 3 issue(s)

  [stale_path] CLAUDE.md references `src/old_module.py` but it does not exist
  [sync_issue] `new_doc.md` exists in docs/ but is not listed in docs_guide.md
  [empty_doc] `conventions.md` appears to be an empty stub (12 bytes)
```

## What It Checks

**CLAUDE.md quality** (6 dimensions):
- Commands & workflows — are build/test/lint commands documented?
- Architecture clarity — is there a module map with role descriptions?
- Conventions — are project-specific style rules present?
- Conciseness — is the file scannable, not bloated?
- Currency — do referenced paths actually exist?
- Actionability — are instructions specific enough to act on?

**Documentation completeness**: docs_guide.md, architecture.md, conventions.md,
known_issues.md, and content quality.

**Skills & agents**: SKILL.md presence, descriptions, setup-auditor agent.

**Cross-references**: paths in CLAUDE.md validated against the filesystem.

**Overall health**: weighted score (A–F grade) combining all components.

## Output Formats

All commands support `--format json` for machine-parseable output:

```bash
opsward diagnose-cmd . --format json
opsward generate-cmd . --format json
opsward maintain-cmd . --format json
```

## Python API

```python
from opsward import scan, diagnose, generate, maintain

sr = scan('.')
report = diagnose(sr)
print(report)              # human-readable report card
print(report.grade)        # 'A', 'B', 'C', 'D', or 'F'

files = generate(sr)       # list[GeneratedFile]
issues = maintain(sr)      # list[MaintenanceSuggestion]
```
