"""Eval harness (opsward#17, gap 3): opt-in, report-only quality signals beyond the rubric.

Two layers, both of which *report* and never gate (model calls cost money and are
nondeterministic, so the deterministic rubric stays the only gate):

* **LLM-as-judge** for the rubric's subjective dimensions (actionability, conciseness):
  :func:`judge_claude_md` asks a *judge* to score CLAUDE.md against an explicit rubric,
  ``samples`` times, and reports the median next to the rubric's own score.
* **Golden tasks**: :func:`run_golden_tasks` runs an *agent* on repo-specific tasks with
  and without a candidate config, and checks each output against the task's ``expect`` /
  ``forbid`` patterns. The with-minus-without pass rate is the signal that a config helps.

The judge and the agent are injected. :func:`rubric_judge` (the default judge) and
:func:`echo_agent` are free and deterministic -- they exercise the harness and anchor the
scale -- while :func:`anthropic_judge` and :func:`anthropic_agent` make paid calls through
the ``anthropic`` SDK (``pip install 'opsward[eval]'``) and are never used by default.

>>> report = judge_claude_md("# P\\n\\n## Commands\\n\\n```bash\\npytest\\n```\\n")
>>> sorted(report.scores), report.judge
(['actionability', 'conciseness'], 'rubric')
>>> tasks = [GoldenTask("kw", "Write f(a, b, c)", expect=[r"\\*,"])]
>>> golden = run_golden_tasks(tasks, agent=echo_agent, config="Use `*,` before the 3rd arg.")
>>> golden.delta()
1.0
"""

from __future__ import annotations

import json
import re
import statistics
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

#: Default model for the paid judge and agent; override with ``model=``.
DFLT_JUDGE_MODEL = "claude-opus-5-5"
DFLT_MAX_TOKENS = 16000

#: Explicit rubrics: vague "rate the quality" prompts give noise, anchored bands do not.
JUDGE_RUBRICS: dict[str, dict] = {
    "actionability": {
        "max": 15,
        "question": "Can a coding agent act on these instructions without guessing?",
        "bands": {
            "13-15": "Every instruction names a concrete command, path, pattern or rule; nothing needs interpretation.",
            "9-12": 'Mostly concrete; a few instructions are vague ("keep code clean") or lack the command to run.',
            "5-8": "About half is aspiration or description rather than instruction.",
            "1-4": "Mostly generic advice an agent cannot turn into an action.",
            "0": "Empty, or nothing actionable.",
        },
    },
    "conciseness": {
        "max": 15,
        "question": "Is it dense and scannable, with every line earning its place in an agent's context?",
        "bands": {
            "13-15": "No filler, no repetition, no prose where a list or a command would do; detail lives in linked docs.",
            "9-12": "Mostly tight; some repetition or paragraphs that could be one line.",
            "5-8": "Noticeable padding: restated points, long explanations an agent does not need every session.",
            "1-4": "Bloated: the useful instructions are hard to find.",
            "0": "Empty.",
        },
    },
}
DFLT_DIMENSIONS = tuple(JUDGE_RUBRICS)

_JUDGE_TEMPLATE = """You are grading one dimension of a CLAUDE.md file, the instructions a coding agent reads at the start of every session.

Dimension: {dimension}
Question: {question}
Score bands (integer 0-{max}):
{bands}

Rules:
- Judge only against this rubric. Length is not quality: do not reward a longer file, and do not reward a confident or authoritative tone.
- Quote the lines that decide the score before giving it.
- Reply with one JSON object and nothing else: {{"reasoning": "<your quotes and argument>", "score": <integer 0-{max}>}}

<claude_md>
{content}
</claude_md>"""


@dataclass(frozen=True)
class JudgeRequest:
    """One dimension to judge: the rubric, the content, and the rendered prompt."""

    dimension: str
    content: str

    @property
    def rubric(self) -> dict:
        return JUDGE_RUBRICS[self.dimension]

    @property
    def prompt(self) -> str:
        r = self.rubric
        bands = "\n".join(f"- {band}: {text}" for band, text in r["bands"].items())
        return _JUDGE_TEMPLATE.format(
            dimension=self.dimension,
            question=r["question"],
            max=r["max"],
            bands=bands,
            content=self.content,
        )


#: A judge reads a request and returns its raw reply (expected: the JSON object above).
Judge = Callable[[JudgeRequest], str]


def rubric_judge(request: JudgeRequest) -> str:
    """The free, deterministic judge: answers with opsward's own rubric score.

    It exercises the harness end to end and anchors the scale (a real judge's scores are
    read next to it), but it is not an independent opinion.
    """
    from opsward import score

    dim = {
        "actionability": score._dim_actionability,
        "conciseness": score._dim_conciseness,
    }
    notes: list[str] = []
    value = dim[request.dimension](request.content, notes)
    return json.dumps({"reasoning": "; ".join(notes) or "rubric score", "score": value})


rubric_judge.judge_name = "rubric"  # type: ignore[attr-defined]


def _client(client):
    if client is not None:
        return client
    try:
        import anthropic
    except ImportError as error:  # pragma: no cover - depends on the environment
        raise ImportError(
            "the paid judge needs the anthropic SDK: pip install 'opsward[eval]'"
        ) from error
    return anthropic.Anthropic()


def _text_of(response) -> str:
    if getattr(response, "stop_reason", None) == "refusal":
        raise RuntimeError("the model declined the request (stop_reason: refusal)")
    return "".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    )


def _create(
    client, *, model: str, max_tokens: int, messages: list, system: str | None = None
):
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
        # On a policy decline the API re-runs the request on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if system:
        kwargs["system"] = system
    return client.beta.messages.create(**kwargs)


def anthropic_judge(
    *, model: str = DFLT_JUDGE_MODEL, client=None, max_tokens: int = DFLT_MAX_TOKENS
) -> Judge:
    """A paid judge over the Messages API. ``client`` defaults to ``anthropic.Anthropic()``."""
    client = _client(client)

    def judge(request: JudgeRequest) -> str:
        messages = [{"role": "user", "content": request.prompt}]
        return _text_of(
            _create(client, model=model, max_tokens=max_tokens, messages=messages)
        )

    judge.judge_name = model  # type: ignore[attr-defined]
    return judge


def parse_verdict(reply: str, *, max_score: int) -> tuple[int, str]:
    """``(score, reasoning)`` from a judge reply: the *last* JSON object in it with a ``score``.

    The last, because a judge that quotes a snippet or restates the format writes its
    verdict at the end. ``9``, ``9.0`` and ``"9"`` are all read as 9.

    :raises ValueError: no JSON object with a ``score``, or one that is not an integer in
        ``0..max_score``.

    >>> parse_verdict('Quote {"a": 1}. Verdict: {"reasoning": "ok", "score": 12}', max_score=15)
    (12, 'ok')
    """
    decoder = json.JSONDecoder()
    verdict = None
    for start in (i for i, ch in enumerate(reply) if ch == "{"):
        try:
            data, _ = decoder.raw_decode(reply, start)
        except ValueError:
            continue
        if isinstance(data, dict) and "score" in data:
            verdict = data
    if verdict is None:
        raise ValueError("no JSON object with a `score` in the judge reply")
    value = _as_int(verdict["score"])
    if value is None or not 0 <= value <= max_score:
        raise ValueError(
            f"score must be an integer in 0..{max_score}, got {verdict['score']!r}"
        )
    return value, str(verdict.get("reasoning", ""))


def _as_int(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return None


@dataclass
class DimensionVerdict:
    """A dimension's judged score (median of the samples) next to the rubric's own."""

    score: float | None
    max_score: int
    rubric_score: int
    samples: list[int] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def spread(self) -> int:
        return max(self.samples) - min(self.samples) if self.samples else 0


@dataclass
class JudgeReport:
    """Every judged dimension. Report-only: nothing here is meant to fail a build."""

    judge: str
    scores: dict[str, DimensionVerdict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "judge": self.judge,
            "scores": {k: asdict(v) for k, v in self.scores.items()},
        }

    def __str__(self) -> str:
        lines = [f"Judge: {self.judge}"]
        for name, v in self.scores.items():
            shown = "n/a" if v.score is None else f"{v.score:g}/{v.max_score}"
            extra = f", spread {v.spread}" if len(v.samples) > 1 else ""
            lines.append(
                f"  {name}: {shown} (rubric {v.rubric_score}/{v.max_score}{extra})"
            )
            lines += [f"    error: {e}" for e in v.errors]
        return "\n".join(lines)


def judge_claude_md(
    content: str,
    *,
    judge: Judge = rubric_judge,
    dimensions: Sequence[str] = DFLT_DIMENSIONS,
    samples: int = 1,
) -> JudgeReport:
    """Score CLAUDE.md ``content`` on each subjective dimension, ``samples`` times each.

    A reply that cannot be parsed is recorded as an error on its dimension, never raised.

    :raises ValueError: ``samples < 1`` or an unknown dimension (a mistake in the call).
    """
    if samples < 1:
        raise ValueError("samples must be at least 1")
    if unknown := [d for d in dimensions if d not in JUDGE_RUBRICS]:
        raise ValueError(
            f"unknown dimension(s) {unknown} (known: {', '.join(JUDGE_RUBRICS)})"
        )
    report = JudgeReport(
        judge=getattr(judge, "judge_name", getattr(judge, "__name__", "judge"))
    )
    for dimension in dimensions:
        request = JudgeRequest(dimension, content)
        max_score = request.rubric["max"]
        rubric_score, _ = parse_verdict(rubric_judge(request), max_score=max_score)
        verdict = DimensionVerdict(None, max_score, rubric_score)
        for _ in range(samples):
            try:
                value, why = parse_verdict(judge(request), max_score=max_score)
            except Exception as error:  # a bad sample is data, not a crash
                verdict.errors.append(f"{type(error).__name__}: {error}")
                continue
            verdict.samples.append(value)
            verdict.reasoning.append(why)
        if verdict.samples:
            verdict.score = statistics.median(verdict.samples)
        report.scores[dimension] = verdict
    return report


# -- golden tasks ------------------------------------------------------------------------


@dataclass(frozen=True)
class GoldenTask:
    """A repo-specific task, passed when the output matches every ``expect`` regex and no ``forbid``."""

    name: str
    prompt: str
    expect: Sequence[str] = ()
    forbid: Sequence[str] = ()

    def __post_init__(self):
        for field_name in ("expect", "forbid"):
            patterns = getattr(self, field_name)
            if isinstance(patterns, str) or not all(
                isinstance(p, str) for p in patterns
            ):
                raise ValueError(
                    f"task {self.name!r}: `{field_name}` must be a list of regexes"
                )
            for p in patterns:
                try:
                    re.compile(p)
                except (
                    re.error
                ) as error:  # a bad pattern must not look like an agent failure
                    raise ValueError(
                        f"task {self.name!r}: bad regex {p!r}: {error}"
                    ) from error

    def passed(self, output: str) -> bool:
        return all(re.search(p, output, flags=re.M) for p in self.expect) and not any(
            re.search(p, output, flags=re.M) for p in self.forbid
        )


#: An agent does a task under a config (CLAUDE.md text; ``""`` = no config) and returns its output.
Agent = Callable[[GoldenTask, str], str]


def echo_agent(task: GoldenTask, config: str) -> str:
    """The free agent: "does" the task by quoting its config, so a config that states the
    convention passes and an empty one does not. It tests the harness, not a model."""
    return f"{config}\n{task.prompt}"


def anthropic_agent(
    *, model: str = DFLT_JUDGE_MODEL, client=None, max_tokens: int = DFLT_MAX_TOKENS
) -> Agent:
    """A paid single-call agent: the config is the system prompt, the task the user turn."""
    client = _client(client)

    def agent(task: GoldenTask, config: str) -> str:
        messages = [{"role": "user", "content": task.prompt}]
        return _text_of(
            _create(
                client,
                model=model,
                max_tokens=max_tokens,
                messages=messages,
                system=config or None,
            )
        )

    return agent


def load_golden_tasks(path: str | Path) -> list[GoldenTask]:
    """Tasks from a JSON list of ``{"name", "prompt", "expect": [...], "forbid": [...]}``."""
    name = Path(path).name
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{name}: expected a JSON list of tasks")
    tasks = []
    for i, d in enumerate(data):
        if not (
            isinstance(d, dict)
            and isinstance(d.get("name"), str)
            and isinstance(d.get("prompt"), str)
        ):
            raise ValueError(f"{name}, task {i}: needs a string `name` and `prompt`")
        for key in ("expect", "forbid"):
            if not isinstance(d.get(key, []), list):
                raise ValueError(f"{name}, task {i}: `{key}` must be a list of regexes")
        tasks.append(
            GoldenTask(
                d["name"],
                d["prompt"],
                tuple(d.get("expect", ())),
                tuple(d.get("forbid", ())),
            )
        )
    return tasks


@dataclass
class GoldenReport:
    """Per task and arm (``with`` / ``without`` the config): runs passed and runs that errored.

    A run whose agent raised is left out of its arm's pass rate (it says nothing about the
    config), so a flaky agent cannot skew :meth:`delta`; the errors are listed.
    """

    runs: int
    results: dict[str, dict[str, int]] = field(default_factory=dict)
    errors: dict[str, list[str]] = field(default_factory=dict)

    def rate(self, arm: str) -> float:
        """Passed / completed (non-errored) runs in ``arm``; 0.0 when none completed."""
        done = sum(self.runs - r[f"{arm}_errors"] for r in self.results.values())
        return sum(r[arm] for r in self.results.values()) / done if done else 0.0

    def delta(self) -> float:
        """Pass rate with the config minus without: positive means the config helps."""
        return self.rate("with") - self.rate("without")

    def to_dict(self) -> dict:
        return {
            "runs": self.runs,
            "results": self.results,
            "errors": self.errors,
            "with": self.rate("with"),
            "without": self.rate("without"),
            "delta": self.delta(),
        }

    def __str__(self) -> str:
        lines = [
            f"Golden tasks: {len(self.results)} x {self.runs} run(s); "
            f"pass rate {self.rate('with'):.0%} with the config, {self.rate('without'):.0%} without "
            f"(delta {self.delta():+.0%})"
        ]
        for name, r in self.results.items():
            arms = [
                f"{r[a]}/{self.runs - r[a + '_errors']} {a}"
                for a in ("with", "without")
            ]
            lines.append(f"  {name}: {', '.join(arms)}")
        lines += [
            f"  error in {name}: {e}"
            for name, errs in self.errors.items()
            for e in errs
        ]
        return "\n".join(lines)


def run_golden_tasks(
    tasks: Iterable[GoldenTask],
    *,
    agent: Agent,
    config: str,
    baseline: str = "",
    runs: int = 1,
) -> GoldenReport:
    """Run every task ``runs`` times under ``config`` and under ``baseline``; count passes.

    An agent error is recorded, never raised, and leaves that run out of the pass rate.

    :raises ValueError: two tasks share a name, or ``runs < 1``.
    """
    tasks = list(tasks)
    if runs < 1:
        raise ValueError("runs must be at least 1")
    names = [t.name for t in tasks]
    if dupes := sorted({n for n in names if names.count(n) > 1}):
        raise ValueError(f"task names must be unique, repeated: {dupes}")
    report = GoldenReport(runs=runs)
    for task in tasks:
        counts = {"with": 0, "without": 0, "with_errors": 0, "without_errors": 0}
        report.results[task.name] = counts
        for arm, text in (("with", config), ("without", baseline)):
            for _ in range(runs):
                try:
                    counts[arm] += task.passed(agent(task, text))
                except Exception as error:
                    counts[f"{arm}_errors"] += 1
                    report.errors.setdefault(task.name, []).append(
                        f"{arm}: {type(error).__name__}: {error}"
                    )
    return report
