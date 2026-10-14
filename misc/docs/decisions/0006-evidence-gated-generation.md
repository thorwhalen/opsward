# 0006 — Generated content asserts only what the scan can back up

## Status

Accepted (2026-06-05, extended 2026-06-10)

## Context

Generated docs are read by agents as facts about the project. Dogfooding found the generator asserting things it had not checked: a `deployment.md` offered for every library with CI (a `.github/workflows/` directory was treated as a deployment signal), a `testing.md` claiming fixtures live in a `conftest.py` that did not exist, and a module map whose descriptions were blank.

## Decision

- Generate an artifact only when the scan finds evidence it is useful (minimal generation). CI is not deployment: `def _has_deploy_artifacts` needs a real deploy signal (e.g. a Dockerfile).
- A claim inside generated content is emitted only when the scan confirms it; when evidence is absent the claim is **omitted**, not softened or guessed. The conftest bullet appears only if a `conftest.py` exists.
- Where content cannot be derived, emit an explicit placeholder (`<!-- describe -->`) rather than a blank or an invented description. Module descriptions come from each module's real docstring.

## Consequences

- Generated docs are thinner for projects with little evidence, but nothing in them is false.
- Module docstrings become load-bearing: they feed the generated module map, which is one reason every module needs one.
- New template variables that make factual claims need a scan-backed `_detect_*` helper and a regression test for the absent case.

## Evidence

- `deployment.md` false positive on CI-only projects ([issue #2](https://github.com/thorwhalen/opsward/issues/2)): [PR #5](https://github.com/thorwhalen/opsward/pull/5)
- Docstring-derived module map and evidence-gated `testing.md` claims ([issue #10](https://github.com/thorwhalen/opsward/issues/10), "gate on scan evidence — omit when absent rather than soften to placeholder", confirmed with the maintainer): [PR #11](https://github.com/thorwhalen/opsward/pull/11)
