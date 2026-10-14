# Design: `recommend.py` — tech-stack to skill recommendations

`opsward/recommend.py` answers one question: *given what this project depends on, which ready-made ecosystem skills should its agent have?* It is the "pull" side of opsward: `diagnose` grades the setup a project already has, `generate` scaffolds opsward's own artifacts, and `recommend` points at third-party skills the project does not have yet. It shipped in commit `283d71a` (March 2026), as item 8 of the v1 roadmap (`roadmap.md`, "Skill Recommendation from Ecosystem Catalogs").

## Inputs and outputs

| | |
|---|---|
| Public function | `recommend_skills(scan_result: ScanResult) -> list[SkillRecommendation]`, exported from `opsward/__init__.py` |
| Input | a `ScanResult` from `scan.py`. Only two fields are used: `project_root` (to locate dependency files) and `skills` (to skip skills already installed) |
| Output | a list of `SkillRecommendation(name, reason, source)` — a frozen dataclass defined in `recommend.py` itself, not in `base.py` |
| CLI | `opsward recommend [ROOT ...] [--format text\|json]` (`def recommend` in `cli.py`): one block per root in text mode, one flat JSON list of `{name, reason, source}` across all roots in JSON mode. Exits 0 for any existing root, never 1 on content (a recommendation is advice, not a failure); 2 for a missing root, like every command |
| Side effects | none. Files are read with `read_text_safe`; nothing is written or fetched from the network |

## How it works

`recommend_skills` materialises the generator `_iter_recommendations`, which does three things:

1. **Build a signal corpus.** `_build_signal_corpus` reads a fixed list of dependency and build files at the project root — `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`, `package.json`, `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml` — lowercases each, and joins them into one string. Missing or undecodable files contribute nothing. An empty corpus yields no recommendations.
2. **Match the curated table.** `_RECOMMENDATIONS` is an ordered list of `(signal_keywords, SkillRecommendation)` pairs (15 entries today: Supabase, Stripe, Cloudflare Workers, Firebase, Prisma, Docker, Terraform, FastAPI, Django, Flask, Next.js, Tailwind CSS, Vercel, Netlify, Anthropic SDK). An entry fires if **any** of its keywords is a **substring** of the corpus.
3. **Deduplicate.** An entry is skipped if a skill of the same `name` is already in `sr.skills` (installed in `.claude/skills/`) or was already yielded in this run. Output order is table order.

Every current entry points `source` at the VoltAgent `awesome-agent-skills` catalog; the catalog itself is not fetched or checked.

## The heuristics, and their known limits

The matcher is deliberately crude — substring search over raw file text, no dependency parsing — because it keeps the module dependency-free (no TOML/JSON parser, no lockfile reader) and cheap enough to run on every project. The price is precision:

- **Substring, not package-name, matching.** Keywords are found anywhere in the file text, including project descriptions, keywords and comments. Concretely, opsward itself gets an `anthropic-sdk` recommendation because `claude` appears in its `pyproject.toml` (the `keywords` list, and the `description`'s mention of CLAUDE.md), not because it depends on the Anthropic SDK. Short keywords are the riskiest: `next` (in the Next.js entry) matches any file containing the word "next".
- **Case.** The corpus is lowercased but keywords are not, so a keyword must be written in lowercase to ever match. The `"Dockerfile"` keyword in the Docker entry can never match; the entry only works through its other keyword, `docker`.
- **Root only.** Only files at `project_root` are read. A monorepo's per-package manifests (which `scan.py` does detect, as `monorepo_packages`) are not consulted, and neither are lockfiles or `requirements/*.txt` variants.
- **Name-based dedup.** "Already installed" means a skill directory with exactly the recommendation's `name`. A differently named skill covering the same tool does not suppress the recommendation.

These are acceptable for an advisory command that always exits 0, but they are the first things to fix if `recommend` output is ever fed into scoring or automation.

## Relation to the scorer

`recommend` is **independent of `score.py`**. `diagnose` does not call it, and no `ComponentScore` reflects whether recommended skills are installed. That separation is intentional for now:

- the scorer is a pure, deterministic judgment of what is *present* (see `decisions/0002-hardcoded-scoring-rubric.md`), while a recommendation is a suggestion about what is *absent* and depends on a curated, opinionated, and fast-changing third-party catalog;
- the matcher's false positives (above) would turn into unfair point deductions;
- a project may legitimately decline a recommended skill.

The `Skills` component in `score.py` (`def _score_skills`) only grades the skills that exist: SKILL.md present, description present, `validate_skill_spec` clean. If recommendations ever feed `diagnose`, they belong in the advisory `suggestions` list (as `_check_agents_md` does for AGENTS.md), not in a weighted score, and only after the precision limits above are fixed.

## Extension points

- **Add a mapping.** Append a `(keywords, SkillRecommendation)` pair to `_RECOMMENDATIONS`. Keywords must be lowercase and specific enough to avoid false positives. The step-by-step recipe is the `opsward-add-recommendation` dev skill (`.claude/skills/opsward-add-recommendation/SKILL.md`).
- **Add a signal file.** Add its filename to the tuple in `_build_signal_corpus`. Keep it a read via `read_text_safe` so a missing file stays harmless.
- **Change the source.** `source` is a free string per entry; a skill that lives outside the default catalog just names its own URL.
- **Structured matching (not built).** Replacing the substring corpus with parsed dependency names (from `pyproject.toml` `[project.dependencies]`, `package.json` `dependencies`/`devDependencies`) would remove most false positives. The natural seam is `_build_signal_corpus`: return a set of normalised dependency names instead of a string, and match keywords against it by equality. If that data is wanted elsewhere too, it belongs on `ScanResult` (see the `opsward-add-scan-field` dev skill) rather than being re-parsed here.
- **Catalog as data (not built).** The table is a hardcoded module constant, like the scoring rubric. Moving it to a bundled data file under `opsward/data/` (read via `importlib.resources`) is the natural step if it grows large or is shared with other tools; it should stay bundled, not user-overridable, for the same reproducibility reasons as the rubric.

## Tests

`tests/test_new_features.py::TestRecommendSkills` covers the empty project, a FastAPI match, no duplicates, and suppression by an installed skill. The `recommend_skills` doctest covers the empty `ScanResult`. `misc/cli_cases.txt` pins `recommend tests/fixtures/python_project` (which yields no recommendations) and `recommend --help` in the CLI goldens.
