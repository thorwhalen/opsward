"""Eval harness (opsward#51): judge + golden tasks, exercised with fakes only (no paid calls)."""

import json
from types import SimpleNamespace

import pytest

from opsward.evals import (
    GoldenTask,
    JudgeRequest,
    anthropic_agent,
    anthropic_judge,
    echo_agent,
    judge_claude_md,
    load_golden_tasks,
    parse_verdict,
    rubric_judge,
    run_golden_tasks,
)

CLAUDE_MD = "# Proj\n\n## Commands\n\n```bash\npytest\n```\n\n- Run `ruff check opsward/` before committing.\n"


class FakeClient:
    """Stands in for ``anthropic.Anthropic()``: records requests, returns canned text."""

    def __init__(self, *replies, stop_reason="end_turn"):
        self.replies, self.calls, self.stop_reason = list(replies), [], stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        text = self.replies.pop(0) if self.replies else ""
        return SimpleNamespace(stop_reason=self.stop_reason,
                               content=[SimpleNamespace(type="text", text=text)])


def test_the_rubric_judge_reproduces_the_rubric_score():
    report = judge_claude_md(CLAUDE_MD)
    for v in report.scores.values():
        assert v.score == v.rubric_score and v.errors == []


def test_samples_give_a_median_and_a_spread():
    replies = iter(['{"reasoning": "a", "score": 9}', '{"reasoning": "b", "score": 13}',
                    '{"reasoning": "c", "score": 10}'])
    report = judge_claude_md(CLAUDE_MD, judge=lambda req: next(replies),
                             dimensions=["actionability"], samples=3)
    v = report.scores["actionability"]
    assert v.score == 10 and v.spread == 4 and v.reasoning == ["a", "b", "c"]


def test_an_unparseable_reply_is_an_error_not_a_crash():
    report = judge_claude_md(CLAUDE_MD, judge=lambda req: "I think it's fine",
                             dimensions=["conciseness"])
    v = report.scores["conciseness"]
    assert v.score is None and "no JSON object" in v.errors[0]
    assert "n/a" in str(report)


@pytest.mark.parametrize("reply", ['{"score": 16}', '{"score": "9"}', '{"score": true}', '{"score": -1}'])
def test_out_of_range_or_non_integer_scores_are_rejected(reply):
    with pytest.raises(ValueError):
        parse_verdict(reply, max_score=15)


def test_the_judge_prompt_carries_the_rubric_and_the_bias_controls():
    prompt = JudgeRequest("actionability", CLAUDE_MD).prompt
    assert "Length is not quality" in prompt and "13-15" in prompt and CLAUDE_MD in prompt


def test_anthropic_judge_sends_the_prompt_and_parses_the_reply():
    client = FakeClient('{"reasoning": "concrete", "score": 12}')
    report = judge_claude_md(CLAUDE_MD, judge=anthropic_judge(client=client, model="m"),
                             dimensions=["actionability"])
    assert report.judge == "m" and report.scores["actionability"].score == 12
    (call,) = client.calls
    assert call["model"] == "m" and "claude_md" in call["messages"][0]["content"]


def test_a_refusal_is_recorded_as_an_error():
    client = FakeClient("", stop_reason="refusal")
    report = judge_claude_md(CLAUDE_MD, judge=anthropic_judge(client=client), dimensions=["conciseness"])
    assert "refusal" in report.scores["conciseness"].errors[0]


def test_golden_tasks_measure_what_the_config_changes():
    tasks = [
        GoldenTask("keyword-only", "Write f(a, b, c).", expect=[r"\*,"]),
        GoldenTask("no-print", "Log it.", forbid=[r"\bprint\("]),
    ]
    report = run_golden_tasks(tasks, agent=echo_agent, config="Put `*,` before the third arg.", runs=2)
    assert report.results["keyword-only"] == {"with": 2, "without": 0}
    assert report.results["no-print"] == {"with": 2, "without": 2}
    assert report.delta() == pytest.approx(0.5)
    assert json.loads(json.dumps(report.to_dict()))["delta"] == pytest.approx(0.5)


def test_an_agent_error_is_a_failed_run_and_is_recorded():
    def flaky(task, config):
        if config:
            raise RuntimeError("boom")
        return "ok"

    report = run_golden_tasks([GoldenTask("t", "p", expect=["ok"])], agent=flaky, config="c")
    assert report.results["t"] == {"with": 0, "without": 1}
    assert "with: RuntimeError: boom" in report.errors["t"][0]


def test_anthropic_agent_puts_the_config_in_the_system_prompt():
    client = FakeClient("def f(a, b, *, c): ...", "def f(a, b, c): ...")
    agent = anthropic_agent(client=client)
    report = run_golden_tasks([GoldenTask("kw", "Write f.", expect=[r"\*,"])], agent=agent, config="Use *,")
    assert report.results["kw"] == {"with": 1, "without": 0}
    assert client.calls[0]["system"] == "Use *," and "system" not in client.calls[1]


def test_golden_tasks_load_from_json(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps([{"name": "a", "prompt": "p", "expect": ["x"]}]))
    assert load_golden_tasks(path) == [GoldenTask("a", "p", ("x",), ())]
    path.write_text("{}")
    with pytest.raises(ValueError, match="JSON list"):
        load_golden_tasks(path)


def test_rubric_judge_reply_is_valid_json():
    reply = json.loads(rubric_judge(JudgeRequest("conciseness", CLAUDE_MD)))
    assert 0 <= reply["score"] <= 15
