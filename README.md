# opsward

Diagnose, generate, and maintain the AI agent setup of your projects —
CLAUDE.md, skills, subagents, rules, and supporting docs.

Opsward works in two modes:

- **CLI mode** — deterministic, pure-code analysis you run directly. No AI involved.
- **Claude Code mode** — install opsward as Claude Code skills so that Claude runs the
  CLI tools, interprets results intelligently, and acts on suggestions. No API keys
  needed — Claude Code is the AI engine.

## Install

```bash
pip install opsward
```

---

## CLI Mode (no AI)

These commands are deterministic Python code — regex scoring, filesystem checks,
template substitution. Same input always gives the same output.

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
skill templates, and agents — only what's missing, never overwrites existing files.

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

### Output Formats

All CLI commands support `--format json` for machine-parseable output:

```bash
opsward diagnose-cmd . --format json
opsward generate-cmd . --format json
opsward maintain-cmd . --format json
```

---

## Claude Code Mode (AI-enhanced)

Install opsward's skills into Claude Code, and Claude becomes an intelligent
layer on top of the deterministic tools — it runs `opsward diagnose`, reads the
scores, figures out what to fix, and does it.

### Install Skills

```bash
opsward install-skills-cmd --write                    # into ./.claude/ (project-level)
opsward install-skills-cmd --global-install --write   # into ~/.claude/ (all projects)
```

### What the Skills Do

Once installed, these skills activate automatically in Claude Code when you ask
the right thing:

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `opsward` | "check my setup", "opsward" | Diagnose → decide next step → generate or maintain → re-diagnose |
| `opsward-diagnose` | "audit my AI config" | Run `opsward diagnose`, interpret scores, offer concrete fixes |
| `opsward-generate` | "scaffold AI setup" | Run `opsward generate`, review, customize templates with real content |
| `opsward-maintain` | "check for staleness" | Run `opsward maintain`, prioritize issues, apply fixes |

### How It Works

1. Claude Code runs `opsward diagnose . --format json` via Bash
2. Opsward returns deterministic scores and suggestions (pure code, no AI)
3. Claude reads the structured output and reasons about what to do
4. Claude offers fixes, edits files, re-runs diagnose to show improvement

The CLI does the analysis. Claude does the thinking and acting.

---

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

## Python API

```python
from pathlib import Path
from opsward import scan, diagnose, generate, generate_skills, maintain

sr = scan('.')
report = diagnose(sr)
print(report)              # human-readable report card
print(report.grade)        # 'A', 'B', 'C', 'D', or 'F'

files = generate(sr)       # list[GeneratedFile]
issues = maintain(sr)      # list[MaintenanceSuggestion]

# Install skills programmatically
skill_files = generate_skills(Path.home() / '.claude')
```
