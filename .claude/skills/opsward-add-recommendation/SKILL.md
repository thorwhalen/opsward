---
name: opsward-add-recommendation
description: Add a tech-stack→skill mapping to opsward's recommendation engine in recommend.py, so `opsward recommend` suggests an ecosystem skill when it detects a dependency or framework (e.g. Supabase, FastAPI, Tailwind). Use when extending the curated `_RECOMMENDATIONS` list, adding a new detection signal, or changing where recommended skills are sourced from.
---

# Adding a skill recommendation to opsward

`opsward recommend` inspects a project's dependency files and suggests curated
ecosystem skills for the detected stack. All logic is in `opsward/recommend.py`.

## How matching works

`recommend_skills(scan_result)` (`recommend.py:153`) →
`_iter_recommendations` (`recommend.py:164`):

1. `_build_signal_corpus(sr)` concatenates and **lowercases** the text of the
   project's dependency files — `pyproject.toml`, `setup.py`, `setup.cfg`,
   `requirements.txt`, `package.json`, `Dockerfile`, `docker-compose.yml/.yaml`
   (`recommend.py:181`).
2. For each `(signal_keywords, SkillRecommendation)` entry in `_RECOMMENDATIONS`,
   if **any** keyword is a substring of the corpus, the recommendation is
   yielded.
3. Recommendations already installed as skills (`sr.skills`) or already yielded
   are skipped (dedup by `rec.name`).

## Add an entry

Append a tuple to `_RECOMMENDATIONS` (`recommend.py:29`):

```python
(
    ("signal1", "signal2"),          # lowercase substrings to look for in deps
    SkillRecommendation(
        name="my-skill",             # also the dedup key
        reason="Foo framework detected",
        source="https://github.com/VoltAgent/awesome-agent-skills",
    ),
),
```

Guidelines:

- **Signals are lowercase substrings** matched against the corpus. Keep them
  specific enough to avoid false positives (e.g. `"tailwindcss"` not `"css"`).
  Provide multiple aliases when a tool has several (`("react", "next", "nextjs")`).
- **`name`** doubles as the dedup/existing-skill key — make it the canonical
  skill name.
- **`reason`** is a short human phrase shown in the report ("X detected").
- **`source`** is where the user gets the skill. The existing catalog points at
  `awesome-agent-skills`; reuse it unless the skill genuinely lives elsewhere.
- Order matters only for output ordering; matching is independent per entry.

## If you need a new detection signal

To match on a file not already scanned, add its filename to the tuple in
`_build_signal_corpus` (`recommend.py:185`). It is read with `read_text_safe`
(missing files are ignored), keeping the function read-only.

## Verify

```bash
python -m opsward recommend /path/to/project-with-that-dep   # should list it
python -m opsward recommend . --format json                  # machine output
pytest
```

Add a test in `tests/`: build a `ScanResult` (or a temp project) whose dep file
contains the signal and assert your recommendation appears — and that it is
suppressed when an equally-named skill already exists. The doctest on
`recommend_skills` (`recommend.py:156`) shows the empty-project baseline.
