# Opsward Roadmap

Generated from competitive landscape analysis (March 2026).

## Integrate (use or defer to these established tools)

### Agent Skills Open Standard (agentskills.io)
Opsward-generated SKILL.md files must be fully compliant. The spec defines strict rules (name format, frontmatter fields, directory structure, size limits) that opsward should validate against — not reinvent.

- **Action**: Add `validate_skill_spec(skill_dir: Path) -> list[SpecViolation]` in `opsward/score.py`. Check: `name` matches directory name, 1-64 chars lowercase+hyphens, no consecutive hyphens; `description` is 1-1024 chars; SKILL.md ≤500 lines; optional fields (`license`, `compatibility`, `metadata`, `allowed-tools`) conform to spec types.
- **Action**: Wire this into `diagnose` so every skill in `.claude/skills/` gets validated. Report violations in `DiagnosisReport`.

### Vercel Skills CLI (`npx skills`)
This is the emerging package manager for skills. Opsward should generate skills that are installable via `npx skills add`.

- **Action**: Ensure opsward-generated skill directories follow the exact structure expected by `npx skills`: `SKILL.md` at root, optional `scripts/`, `references/`, `assets/` subdirectories. Already mostly true — verify and add integration test.
- **Action**: In `generate.py`, when generating skills, include a comment in output noting the skill can be installed via `npx skills add <local-path>`.

### AGENTS.md Standard
60,000+ projects use AGENTS.md. Opsward should generate it alongside CLAUDE.md for cross-platform portability.

- **Action**: Add an `--agents-md` flag to `opsward generate`. When set, emit an `AGENTS.md` at the project root containing the cross-platform subset of CLAUDE.md content (build/test commands, code style, project structure, PR instructions). Use a new template at `opsward/data/templates/shared/AGENTS.md.template`.
- **Action**: In `diagnose`, check if AGENTS.md exists and whether it's consistent with CLAUDE.md. Report as an optional suggestion (not a required component).

### MADR Decision Records
Already targeted. No changes needed — opsward generates `decisions/` with MADR templates.

## Differentiate (opsward's unique value — protect and sharpen these)

### Diagnosis + Scoring
No other tool scores a project's AI setup on a rubric. spec-kit scaffolds but can't tell you what's wrong. Inside-agent tools consume context without producing reusable scores.

- **Action**: Make scoring output machine-readable (JSON) in addition to human-readable. Add `--format json` flag to `opsward diagnose`. This enables CI integration (fail the build if AI setup score drops below threshold).
- **Action**: Add a `--ci` flag that returns exit code 1 if any component scores below a configurable threshold. Example: `opsward diagnose . --ci --min-score 60`.

### External CLI (CI-friendly, context-free)
Opsward runs outside the agent — it doesn't consume context, works in CI pipelines, and handles multiple projects. This is a fundamental advantage over skill-factory, agents-md-generator, and agent-rules-skill.

- **Action**: Add a GitHub Actions example to the README showing `opsward diagnose` in a CI workflow.
- **Action**: Document the CI use case in `misc/docs/deployment.md` or a new `misc/docs/ci_integration.md`.

### Multi-Project Scanning
No competitor handles multiple projects. This is unique to opsward.

- **Action**: Ensure `MultiProjectReport` includes cross-project pattern detection (e.g., "3/5 projects missing conventions.md", "average CLAUDE.md score: 42/100"). Already in the design — verify implementation matches.

### Maintenance Loop (Drift Detection)
No competitor has staleness/drift detection. spec-kit scaffolds once; inside-agent tools don't track changes over time.

- **Action**: Prioritize implementing `maintain.py` fully. The staleness checks (stale paths, outdated docs, skills with stale descriptions, docs_guide.md drift) are the highest-value differentiator after diagnosis.

## Expand (gaps opsward could fill)

### Skill Recommendation from Ecosystem Catalogs
VoltAgent/awesome-agent-skills has 549+ skills from official teams. Opsward could analyze a project's tech stack and recommend relevant skills.

- **Action**: Add a `recommend_skills(scan_result: ScanResult) -> list[SkillRecommendation]` function in a new `opsward/recommend.py`. Match detected tech stack (Python packages, JS dependencies, cloud providers) against a curated mapping of skill categories → skill repos. Start with a small hand-curated mapping (e.g., `supabase` in deps → recommend Supabase skills, `stripe` → Stripe skills).
- **Effort**: Medium. **Impact**: High for discoverability.

### Hook Scaffolding
Reference repos (disler, diet103, ChrisWiles) demonstrate hook patterns that most projects could benefit from: auto-formatting on PostToolUse, skill-activation on UserPromptSubmit, session context loading on SessionStart.

- **Action**: Add hook templates to `opsward/data/templates/shared/hooks/`. Start with three: `auto-format.sh` (PostToolUse), `skill-activation.sh` (UserPromptSubmit with skill-rules.json), `session-context.sh` (SessionStart). Generate them via `opsward generate --hooks`.
- **Action**: In `diagnose`, check if any hooks are configured. If none, suggest the starter hooks.
- **Effort**: Low-medium. **Impact**: Medium.

### Self-Improvement Loop Pattern
christianestay/claude-code-base-project demonstrates a tasks/lessons.md pattern for cross-session learning. Opsward could scaffold this.

- **Action**: Add a `tasks/` directory template with `todo.md` and `lessons.md` stubs. Include in `generate` output when `--tasks` flag is set. Low priority — nice-to-have.
- **Effort**: Low. **Impact**: Low-medium.

### AGENTS.md Scoped Generation for Monorepos
netresearch/agent-rules-skill generates thin root AGENTS.md + scoped subsystem files. Opsward could detect monorepo structures and generate scoped AGENTS.md files.

- **Action**: In `scan.py`, detect monorepo patterns (multiple `package.json` or `pyproject.toml` at different levels, `packages/` or `apps/` directories). In `generate.py`, when monorepo detected and `--agents-md` set, generate scoped AGENTS.md files per subsystem.
- **Effort**: Medium. **Impact**: Medium (monorepo-specific).

## Mention (peer projects for the README's "Related Work" section)

Add a "Related Work" section to the README acknowledging these projects:

| Project | Relationship |
|---------|-------------|
| **spec-kit** (GitHub) | Closest competitor on scaffolding. Template-based, no diagnosis/maintenance. |
| **claude-code-skill-factory** | Inside-agent skill/agent builders. Good for interactive authoring. |
| **ccexp** | TUI for browsing Claude Code config. Complements opsward. |
| **npx skills** (Vercel) | Skill package manager. Opsward-generated skills should be installable via it. |
| **awesome-agent-skills** (VoltAgent) | 549+ community skills catalog. Opsward could recommend from it. |
| **awesome-claude-code** (hesreallyhim) | Best ecosystem index. List opsward here. |
| **wshobson/agents** | Pre-built plugin monorepo. Opposite philosophy (pre-built vs. project-specific). |
| **Mintlify skill.md** | Auto-generates skill.md from docs sites. Same philosophy, different input. |

## Concrete Next Actions

Ordered by effort/impact ratio (best first):

1. **Add agentskills.io validation to `score.py`**: Add `validate_skill_spec()` that checks SKILL.md frontmatter (name format, description length, directory name match, size ≤500 lines). Wire into `diagnose`. ~50 lines of code.

2. **Add `--format json` to `diagnose`**: Make `DiagnosisReport` serializable to JSON. Add `--format` flag to CLI. Enables CI integration. ~30 lines.

3. **Add `--ci` flag to `diagnose`**: Return exit code 1 if any score below `--min-score` threshold. ~15 lines in `cli.py`.

4. **Add AGENTS.md template and `--agents-md` flag to `generate`**: Create `opsward/data/templates/shared/AGENTS.md.template` with cross-platform sections (build commands, code style, project structure). Add flag to `generate` command. ~60 lines.

5. **Add hook templates**: Create three starter hook scripts in `opsward/data/templates/shared/hooks/` (auto-format, skill-activation, session-context). Add `--hooks` flag to `generate`. ~100 lines of templates + 30 lines of generation logic.

6. **Add hook diagnosis**: In `score.py`, check if any hooks are configured. If none, include a suggestion in `DiagnosisReport`. ~20 lines.

7. **Add Related Work section to README**: List the peer projects from the table above. ~30 lines of markdown.

8. **Add `recommend.py` for ecosystem skill recommendations**: Match project dependencies against a curated tech→skill mapping. Start with 10-15 popular tech stacks. ~80 lines.

9. **Add AGENTS.md consistency check to `diagnose`**: If both CLAUDE.md and AGENTS.md exist, check that build commands and project structure are consistent between them. ~40 lines.

10. **Add monorepo detection to `scan.py`**: Detect multi-package structures. Use in scoped AGENTS.md generation. ~60 lines.

11. **Add GitHub Actions CI example**: Create `.github/workflows/ai-setup-check.yml` example in docs or templates showing `opsward diagnose --ci` in a workflow. ~20 lines.

12. **Submit opsward to awesome-claude-code**: Open a PR to hesreallyhim/awesome-claude-code adding opsward to the Tooling section.
