# Rule: templates, generation safety, and path citations

## Templates
- Templates use `string.Template` (`${var}`) — **not** Jinja2. No conditionals
  inside a template; if you need a variant, split into separate template files.
- Access bundled templates via `importlib.resources.files("opsward.data")` —
  never hardcode a filesystem path to package data.
- Every module needs a top-level docstring (auto-extracted for generated docs).

## Generation safety
- `generate`/`maintain` are **dry-run by default**; writing requires `--write`.
- **Never overwrite** an existing target file without explicit confirmation.
- **Minimal generation**: only offer artifacts genuinely useful for the detected
  project type (e.g. no `deployment.md` for a non-deployed library — CI workflows
  are not a deployment signal).

## Path citations (avoid self-inflicted cross-ref dings)
opsward's own cross-reference check parses bare `dir/file.md` tokens in CLAUDE.md
and resolves them against the repo root. Always cite **full repo-relative paths**
(e.g. `opsward/data/templates/shared/setup-auditor.md`), never bare or partial
ones, or you create a broken-reference ding in opsward's self-diagnosis.
