# Conventions — ${project_name}

## Code Style

- **Formatter:** ${formatter}
- **Linter:** ${linter}
- **Line length:** ${line_length}

## Naming

- Modules: `snake_case`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

## Imports

- Standard library first, then third-party, then local
- Prefer absolute imports

## Type Hints

- Use type hints for all public function signatures
- Prefer `collections.abc` types (`Mapping`, `Iterable`, `Sequence`) over concrete types

## Testing

- Tests in `tests/` with `test_{module_name}.py` naming
- Use pytest fixtures for shared setup

## Project-Specific Conventions

<!-- Add conventions specific to this project -->
