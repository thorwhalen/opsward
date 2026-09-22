# opsward.discover

Optional cross-repo asset discovery, delegating to the `toolery` package.

opsward scans and *scores* the AI setup of one repo; this adds *finding* assets — skills,
subagents, docs — across one or more repos. It is opt-in and keeps opsward’s core
dependency-light: `pip install 'opsward[discovery]'` pulls in `toolery` (add
`toolery[ir]` for semantic search). Conceptually this is opsward’s per-repo/fleet
orchestration meeting toolery’s discovery engine (epic #12 → #13).

### Functions

| [`find_assets`](#opsward.discover.find_assets)(\*roots, query[, kinds, ...])   | Find assets matching `query` across one or more project `roots`.   |
|----------------------------------------------------------------------------------------------|--------------------------------------------------------------------|

### opsward.discover.find_assets(\*roots, query, kinds='skill,agent', semantic=False, limit=10)

Find assets matching `query` across one or more project `roots`.

Harvests the requested `kinds` (comma-separated string or a sequence of
`"skill"`/`"agent"`/`"doc"`) from each root via `toolery` and returns ranked
`(Card, score)` results. With `semantic=True`, uses `toolery`’s ir federated
backend (needs `toolery[ir]`). Defaults to the current directory when no roots given.
