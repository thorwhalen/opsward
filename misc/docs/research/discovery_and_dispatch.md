# Intelligent Discovery and Dispatch over a Large Personal AI-Asset Ecosystem

**Abstract.** This report examines the state of the art for finding and routing to the right asset inside a heterogeneous personal corpus of ~400 small text artifacts (Claude skills, subagent specs, deep-research reports, MCP tool schemas, READMEs across ~200 packages). The dominant 2024–2026 lesson is convergent: do not flood an agent's context with hundreds of tool/skill schemas — expose *one* search affordance over a normalized, freshness-maintained catalog and disclose detail just-in-time [1][2][3]. We map the design space across lexical/semantic/agentic retrieval, progressive tool disclosure, hierarchical dispatch, and asset registries, then ground every recommendation in the user's existing packages (`ir`, `imbed`, `grub`, `skill`, `raglab`, `chromadol`, `aw`), arguing that the only genuinely missing piece is a thin **asset-catalog/ingestion layer** — not another retrieval engine.

## Scope

The target system answers two questions repeatedly: *"which of my ~400 assets is relevant to this intent?"* (discovery) and *"hand control to it"* (dispatch). The corpus is small by IR standards but heterogeneous in schema (YAML frontmatter, JSON tool schemas, freeform markdown, pyproject metadata) and constantly drifting. Latency budget is interactive; precision matters more than recall because a wrong dispatch is expensive (wasted agent turns) while a missed candidate is recoverable (the user re-queries). This is a precision-favoring, freshness-sensitive, schema-heterogeneous regime — which dictates much of what follows.

## 1. Search tools vs. search agents: lexical, semantic, agentic

Three retrieval regimes form a cost/capability ladder. **Lexical (BM25/TF-IDF)** scores against an inverted index of exact tokens; it has no notion of paraphrase but is unbeatable on exact identifiers, rare jargon, and symbol names — error codes, package names, function symbols have near-zero semantic signal and dense retrievers fail *silently* on them [4]. For an asset catalog full of names like `wads-ci-fix` or `chromadol`, this is decisive: lexical match is often the *correct* primary signal, not a fallback. **Dense/semantic** embedding search recovers meaning when the user paraphrases intent ("find me my thing that keeps embeddings fresh") and the asset never uses those words. The empirically robust default for mixed exact+paraphrase workloads is **hybrid**: run both and fuse by rank, not score [4]. Notably, on *small* corpora hybridization helps weaker embedding models but can *degrade* top-tier embedders — so hybrid is a safe default but should be measured, not assumed [4].

Rank fusion is the load-bearing primitive. **Reciprocal Rank Fusion (RRF)** [5] combines ranked lists using only positions (`1/(k+rank)`), making it scale-independent and immune to the incompatible-magnitude problem that plagues naive score-blending across a BM25 list and a cosine list. RRF "consistently yields better results than any individual system" and is the right cross-source combiner for a federated catalog where each asset-type may have its own retriever. The user's `ir` already implements exactly this (`fuse_hits(..., rrf_k=60)`, `FUSIONS = {"rrf","blend"}`) and `raglab` exposes `make_rrf_reranker` — so the fusion layer is *already built*.

**Agentic retrieval** adds an LLM control loop: query decomposition, query rewriting (HyDE), self-critique of sufficiency, and *re-retrieval with a reformulated query* (the Self-RAG pattern [6]). The capability gap is real but task-dependent: static one-shot RAG reaches ~34% on multi-hop reasoning where agentic loops reach ~89% [7], and iterative strategies dominate when the answer requires *combining disjoint facts* that no single top-k window captures [8]. For **single-asset discovery** ("which skill do I run?") this machinery is overkill — one hybrid query plus a confident selection cut suffices, and the added latency/tokens of a reformulation loop hurt. For **cross-asset Q&A** ("what have I built across all my packages for routing?") the multi-hop loop earns its cost. The architecture should therefore make agentic retrieval *opt-in*, layered above a cheap deterministic search, not the default path. `ir.discover()` (deterministic, JSON-serializable, abstention-calibrated) is the cheap path; `raglab`'s `SingleContextAgent` with its evaluator→reformulate back-edge is the expensive path — and they already compose, since `raglab` retrievers *are* `ir` retrievers.

A precision-favoring corpus also needs **calibrated abstention**: returning "nothing relevant" rather than the least-bad match. `ir` already bakes this in via mode-specific `min_score='auto'` floors learned from case files — exactly the right behavior for dispatch, where a false positive triggers a wrong handoff.

## 2. Progressive tool/context disclosure

The single most important pattern for this user's problem — and the one the harness running this very report uses — is **progressive disclosure of tool/context**: keep the agent's context lean by exposing capabilities as *searchable references* rather than pre-loaded schemas, materializing full detail only on demand [2][3].

Three concrete 2025–2026 mechanisms, all from Anthropic, instantiate this:

- **Tool Search Tool** [1][9]: tools are marked `defer_loading: true`; the agent sees only a search tool plus a few always-on tools, then discovers the rest via BM25/regex. Reported effect: ~85% reduction in tool-definition tokens (a 5-server setup's ~55k tokens of definitions collapses to loading the 3–5 tools actually needed), with measured *accuracy* gains (Opus 4.5: 79.5%→88.1%) because a smaller, relevant tool set reduces selection errors [1][9]. The lesson is counterintuitive but firm: **fewer visible tools improves both cost and accuracy.**
- **Agent Skills' three-stage disclosure** [3][10]: at startup only each skill's `name`+`description` (≤1024 chars) load into the system prompt; the full `SKILL.md` body loads only when the description matches the task; bundled reference files load only when the body points to them. This means "you can install many Skills without context penalty." This is *the* model for a 400-asset catalog: the catalog's job is to maintain the cheap first level (name+description+tags) so a router can match on it, and to make the full body retrievable on demand.
- **Code execution with MCP** [11]: rather than loading tool schemas, present servers as files on a filesystem the agent greps/reads; intermediate results stay out of context. Reported 150k→2k token reduction (98.7%). Generalized, this is "just-in-time context" [2]: maintain lightweight identifiers (paths, stored queries) and dereference them at runtime, exactly as Claude Code uses `glob`/`grep` instead of pre-loading the repo.

The unifying principle from Anthropic's context-engineering guidance [2] is to treat context as a finite, curated resource. For a 400-asset ecosystem this directly implies the target architecture: **one search tool over a catalog, where each catalog entry is a lightweight metadata card plus a pointer to the full artifact.** The user's `ir` charter — "give an agent one search tool, not fifty tool schemas" — is a verbatim restatement of this industry pattern, which is strong validation that `ir` is the correct contract layer.

## 3. Hierarchical / router / orchestrator-dispatcher patterns

Once the right asset(s) are discovered, *dispatch* is a routing decision. Anthropic's "Building Effective Agents" [12] codifies five composable patterns; two matter here: **Routing** (classify input, send to a specialized follow-on) and **Orchestrator-Workers** (a central LLM dynamically decomposes a task, delegates to workers, synthesizes results). The key distinction from static parallelization is that subtasks are *determined at runtime*, not pre-listed [12][13]. In Claude Code this maps to subagents via the Task tool; Skills are the reusable-instruction layer the orchestrator pulls in.

The framework landscape converges on the same shapes with different ergonomics [14][15]: **LangGraph** models agents as nodes in a directed graph over shared state with checkpointing — best when control flow is stateful and conditional, and its `supervisor` pattern is a literal router-to-specialists. **OpenAI Agents SDK** uses explicit **handoffs**: agents declare which agents they may transfer control to, and the SDK runs the loop — the lightest-weight way to express "front-desk router → specialist" (the descendant of the Swarm experiment) [16]. **CrewAI** offers a `hierarchical` process where a manager agent delegates to role-defined workers, strong for prototyping but awkward for conditional branching [17]. The common abstraction across all three is *a supervisor that selects among specialists by matching intent to capability descriptions* — i.e., routing **is** a retrieval problem over capability metadata, which is why discovery and dispatch are the same engine viewed twice.

Crucially, **routing is not universally beneficial**. A router adds a classification step whose accuracy and latency determine whether it helps or hurts. Evidence: semantic/learned routers improve accuracy >10pp and cut latency ~47% on some benchmarks, but their advantage *reverses* on others where the classifier is no better than random at separating hard cases [18][19]. LLM-based routing is "slow and unreliable" relative to lightweight retrieval-based selection with outcome refinement [18]. The design implication: for the common case, use **cheap deterministic routing** (rank the catalog, take the confident top-1, dispatch) and reserve **LLM/agentic routing** for ambiguous queries where the top candidates are close in score — a graceful escalation, not an always-on supervisor. The user's `aw` package already provides exactly the deterministic primitives for this: `PriorityRouter` (try strategies in order, short-circuit on first match) and `ConditionalRouter` (accept a match only if a predicate holds). A retrieval-backed strategy plugged into `PriorityRouter`, with an LLM strategy appended as the last resort, is the precise "cheap-first, escalate-on-ambiguity" shape the literature recommends — built from primitives already in hand.

## 4. Registries, indexes, catalogs of AI assets

The MCP ecosystem is rapidly standardizing how *external* tools are catalogued, and the schema choices are directly reusable. The **official MCP Registry** (`registry.modelcontextprotocol.io`, preview Sept 2025) is an open catalog/API where maintainers publish self-reported server metadata; it is explicitly designed as an *upstream* that downstream "subregistries" (marketplaces, private enterprise catalogs) augment and re-serve [20][21]. The de-facto record schema across registries is stable: **name, transport, tool list, auth requirement, homepage/repository, a short capability description**, plus verification status and usage counts [22]. **Smithery** (~7,000 servers) is the Docker-Hub-like hub [21][22]. The ecosystem's open problem — "publish once or fragment forever" — is precisely the federation problem the user faces internally across ~400 assets in ~200 repos.

Two takeaways for the personal catalog. First, **normalize to a common record**: every asset type (SKILL.md frontmatter, `.claude/agents/*.md`, MCP tool schema, research report, README/pyproject) should be projected onto a shared card — `{id, kind, name, description, tags, source_uri, content_ref, change_signal}` — so a single retriever ranks across all of them. This is the registry pattern applied inward. Second, **the upstream/subregistry split is the right mental model**: the local catalog is the *aggregating subregistry* that harvests many sources (the github/smithery/composio/awesome-list/skillsdirectory backends `skill` already speaks, plus the local filesystem). The user's `skill` package is already a registry over one asset type (skills) with a `LocalSkillStore` (a `MutableMapping` index) and a pluggable `backends` registry — it is the existing prototype of the catalog, just scoped to a single `kind`.

## 5. Capability discovery as a maintained engine, not a one-off search

A catalog over a drifting corpus is only useful if it stays fresh, and freshness is where naive embedding indexes fail. Full re-embedding of everything on every change is slow, costly, and leaves the index in a *partially-stale* state during the rebuild, returning outdated results mid-reindex [23]. The production answer is **incremental, change-tracked indexing**: detect which artifacts actually changed (mtime/content-hash/delta-sync), and re-embed only those — an incremental update of 10 changed files can be ~45s/$0.07 versus a 22-minute/$8.50 full reindex of 12k files [23][24]. Tools like CocoIndex frame this as a dataflow substrate with lineage so the system *knows* what is stale [24]. A second subtlety: distinguish **re-index** (make new/changed docs searchable, cheap) from **re-embed** (regenerate vectors after content edits or an embedder upgrade, expensive) — they have different triggers and SLAs [23].

This maps cleanly onto abstractions the user already has. `ir`'s `CorpusSource` is defined as *scope + change_signal + strategy + embedder* — i.e., it already carries a `change_signal` for exactly this incremental-refresh purpose, and `CorpusStore` provides dol-backed persistence. The maintained-engine requirement is therefore a *wiring and scheduling* task over `ir`'s existing change-signal contract, not a new subsystem: a watcher (or a periodic sweep, or a git-hook) recomputes content hashes, asks each source for its changed ids, and re-embeds only the delta into the backing vector store (`chromadol` over ChromaDB, or `ir`'s native `vd`).

## Grounding in the existing ecosystem

Mapping the building blocks to the layered design, the recommendation is overwhelmingly **compose, not build** — with exactly one new thin package.

- **`ir` — the contract layer (compose, central).** Its `search`/`select`/`disclose`/`discover`/`fuse_hits`/`traverse` surface and its `Corpus`/`CorpusSource`/`CorpusStore` storage model already *are* the "one search tool over a corpus" pattern the industry converged on [1][2][3]. Calibrated abstention, federated per-source gating + RRF fusion, and the `change_signal` hook are all present. **Build nothing here; this is the spine.**
- **`imbed` + `chromadol` — embedding & vector-store backends (compose).** `imbed` supplies segmentation, planar/cluster viz (valuable for *seeing* 400 assets in 2D and spotting redundancy/clusters), and cluster labeling; `chromadol` supplies the dict-like persistent vector store. Wire them as `ir` backends, not as a parallel stack.
- **`grub` — the fast-start lexical/hybrid backend (compose).** Its `Searcher(method='tfidf'|'semantic'|'hybrid')` over any `Mapping[str,str]` source is the quickest way to stand up the lexical leg (critical for exact name matches [4]) and a baseline before tuning `ir`. Use `grub` as an `ir` retriever or as the v0 catalog search.
- **`skill` — the harvesting prototype + one asset-type's backends (compose/extend).** `LocalSkillStore`, the generic `Registry`, and the remote `backends` (github/smithery/composio/awesome-list/skillsdirectory) are the existing ingestion machinery — but scoped to skills only, single-folder, keyword-substring. **Extend its registry concept to the new catalog; reuse its remote backends; do not duplicate them.**
- **`raglab` — the agentic Q&A layer (compose).** Its 6-role loop (Planner/Formulator/Retriever/Evaluator/Reranker/Citer) with the evaluator→reformulate back-edge over `ir` sources is precisely the opt-in multi-hop path from §1. Use it for "ask my whole ecosystem a question," not for single-asset dispatch.
- **`aw.routing` — the deterministic dispatch layer (compose).** `PriorityRouter`/`ConditionalRouter` give the cheap-first, escalate-on-ambiguity router of §3 without an LLM in the hot path. For *control-handoff* dispatch (actually invoking a subagent/skill), Claude Code subagents/Skills are the runtime; `aw` decides *which*.

**THE GAP (build new — one thin package).** No existing package harvests *all* asset types into one normalized corpus with a maintained index. The missing piece is an **asset-catalog/ingestion layer** — call it the *catalog* — whose sole job is: (1) walk sources (SKILL.md frontmatter, `.claude/agents/*.md`, MCP tool schemas, research reports, README/pyproject across ~200 repos); (2) project each onto the common record `{id, kind, name, description, tags, source_uri, content_ref, change_signal}`; (3) register the result as one (or federated) `ir.CorpusSource`(s); (4) keep it fresh via incremental re-embed on change. It is deliberately *thin*: it owns *normalization and harvesting*, and delegates retrieval to `ir`, storage to `chromadol`/`dol`, lexical fast-start to `grub`, agentic Q&A to `raglab`, and dispatch to `aw`/subagents. It is the inward-facing analogue of the MCP registry's aggregating subregistry [20][22], and a generalization of `skill`'s `LocalSkillStore` from one `kind` to many.

## Recommendations

Prioritized, concrete, for the layered architecture (contract = `ir`; backends = `imbed`/`chromadol`/`grub`; new catalog = the gap; Q&A = `raglab`; dispatch = `aw`/subagents):

1. **Build the thin `catalog` package now, around `ir`'s `CorpusSource` contract.** Define the normalized record and one harvester per asset kind (start with SKILL.md frontmatter and `.claude/agents/*.md` — highest value, structured metadata). Each harvester yields cards; register them as an `ir` source. ~A few hundred LOC, because all retrieval/storage/fusion is delegated. (Owns: normalization + harvest only.)
2. **Default to hybrid retrieval with RRF fusion; make lexical first-class.** Asset names/symbols demand exact-match recall [4]; configure `ir` `mode='hybrid'` with `fuse='rrf'`, and keep calibrated abstention on (`min_score='auto'`) so dispatch refuses rather than mis-routes. Measure on a held-out query set — on this small corpus, confirm hybrid beats pure-dense before committing [4].
3. **Expose exactly ONE discovery tool to agents** (`discover(query) -> ranked cards`), with detail disclosed just-in-time [1][2][3]. The card is the cheap first-disclosure level; the full artifact loads only when selected. This is the whole point — do not surface 400 schemas.
4. **Make dispatch cheap-first, escalate-on-ambiguity.** Use `aw.PriorityRouter` with a retrieval-backed strategy; if the top candidates are within a score gap (ambiguous), escalate to an LLM/`raglab` decision. Reserve agentic multi-hop for cross-asset Q&A, not single-asset routing [18][19].
5. **Maintain freshness incrementally via `ir`'s `change_signal`.** Content-hash each source; re-embed only the delta on a git-hook or periodic sweep; distinguish re-index from re-embed [23][24]. Never full-reindex on every change.
6. **Reuse `skill`'s remote backends and generalize its registry**, rather than re-implementing github/smithery/awesome-list ingestion. Promote `LocalSkillStore`'s pattern to the multi-kind catalog.
7. **Use `imbed`'s 2D/3D viz as a maintenance dashboard** — cluster the 400 cards to *see* redundancy and gaps (the user's actual pain: "I can't remember what I have"). Discovery and curation share the embedding space.

## Open questions / decisions (seed for GitHub sub-issues)

- **Catalog package boundary:** new standalone package vs. a subpackage/extension of `skill` (which already harvests one kind)? The normalization+harvest scope argues standalone; the existing `LocalSkillStore`/`Registry`/backends argue extension. Decide ownership before writing code.
- **Vector store of record:** `ir`'s native `vd` vs. `chromadol`/ChromaDB for the persisted index. Tradeoff: zero-dep numpy/BM25 vs. a real ANN store at 400 (small) → likely 10k+ (chunks) scale.
- **Card schema SSOT:** exact fields beyond `{id,kind,name,description,tags,source_uri,content_ref,change_signal}` — do we mirror the MCP registry record [22] for future interop, and how are per-kind extras (skill `allowed-tools`, agent model, tool input schema) carried without bloating the common card?
- **Freshness trigger:** git-hook vs. filesystem watcher vs. periodic sweep vs. on-demand-with-staleness-check — and the re-index vs. re-embed SLA per kind [23].
- **Routing escalation threshold:** what score-gap / abstention boundary flips a query from deterministic `aw` routing to LLM/`raglab` adjudication, and how is it calibrated [18]?
- **Cross-repo harvest mechanics:** how to enumerate ~200 packages' READMEs/pyproject without a heavy clone-everything step — reuse the user's existing `.pth`/projreg manifest as the source-of-truth scope?
- **Evaluation harness:** a small labeled query→expected-asset set to regression-test precision@1 and abstention as the catalog grows — without it, hybrid/routing tuning is guesswork.

## References

[1] Anthropic. Introducing advanced tool use on the Claude Developer Platform (Tool Search Tool, Programmatic Tool Use). 2025. [anthropic.com/engineering/advanced-tool-use](https://www.anthropic.com/engineering/advanced-tool-use)

[2] Anthropic (Rajasekaran P, Dixon E, Ryan C, Hadfield J). Effective context engineering for AI agents. 2025. [anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

[3] Anthropic. Equipping agents for the real world with Agent Skills. 2025. [anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

[4] Pan T. Hybrid Search in Production: Why BM25 Still Wins on the Queries That Matter. 2026. [tianpan.co/blog/2026-04-12-hybrid-search-production-bm25-dense-embeddings](https://tianpan.co/blog/2026-04-12-hybrid-search-production-bm25-dense-embeddings)

[5] Cormack GV, Clarke CLA, Büttcher S. Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods. SIGIR 2009. [dl.acm.org/doi/10.1145/1571941.1572114](https://dl.acm.org/doi/10.1145/1571941.1572114)

[6] Asai A, Wu Z, Wang Y, Sil A, Hajishirzi H. Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. 2023. [arxiv.org/abs/2310.11511](https://arxiv.org/abs/2310.11511)

[7] Singh A, et al. Agentic Retrieval-Augmented Generation: A Survey. 2025. [arxiv.org/abs/2501.09136](https://arxiv.org/abs/2501.09136)

[8] Anon. Fishing for Answers: Exploring One-shot vs. Iterative Retrieval Strategies for Retrieval-Augmented Generation. 2025. [arxiv.org/abs/2509.04820](https://arxiv.org/abs/2509.04820)

[9] Anthropic. Tool search tool — Claude Platform Docs. 2025. [platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)

[10] Anthropic. Agent Skills overview — Claude Platform Docs. 2025. [platform.claude.com/docs/en/agents-and-tools/agent-skills/overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

[11] Anthropic. Code execution with MCP: building more efficient AI agents. 2025. [anthropic.com/engineering/code-execution-with-mcp](https://www.anthropic.com/engineering/code-execution-with-mcp)

[12] Anthropic. Building Effective AI Agents. 2024. [anthropic.com/research/building-effective-agents](https://www.anthropic.com/research/building-effective-agents)

[13] Anthropic. orchestrator_workers.ipynb (claude-cookbooks). 2024. [github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/orchestrator_workers.ipynb](https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/orchestrator_workers.ipynb)

[14] LangChain. LangGraph multi-agent concepts (supervisor / network). 2025. [langchain-ai.github.io/langgraph/concepts/multi_agent/](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)

[15] OpenAI. Agents SDK — Handoffs. 2025. [openai.github.io/openai-agents-python/handoffs/](https://openai.github.io/openai-agents-python/handoffs/)

[16] OpenAI. Swarm (educational multi-agent orchestration). 2024. [github.com/openai/swarm](https://github.com/openai/swarm)

[17] CrewAI. Processes — hierarchical & sequential. 2025. [docs.crewai.com/concepts/processes](https://docs.crewai.com/concepts/processes)

[18] Anon. Outcome-Aware Tool Selection for Semantic Routers: Latency-Constrained Learning Without LLM Inference. 2026. [arxiv.org/abs/2603.13426](https://arxiv.org/abs/2603.13426)

[19] Anon. When to Reason: Semantic Router for vLLM. 2025. [arxiv.org/abs/2510.08731](https://arxiv.org/abs/2510.08731)

[20] Model Context Protocol. Introducing the MCP Registry (preview). 2025. [blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/](https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/)

[21] Smithery. Central hub for MCP servers. 2025. [smithery.ai](https://smithery.ai/)

[22] TrueFoundry. Best MCP Registries in 2026: Compared for Developers and Enterprises. 2026. [truefoundry.com/blog/best-mcp-registries](https://www.truefoundry.com/blog/best-mcp-registries)

[23] Rana B. Top 7 Freshness SLAs: Re-Embed vs Re-Index. 2025. [medium.com/@bhagyarana80/top-7-freshness-slas-re-embed-vs-re-index-de6408a78a9f](https://medium.com/@bhagyarana80/top-7-freshness-slas-re-embed-vs-re-index-de6408a78a9f)

[24] CocoIndex. Incremental engine for long-horizon agents. 2025. [github.com/cocoindex-io/cocoindex](https://github.com/cocoindex-io/cocoindex)

[25] Red Hat. Bringing intelligent, efficient routing to open source AI with vLLM Semantic Router. 2025. [redhat.com/en/blog/bringing-intelligent-efficient-routing-open-source-ai-vllm-semantic-router](https://www.redhat.com/en/blog/bringing-intelligent-efficient-routing-open-source-ai-vllm-semantic-router)

Related reports: multiplatform_config.md, adr_and_home_finding.md, lifecycle_agentops.md (in this directory).
