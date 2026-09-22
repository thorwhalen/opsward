# opsward.data

Bundled package resources for opsward, accessed via `importlib.resources.files("opsward.data")`.

Holds the generation templates (under `templates/`) and any other static
assets the generator installs into target projects. Never hardcode filesystem
paths to these resources – resolve them through `importlib.resources`.

### Modules

| [`templates`](opsward.data.templates.html.md#module-opsward.data.templates)   | Generation templates organized by target project type.   |
|--------------------------------------------------------------------------------------------|----------------------------------------------------------|
