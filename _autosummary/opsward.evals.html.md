# opsward.evals

Eval harness (opsward#17, gap 3): opt-in, report-only quality signals beyond the rubric.

Two layers, both of which *report* and never gate (model calls cost money and are
nondeterministic, so the deterministic rubric stays the only gate):

* **LLM-as-judge** for the rubric’s subjective dimensions (actionability, conciseness):
  [`judge_claude_md()`](#opsward.evals.judge_claude_md) asks a *judge* to score CLAUDE.md against an explicit rubric,
  > `samples` times, and reports the median next to the rubric’s own score.
* **Golden tasks**: [`run_golden_tasks()`](#opsward.evals.run_golden_tasks) runs an *agent* on repo-specific tasks with
  and without a candidate config, and checks each output against the task’s `expect` /
  `forbid` patterns. The with-minus-without pass rate is the signal that a config helps.

The judge and the agent are injected. [`rubric_judge()`](#opsward.evals.rubric_judge) (the default judge) and
[`echo_agent()`](#opsward.evals.echo_agent) are free and deterministic – they exercise the harness and anchor the
scale – while [`anthropic_judge()`](#opsward.evals.anthropic_judge) and [`anthropic_agent()`](#opsward.evals.anthropic_agent) make paid calls through
the `anthropic` SDK (`pip install 'opsward[eval]'`) and are never used by default.

```pycon
>>> report = judge_claude_md("# P\n\n## Commands\n\n```bash\npytest\n```\n")
>>> sorted(report.scores), report.judge
(['actionability', 'conciseness'], 'rubric')
>>> tasks = [GoldenTask("kw", "Write f(a, b, c)", expect=[r"\*,"])]
>>> golden = run_golden_tasks(tasks, agent=echo_agent, config="Use `*,` before the 3rd arg.")
>>> golden.delta()
1.0
```

### Module Attributes

| [`DFLT_JUDGE_MODEL`](#opsward.evals.DFLT_JUDGE_MODEL)          | Default model for the paid judge and agent; override with `model=`.                                                                         |
|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| [`JUDGE_RUBRICS`](#opsward.evals.JUDGE_RUBRICS)             | vague "rate the quality" prompts give noise, anchored bands do not.                                                                         |
| [`Judge`](#opsward.evals.Judge)                     | the JSON object above).                                                                                                                     |
| [`Agent`](#opsward.evals.Agent)                     | An agent does a task under a config (CLAUDE.md text; `""` = no config) and returns its output.                                              |
| [`DFLT_GOLDEN_TASKS_RELPATH`](#opsward.evals.DFLT_GOLDEN_TASKS_RELPATH) | Where a repo keeps its golden tasks, relative to its docs folder (`opsward.scan.docs_dir_for()`: `misc/docs` for Python, `docs` for JS/TS). |

### Functions

| [`anthropic_agent`](#opsward.evals.anthropic_agent)(\*[, model, client, max_tokens])   | A paid single-call agent: the config is the system prompt, the task the user turn.                                              |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| [`anthropic_judge`](#opsward.evals.anthropic_judge)(\*[, model, client, max_tokens])   | A paid judge over the Messages API.                                                                                             |
| [`echo_agent`](#opsward.evals.echo_agent)(task, config)                           | The free agent: "does" the task by quoting its config, so a config that states the convention passes and an empty one does not. |
| [`golden_tasks_path`](#opsward.evals.golden_tasks_path)(scan_result)                     | The default golden-tasks file of a scanned project (it may not exist).                                                          |
| [`judge_claude_md`](#opsward.evals.judge_claude_md)(content, \*[, judge, ...])         | Score CLAUDE.md `content` on each subjective dimension, `samples` times each.                                                   |
| [`load_golden_tasks`](#opsward.evals.load_golden_tasks)(path)                            | Tasks from a JSON list of `{"name", "prompt", "expect": [...], "forbid": [...]}`.                                               |
| [`parse_verdict`](#opsward.evals.parse_verdict)(reply, \*, max_score)                | `(score, reasoning)` from a judge reply: the *last* JSON object in it with a `score`.                                           |
| [`rubric_judge`](#opsward.evals.rubric_judge)(request)                              | The free, deterministic judge: answers with opsward's own rubric score.                                                         |
| [`run_golden_tasks`](#opsward.evals.run_golden_tasks)(tasks, \*, agent, config[, ...])  | Run every task `runs` times under `config` and under `baseline`; count passes.                                                  |

### Classes

| [`DimensionVerdict`](#opsward.evals.DimensionVerdict)(score, max_score, rubric_score)   | A dimension's judged score (median of the samples) next to the rubric's own.               |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| [`GoldenReport`](#opsward.evals.GoldenReport)(runs[, results, errors])              | Per task and arm (`with` / `without` the config): runs passed and runs that errored.       |
| [`GoldenTask`](#opsward.evals.GoldenTask)(name, prompt[, expect, forbid])         | A repo-specific task, passed when the output matches every `expect` regex and no `forbid`. |
| [`JudgeReport`](#opsward.evals.JudgeReport)(judge[, scores])                       | Every judged dimension.                                                                    |
| [`JudgeRequest`](#opsward.evals.JudgeRequest)(dimension, content)                   | One dimension to judge: the rubric, the content, and the rendered prompt.                  |

### opsward.evals.Agent

An agent does a task under a config (CLAUDE.md text; `""` = no config) and returns its output.

alias of [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`GoldenTask`](#opsward.evals.GoldenTask), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### opsward.evals.DFLT_GOLDEN_TASKS_RELPATH *= 'evals/golden_tasks.json'*

Where a repo keeps its golden tasks, relative to its docs folder
(`opsward.scan.docs_dir_for()`: `misc/docs` for Python, `docs` for JS/TS).

### opsward.evals.DFLT_JUDGE_MODEL *= 'claude-opus-5-5'*

Default model for the paid judge and agent; override with `model=`.

### *class* opsward.evals.DimensionVerdict(score, max_score, rubric_score, samples=list(), reasoning=list(), errors=list())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A dimension’s judged score (median of the samples) next to the rubric’s own.

### *class* opsward.evals.GoldenReport(runs, results=dict(), errors=dict())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Per task and arm (`with` / `without` the config): runs passed and runs that errored.

A run whose agent raised is left out of its arm’s pass rate (it says nothing about the
config), so a flaky agent cannot skew [`delta()`](#opsward.evals.GoldenReport.delta); the errors are listed.

#### delta()

Pass rate with the config minus without: positive means the config helps.

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float)

#### rate(arm)

Passed / completed (non-errored) runs in `arm`; 0.0 when none completed.

* **Return type:**
  [`float`](https://docs.python.org/3/builtins/functions.html#float)

### *class* opsward.evals.GoldenTask(name, prompt, expect=(), forbid=())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A repo-specific task, passed when the output matches every `expect` regex and no `forbid`.

### opsward.evals.JUDGE_RUBRICS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)]* *= {'actionability': {'bands': {'0': 'Empty, or nothing actionable.', '1-4': 'Mostly generic advice an agent cannot turn into an action.', '13-15': 'Every instruction names a concrete command, path, pattern or rule; nothing needs interpretation.', '5-8': 'About half is aspiration or description rather than instruction.', '9-12': 'Mostly concrete; a few instructions are vague ("keep code clean") or lack the command to run.'}, 'max': 15, 'question': 'Can a coding agent act on these instructions without guessing?'}, 'conciseness': {'bands': {'0': 'Empty.', '1-4': 'Bloated: the useful instructions are hard to find.', '13-15': 'No filler, no repetition, no prose where a list or a command would do; detail lives in linked docs.', '5-8': 'Noticeable padding: restated points, long explanations an agent does not need every session.', '9-12': 'Mostly tight; some repetition or paragraphs that could be one line.'}, 'max': 15, 'question': "Is it dense and scannable, with every line earning its place in an agent's context?"}}*

vague “rate the quality” prompts give noise, anchored bands do not.

* **Type:**
  Explicit rubrics

### opsward.evals.Judge

the JSON object above).

* **Type:**
  A judge reads a request and returns its raw reply (expected

alias of [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`JudgeRequest`](#opsward.evals.JudgeRequest)], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### *class* opsward.evals.JudgeReport(judge, scores=dict())

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Every judged dimension. Report-only: nothing here is meant to fail a build.

### *class* opsward.evals.JudgeRequest(dimension, content)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One dimension to judge: the rubric, the content, and the rendered prompt.

### opsward.evals.anthropic_agent(, model='claude-opus-5-5', client=None, max_tokens=16000)

A paid single-call agent: the config is the system prompt, the task the user turn.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`GoldenTask`](#opsward.evals.GoldenTask), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### opsward.evals.anthropic_judge(, model='claude-opus-5-5', client=None, max_tokens=16000)

A paid judge over the Messages API. `client` defaults to `anthropic.Anthropic()`.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`JudgeRequest`](#opsward.evals.JudgeRequest)], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### opsward.evals.echo_agent(task, config)

The free agent: “does” the task by quoting its config, so a config that states the
convention passes and an empty one does not. It tests the harness, not a model.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.evals.golden_tasks_path(scan_result)

The default golden-tasks file of a scanned project (it may not exist).

```pycon
>>> import tempfile
>>> from opsward.scan import scan
>>> root = Path(tempfile.mkdtemp())
>>> _ = (root / "pyproject.toml").write_text("")
>>> golden_tasks_path(scan(root, claude_config_dir=None)).relative_to(root).as_posix()
'misc/docs/evals/golden_tasks.json'
```

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### opsward.evals.judge_claude_md(content, \*, judge=<function rubric_judge>, dimensions=('actionability', 'conciseness'), samples=1)

Score CLAUDE.md `content` on each subjective dimension, `samples` times each.

A reply that cannot be parsed is recorded as an error on its dimension, never raised.

* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – `samples < 1` or an unknown dimension (a mistake in the call).
* **Return type:**
  [`JudgeReport`](#opsward.evals.JudgeReport)

### opsward.evals.load_golden_tasks(path)

Tasks from a JSON list of `{"name", "prompt", "expect": [...], "forbid": [...]}`.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`GoldenTask`](#opsward.evals.GoldenTask)]

### opsward.evals.parse_verdict(reply, , max_score)

`(score, reasoning)` from a judge reply: the *last* JSON object in it with a `score`.

The last, because a judge that quotes a snippet or restates the format writes its
verdict at the end. `9`, `9.0` and `"9"` are all read as 9.

* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – no JSON object with a `score`, or one that is not an integer in
  `0..max_score`.
* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`int`](https://docs.python.org/3/builtins/functions.html#int), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> parse_verdict('Quote {"a": 1}. Verdict: {"reasoning": "ok", "score": 12}', max_score=15)
(12, 'ok')
```

### opsward.evals.rubric_judge(request)

The free, deterministic judge: answers with opsward’s own rubric score.

It exercises the harness end to end and anchors the scale (a real judge’s scores are
read next to it), but it is not an independent opinion.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.evals.run_golden_tasks(tasks, , agent, config, baseline='', runs=1)

Run every task `runs` times under `config` and under `baseline`; count passes.

An agent error is recorded, never raised, and leaves that run out of the pass rate.

* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – two tasks share a name, or `runs < 1`.
* **Return type:**
  [`GoldenReport`](#opsward.evals.GoldenReport)
