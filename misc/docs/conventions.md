# Conventions

## Code Style

- **Functional first.** Logic lives in functions, not methods. Classes are for data (`dataclasses`) and storage abstractions (`Mapping`).
- **Keyword-only args** from position 3+. Use `*` separator.
- **Generators** over lists. Return `Iterable[T]` / `Iterator[T]` unless the caller genuinely needs a concrete collection.
- **Helper naming:**
  - Inner function → define inside its single caller
  - Module-private → prefix with `_` (e.g., `_parse_frontmatter`)
  - Reusable across modules → no underscore, consider moving to `util.py`
- **Docstrings:** Minimal. One line for simple functions. Include a doctest if it's cheap to write.
- **Type hints:** Use them. Prefer `collections.abc` types (`Mapping`, `Iterable`, `Sequence`) over concrete types in signatures.

## Template Authoring

- Templates use `string.Template` syntax: `${variable_name}`.
- Template files live in `opsward/data/templates/` and have a `.md` extension (not `.md.template` — they ARE valid markdown, just with placeholders).
- If a template needs conditional sections, split into separate files (e.g., `claude_md_python.md` vs `claude_md_jsts.md`) rather than adding a template engine.
- Every template must be valid markdown even with placeholders unreplaced — so `${project_name}` reads naturally in context.

## File Organization

- Keep modules focused. If a module grows past ~300 lines, consider splitting.
- Tests go in `tests/` with `test_{module_name}.py` naming.
- Test data / fixtures go in `tests/fixtures/` (mock project directories).

## Error Handling

- Use informative error messages that tell the user what to do.
- For missing optional dependencies, provide install instructions in the error message.
- Separate error-raising from business logic where practical (e.g., a validation function returns errors, the caller decides whether to raise or log).

## CLI Conventions

- All CLI functions accept `*project_roots: str` as positional args (one or more paths).
- Common keyword args: `--dry-run` (default True for generate/maintain), `--format` (text/json), `--verbose`.
- Output goes to stdout. Errors go to stderr. Exit codes: 0 = success, 1 = issues found, 2 = error.
- When `--format json` is used, output is machine-parseable JSON matching the dataclass structure.
