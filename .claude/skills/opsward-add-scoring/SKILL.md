---
name: opsward-add-scoring
description: Add or adjust opsward's quality scoring — a CLAUDE.md sub-dimension, a whole weighted component, or the skill/spec validation rules — in score.py. Use when changing how `opsward diagnose` grades a project, tuning weights or point thresholds, adding a new ComponentScore, or modifying validate_skill_spec. Explains the pure-function contract, the weighting math, and the constants to keep balanced.
---

# Changing opsward's scoring

All scoring lives in `opsward/score.py` and is **pure**: functions take a
`ScanResult` (and helper lists) and return data — no I/O, no writes. The entry
point is `diagnose(scan_result) -> DiagnosisReport` (`score.py:29`).

## The two levels of score

### 1. Components (the top level)

`diagnose` builds a `list[ComponentScore]`, each 0–100, then computes a weighted
overall via `_OVERALL_WEIGHTS` (`score.py:17`):

```python
_OVERALL_WEIGHTS = {
    "CLAUDE.md quality": 0.35,
    "Documentation": 0.25,
    "Skills": 0.20,
    "Setup (rules/agents/hooks)": 0.10,
    "Cross-references": 0.10,
}
```

**Invariant: the weights must sum to 1.0.** A `ComponentScore.name` must match
its key here exactly, or its weight silently falls to 0 (`score_map.get(name, 0)`
in `diagnose`).

To add a component: write `_score_<thing>(sr, *, missing, suggestions) ->
ComponentScore`, append it in `diagnose`, add its weight to `_OVERALL_WEIGHTS`,
and **rebalance the other weights so the total stays 1.0**.

### 2. CLAUDE.md dimensions (inside the "CLAUDE.md quality" component)

`_score_claude_md` (`score.py:99`) sums six `_dim_*` helpers whose maxes are
declared as constants and **must sum to 100**:

```python
_CMD_MAX=20  _ARCH_MAX=20  _CONV_MAX=15  _CONCISE_MAX=15  _CURRENCY_MAX=15  _ACTION_MAX=15
```

To add/replace a dimension: add a `_dim_<name>(content, notes) -> int` returning
0..max, call it in `_score_claude_md`, and adjust the `_*_MAX` constants so they
still total 100. Each `_dim_*` is a small pure function over the CLAUDE.md text
(regex/heuristics) — see `_dim_commands` (`score.py:126`) as the template.

## Conventions for score helpers

- Append human-readable strings to `notes` (shown per-component), `missing`
  (checklist of absent artifacts), and `suggestions` (numbered remediation
  steps). These lists are threaded through by reference.
- Clamp totals with `min(total, 100)` as existing components do.
- Keep it heuristic and cheap — scoring is regex/string-level, not semantic.
  Deeper semantic judgment is intentionally left to the AI skill layer.

## Skill spec validation

`validate_skill_spec(skill) -> list[str]` (`score.py:365`, public, exported from
`__init__`) checks a `SkillInfo` against the agentskills.io spec — `name`
pattern/length, `name` matches directory, `description` present/length,
`compatibility` length, and SKILL.md line cap. Constants: `_NAME_PATTERN`,
`_MAX_SKILL_LINES`, `_MAX_NAME_LEN`, `_MAX_DESC_LEN`, `_MAX_COMPAT_LEN`
(`score.py:380`). It feeds the "Skills" component (`_score_skills`). Add a check
by appending to `violations`; add a constant rather than inlining a magic number.

## After changing scores

1. **Update the docs.** The dimension list lives in `CLAUDE.md` ("Scoring
   Pattern") — keep it in sync. Mention non-obvious weighting in
   `misc/docs/architecture.md` if relevant.
2. **Test.** Extend `tests/` — assert grade boundaries or a known fixture's
   component scores. Doctests on `diagnose` (`score.py:32`) show the style.
3. **Sanity-check the math:** weights sum to 1.0; dimension maxes sum to 100.

```bash
pytest
python -m opsward diagnose .        # eyeball the report on opsward itself
```
