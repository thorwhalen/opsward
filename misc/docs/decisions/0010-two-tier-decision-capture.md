# 0010 — Two-tier decision capture: a log line or a numbered ADR, never an edit

## Status

Accepted (2026-10-19). Closes the decision-capture half of [thorwhalen/opsward#16](https://github.com/thorwhalen/opsward/issues/16).

## Context

Decision practice in this fleet was ad hoc: some rationale in `docs/`, some in issues, discussions and private files, none of it indexed or linked, and opsward, which scaffolds a `decisions/` folder for other projects, had an empty one of its own until the self-maintenance pass ([#18](https://github.com/thorwhalen/opsward/issues/18)) backfilled ADRs 0001–0008. The research report `misc/docs/research/adr_and_home_finding.md` found that the community converged on a format philosophy rather than a tool: immutable, numbered, one-page Markdown records in the repo, status-tracked, superseded rather than edited; MADR as the skeleton for load-bearing choices and Zimmermann's Y-statement ("In the context of …, facing …, we decided for …, to achieve …, accepting …, because …") as the lowest-friction form that still keeps the *because*. The binding constraint for a solo maintainer of ~280 packages is friction: a capture step that costs more than seconds will not survive daily work, and a reuse-discovery step that is not mandatory will be skipped. Reuse discovery already exists as fleet practice (the `fleet-protocol` skill's three questions, `ir discover`, `priv skills-index`, `projreg`), so the gap was on the capture side: no helper, no drift check, no stated promotion rule.

## Decision

1. **Two tiers, chosen by reversal cost.** A decision is a one-line Y-statement in `<docs>/decisions/log.md` unless it is **expensive to reverse, crosses a package boundary, or touches a published API or CLI surface**; those get a numbered MADR file `<docs>/decisions/NNNN-slug.md`. A home-finding decision ("new package rather than extend X") always meets the bar: reversing a published package split is costly. When in doubt, log it; a log line can be promoted later by citing it from the ADR that supersedes it.
2. **Capture the kernel at the moment of choice; expand later, with checks.** `opsward decision note "…" --write` appends a dated line; `opsward decision new "title" --write` allocates the next number from the template, stamps status and date, and takes `--evidence` for the issue, discussion or PR the decision rests on. Both are dry-run by default and never overwrite (ADR 0001). Expanding a kernel into prose is the agent's job and is gated the same way as any edit: the paths it cites are checked by `opsward maintain`, and a human accepts the ADR by changing its status.
3. **Immutable and superseding.** An accepted ADR is never edited. A change is a new ADR whose Status line names the one it supersedes, and the old one's Status is updated to point forward; that status edit is the single permitted edit. `opsward maintain` reports, under `stale_adr`, an ADR that cites a path that no longer exists or that has no Status section; it never rewrites or auto-opens a superseding stub, because scan and maintain do not write (ADR 0001) and a stub nobody asked for is noise.
4. **Three surfaces, linked from the record.** The Evidence section is mandatory and names the issue that surfaced the need, the discussion that deliberated it (when one exists) and the PR or commit that carried it out; the `misc/docs/decisions/README.md` index row repeats the "rests on" pointer so the link survives a renumbering.
5. **Per-repo records; the fleet index is the search layer.** Decisions live in the repo they bind (`docs/decisions/` or `misc/docs/decisions/` by the project's docs convention), where an agent cloning the repo sees them without an API call. Cross-repo retrieval is `ir discover reports`, whose corpus already covers every `docs/` and `misc/docs/` under the projects root, so a recorded decision re-enters the search corpus on the next hourly reindex without a central registry. Whether a fleet-wide conventions repo should also exist, and whether `projreg` should gain a capability field for reuse discovery, are the user's calls and are filed as a `manual-task` with the recommendation below.
6. **Search before building, and record the home.** Before a new package or module: `rg` for the symbol, `ir discover packages` and `priv skills-index -f` for the capability, the group's routing document for the user's own routing decisions (the `fleet-protocol` skill, question 1). The outcome, including "nothing found", is the Context of the resulting record.

Rejected: a central `decisions` repository as the primary store (an agent working in a package would not see it; the index layer gives cross-repo search without it); editing accepted ADRs in place (destroys the history the record exists for); `maintain` auto-writing superseding stubs (writes outside the CLI edge; produces records nobody decided); a nested `decision` group with its own prog (kept under the one `opsward` parser so the pinned CLI surface stays one golden).

## Consequences

- One command per tier, both dry-run by default, both printing only repo-relative paths, so they are safe in an agent's hands and portable in the CLI goldens.
- `_dispatch_funcs` becomes a mapping (name → command, with `decision` as the one nested group); the goldens gain seven cases and the top-level help lists `decision`.
- The promotion rule is a judgment with a stated test, not a metric; the fleet sweep can only check that a log or ADR exists, not that the right tier was chosen.
- Dogfood: this repository's `misc/docs/decisions/log.md` starts with the small decisions made while landing #23, #26, #35 and this issue.

## Evidence

- [thorwhalen/opsward#16](https://github.com/thorwhalen/opsward/issues/16) (the need) and its research report `misc/docs/research/adr_and_home_finding.md` (the deliberation).
- The PR that carried it out, linked from the index row in `misc/docs/decisions/README.md`.
- ADR 0001 (writes only at the CLI edge), ADR 0008 (the pinned CLI surface), and the `github-memory` skill for the issue/discussion side of the three surfaces.
