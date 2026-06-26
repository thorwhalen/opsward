# Decision Records and Home-Finding: Capturing Rationale and Placing Work in a Large Personal Ecosystem

## Abstract

This report treats two problems that look distinct but are the same problem viewed from two ends. **Part A** surveys decision-record practice — Nygard's original ADR, MADR, Y-statements, Tyree-Akerman, and the tooling around them — and asks where rationale should live so that both humans and AI agents can later retrieve "why did we do X." **Part B** asks the prior question: *where does new work belong* — a fresh package or an existing one — which is itself a search problem (does an answer already exist?) and a decision problem (record why this home was chosen). For a solo maintainer of ~200 packages and ~200 AI assets, the binding constraint is friction: any capture or discovery workflow that costs more than a few seconds per decision will not survive contact with daily work. The recommendation composes the maintainer's *existing* building blocks — opsward's `decisions/` scaffold, the `github-memory` skill, and the grub/ir/imbed search engines plus a package registry — rather than adopting new heavyweight tooling.

## Scope

In scope: lightweight rationale capture (formats, storage surfaces, AI-era retrieval, solo pragmatics) and home-finding for new work (monorepo vs many-small-packages, boundary heuristics, reuse discovery, and the link back to decision records). Out of scope: full architecture documentation systems (arc42, C4), team-process governance (RFC pipelines with sign-off), and the mechanics of the search engines themselves (deferred to the discovery report). The audience is a single expert maintainer working alongside AI agents; "team consensus" concerns are deliberately downweighted in favour of *future-self and future-agent retrieval*.

## Part A — Decision records

### A.1 Standards, formats, and what the community converged on

The canonical reference is Michael Nygard's 2011 essay *Documenting Architecture Decisions* [1], which framed the durable problem ("a new person coming on to a project may be perplexed, baffled, delighted, or infuriated by some past decision") and proposed a deliberately lightweight document focused on the decision itself, with four sections: **Title, Status, Context, Decision, Consequences**. Nygard did not invent decision logs — Tyree and Akerman's 2005 IEEE *Architecture Decisions: Demystifying Architecture* [6] predates him with a richer, heavier template (issue, assumptions, constraints, positions, argument, implications) — but Nygard's minimalism is what spread. ThoughtWorks moved ADRs to "Adopt" on its Technology Radar in 2018, and Martin Fowler's bliki entry [2] codified the now-standard conventions: ADRs live in the source repo under `doc/adr`, are written in Markdown "so they can be easily read and diffed just like any code," and — crucially — **once accepted, an ADR is never edited; it is superseded** by a new record that links back to it [2].

Two notable refinements:

- **MADR (Markdown ADR)** [3] is the most actively maintained modern format; **MADR 4.0.0** shipped September 2024. It hosts on `adr.github.io/madr` and adds *tradeoff analysis* (pros/cons per option) and metadata (decision-makers, confirmation status) on top of Nygard's skeleton, offered in both a full and a minimal template, each in annotated and bare variants. MADR is effectively the community's current default.
- **Y-statements** (Olaf Zimmermann) [7] compress a decision to a single structured sentence: *"In the context of \<use case\>, facing \<concern\>, we decided for \<option\> to achieve \<quality\>, accepting \<downside\>, because \<rationale\>."* This is the lowest-friction format that still captures the *because* — the part that rots first and matters most for later retrieval.

Tooling has *not* converged the way the format has. The `adr.github.io` org maintains a tooling index [5]; the practical landscape is: **adr-tools** [8] (Nat Pryce's Bash scripts, Nygard format, the de-facto baseline), **Log4brains** [9] (MADR-default, renders ADRs to a static knowledge-base site, but now in low-maintenance mode), and **dotnet-adr** [10] (cross-platform .NET global tool). The honest reading is that no tool dominates; most teams use a numbered-Markdown-files convention plus, at most, a thin `new`/`supersede` helper. For a Python maintainer this matters: there is no compelling reason to adopt a Node or .NET toolchain when a 30-line generator (opsward already has the template-rendering machinery) reproduces 90% of the value.

**Bottom line:** the community has converged on a *format philosophy* (immutable, numbered, Markdown, in-repo, one page, status-tracked, superseding over editing) far more than on any tool. MADR is the safe default skeleton; Y-statements are the safe default for trivially small decisions.

### A.2 Where to store decisions

The storage surface is a tradeoff across four axes: **proximity to code**, **discoverability**, **longevity**, and **friction-to-write**. The options and their honest costs:

| Surface | Proximity to code | Discoverability | Longevity | Friction |
|---|---|---|---|---|
| In-repo `docs/decisions/*.md` | Highest — versioned, diffed, PR-reviewable [2] | Medium — grep/agent-readable, but siloed per repo | High — survives as long as the repo | Low-medium |
| GitHub **Issues** | Medium — linkable from commits (`Refs #N`) | High *within* a repo; searchable | Medium — issues get closed/archived | Lowest |
| GitHub **Discussions** | Medium | High; threaded deliberation | High | Low |
| Wiki / Confluence / Notion | Low — detached from code | High for non-technical readers | Medium — drifts from code | Medium |
| External KB | Lowest | Variable | Variable | Variable |

The mainstream recommendation is unambiguous: **store ADRs in the repo** (`docs/decisions/` or `docs/adr/`) because they version alongside the code they explain and can be reviewed as PRs [2]. Microsoft's [11] and AWS's [12] prescriptive guidance both adopt in-repo, append-only, immutable logs. Wikis win only when non-technical stakeholders must read decisions without touching the repo — not a solo-maintainer concern.

But "in the repo" and "in GitHub Issues/Discussions" are not mutually exclusive, and the right answer depends on the *granularity and life-stage* of the rationale. The useful distinction (which the maintainer's own `github-memory` skill already encodes) is **decision *stream* vs decision *log***: the deliberation — the back-and-forth, the half-formed options, the "let's not do X" — is a stream best captured in an Issue or Discussion *while it's happening*; the **hardened conclusion** is a log entry that belongs as an immutable Markdown ADR in `docs/decisions/`. Issues are where the dev-journal lives; Discussions are where durable design rationale lives; the ADR file is the *crystallised* output. Linking the three (ADR cites the Discussion that produced it; the Discussion links the Issue that surfaced the need) gives the best of all axes.

### A.3 The AI-era angle: rationale that both humans and agents can retrieve

The new requirement is **machine-retrievability of "why."** When an AI agent edits code six months later, it needs to recover the constraint that made the original choice non-obvious, or it will "fix" the thing that was deliberate. Three implications:

1. **Format for retrieval, not just reading.** Markdown ADRs in-repo are already ideal for agents: greppable, chunkable for embeddings, and co-located with the code. The Y-statement's explicit `because` clause is a gift to retrieval — it puts the rationale in one searchable sentence. This is a point in favour of *in-repo files over Issues* for the hardened log: an agent cloning the repo sees the ADRs without API calls, whereas Issues require a `gh` round-trip the agent may not make.

2. **AI-assisted authoring lowers the capture cost.** Equal Experts report a *metaprompting* workflow [13]: collect terse "kernel-of-truth" one-liners, then have an LLM expand them into full ADRs — "we might generate dozens of ADRs in a single morning." The big win is *retrospective* documentation velocity: an agent can inspect code and existing docs to infer the implicit decisions that were never written down. The failure mode is equally clear: LLMs "frequently hallucinated reference material, including non-existent APIs, web pages, or entire product features" [13], so generated drafts need fact-check guardrails and human (or tool-verified) review. A coding agent asked to review *all* ADRs collectively for contradictions worked, but "success was variable" [13]. The 2025 survey of generative AI for software architecture [14] confirms the pattern across the field: LLMs accelerate *drafting and consistency-checking* but are not trustworthy as the sole author of rationale.

3. **Anti-rot is structural, not disciplinary.** ADRs rot when the code moves and the record doesn't. The immutability convention is the defence: you never edit an accepted ADR, you supersede it [2][11], so the log is *append-only* and a stale-looking entry is correctly read as "this was true then." Opsward's own niche is here — its scoring rubric already checks **currency** (do referenced paths still exist?) and cross-references; a maintenance pass can flag ADRs whose cited files have moved and propose a superseding record rather than silently letting the old one drift.

**Assessment of the maintainer's current practice** (docs files with private ones symlinked in, plus Issues, Discussions, Projects): this is *already aligned* with best practice and arguably ahead of it. The one gap is that the hardened-conclusion layer — the immutable, numbered ADR file — is scaffolded (opsward ships an empty `misc/docs/decisions/0000-template.md`) but not yet *habitually populated*. The deliberation is being captured (Issues/Discussions); the crystallised, agent-retrievable log entry often is not. Closing that gap is the whole of the Part-A recommendation.

### A.4 Solo-maintainer pragmatics

Across 200 repos, the binding constraint is *marginal cost per decision*. Heavyweight templates (Tyree-Akerman's eight sections) are a tax that guarantees non-adoption. The pragmatic stance:

- **Tier by significance.** Most decisions get a one-line Y-statement appended to a running `decisions/` log or the relevant Issue. Only genuinely load-bearing, expensive-to-reverse decisions get a full numbered MADR file. This is the "log not stream" discipline applied to *volume*.
- **Capture at the moment of choice, AI-expand later.** Drop the kernel-of-truth one-liner when you decide; let an agent batch-expand the ones that deserve full records [13]. The maintainer never does form-filling.
- **Make the tool do the boilerplate.** A `decision new "title"` helper that allocates the next number, stamps the date/status, and opens the file removes the only remaining friction. opsward already renders templates from `importlib.resources` — this is a few lines.

## Part B — Home-finding and reuse

### B.1 Monorepo vs many-small-packages for a solo maintainer

The maintainer's existing philosophy (dol/epythet: many small, composable packages) is a deliberate *polyrepo-of-micropackages* stance, and it is defensible — but it has a real, measurable cost. The literature frames the tradeoff cleanly [19][20][21]:

- **Monorepo** wins on *cross-project change* (atomic refactors across packages in one commit; no publish-version-bump dance to share code), *unified tooling*, and — most relevant here — **discoverability and code visibility** [19]. Google's CACM paper [19] is the canonical scale argument: a single repo gives "extensive code sharing and reuse" and "code visibility" precisely *because everything is in one searchable place*. The cost of finding existing code is near-zero when there is one index.
- **Polyrepo / many packages** wins on *isolation* (each repo is small, fast to clone, independently versioned and released) and *clean boundaries*, at the cost of cross-cutting changes and — the sharp edge for this maintainer — **reuse discovery**. With 200 separate packages, "do I already have something that does this?" becomes a genuine search problem rather than a glance.

For a solo maintainer the standard advice is "start monorepo, split when it clearly pays" [20], but that ship has sailed at 200 packages, and the many-small-packages philosophy has compounding benefits (each package is independently publishable, testable, and composable — the dol/epythet thesis). The pragmatic conclusion is **not** to consolidate, but to *recover the monorepo's one decisive advantage — a single discoverability index — without merging the repos*. That is exactly what a package registry plus a code search engine provides (B.3). The proliferation cost is real but is a *tooling* problem, not a *structure* problem.

### B.2 Package-boundary decisions: extend or create?

The core question — does new work extend an existing package or warrant a new one — is the micro-scale version of the DDD bounded-context question [18]. Heuristics, ordered by reliability:

1. **Rule of three** [16][17]. Don't extract a package (or even an abstraction) until you have *three* real call sites. Two instances tempt you to abstract on incomplete information, baking incidental details of the first two cases into the boundary. Sandi Metz's sharper formulation [17]: *"duplication is far cheaper than the wrong abstraction"* — a wrong package boundary is more expensive to undo than the duplication it was meant to remove, because reversing it means re-merging published packages. For a many-small-packages maintainer this is the single most important guardrail against proliferation: **a new package is the most expensive abstraction you can create; demand three uses.**

2. **Cohesion/coupling and ubiquitous language** [18]. Extend an existing package when the new work shares its *vocabulary and reason-to-change* (high cohesion, it would change for the same reasons). Create a new one when the work serves a *distinct capability with its own language* and you can name a clean contract (the public function/Protocol) across the seam. "Too many small contexts generate complexity and excessive integration" [18] — micro-package sprawl is the failure mode of over-applying this.

3. **The dependency direction test.** If the new code would force the existing package to depend on something *it has no business depending on* (a heavy or unrelated dependency), that is a boundary: split. If the new code depends *only* on what the existing package already exposes, extend. This keeps the dol/epythet "lightweight, composable" property intact.

4. **Release-cadence test.** If the new work will version and release on a *different rhythm* than the host package, that is a polyrepo-shaped signal for a separate package; if it co-evolves, keep it together.

The decision is rarely clean, which is exactly why it should be *recorded* (B.4).

### B.3 Reuse discovery: "do I already have something that does this?"

This is the search problem the many-packages structure creates, and it has three layers, weakest to strongest:

- **Lexical/structural search** — `rg` / `grep` / GitHub code search across the local ecosystem. Fast, exact, zero-setup; fails when you don't know the *name* of the thing you're looking for (the common case for reuse: "I want validation logic but I don't know what I called it").
- **A capability registry / catalog.** This is the Backstage [22] pattern at personal scale: a single index that makes "all the software and who owns it discoverable," so the answer to "do we already have something that does X?" is "a search away rather than a series of educated guesses" [22]. The maintainer's **projreg** concept (indexing the ~200 packages) and the `my-packages` skill are exactly this — a personal software catalog. The recommendation is to treat projreg as the SSOT registry and make *every* new-package decision consult it first.
- **Semantic code search.** Convert the codebase to embeddings and query by *meaning*, not keyword [23][24]. Sourcegraph's framing [23]: semantic search "excels at discovery, where you know the concept but not the exact implementation" — precisely the reuse case. Cursor's indexing approach [24] (chunk → embed → cache by chunk content, so only churned files re-embed) shows this is cheap to keep fresh even at scale. The maintainer's **grub / ir / imbed** engines are the home-grown version of this; pointed at the package corpus, they answer "do I already have something that does this?" semantically. (Mechanics deferred to the discovery report.)

The right architecture composes all three: lexical for exact, **projreg** for "which package owns capability X," and **grub/ir/imbed** for semantic "find me anything conceptually like this." The agent-facing entry point already exists — the `my-packages` skill instructs the agent to search the local ecosystem *before* suggesting any third-party PyPI package. Extending that habit to *before creating a new package* closes the loop.

### B.4 The connection between A and B

The two halves are one practice. A home-finding decision — "this goes in a new package `foo` rather than extending `bar`, because the dependency direction and release cadence differ" — **is a decision record**, and a load-bearing, expensive-to-reverse one (reversing a published package split is costly). It deserves exactly the Y-statement (or full MADR) treatment of Part A. And the *input* to that decision — "have I already built this?" — **is a search problem**, answered by the reuse-discovery stack of B.3. So the workflow is a pipeline: **discover (search) → decide (boundary heuristics) → record (decision log) → the record becomes future search corpus.** The decision records themselves become part of the searchable rationale that future home-finding decisions consult — a virtuous loop where today's recorded "why" is tomorrow's retrieved context.

## Grounding in the existing ecosystem

Mapping the recommendations to what the maintainer *already has* (prefer composing over building):

| Need | Compose existing | Don't build |
|---|---|---|
| Hardened decision log | opsward's `misc/docs/decisions/` MADR scaffold + `docs_guide.md` index pattern; opsward *generates* a `decisions/` folder for target projects | A new ADR tool (Log4brains/dotnet-adr) |
| Deliberation capture | `github-memory` skill — Issues as dev-journal (stream), Discussions as durable rationale | A separate wiki/KB |
| Cross-repo decision visibility | `github-memory`'s optional GitHub Projects for cross-repo tracking | A custom dashboard |
| "Do I already have this?" | **projreg** registry + `my-packages` skill (lexical/catalog) and **grub/ir/imbed** (semantic) | A new code-search service |
| Boundary-decision recording | opsward's `decision new` generator (template-render via `importlib.resources`) | Manual numbering |
| Anti-rot | opsward's existing *currency* + cross-reference scoring, extended to flag stale ADRs | A linter from scratch |

The **compose-X vs build-new-Y** verdict is consistently *compose*. The only genuinely new pieces are thin glue: (1) a `decision new "title"` helper in opsward that allocates the next number and stamps status/date — small, and it reuses the template engine; (2) a convention that boundary decisions ("extend vs new package") route through projreg/grub *before* the decision and into a `decisions/` entry *after*; (3) extending opsward's maintenance pass to detect ADRs whose cited paths have moved. Everything else is habit, not code. Notably, opsward is *itself* an instance of the Part-A gap: it ships the `decisions/` scaffold but its own folder holds only `0000-template.md` — the meta-tool that generates decision folders for others has not yet populated its own. Eating that dog food is the cheapest possible validation.

## Recommendations

**A low-friction decision-capture workflow (solo + AI, ~200 repos):**

1. **Two tiers.** Trivial/medium decisions → a one-line **Y-statement** [7] appended to the relevant Issue (the stream) or a running `decisions/log.md`. Load-bearing, expensive-to-reverse decisions → a numbered **MADR** [3] file in `docs/decisions/` (the immutable log).
2. **Capture the kernel at the moment of choice; AI-expand on demand.** Drop the one-liner now; let an agent batch-expand selected ones into full ADRs with fact-check guardrails [13], never hand-filling forms.
3. **Immutable + superseding** [2][11]: never edit an accepted ADR; write a new one that links back. The log stays honest by construction.
4. **Link the three surfaces:** ADR file ⟶ the Discussion that deliberated it ⟶ the Issue that surfaced the need (`github-memory`). The crystallised file is the agent-retrievable artifact; keep it in-repo so agents see it on clone.
5. **Tooling = opsward, not a new stack:** `decision new "title"` for boilerplate; `opsward maintain` to flag rotted (stale-path) ADRs.

**A concrete reuse-discovery workflow (before any new package):**

1. **Search first, three layers:** `rg` (lexical) → **projreg**/`my-packages` (capability catalog: "which package owns X?") [22] → **grub/ir/imbed** (semantic: "anything conceptually like this?") [23][24]. This is mandatory *before* writing new code and *before* creating a package — the same discipline `my-packages` already applies to third-party PyPI choices.
2. **Apply the boundary heuristics** in order: rule of three [16][17] (≥3 real uses before extracting a package), cohesion/ubiquitous-language [18], dependency-direction, release-cadence (B.2).
3. **Record the home-finding decision** as a Y-statement or MADR (it is a decision record), and link it from both packages it concerns. The record re-enters the search corpus for next time.

## Open questions / decisions

These seed sub-issues:

- **Tier threshold:** what concrete signal promotes a decision from a Y-statement one-liner to a full MADR file? (Reversal cost? Cross-package blast radius? "Touches a published API"?)
- **Single global decision log vs per-repo `decisions/`:** across 200 repos, do cross-cutting decisions (ecosystem-wide conventions) need a *central* registry (a `decisions` repo, or projreg-indexed), distinct from per-repo ADRs?
- **AI-expansion trust boundary:** what guardrails make LLM-drafted ADRs safe to commit unreviewed — tool-verified path/reference checks, or always human-gated? [13]
- **Anti-rot ownership:** should opsward's `maintain` *auto-open a superseding-ADR stub* when a cited path moves, or only report it?
- **projreg as the SSOT registry:** does projreg need a "capability" field (what each package *does*, not just its name) to serve reuse discovery well, and can grub/ir/imbed populate it semantically?
- **Boundary-decision automation:** can opsward, given a proposed new package, run the reuse-discovery search and surface "you may already have this in \<pkg\>" before the user commits to a new repo?
- **Eat-the-dog-food milestone:** populate opsward's own `misc/docs/decisions/` with the real decisions behind it (scan-is-read-only, hardcoded rubric, `string.Template` over Jinja2) as the reference exemplar.

## References

[1] Nygard M. Documenting Architecture Decisions. 2011. [cognitect.com](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
[2] Fowler M. bliki: Architecture Decision Record. 2021. [martinfowler.com](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html)
[3] MADR — Markdown Architectural Decision Records (v4.0.0). 2024. [adr.github.io/madr](https://adr.github.io/madr/)
[4] ADR GitHub Organization — Architectural Decision Records homepage. 2024. [adr.github.io](https://adr.github.io/)
[5] ADR Org. Decision Capturing Tools (tooling index). 2024. [adr.github.io/adr-tooling](https://adr.github.io/adr-tooling/)
[6] Tyree J, Akerman A. Architecture Decisions: Demystifying Architecture. IEEE Software. 2005. [utdallas.edu (PDF)](https://personal.utdallas.edu/~chung/SA/zz-Impreso-architecture_decisions-tyree-05.pdf)
[7] Zimmermann O. Architecture Decision Record Template: Y-Statements. 2020. [medium.com/olzzio](https://medium.com/olzzio/y-statements-10eb07b5a177)
[8] Pryce N. adr-tools — command-line tools for working with ADRs. [github.com/npryce/adr-tools](https://github.com/npryce/adr-tools)
[9] Vaillant T. Log4brains — ADR management and publication tool. [github.com/thomvaill/log4brains](https://github.com/thomvaill/log4brains)
[10] endjin. dotnet-adr — cross-platform .NET global tool for ADRs. [github.com/endjin/dotnet-adr](https://github.com/endjin/dotnet-adr)
[11] Microsoft. Maintain an architecture decision record (ADR) — Azure Well-Architected Framework. 2024. [learn.microsoft.com](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)
[12] AWS. ADR process — Prescriptive Guidance. 2023. [docs.aws.amazon.com](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
[13] Equal Experts. Accelerating Architectural Decision Records (ADRs) with Generative AI. 2024. [equalexperts.com](https://www.equalexperts.com/blog/our-thinking/accelerating-architectural-decision-records-adrs-with-generative-ai/)
[14] Esposito M, et al. Generative AI for Software Architecture: Applications, Challenges, and Future Directions. arXiv:2503.13310. 2025. [arxiv.org](https://arxiv.org/html/2503.13310v2)
[15] Henderson JP. architecture-decision-record — ADR examples and templates. [github.com/joelparkerhenderson/architecture-decision-record](https://github.com/joelparkerhenderson/architecture-decision-record)
[16] Wikipedia. Rule of three (computer programming). 2024. [en.wikipedia.org](https://en.wikipedia.org/wiki/Rule_of_three_(computer_programming))
[17] Metz S. The Wrong Abstraction. 2016. [sandimetz.com](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction)
[18] Fowler M. bliki: Bounded Context. 2014. [martinfowler.com](https://martinfowler.com/bliki/BoundedContext.html)
[19] Potvin R, Levenberg J. Why Google Stores Billions of Lines of Code in a Single Repository. Communications of the ACM 59(7). 2016. [cacm.acm.org](https://cacm.acm.org/research/why-google-stores-billions-of-lines-of-code-in-a-single-repository/)
[20] Spacelift. Monorepo vs. Polyrepo: What's the Difference? 2024. [spacelift.io](https://spacelift.io/blog/monorepo-vs-polyrepo)
[21] Henderson JP. monorepo-vs-polyrepo — architecture for source code management. [github.com/joelparkerhenderson/monorepo-vs-polyrepo](https://github.com/joelparkerhenderson/monorepo-vs-polyrepo)
[22] Backstage. Software Catalog — discover all software and who owns it. 2024. [backstage.io](https://backstage.io/docs/features/software-catalog/)
[23] Sourcegraph. Semantic Code Search: What it is and how it works. 2024. [sourcegraph.com](https://sourcegraph.com/blog/semantic-code-search-what-it-is-and-how-it-works)
[24] Cursor. Securely Indexing Large Codebases. 2024. [cursor.com](https://cursor.com/blog/secure-codebase-indexing)

Related reports: discovery_and_dispatch.md, multiplatform_config.md, lifecycle_agentops.md (in this directory).
