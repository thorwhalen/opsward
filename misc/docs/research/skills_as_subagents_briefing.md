# Reusing skills as subagents: research briefing

**Scope.** Backs [ADR 0009](../decisions/0009-skills-declare-their-subagent-twin.md) and [thorwhalen/opsward#26](https://github.com/thorwhalen/opsward/issues/26). Three questions: what "subagent" means on each host and whether a `SKILL.md` can be reused as one; prior art on deriving agents from skills or the reverse; what delegating to a fresh context measurably costs and saves. Everything cited was fetched on 2026-10-19; "verified" means read on the page, "snippet" means a search result only. Claude Code's own mechanics (`skills:` preload, `context: fork`) are in the ADR and not repeated here.

## A. What a subagent is on each host, and whether a skill can be one

1. **GitHub Copilot custom agents** are `.github/agents/*.agent.md` with frontmatter `name, description, target, tools, model, disable-model-invocation, user-invocable, mcp-servers, metadata`; no `skills` field. Agent-to-agent delegation is a tool alias (`agent` in `tools`); `handoffs` is not supported for the cloud agent [1]. VS Code adds `agents:` (names available as subagents), `handoffs` and `hooks`; `user-invocable: false` makes an agent subagent-only; still no `skills` field [2]. Copilot reads project skills from `.github/skills`, `.claude/skills` or `.agents/skills` and personal ones from `~/.copilot/skills` or `~/.agents/skills`, and never links skills to custom agents [3]. Verified.
2. **Cursor subagents** are Markdown in `.cursor/agents/`, and Cursor also reads `.claude/agents/` and `.codex/agents/` "for compatibility" (`.cursor/` wins on a name clash). Frontmatter: `name, description, model (inherit), readonly, is_background`; no skills field; the page recommends a *skill* "for single-purpose tasks that don't need context isolation" [4]. Cursor reads `.agents/skills/`, `.cursor/skills/`, `.claude/skills/` and `.codex/skills/`; skill frontmatter adds `paths, disable-model-invocation, icon, color, metadata`; nothing on running a skill as a subagent beyond a built-in `/create-subagent` skill [5]. Verified.
3. **OpenAI Codex** scans `.agents/skills` from the cwd up to the repo root, plus `$HOME/.agents/skills` and `/etc/codex/skills`; only `name`/`description` are documented, extras go in `agents/openai.yaml` [6]. Codex custom agents are **TOML** in `.codex/agents/` with required `name, description, developer_instructions`; built-ins `default, worker, explorer`; skills are *inherited* from the parent, not preloaded, and a custom agent can disable individual skills; "current local Codex releases spawn agents after a direct request or applicable project or skill instruction" [7]. Verified.
4. **Gemini CLI subagents** are Markdown in `.gemini/agents/` with `name, description, kind, tools, mcpServers, model, temperature, max_turns, timeout_mins`; "the body of the markdown file becomes the agent's System Prompt"; subagents cannot call subagents; extensions ship agents via an `agents/` directory [8][10]. Gemini reads `.gemini/skills/` with `.agents/skills/` as an alias; no subagent mention [9]. Verified.
5. **The Agent Skills spec** defines six keys and says nothing about agents [11], but the integration guide names `.agents/skills/` as "a widely-adopted convention for cross-client skill sharing" and has an optional section, "Subagent delegation": the skill is run in a separate subagent session that "receives the skill instructions, performs the task, and returns a summary" [12]. Verified.
6. **The `.agents/` convention**: `.agents/skills` is read natively by Codex, Gemini CLI (alias), Cursor and Copilot. No host reads an `.agents/agents`; subagent directories are per client (`.claude/agents`, `.cursor/agents`, `.codex/agents`, `.gemini/agents`, `.github/agents`), and Cursor is the only one that reads another client's agent directory.

**Consequence for the design.** Preloading a skill into an agent is Claude-only today; every other host either inherits skills (Codex), has no link at all (Copilot, Gemini), or reads Claude's agent files (Cursor). Keeping the declaration in the skill's `metadata` is the only placement every host tolerates, and a second renderer per host is the way to reach the others.

## B. Prior art: skill-as-subagent, agents generated from skills

7. **Devin CLI skills** carry `subagent: true` or `agent: <profile>` in frontmatter and run the skill body as the subagent's task; "the subagent inherits the profile's system prompt, tool restrictions, and model"; the skill's own `allowed-tools`/`permissions` are not applied; nested subagents are forbidden and a skill already inside a subagent runs inline. Marked experimental [13]. The closest analogue to Claude Code's `context: fork`. Verified.
8. **Anthropic's own framing**: the "Extend Claude Code" overview has a skill-versus-subagent tab: skills "share content across contexts", subagents give "context isolation … only summary returns", "they can combine" (a subagent preloads skills; a skill runs isolated with `context: fork`); the trigger rule is "a side task floods your conversation with output you won't reference again → route it through a subagent" [14]. The "Steering Claude Code" post: use a skill "when you want the procedure to play out inside the main thread so you can see and steer each step", a subagent when a side task "would clutter your main conversation with intermediate results you won't reference again"; "the only thing that returns to your main session is the subagent's final message" [15]. Verified; no numbers.
9. **`context: fork` has been flaky**: [anthropics/claude-code#21725](https://github.com/anthropics/claude-code/issues/21725) (`context: fork` with a custom `agent:` ran inline) was closed 2026-01-29 as a duplicate of #16803 [16]. One reason to prefer a generated twin file, which the host treats as any other agent.
10. **The reverse direction exists as a skill**: `migrate-to-skills` converts subagent `.md` files into skills by adding `context: fork`, keeping `allowed-tools`, simplifying model names, to standardise "across Claude Code, Cursor, Copilot, Codex, and Open Code" [17]. Verified.
11. **Superpowers** ships `skills/` and per-client plugin directories but no `agents/`; its `subagent-driven-development` skill dispatches a fresh subagent per task using prompt files inside the skill, so subagent prompts live in skills, not in agent definitions [18]. **anthropics/skills** has `skills/, spec/, template/`, no agents, and its README never mentions subagents [19]. Verified.
12. **Nothing found** that generates Claude Code `.claude/agents/*.md` from skills, or a plugin that pairs a skill and an agent for the same task. A LangGraph4j/Spring AI post derives a sub-agent from `SKILL.md` ("tool definition is derived from the skill metadata, while the agent behavior is derived from the skill content"), but the page returned 403 and is unverified.

## C. Measured cost and benefit of delegating

13. Anthropic's multi-agent research system: "agents typically use about 4× more tokens than chat interactions, and multi-agent systems use about 15× more tokens than chats"; token usage explains 80% of performance variance; +90.2% over a single Opus 4 on their research eval; "cut research time by up to 90%"; not fit for "domains that require all agents to share the same context" [20]. Verified.
14. One task run inline and as a subagent, from session JSON: parent input tokens 47,812 → 2,104 (−95.6%), **total billed 49,452 → 21,840 (−55.8%)**, wall time 1m47 → 1m02; "small tasks pay startup overhead and lose" [21]. Verified; n=1.
15. The same task as an inline skill, a forked skill and a subagent: parent-conversation characters 10,633 / 806 / 2,377; the forked skill "cannot access conversation history" [22]. Verified; single run, characters not tokens.
16. **Nothing found** that measures quality loss from the lossy summary back to the caller; the one piece that discusses it reasons arithmetically ("10,000 tokens of work … 500-token summary saves 9,500") without data [23].

## REFERENCES

[1] GitHub. Custom agents configuration reference. 2026. [docs.github.com](https://docs.github.com/en/copilot/reference/custom-agents-configuration)

[2] Microsoft. VS Code custom agents. 2026. [code.visualstudio.com](https://code.visualstudio.com/docs/copilot/customization/custom-agents)

[3] GitHub. About agent skills. 2026. [docs.github.com](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)

[4] Cursor. Subagents. 2026. [cursor.com/docs/agent/subagents](https://cursor.com/docs/agent/subagents)

[5] Cursor. Skills. 2026. [cursor.com/docs/context/skills](https://cursor.com/docs/context/skills)

[6] OpenAI. Agent Skills (Codex). 2026. [learn.chatgpt.com](https://learn.chatgpt.com/docs/build-skills.md)

[7] OpenAI. Subagents (Codex). 2026. [learn.chatgpt.com](https://learn.chatgpt.com/docs/agent-configuration/subagents.md)

[8] Google. Gemini CLI: Subagents. 2026. [geminicli.com](https://geminicli.com/docs/core/subagents.md)

[9] Google. Gemini CLI: Skills. 2026. [geminicli.com](https://geminicli.com/docs/cli/skills.md)

[10] Google. Subagents have arrived in Gemini CLI. 2026. [developers.googleblog.com](https://developers.googleblog.com/en/subagents-have-arrived-in-gemini-cli/)

[11] agentskills.io. Specification. 2026. [agentskills.io/specification](https://agentskills.io/specification)

[12] agentskills.io. How to add skills support to your agent. 2026. [agentskills.io/integrate-skills](https://agentskills.io/integrate-skills)

[13] Devin. Creating skills. 2026. [docs.devin.ai](https://docs.devin.ai/cli/extensibility/skills/creating-skills)

[14] Anthropic. Claude Code docs: Extend Claude Code (skill vs subagent). 2026. [code.claude.com](https://code.claude.com/docs/en/features-overview)

[15] Anthropic. Steering Claude Code: skills, hooks, rules, subagents and more. 2026. [claude.com/blog](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)

[16] anthropics/claude-code#21725: `context: fork` with a custom agent runs inline. 2026. [github.com](https://github.com/anthropics/claude-code/issues/21725)

[17] carsten-j. migrate-to-skills (agent-resources). 2026. [skills.cat](https://skills.cat/skills/carsten-j/agent-resources/migrate-to-skills)

[18] Vincent J. obra/superpowers. 2026. [github.com/obra/superpowers](https://github.com/obra/superpowers)

[19] Anthropic. anthropics/skills. 2026. [github.com/anthropics/skills](https://github.com/anthropics/skills)

[20] Anthropic. How we built our multi-agent research system. 2025. [anthropic.com/engineering](https://www.anthropic.com/engineering/multi-agent-research-system)

[21] Vantaige. Claude Code subagents that save context: 3 patterns. 2026. [vantaige.io](https://vantaige.io/blog/claude-code-subagents-save-context-3-patterns)

[22] Classmethod. Skill に context: fork を1行足すだけで…. 2026. [dev.classmethod.jp](https://dev.classmethod.jp/articles/claude-code-context-fork/)

[23] HackerNoon. Navigating Claude Code: Subagents Done Right. 2026. [hackernoon.com](https://hackernoon.com/navigating-claude-code-subagents-done-right)

Related: [`skill_tiering_and_reachability.md`](skill_tiering_and_reachability.md) (the listing budget a twin's description competes in), [`discovery_and_dispatch.md`](discovery_and_dispatch.md).
