# opsward.recommend

Recommend skills from the ecosystem based on project tech stack.

Maps detected dependencies and frameworks to curated skill sources.

### Functions

| [`recommend_skills`](#opsward.recommend.recommend_skills)(scan_result)   | Recommend ecosystem skills based on detected tech stack.   |
|----------------------------------------------------------------------------------|------------------------------------------------------------|

### Classes

| [`SkillRecommendation`](#opsward.recommend.SkillRecommendation)(name, reason, source)   | A recommended skill from the ecosystem.   |
|----------------------------------------------------------------------------------------------|-------------------------------------------|

### *class* opsward.recommend.SkillRecommendation(name, reason, source)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A recommended skill from the ecosystem.

### opsward.recommend.recommend_skills(scan_result)

Recommend ecosystem skills based on detected tech stack.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`SkillRecommendation`](#opsward.recommend.SkillRecommendation)]

```pycon
>>> from pathlib import Path
>>> from opsward.base import ScanResult
>>> recommend_skills(ScanResult(project_root=Path('/tmp/empty')))
[]
```
