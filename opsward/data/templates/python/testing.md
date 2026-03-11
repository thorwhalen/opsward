# Testing — ${project_name}

## Test Framework

${test_framework}

## Running Tests

```bash
${test_command}
```

## Test Structure

- Tests live in `${test_dir}/`
- Test files follow `test_{module_name}.py` naming
- Fixtures and shared helpers in `${test_dir}/conftest.py`

## Coverage

```bash
${coverage_command}
```

## Writing Tests

- Each test function tests one behavior
- Use descriptive test names: `test_{what}_{condition}_{expected}`
- Prefer pytest fixtures over setUp/tearDown
