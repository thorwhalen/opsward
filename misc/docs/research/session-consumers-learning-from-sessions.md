# Learning from persisted agent sessions: community practice since 2026-09 — research
*Research reference, 2026-11-08. Web sources retrieved 2026-11-08. Scope: the delta since the in-house surveys of 2026-09-07 and 2026-10-03, plus mechanisms they did not cover (analysis ledger, consumer registry, multi-machine aggregation). Serves the design of a fleet component that registers consumers of persisted and live Claude Code sessions, records which session was analysed by which analyser version, aggregates several machines, and runs the first consumers (repeated-ad-hoc-tooling detector, operator mentor, agent-setup improver). Numbers marked **estimate** are the author's; claims not confirmed at a primary source are marked **unverified**. `$PP` is the projects folder.*

## Summary and recommendation

1. **Most of the ledger already exists in-house.** `$PP/t/astern/astern/ledger.py` keys session × lens × lens version × last turn seen and plans `skip` / `incremental` / `full`. The work is to generalise it from "lens" to "consumer", not to write a new one. Its two gaps against standard practice: findings are stored at `<lens>/<sid>` and overwritten in place, and the version is a hand-bumped integer with no model or prompt fingerprint for LLM consumers.
2. **Adopt the Dagster vocabulary and the Kappa reprocessing move.** A consumer has a *code version* (declared by hand) and each output carries a *data version* (hash of code version + input fingerprint); a mismatch makes the output *stale* [1]. On a version bump, write the new version's outputs **beside** the old ones, backfill, switch readers, then delete the old [2]. Key: `(session_id, source_fingerprint, consumer, consumer_version[, model, prompt_hash])`.
3. **One consumer registry, two drivers.** Consumers are plain callables registered through Python entry points [3] (astern's `@lens` decorator generalised), each declaring `name`, `version`, `kind` (batch, live or both). A batch driver walks sessions through the ledger; a live driver drains a Maildir-style spool that one thin async hook appends to [4][5]. Batch is the reconciler, live is only a latency optimisation, because hooks can miss events and `SessionEnd` has a 1.5 s budget [5]. pluggy [6] is not needed for independent fan-out.
4. **Aggregate machines by analysing remotely and pulling derived rows, plus a one-way raw archive.** Do not use bidirectional sync: Syncthing propagates deletions [7], so a server's retention sweep would delete Mac copies. Normalise `cwd` to the `$PP/...` form, not the project-dir slug, which is lossy and truncated past 200 characters [8].
5. **Urgent and not asked: the servers' oldest transcripts are 29 days old** (2026-10-10 against today), which matches the default `cleanupPeriodDays` of 30 [9]. **Estimate**: the servers are deleting transcripts now. Raise `cleanupPeriodDays` there before building anything (`$PP/_agent_work/opsward/2026-11-08-session-consumers/sources.md`).
6. **The research now backs the first consumer.** Agents stop reusing existing code as turns accumulate: 50.8% of task chains contain duplicated logic by turn 5 while pass rates stay flat [10]. No shipped tool detects cross-session rewrites; build it on astern's `rewrites` lens with a Type-1/2 → Type-3 → Type-4 clone cascade.
7. **Keep a human gate and transcripts as ground truth.** Anthropic's own write-up of transcript-to-memory "dreaming" (2026-11-06) shows notes going wrong and staying wrong unless corrected against transcripts [11]. 2026 benchmarks still find self-generated skills and memory fragile [12][13].

## What already exists (in-house)

- `$PP/g/g_ai/docs/session-mining-research.md` (2026-09-07): built-ins, about 20 community miners, the research line Reflexion → ACE → Trace2Skill, and the JSONL format. Not repeated here.
- `$PP/g/g_ai/docs/session-mining-plan.md`: the lens catalogue (A–V), sources → records → lenses → aggregates → sinks, and "cached per session × lens × version".
- `$PP/tt/my_skills/references/self-improving-agent-setup-research.md` §3: OTel events, hooks as the local source, `skill_activated`, metrics such as search-before-write, privacy rules.
- `$PP/t/astern/astern/ledger.py`, `store.py`, `sources.py`, `lenses/__init__.py`, `lenses/commands.py`: ledger, `dol`-backed store under `~/.local/share/astern/`, multi-home sources, the `@lens(name, version, kind, incremental)` registry, and the `rewrites` lens (heredocs, scratchpad `Write`s, long Bash; normalised fingerprint for grouping).
- `$PP/t/openloops/openloops/transcripts.py` (canonical reader) and `egress.py` (scrub-or-raise before data leaves the machine).
- `$PP/tt/my_skills/hooks/fix_at_source.py` and `fe_recall.py`: the existing live consumers (hooks).
- `$PP/t/opsward/misc/docs/research/skill_tiering_and_reachability.md` (skill reach measured from transcripts) and `lifecycle_agentops.md`; opsward issues [thorwhalen/opsward#80](https://github.com/thorwhalen/opsward/issues/80), [#79](https://github.com/thorwhalen/opsward/issues/79), [#52](https://github.com/thorwhalen/opsward/issues/52), [#17](https://github.com/thorwhalen/opsward/issues/17).
- Corpus inventory: `$PP/_agent_work/opsward/2026-11-08-session-consumers/sources.md` (2,151 top-level and 19,003 subagent transcripts, about 21.7 GB, four homes, no transcript sync between machines).

## 1. Claude Code's own transcript-derived features: what changed since 2026-09

Changelog window read: 2.1.251 (2026-08-28) to 2.1.319 (2026-11-06), from the docs mirror [14]. The GitHub `CHANGELOG.md` was not read byte for byte.

| Feature | State on 2026-11-08 (delta in bold) | Relevance to the component | Verdict |
|---|---|---|---|
| Transcript format | Still no schema: the format "is internal to Claude Code and changes between versions" [15]. **Since 2.1.300 (2026-10-14) local transcripts also record each API request's system prompt, tools and parameters** [14][9]. **Set-aside copies `<sid>.orphaned-<ts>-<suffix>.jsonl` and `<sid>.jsonl.superseded-<ts>`** exist [9]. `CLAUDE_CODE_TRANSCRIPT_LOCAL_GC` rewrites `-p`/SDK transcripts to cap growth [14]. | Line types such as `api-request`, `tools-used`, `pr-link` remain undocumented (**unverified** beyond local observation). Fingerprints must tolerate files that shrink or are rewritten; dedupe on `sessionId`, not file path. | Keep tolerant parsing; record `version` per row |
| SDK session API | **`list_sessions`, `get_session_messages`, `get_session_info`, `rename_session`, `tag_session`** (Python and TS) and a **`SessionStore` adapter that mirrors transcripts to your own backend** [8]. Slug rule now documented: every non-alphanumeric → `-`, truncated with a hash past 200 characters; **`CLAUDE_CODE_PROJECT_DIR_NAME`** names the project dir yourself [8]. | An official reader to wrap behind the source seam; a sanctioned way to mirror transcripts; a lever for cross-machine project identity. | **Wrap** (as one source implementation) |
| `/insights` | Up to 200 unseen sessions per run, excludes other devices and claude.ai; report at `~/.claude/usage-data/report.html` with timestamped copies [16]. **2.1.281 (2026-09-23) adds an estimate of prompts auto mode could have handled** [14]. Facet cache is described only as "cached per-session analysis data" [9]; per a third-party teardown it is keyed by session ID [17]. No scheduled mode. | A session-keyed cache with no analyser version means a prompt change does not re-analyse old sessions (**inference** from [17]): the exact gap the ledger fills. `usage-data/` is swept at `cleanupPeriodDays` [9]. | **Consume** facets when present; do not depend on their schema |
| Auto memory | Unchanged layout and four types; `autoMemoryEnabled`, `autoMemoryDirectory`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY` [18]. **Subagents get their own `agent-memory/<name>/`** [9]. 2.1.284 neutralises markup-like tags in recalled notes [14]. Memory is excluded from the sweep [9]. | A sink for "setup improver" output, and a source for the stranded-rule audit (opsward#79). | **Consume and write to** |
| "Dream" consolidation | `autoDreamEnabled` appears in the settings schema with no docs; the issue was closed as stale [19]; `/dream` answered "Unknown skill" [20]. Anthropic's engineering post describes dreaming for Managed Agents [11]. | Do not assume Claude Code consolidates memory for you. | **Unverified**; study the post |
| Retention | Default 30, **minimum 1, `0` fails validation**; sweep covers transcripts, `subagents/`, `tool-results/`, `file-history/`, `usage-data/`; keeps `history.jsonl`, `stats-cache.json`, memory [9]. **`claude purge`** (renamed before 2.1.288); **`retention_sweep` OTel event** with `transcripts_deleted`; 2.1.310 fixed very large values deleting recent files [9][21][14]. | The component must archive before the sweep; `retention_sweep` is a cheap alarm. | **Act** (raise on every machine, monitor) |
| Hooks | 33 events; none new in the window (**unverified** dates for older ones) [5]. Common input adds **`scratchpad_dir`** (2.1.257) and `prompt_id`; `transcript_path` "may lag the in-memory conversation", so use `last_assistant_message` on `Stop`/`SubagentStop` [5]. `SessionEnd` reasons `clear`, `resume`, `logout`, `prompt_input_exit`, `other`, **1.5 s shared budget** (raisable to 60 s) [5]. `SubagentStop` carries `agent_transcript_path`; `InstructionsLoaded` carries `load_reason` and, **since 2.1.288, `agent_id`** [5][14]. Handlers: `command`, `http`, `mcp_tool`, `prompt`, `agent`; `async: true` on command hooks only; **HTTP `onFailure` (2.1.295)** [5][14]. | The live source. Hooks must enqueue, never analyse inline. `scratchpad_dir` is a free signal for the ad-hoc-code detector. | **Use** as event bus via a spool |
| Telemetry | `skill_activated` with `invocation_trigger` and `skill.source` [21]. **New: `hook_execution_complete` (2.1.280), tool output in spans under `OTEL_LOG_TOOL_CONTENT=1` (2.1.283), `classifier_verdict` on `tool_decision` (2.1.301)** [14]. No local file exporter (only `otlp`, `prometheus`, `console`) [21]. | Metadata stream complementary to transcripts; needs a local collector. | **Optional** second source |
| Skill evaluation | **`claude plugin eval` (2.1.269, 2026-09-11)**: case directories, `graders/*.md`, `results/<ts>/aggregate-result.json` with `schemaVersion: 1` [14][22]. **`/skill-doctor` (2.1.261)**: listing cost and invocation count per skill, never-invoked skills [23][14]. `/usage` attributes usage to skills, subagents, plugins and MCP servers "computed from local session history" [16]. | The setup improver's "measure" step exists now: propose a change, prove it with `plugin eval`. `/skill-doctor` overlaps opsward's reachability work. | **Depend** for evals; **compare** with opsward |
| Other consumers | `/recap` runs after 3 minutes unfocused, 400-character cap [24]; session picker searches across projects [15]. Remote Control stores the transcript on Anthropic servers while connected [25]. | `/recap` text (`away_summary` lines) is free synopsis material. | **Consume** |

## 2. Community tools and research since 2026-09

### 2a. Transcript miners and trace-to-memory tools

| Tool | What it does | Maturity, licence | Verdict |
|---|---|---|---|
| Anthropic "components of agent memory" (2026-11-06) [11] | Four layers: transcripts, notes, representations (wikis), injected context. Dreaming replays logs offline to fix notes, build wikis and choose what to preload. Measured: Opus 5 0.564 → 0.828 on a CL-Bench task with memory; wiki accuracy 13% → 48% over 128 sessions; wiki + search 61% vs search 53%. Failure modes: wrong notes persist, over-recording, a wiki reaching 1.77× its sources, concurrent overwrites, "record only failures" cutting the gain by 0.234. | First-party write-up, not a library | **Study**: reference design for the setup improver |
| d06-p01-self-improve [26] | Nightly miner over Claude and Codex JSONL: corrections, tool errors, repeated loops; a lesson is "ripe" at its second occurrence; writes a managed block in CLAUDE.md/AGENTS.md with undo. | MIT, 0 stars | **Study** (recurrence threshold, managed block) |
| claude-introspection [27] | jq detectors: piped head/tail, tiny agent dispatch, long Bash, repeat reads, sequential edits; never-invoked skills; stale CLAUDE.md. | MIT, 2 stars | **Study**: ready detector list |
| claudephant [28] | Tags turns `user_correction` / `error` / `self_correction`; mines API misuse per library; repeated workflows → skills. | 0 stars, licence not shown | **Study** |
| claude-code-history-viewer [29] | Offline browser and analytics over 31 agents' histories. | MIT, about 2.3k stars | **Study** parsers (cross-agent formats) |
| Entire CLI [30] | Hooks store prompts and transcripts on a hidden git ref linked to commits; `entire import` ingests past transcripts. | MIT, funded startup | **Study**; **avoid** on public repos (transcripts in git) |
| Agent Trace [31] | Spec for line-level human/AI attribution in version control. | RFC v0.1, CC BY 4.0 | **Study** as provenance format |
| Arize harness tracing [32] | Live tracing of Claude Code, Codex, Cursor and others into Phoenix. | Licence not stated | **Avoid** (live tracing stack, not JSONL mining) |
| Letta context repositories [33] | Git-versioned memory tree with a sleep-time reflection subagent. | Product feature | **Study** (git-versioned, auditable memory) |
| Mem0 2.0.0 [34] | Moved to single-pass ADD-only extraction. | Apache-2.0 (**unverified** for 2.0) | **Avoid**: accumulates what consolidation should prune |

### 2b. Repeated ad-hoc code across sessions

Standard clone taxonomy: Type-1 identical modulo layout and comments; Type-2 also renamed identifiers and literals; Type-3 near-miss with statements added or removed; Type-4 semantically equivalent with different syntax [35].

| Approach | Clone types | Notes | Verdict |
|---|---|---|---|
| `ast` normalise + hash per function (astern `rewrites` fingerprint today) | 1–2 | Zero dependencies; fits heredocs, `python -c`, scratchpad `Write` bodies. | **Build** (extend in-house) |
| MinHash/LSH over normalised token shingles, datasketch [36] | 1–3 | Corpus-scale near-duplicate grouping. | **Depend** |
| jscpd 5 (Rust rewrite, MCP server, `--similarity`) [37][38] | 1–2, partial 3 | Repo-level, JSON/SARIF output aimed at agents. | **Wrap** for repo-side checks |
| treepeat (tree-sitter + LSH) [39], NiCad / SourcererCC [35] | 1–3 | NiCad and SourcererCC are the research baselines with high Type-3 recall. | **Study** |
| Code embeddings + kNN [40] | 4 (candidates) | 2026 rankings are mostly vendor claims. | **Depend** via the fleet's embedding layer |
| Pre-write duplicate guards (ASTrograph MCP) [41] | 1–3 | Blocks a write when it is isomorphic to an existing function. | **Study** for a later `PreToolUse` sensor |

Research. RepoReuse (arXiv 2609.35357, 2026-09-28): agents explore relevant repository code less and reuse their own earlier work less as turns accumulate; 50.8% of chains duplicate logic by turn 5; pass rates barely move [10]. Super Library Agent (2608.29310): candidate-guided extraction over chunk summaries, consolidation, then call-graph-aware migration to a shared library across N related apps; no numbers in the abstract [42]. "More Code, Less Reuse" (MSR 2026): agent PRs carry more redundancy, typically Type-4, unnoticed by reviewers [43]. CodeTaste: agents miss refactorings humans would pick unless told [44]. GitClear's 2026 duplication figures circulate only through secondary sources (**unverified**) [45].

**Estimate**: a cascade of `ast` hash → MinHash LSH → embedding kNN → LLM judge proposing the library function and its home package is the cheapest stack that reaches Type-4, and only the last step costs tokens.

### 2c. Traces → skills and memory, 2026

- **Skill induction**: HSE (2610.35616) evolves skills per task, aggregates per repo, consolidates across repos, with a writer–evaluator loop; 10 skills from SWE-Gym help in every tested setting including a Claude Code harness [46]. This per-repo then fleet-wide shape matches the fleet. CodeSkill (2605.25430) learns extraction and bank maintenance with RL [47].
- **Lifecycle survey** (2607.10113, TMLR 2026): eight stages from evidence acquisition through admission, storage, retrieval, maintenance and governance; admission and repair matter, flat retrieval degrades as libraries grow [48].
- **Transfer**: Memory Transfer Learning (2604.14004): gains come from meta-knowledge such as validation routines; low-level traces transfer negatively [49]. Store abstractions, not traces.
- **Negative or mixed results**: SkillsBench: curated skills 33.9% → 50.5%; the v1 figure of −1.3 pp for self-generated skills is absent from the current abstract (**unverified** now) [12]. Fragility of Self-Improving Agents (2608.18066): gains swing across runs and depend on task order [13]. EvoMemBench (2605.18421): long-context baselines stay competitive with 15 memory methods [50].

### 2d. Mentoring the human operator

- Anthropic's expertise study (2026-06-16, about 400k Claude Code sessions): verified success about 15% for novices against 28–33% above; experts frame precisely, ask for verification and are corrected less [51]. Its features (framing precision, verification requests, correction dynamics, nine work modes) are a ready rubric for the mentor.
- AI Fluency Index (2026-02-23): 11 of the 24 behaviours of the 4D framework (Delegation, Description, Discernment, Diligence) are observable in chat text [52]. The framework text is CC BY-NC-SA, so cite rather than embed.
- Prompt Coach (2607.06074): scores prompts on 8 dimensions and coaches Socratically; gains after one session with 15 developers, but on live prompts, not transcripts [53].
- No tool found that scores an operator's prompting and delegation from their own coding-agent transcripts; `/insights` "interaction style" is the nearest.

## 3. The analysis ledger: item × analyser version

**Standard terms.** *Materialisation* (an output computed and stored), *code version* and *data version*, *stale* / *unsynced* [1]; *partition* (one session) and *backfill* (re-running partitions); *incremental model* with `unique_key` and *full refresh* [54]; *idempotency*; *reprocessing* [2]; *projection* or *read model* rebuilt by *event replay* [55]; *memoisation* with *cache key* and *invalidation* [56][57]; *consumer offset* [58].

| Pattern | Mechanism | Fit for one user, files + SQLite | Verdict |
|---|---|---|---|
| Dagster code/data version [1] | `code_version` string set by hand; data version = hash(code version, input data versions); mismatch → "Unsynced", not transitive | Exactly the needed staleness rule; carry it without Dagster | **Adopt the model** |
| Kappa reprocessing [2] | New job version reads from the start of the retained log into a new output table; switch; drop old | Version in the output key makes backfills safe and comparable (old vs new findings side by side) | **Adopt** |
| dbt incremental [54] | `is_incremental()` filters new rows; `unique_key` upserts; `--full-refresh` rebuilds | Matches astern's `incremental` / `full`; SQLite `INSERT … ON CONFLICT DO UPDATE` is the upsert [59] | **Adopt** |
| Code hashing (luisy, gokart, joblib) [60][61][56] | Hash task source (luisy) or bump a `__version` parameter (gokart); joblib invalidates on code change | Auto-hash is noisy (any refactor re-runs a paid LLM pass); hand version + hash of prompt and model id for LLM consumers is the compromise | **Partial** |
| Bazel action key [57] | Digest of command, input hashes, environment, toolchain | Reminder that model id and prompt are inputs | **Study** |
| Feature-store versions [62] | Breaking change → new feature-group version, backfill, old readers keep the old version | Same as Kappa, named per output schema | **Adopt naming** |
| Event-sourcing projection [55] | Read model is disposable and rebuilt by replaying the log | Transcripts are the log; every finding is a projection | **Adopt framing** |
| Consumer offsets [58] | Per-group committed offset; at-least-once; new group starts from earliest | `through_index` / `through_uuid` per consumer per session is the offset | **Already in astern** |

Recommended for a single-user store under `~/.local/share/<package>/`:

1. **Ledger row** `(session_id, consumer, consumer_version, through_uuid, source_fingerprint, data_version, status, ran_at)`, with `data_version = hash(consumer_version, model_id, prompt_hash, source_fingerprint)`. Plan rules as in astern: missing or other version → `full`; same version, more turns → `incremental` if the consumer allows it; else `skip`.
2. **Outputs keyed with the version**: `findings/<consumer>/<version>/<sid>`. A bump backfills into a new prefix; readers point at a chosen version; old prefixes are deleted after comparison. This is the change astern needs.
3. **SQLite in WAL mode for the ledger, JSON files for outputs.** WAL lets readers and the single writer run together, but "does not work over a network filesystem" [63]; copying a live database without its `-wal` file corrupts it [64]. So the store stays out of Dropbox-synced `$PP` and is backed up with `VACUUM INTO` or the backup API [64].

## 4. A registry of consumers over a batch source and a live source

| Shape | Discovery | Delivery | Fit | Verdict |
|---|---|---|---|---|
| Python entry points [3] | Installed packages advertise consumers; host loads them | Host calls each | Lets opsward, openloops or a private package register consumers without the host importing them | **Use for discovery** |
| pluggy [6] | Hookspecs and hookimpls, entry-point loading, `firstresult`, wrappers, historic calls | Ordered, validated calls | Worth it when consumers return values into one pipeline or wrap each other; independent fan-out does not need it | **Defer** |
| Django signals [65] | Receivers connect to senders | Synchronous, implicit | Django's own docs warn signals make code "hard to understand, adjust and debug"; `dispatch_uid` against double registration | **Avoid** |
| Unix drop-in directory, `run-parts` [66] | Executables in a directory, lexical order | Sequential processes | Good for shell-level consumers; weak typing and no versions | **Allow as an adapter** |
| Maildir spool [4] | n/a | Write to `tmp/`, atomic rename into `new/`, reader moves to `cur/`; no locks | The right live-source buffer: a hook writes one file and exits | **Use for the live path** |
| OTel collector fan-out [67] | Pipelines of receivers → processors → exporters, several exporters per pipeline | Push | Only if OTel becomes a source | **Optional** |

How the built-ins are shaped: `/insights` is a batch consumer with a per-session cache and an aggregate stage [17]; `/fewer-permission-prompts` is a stateless skill prompt that rescans the 50 most recent transcripts on every run [68]. Neither has a version-aware ledger.

**Recommendation**: a single registry of consumers discovered through entry points (the `@lens` decorator generalised to declare `kind` batch / live / both and a `version`), with one batch driver over the ledger and one live driver draining a Maildir spool fed by a single `async` command hook. Justification: one registration and one versioned ledger serve both sources, the hook stays within the 1.5 s `SessionEnd` budget [5], and the batch pass repairs whatever the live path missed, which is the Kappa principle of one code path over one log [2]. The existing live consumers (`fix_at_source.py`, `fe_recall.py`) need in-session latency and stay as their own hooks; they register only to have their event logs read by batch consumers.

## 5. Multi-machine aggregation

Facts:

- Claude Code has no built-in transcript sync; the cross-machine project-identity request is open [69]. The SDK's sanctioned route is a `SessionStore` adapter or moving the `.jsonl` [8].
- The project dir is the absolute `cwd` with every non-alphanumeric replaced by `-`, truncated with a hash past 200 characters; `CLAUDE_CODE_PROJECT_DIR_NAME` can override it [8]. Paths also live in each line's `cwd`, in message bodies and in `~/.claude.json` [70].
- Transcripts are plaintext and protected only by file permissions; anything a tool read, including a `.env`, is in them [9]. Remote Control keeps a server-side copy while connected [25].
- Syncthing is not a backup and propagates deletions; conflicts become `.sync-conflict-…` files [7][71]. restic encrypts with AES-256 and deduplicates with content-defined chunking, though storage access still reveals sizes and timing [72]. rsync's delta transfer suits append-mostly files [73].
- gitleaks scans directories and stdin for secrets (MIT) [74].

| Option | Privacy | Cost | Verdict |
|---|---|---|---|
| Pull raw transcripts to the Mac (rsync over ssh, one-way, hub and spoke) | Plaintext copies multiply | About 5 GB from the servers (fact from inventory); simple | **Use** as archive, `--ignore-existing`-style, into `~/.local/share/<package>/archive/<machine>/` |
| Analyse remotely, pull derived rows | Raw text stays put; only findings move, through `openloops.egress` scrubbing | Requires the package on each server (astern is absent there today) | **Use** as the main path |
| Syncthing or Dropbox of `~/.claude` | Deletions from a retention sweep propagate; SQLite corruption risk [64] | Low effort | **Avoid** |
| restic snapshots of each home | Encrypted at rest | Restore needed to analyse | **Use** for retention beyond `cleanupPeriodDays` |
| `SessionStore` mirror [8] | Depends on backend | SDK sessions only, not interactive CLI (**unverified**) | **Study** |

Path normalisation: derive identity from each line's `cwd`, never from the slug. Map each machine's projects root to `$PP` so that every session gets a `$PP/...` path, the same form the fleet uses in documents. Fall back to the git remote URL for paths outside `$PP`, as both the open request and community sync tools propose [69]. Store `(machine, home, session_id)` as the key, since one corpus's work is split across machines. **Estimate**: session-id collisions across machines are negligible (UUIDs).

## Terminology

trajectory / trace mining; experience replay; learning from interaction logs; skill induction and skill library; procedural, episodic and semantic memory; memory consolidation, sleep-time compute, "dreaming" [11]; context engineering, evolving playbook, context collapse; negative transfer [49]; code clone detection Type-1 to Type-4, missed reuse, library extraction [35][42]; AI fluency, work mode [52][51]; materialisation, code version, data version, staleness, backfill, full refresh, reprocessing, projection, consumer offset (section 3).

## Important and not asked

1. **Server retention is likely deleting data now** (Summary item 5; **estimate**). Check and raise `cleanupPeriodDays` on each server; alarm on the `retention_sweep` event [21].
2. **Transcripts grew more sensitive and larger after 2.1.300**, since they now include system prompts and tool definitions per request [14]. Strip those lines before any LLM consumer sees a session, and expect the corpus size to jump.
3. **A transcript is not append-only any more**: GC rewrites, set-aside `.orphaned` / `.superseded` copies [9][14]. Fingerprint by `(size, mtime, last uuid)` and dedupe on session id.
4. **Measuring a change now has a first-party tool** (`claude plugin eval` [22]); the setup improver should end every proposal with an eval, given the mixed results in 2c.
5. **Reuse is the paved road, not a sermon**: RepoReuse shows decay over turns [10], so the detector's output should become fleet components and pre-write sensors, not more CLAUDE.md text.

## Open questions

- Do the servers' `settings.json` files set `cleanupPeriodDays`? (One read on each settles item 1.)
- Does `/insights` re-run a session's facet when its prompt changes, or only by session ID? Testable by comparing facet files across versions.
- Is `SessionStore` usable for interactive CLI sessions, or SDK only?
- What do the undocumented line types `api-request` and `tools-used` contain since 2.1.300, and how large are they per session?
- Which existing package hosts the registry: astern (owns the ledger) with opsward, openloops and the mentor registering consumers through entry points, or a new package? The evidence here favours extending astern.
- Is `autoDreamEnabled` live in the installed version, and does it touch the same memory files the setup improver would write?

## REFERENCES

In-house (cited by path): `$PP/g/g_ai/docs/session-mining-research.md`; `$PP/g/g_ai/docs/session-mining-plan.md`; `$PP/tt/my_skills/references/self-improving-agent-setup-research.md`; `$PP/t/astern/astern/ledger.py`; `$PP/t/astern/astern/store.py`; `$PP/t/astern/astern/lenses/commands.py`; `$PP/t/openloops/openloops/egress.py`; `$PP/tt/my_skills/hooks/fix_at_source.py`; `$PP/t/opsward/misc/docs/research/skill_tiering_and_reachability.md`; `$PP/_agent_work/opsward/2026-11-08-session-consumers/sources.md`.

1. [Asset versioning and caching — Dagster docs](https://dagster.io/docs/guides/build/assets/asset-versioning-and-caching)
2. [Questioning the Lambda Architecture — J. Kreps, O'Reilly Radar](https://www.oreilly.com/radar/questioning-the-lambda-architecture/)
3. [Entry points specification — Python Packaging User Guide](https://packaging.python.org/en/latest/specifications/entry-points/)
4. [Maildir — Wikipedia](https://en.wikipedia.org/wiki/Maildir)
5. [Hooks reference — Claude Code docs](https://code.claude.com/docs/en/hooks)
6. [pluggy documentation](https://pluggy.readthedocs.io/en/stable/)
7. [FAQ — Syncthing docs](https://docs.syncthing.net/users/faq.html)
8. [Work with sessions — Claude Agent SDK docs](https://code.claude.com/docs/en/agent-sdk/sessions)
9. [Explore the .claude directory (application data, retention) — Claude Code docs](https://code.claude.com/docs/en/claude-directory)
10. [Do Coding Agents Reuse Existing Code or Reinvent the Wheel? — arXiv 2609.35357](https://arxiv.org/abs/2609.35357)
11. [The components of agent memory — Anthropic Engineering, 2026-11-06](https://www.anthropic.com/engineering/components-of-agent-memory)
12. [SkillsBench — arXiv 2602.12670](https://arxiv.org/abs/2602.12670)
13. [On the Fragility of Self-Improving Agents — arXiv 2608.18066](https://arxiv.org/abs/2608.18066)
14. [Changelog — Claude Code docs](https://code.claude.com/docs/en/changelog)
15. [Sessions — Claude Code docs](https://code.claude.com/docs/en/sessions)
16. [Costs: analyze your usage patterns (/insights, /usage) — Claude Code docs](https://code.claude.com/docs/en/costs#analyze-your-usage-patterns)
17. [Deep Dive: How Claude Code's /insights Command Works — zolkos.com](https://www.zolkos.com/2026/02/03/deep-dive-how-claude-codes-insights-command-works.html)
18. [How Claude remembers your project — Claude Code docs](https://code.claude.com/docs/en/memory)
19. [anthropics/claude-code#76186 — autoDreamEnabled undocumented](https://github.com/anthropics/claude-code/issues/76186)
20. [anthropics/claude-code#38426 — /dream unknown skill](https://github.com/anthropics/claude-code/issues/38426)
21. [Monitoring usage (OpenTelemetry) — Claude Code docs](https://code.claude.com/docs/en/monitoring-usage)
22. [Plugin evals — Claude Code docs](https://code.claude.com/docs/en/plugin-evals)
23. [Skills (/skill-doctor) — Claude Code docs](https://code.claude.com/docs/en/skills)
24. [Interactive mode: session recap — Claude Code docs](https://code.claude.com/docs/en/interactive-mode#session-recap)
25. [Data usage — Claude Code docs](https://code.claude.com/docs/en/data-usage)
26. [Feynman520/d06-p01-self-improve — GitHub](https://github.com/Feynman520/d06-p01-self-improve)
27. [ThisIsMissEm/claude-introspection — GitHub](https://github.com/ThisIsMissEm/claude-introspection)
28. [ianhi/claudephant — GitHub](https://github.com/ianhi/claudephant)
29. [jhlee0409/claude-code-history-viewer — GitHub](https://github.com/jhlee0409/claude-code-history-viewer)
30. [Entire CLI overview — Entire docs](https://docs.entire.io/cli/overview)
31. [cursor/agent-trace — GitHub](https://github.com/cursor/agent-trace)
32. [Arize-ai/arize-harness-tracing — GitHub](https://github.com/Arize-ai/arize-harness-tracing)
33. [Context repositories — Letta blog](https://www.letta.com/blog/context-repositories)
34. [mem0ai 2.0.0 — PyPI](https://pypi.org/project/mem0ai/2.0.0/)
35. [Code clone detection study (Type-1 to Type-4, NiCad, SourcererCC) — arXiv 2603.27308](https://arxiv.org/pdf/2603.27308)
36. [ekzhu/datasketch (MinHash, LSH) — GitHub](https://github.com/ekzhu/datasketch)
37. [jscpd 5.4.1 released — Open Collective](https://opencollective.com/jscpd/updates/jscpd-5-4-1-released)
38. [Fast duplicate code detection for agents (jscpd-rs) — V. Bogdanov](https://vv-bogdanov.github.io/posts/fast-duplicate-code-detection-for-agents/)
39. [dsummersl/treepeat — GitHub](https://github.com/dsummersl/treepeat)
40. [Best embedding models 2026 — OpenRouter blog](https://openrouter.ai/blog/insights/best-embedding-models-2026/)
41. [ASTrograph MCP server — Glama](https://images.glama.ai/mcp/servers/Thaylo/astrograph)
42. [Super Library Agent — arXiv 2608.29310](https://arxiv.org/abs/2608.29310)
43. [More Code, Less Reuse — arXiv 2601.21276](https://arxiv.org/abs/2601.21276)
44. [CodeTaste — arXiv 2603.04177](https://arxiv.org/abs/2603.04177)
45. [Write-Only Mode — GitClear](https://www.gitclear.com/write_only_mode_ai_research)
46. [Hierarchical Skill Evolution — arXiv 2610.35616](https://arxiv.org/abs/2610.35616)
47. [CodeSkill — arXiv 2605.25430](https://arxiv.org/abs/2605.25430)
48. [Dynamic agent skills lifecycle survey — arXiv 2607.10113](https://arxiv.org/abs/2607.10113)
49. [Memory Transfer Learning — arXiv 2604.14004](https://arxiv.org/abs/2604.14004)
50. [EvoMemBench — arXiv 2605.18421](https://arxiv.org/abs/2605.18421)
51. [Agentic coding and persistent returns to expertise — Anthropic Research](https://www.anthropic.com/research/claude-code-expertise)
52. [AI Fluency Index — Anthropic Research](https://anthropic.com/research/AI-fluency-index)
53. [Prompt Coach — arXiv 2607.06074](https://arxiv.org/abs/2607.06074)
54. [Incremental models — dbt docs](https://docs.getdbt.com/docs/build/incremental-models)
55. [Event Sourcing — M. Fowler](https://martinfowler.com/eaaDev/EventSourcing.html)
56. [joblib#1214 — Memory cache invalidation on code change](https://github.com/joblib/joblib/issues/1214)
57. [What makes a cache hit — Bazel book, VirtusLab](https://bazel.virtuslab.com/book/2~4~3/)
58. [Kafka consumer groups and offsets — Conduktor](https://www.conduktor.io/kafka/kafka-consumer-groups-and-consumer-offsets)
59. [UPSERT — SQLite docs](https://www.sqlite.org/lang_upsert.html)
60. [Automatic rerun detection — luisy docs](https://boschglobal.github.io/luisy/reruns.html)
61. [Task settings — gokart docs](https://gokart.readthedocs.io/en/stable/task_settings.html)
62. [Feature group versioning — Hopsworks docs](https://docs.hopsworks.ai/3.7/concepts/fs/feature_group/versioning/)
63. [Write-Ahead Logging — SQLite docs](https://www.sqlite.org/wal.html)
64. [How to corrupt an SQLite database file — SQLite docs](https://www.sqlite.org/howtocorrupt.html)
65. [Signals — Django docs](https://docs.djangoproject.com/en/5.2/topics/signals/)
66. [run-parts(8) — Debian manpages](https://manpages.debian.org/bookworm/debianutils/run-parts.8.en.html)
67. [Collector configuration — OpenTelemetry docs](https://opentelemetry.io/docs/collector/configuration/)
68. [Generate permission allowlist from transcripts (system prompt of /fewer-permission-prompts) — Piebald-AI](https://github.com/Piebald-AI/claude-code-system-prompts/blob/main/system-prompts/skill-generate-permission-allowlist-from-transcripts.md)
69. [anthropics/claude-code#25739 — Portable project memory across machines](https://github.com/anthropics/claude-code/issues/25739)
70. [Why you cannot copy a Claude Code session to another machine — DEV](https://dev.to/gowtham-sai-yadav/why-you-cannot-copy-a-claude-code-session-to-another-machine-2008)
71. [Understanding synchronization: conflicting changes — Syncthing docs](https://docs.syncthing.net/users/syncing.html)
72. [References (chunking, encryption, threat model) — restic docs](https://restic.readthedocs.io/en/stable/100_references.html)
73. [How rsync works](https://rsync.samba.org/how-rsync-works.html)
74. [gitleaks/gitleaks — GitHub](https://github.com/gitleaks/gitleaks)
