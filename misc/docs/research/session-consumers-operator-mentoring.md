# Mentoring the operator from their own agent-session logs — research

*2026-11-08 · scope: products, learning science, detectors, risks and output formats for a "mentor" consumer of persisted Claude Code sessions · serves: the design of the session-consumers work in opsward (a single expert operator, ~2,150 top-level transcripts since July 2026, several machines)*

## Summary and recommendation

- **Build a weekly, opt-in debrief letter, not a live coach and not a score.** The strongest evidence in this space is for structured after-event reviews (debriefs raise performance by about 20–25%, d = 0.67 [1]) and for feedback about the task and the process, which beats feedback about the person; over a third of feedback interventions in the classic meta-analysis made performance worse [2][3].
- **Feedback frequency should be low, and the amount small.** Feedback on every trial helps in the moment and hurts retention (the guidance hypothesis [4]); in a randomized field trial of an AI sales coach, the weakest agents were swamped by too much feedback and the strongest resisted the coach [5]. An expert operator sits in the second group. Cap each letter at two or three teachable moments, each grounded in a quoted excerpt of the operator's own brief and a worked rewrite.
- **Teach terminology by attaching a name to a concept the operator has already shown they hold** ("a time for telling" [6]), then schedule those terms for spaced retrieval (practice testing and spacing are the two "high-utility" techniques [7]) using a modern scheduler (FSRS [8]). The personal glossary is the store the flashcards and the detectors share.
- **Run detectors before the model writes anything:** re-stated rules, missing acceptance criteria, terminology gaps, ambiguous referents, missing context, over-specification, mis-levelled delegation and unverified acceptance (section 3). Count only cases with an outcome signal (a correction, a clarifying question, a redo), because a prompt that merely looks vague is often fine [9].
- **Route setup findings to the setup, and person findings to the person.** A rule the operator re-states is a setup gap first (the human-gated loop in the in-house setup report), and only a teachable moment if it keeps recurring after the fix.
- **Guard against the mentor's own failure modes:** sycophancy [10], self-preference when a model grades model-shaped prompts [11], homogenisation toward the model's style [12], and deskilling if the mentor writes the operator's briefs for them [13][14]. Keep it in its own context, keep its profile of the operator open and editable (an open learner model [15]), and never feed it back into the working agents.

## What already exists (in-house)

- `$PP/tt/my_skills/references/self-improving-agent-setup-research.md` (2026-10-03): the setup side; evidence against unsupervised self-generated rules; the human gate. This report does not repeat it; detector D1 below hands off to it.
- `$PP/g/g_ai/docs/session-mining-research.md` (2026-09-07): transcript-mining tools, the JSONL format, and the `/insights` facet schema (including `friction_detail` and `user_satisfaction`). The detectors below are meant to sit on top of that parsing layer.
- No in-house work on mentoring the person (as opposed to the setup) was found.

## 1. Products that coach a person from recordings of their own work

| Product / practice | Signal read | Feedback given | Cadence | Evidence of effect | Verdict |
|---|---|---|---|---|---|
| Conversation intelligence (Gong and peers) | recorded sales calls: talk-to-listen ratio, phrases, topics | manager-annotated moments on the call timeline; benchmarks against winning calls | per call, plus manager review | vendor analyses only (e.g. talk ratios over 17 customers' calls) [16]; no independent controlled study found | study (the "annotated moment + benchmark" pattern) |
| AI sales coach (field RCT) | call recordings of 429 agents | AI-generated coaching vs human coaching | periodic | inverted-U: mid-ranked agents gained most; bottom agents overloaded; top agents averse; restricting feedback volume and pairing AI analysis with a human deliverer helped [5] | adopt the lessons (dose, delivery) |
| Generative AI assistant for support agents | live chats | real-time suggested replies | continuous | about +15% issues resolved per hour on average, large gains for less experienced agents, small gains for the most skilled [17] | study (assistance, not coaching; gains concentrate in novices) |
| Grammarly Insights | text written in the week | weekly statistics on productivity, vocabulary and tone [18] | weekly email | none independent found; automated writing feedback in general: g = 0.55 across 20 studies, highly heterogeneous [19] | adopt the weekly-digest shape, avoid the streaks |
| Yoodli, Poised (speech/meeting coaches) | audio of practice talks or live calls | filler words, pace, talk time | per session / real-time | testimonials only [20]; Poised announced it is shutting down in 2026 [21] | avoid real-time metrics; study rehearsal |
| Humu, Cultivate, Viva Insights (manager and work-pattern nudges) | HR surveys; email, calendar and chat metadata | short behavioural nudges; private reflection prompts | weekly-ish | Humu absorbed into Perceptyx in 2023 [22]; Viva keeps personal insights visible only to the individual [23]; no independent outcome study found | adopt "private to the person"; study nudges |
| WakaTime, Copilot usage metrics | editor activity; suggestion acceptance | time per language/project; acceptance rates | dashboards, weekly emails [24]; 28-day reports aimed at admins [25] | none on learning | avoid as a mentor signal (activity is not skill) |
| Duolingo, Anki | review history per item | next review time | per item, spaced | half-life regression cut prediction error and lifted engagement in Duolingo's experiment [26]; FSRS is the most accurate open scheduler on a ~729M-review benchmark (developer-run) [8] | adopt for terminology only |
| Claude Code `/insights` | the last 30 days of local sessions | HTML report: projects, usage, "where things go wrong", features to try, CLAUDE.md additions [27] | on demand | none published | adopt as the setup-side input; it does not teach the person |
| Anthropic AI Fluency Index | 9,830 Claude.ai conversations, 11 binary behaviour classifiers | population baseline (e.g. only 15.8% question the AI's reasoning, 8.7% check facts) [28] | one-off report | descriptive, correlational | adopt the behaviour vocabulary as detector names |
| Microsoft 365 Copilot Prompt Coach | the prompt the user pastes | critique and a rewritten prompt; does not run it [29] | on demand | none published | study (a pull tool, not a mentor) |
| PromptPilot (research) | the prompt being written | interactive guidance before sending | per prompt | RCT, n = 80: task score 78.3 vs 61.7, d = 0.56 [30] | study (shows prompt guidance can work in the moment) |
| Prompt Sensei (open source) | Claude Code / Codex prompts, optional local history | a score out of 100, the stage, one tip, a rewrite, one habit [31] | live or on demand | none | avoid the score; adopt "one habit" and local-first |
| Claude Code Learning / Explanatory output styles | the current task | inline insights; Learning mode leaves `TODO(human)` for the user to write [32] | inline | none published | adopt for the frontend novice side, inside the working session |

No product was found that reads a person's own coding-agent transcripts and coaches their briefing and delegation over weeks. The closest are `/insights` (setup-facing), Prompt Sensei (prompt-facing, small project) and the AI Fluency Index (population, not personal).

## 2. Learning science that should shape the mentor

| Finding | Evidence quality | Design implication for a weekly digest |
|---|---|---|
| Reflective practice: professionals improve by reflecting on action after the fact [33] | influential theory; a systematic review found the empirical evidence for reflection's effect thin and mostly descriptive [34] | reflection alone is not enough; structure it |
| Structured debriefs / after-event reviews improve later performance, d = 0.67 [1]; reviewing successes as well as failures beats failures only [35] | meta-analysis, 46 samples; experiments | the letter is a debrief: what happened, why, what to do next time; include one thing that worked |
| Deliberate practice: targeted practice with feedback on weaknesses [36]; explains about 12% of performance variance overall and under 1% in professions [37] | meta-analysis; effect small outside games, music, sport | do not promise "practice drills" will make a better manager of agents; pick narrow, repeatable skills (writing an acceptance criterion) |
| Self-explanation improves learning, g = 0.55 [38][39] | meta-analysis of 64 reports | ask the operator one "why did the agent misread this?" question rather than explaining it for them |
| Feedback works through four levels: task, process, self-regulation, self; feedback about the self is least effective [3]; mean effect d = 0.48, larger for high-information feedback, smallest for praise and rewards [40] | meta-analyses | each item names the task and the process; no praise of the person, no grades |
| Feedback-intervention theory: about a third of feedback interventions lowered performance; feedback that draws attention to the self rather than the task does harm [2] | meta-analysis of 607 effects | never "you are vague"; always "this brief had no done-condition, and the agent stopped early" |
| Guidance hypothesis: frequent, immediate feedback aids practice and impairs retention; reduced and faded feedback learns better [4] | motor-learning literature, replicated widely | no per-prompt live coaching from the mentor; low frequency, fading as a habit stabilises |
| Practice testing and distributed practice rate "high utility" [7]; retrieval beats restudy, g = 0.50 [41]; the optimal spacing gap grows with how long the item must be kept [42] | strong, replicated | terms go to flashcards on a scheduler, not into prose re-read weekly |
| Zone of proximal development and scaffolding that fades [43] | classic, widely applied | teach the next concept just beyond what the operator already uses; drop a scaffold once the behaviour appears unprompted |
| Cognitive load: novices need guidance [44]; worked examples help novices [45]; the expertise reversal effect makes the same guidance redundant or harmful for experts [46] | strong, replicated | keep a per-domain level: worked rewrites for frontend briefs, short pointers or a problem to solve for Python architecture |
| Concept before name: telling works best after the learner has met the concept in cases [6]; an attempt before the answer improves retention (pretesting effect) [47] | experiments | detect when the operator described a concept in their own words, then give the name next to their words; the flashcard front is their own phrasing |
| Self-assessment of AI help is unreliable: experienced developers expected a 24% speed-up, were 19% slower, and still believed they had been faster [48] | RCT, n = 16 | ground every claim in a quoted excerpt and an outcome, not the operator's or the model's impression |

On the ratio of positive to corrective feedback: no defensible number was found for this setting; the evidence above supports specific corrective feedback plus one named success [35], not a fixed ratio.

## 3. What to detect in briefs and prompts

Prompt-engineering sources agree on the core of an effective instruction: be clear and specific, give examples, state the format and constraints, give context and a role [49][50][51]. For coding agents, the documented failures are not telling the agent what it cannot see, not saying what "fixed" looks like, and correcting the same thing a third time instead of starting over [9]. For delegation to agents, a subagent needs "an objective, an output format, guidance on the tools and sources to use, and clear task boundaries" [52]; delegation is also a transfer of authority with verification attached, not just a task split [53]. Non-experts over-generalise from single failures and rarely add examples [54]; this operator is an expert, so the expected gaps are terminology outside their home domain and briefs that assume shared context.

| # | Detector | Signal (from the transcript) | False-positive risk | Source |
|---|---|---|---|---|
| D1 | Re-stated rule | the same instruction, clustered by meaning, appears as a correction in two or more sessions | medium: two projects may legitimately differ; hand off to the setup loop first | [9][27] |
| D2 | Missing acceptance criterion | a task brief with no done-condition (test, check, example output, "done when"), followed by a redo or "not what I meant" | high without the outcome check: exploratory prompts are fine vague [9] | [9][52][53] |
| D3 | Terminology gap | a descriptive phrase that matches a glossary definition while the term itself is absent (reverse-dictionary lookup [55]), weighted up when the agent misread it | medium: the operator may avoid jargon on purpose; teach only when the name unlocks docs, libraries or a better agent reading | [6][55] |
| D4 | Ambiguous referent | "it", "that one", "the report" at the start of a brief or after a compaction, confirmed by a clarifying question or a wrong-target edit | high without confirmation; count confirmed cases only | [56][57] |
| D5 | Missing context | the agent spends its first calls discovering something the operator then supplies ("it's in X", "we use Y") | low to medium | [9][28] |
| D6 | Over-specification | many step-level imperatives or hard-coded procedures for routine work, or interrupts during routine steps | medium: deploys and irreversible steps should be spelled out | [58][59][60] |
| D7 | Mis-levelled delegation | a taste or irreversible decision delegated with no criteria (then rejected on taste), or routine work kept and done by hand | medium | [53][60][28] |
| D8 | Unverified acceptance | a polished artifact accepted or merged with no test, review or question turn | high: verification may happen outside the chat, as the Fluency Index itself notes | [28][61] |

Each detector should also report its inverse (a brief that did it well), so the letter can name one success [35]. No validated prompt-quality classifier for agentic coding briefs was found; the AI Fluency Index classifiers are the nearest published instrument and were validated only on Claude.ai chat [28].

## 4. Risks and ethics

- **Deskilling and cognitive offloading.** The MIT EEG preprint reported weaker engagement and recall in essay writers using ChatGPT [62], but it has 54 participants, is not peer-reviewed, and a formal comment argues for more conservative readings and flags an internal inconsistency [63]. Stronger evidence: in an RCT, AI help on a new library lowered quiz mastery from 67% to 50% (d = 0.74) without a significant speed gain, and the users who asked conceptual questions kept their learning [13]; a high-school field experiment found a 17% grade drop after access to an unguarded tutor was removed, largely avoided by a tutor designed to protect learning [14]. A survey of 319 knowledge workers found that higher confidence in the AI went with less critical thinking [61]; students delegate much higher-order work ("Creating" 39.8%, "Analyzing" 30.2% of responses) [64]; offloading is a general cognitive strategy with costs and benefits [65]. Implication: the mentor asks and points, it does not write the operator's next brief.
- **Sycophancy and flattery.** Models tailor feedback to the user's stated views [10]; a production model update was rolled back for it [66]. Implication: no praise of the person, quote evidence, include the counter-case, and let the operator mark items wrong.
- **The mentor optimising the person toward the model.** LLM judges favour their own generations [11]; AI writing suggestions homogenise style toward a Western norm [12]; co-writing with a feedback-tuned model reduces content diversity [67]. Implication: a detector fires on an outcome (a redo, a misread), never on "the model would have phrased it differently"; the operator's own style is not a defect.
- **Self-surveillance and quantified-self fatigue.** Measuring an activity can reduce enjoyment of it and of continuing it [68]; people lapse from and resume self-tracking [69]. Implication: no streaks, scores or dashboards; a skipped week is normal; a lapse is not reported back as a failure.
- **Privacy of the transcript-derived profile.** LLMs infer personal attributes from text with high accuracy [70]; Anthropic's own population analyses run through a privacy-preserving summariser [71]. Implication: keep the profile local and private (as Viva keeps reflections private [23]), store behaviours rather than traits, never infer sensitive categories, and never publish letters or quote private sessions in public repos.
- **Context separation.** The mentor's profile must not leak into the working agents' prompts; a working agent that "knows" the operator is weak at X will hedge and over-explain. The open learner model literature argues the learner should see and correct the model held of them [15].

## 5. Output formats and cadence

| Format | Evidence | Verdict |
|---|---|---|
| Weekly letter (debrief): 2–3 items, each excerpt → outcome → better version → one question; one success | debriefs d = 0.67 [1]; task/process feedback [3]; limited dose [5] | adopt (primary) |
| Flashcards for terms, scheduled by FSRS, front in the operator's own words | testing and spacing [7][41][42]; concept-first [6] | adopt (terms only, few per week) |
| Personal glossary (term, the operator's phrasing, the definition, where it came up) | no direct outcome evidence; it is the substrate for D3 and the flashcards | adopt (as a store) |
| Inline "you could have said…" rewrite | worked examples help novices, hurt experts [45][46]; live per-prompt feedback impairs retention [4]; guided prompt help improved task scores in the moment [30] | adopt inside the letter, levelled per domain; avoid live |
| Skills tree with levels / scores | gamification g = 0.49 for cognitive outcomes, mostly students [72]; expected rewards undermine intrinsic motivation [73]; self-level feedback [2] | avoid |

Cadence: "daily is noise" is supported indirectly (per-trial feedback impairs retention [4]; feedback volume overloads [5]). "Monthly loses context" cannot be verified: no study comparing weekly and monthly digests for adult professionals was found, and debrief research ties reviews to events, not calendars [1]. Weekly is an estimate that matches the industry digests (Grammarly [18], WakaTime [24]) and keeps excerpts recent enough to recall; the flashcards follow their own schedule, not the letter's. A sensible variant (estimate): weekly by default, skipped when no detector crossed its threshold, with `/insights`-style 30-day setup reviews kept separate.

## Terminology

Reflective practice; after-action review / after-event review / debrief; personal informatics and its stage model [74]; reflective informatics [75]; lived informatics [69]; open (scrutable) learner model [15]; conversation intelligence; feedback intervention and feedback levels [2][3]; guidance hypothesis [4]; expertise reversal effect [46]; cognitive offloading [65]; AI fluency and the 4D framework [28]; sycophancy [10]; self-preference bias [11]; task-relevant maturity (delegation) [60]; intelligent delegation [53]; reverse dictionary [55].

## Not asked, but important

- **The operator is an expert in one domain and a novice in another.** Expertise reversal means one mentor voice for both is wrong: keep a level per domain [46], and expect the most resistance where the operator is strongest [5].
- **The mentor's judgments are LLM-as-judge judgments.** Calibrate each detector against a small set of the operator's own labels before trusting it, and measure the mentor by whether confirmed detector rates fall over months, not by whether letters are read. A detector rate that falls because briefs got longer and more rigid is a regression (D6).
- **Most findings are setup findings.** A repeated correction usually means a missing rule, skill or hook; mentoring the person about it before fixing the setup blames the wrong party.

## Open questions

- Which detectors survive a calibration pass on the operator's own labels, and at what threshold? (Needs a labelled sample of perhaps 50–100 briefs; estimate.)
- Should the letter be read-only, or should replies ("this item is wrong") feed the glossary and the detector thresholds? The open-learner-model literature favours the latter [15].
- Where is the line between a setup finding and a person finding when the same correction recurs after a rule was added?
- Does the mentor run per machine and merge, or over a merged corpus? The privacy rule above prefers local runs.
- Is there any measurable change in briefing behaviour after 8–12 letters? No baseline exists; the first letters should record one.

## REFERENCES

1. [Tannenbaum SI, Cerasoli CP. Do team and individual debriefs enhance performance? A meta-analysis. Human Factors 2013;55(1)](https://pubmed.ncbi.nlm.nih.gov/23516804/)
2. [Kluger AN, DeNisi A. The effects of feedback interventions on performance. Psychological Bulletin 1996;119(2)](https://doi.org/10.1037/0033-2909.119.2.254)
3. [Hattie J, Timperley H. The power of feedback. Review of Educational Research 2007;77(1)](https://doi.org/10.3102/003465430298487)
4. [Salmoni AW, Schmidt RA, Walter CB. Knowledge of results and motor learning: a review and critical reappraisal. Psychological Bulletin 1984;95(3)](https://doi.org/10.1037/0033-2909.95.3.355)
5. [Luo X, Qin MS, Fang Z, Qu Z. Artificial intelligence coaches for sales agents: caveats and solutions. Journal of Marketing 2021;85(2)](https://doi.org/10.1177/0022242920956676)
6. [Schwartz DL, Bransford JD. A time for telling. Cognition and Instruction 1998;16(4)](https://doi.org/10.1207/s1532690xci1604_4)
7. [Dunlosky J et al. Improving students' learning with effective learning techniques. Psychological Science in the Public Interest 2013;14(1)](https://doi.org/10.1177/1529100612453266)
8. [Expertium. Benchmark of spaced repetition algorithms (FSRS)](https://expertium.github.io/Benchmark.html)
9. [Anthropic. Best practices for Claude Code](https://code.claude.com/docs/en/best-practices)
10. [Sharma M et al. Towards understanding sycophancy in language models. arXiv:2310.13548](https://arxiv.org/abs/2310.13548)
11. [Panickssery A, Bowman SR, Feng S. LLM evaluators recognize and favor their own generations. arXiv:2404.13076](https://arxiv.org/abs/2404.13076)
12. [Agarwal D, Naaman M, Vashistha A. AI suggestions homogenize writing toward Western styles and diminish cultural nuances. arXiv:2409.11360](https://arxiv.org/abs/2409.11360)
13. [Anthropic. How AI assistance impacts the formation of coding skills (2026); paper arXiv:2601.20245](https://arxiv.org/abs/2601.20245)
14. [Bastani H et al. Generative AI without guardrails can harm learning: evidence from high school mathematics. PNAS 2025;122(26)](https://doi.org/10.1073/pnas.2422633122)
15. [Bull S, Kay J. SMILI: a framework for interfaces to learning data in open learner models. IJAIED 2016](https://doi.org/10.1007/s40593-015-0090-8)
16. [Gong Labs. Taking the guesswork out of sales call effectiveness (vendor analysis)](https://www.gong.io/resources/labs/taking-the-guesswork-out-of-sales-call-effectiveness/)
17. [Brynjolfsson E, Li D, Raymond L. Generative AI at work. Quarterly Journal of Economics 2025](https://doi.org/10.1093/qje/qjae044)
18. [Grammarly Support. How do you create the weekly Grammarly Insights reports](https://support.grammarly.com/hc/en-us/articles/360003816132-How-do-you-create-the-weekly-Grammarly-Insights-reports-I-get-in-my-email)
19. [Fleckenstein J, Liebenow LW, Meyer J. Automated feedback and writing: a multi-level meta-analysis. Frontiers in AI 2023](https://doi.org/10.3389/frai.2023.1162454)
20. [Toastmasters Magazine. Introducing Yoodli (2023)](https://www.toastmasters.org/magazine/magazine-issues/2023/jan/introducing-yoodli)
21. [Poised homepage (shutdown notice)](https://poised.com/)
22. [Perceptyx. Perceptyx acquires behavioral science pioneer Humu (2023)](https://blog.perceptyx.com/perceptyx-acquires-behavioral-science-pioneer-humu-to-close-the-gap-between-employee-insights-and-action)
23. [Microsoft Support. Personal insights in Viva Insights](https://support.microsoft.com/en-us/viva/insights/personal-insights-in-viva-insights)
24. [WakaTime](https://wakatime.com/)
25. [GitHub Docs. About Copilot usage metrics](https://docs.github.com/en/copilot/concepts/copilot-usage-metrics/copilot-metrics)
26. [Settles B, Meeder B. A trainable spaced repetition model for language learning. ACL 2016](https://aclanthology.org/P16-1174/)
27. [Anthropic. Claude Code commands reference (/insights)](https://code.claude.com/docs/en/commands)
28. [Anthropic. The AI Fluency Index (2026)](https://academy.claude.com/tutorials/the-ai-fluency-index)
29. [Microsoft Learn. Prompt Coach agent template](https://learn.microsoft.com/en-us/microsoft-365-copilot/extensibility/agent-builder-template-prompt-coach)
30. [PromptPilot: improving human-AI collaboration through LLM-enhanced prompt engineering. ICIS 2025; arXiv:2510.00555](https://arxiv.org/abs/2510.00555)
31. [Prompt Sensei (GitHub)](https://github.com/chengzhongwei/Prompt-sensei)
32. [Anthropic. Claude Code output styles](https://code.claude.com/docs/en/output-styles)
33. [Donald Schön, The Reflective Practitioner (1983)](https://en.wikipedia.org/wiki/Donald_Sch%C3%B6n)
34. [Mann K, Gordon J, MacLeod A. Reflection and reflective practice in health professions education: a systematic review. Adv Health Sci Educ 2009](https://doi.org/10.1007/s10459-007-9090-2)
35. [Ellis S, Davidi I. After-event reviews: drawing lessons from successful and failed experience. J Applied Psychology 2005;90(5)](https://doi.org/10.1037/0021-9010.90.5.857)
36. [Ericsson KA, Krampe RT, Tesch-Römer C. The role of deliberate practice in the acquisition of expert performance. Psychological Review 1993;100(3)](https://doi.org/10.1037/0033-295X.100.3.363)
37. [Macnamara BN, Hambrick DZ, Oswald FL. Deliberate practice and performance in music, games, sports, education, and professions: a meta-analysis. Psychological Science 2014](https://doi.org/10.1177/0956797614535810)
38. [Chi MTH et al. Self-explanations: how students study and use examples in learning to solve problems. Cognitive Science 1989](https://doi.org/10.1207/s15516709cog1302_1)
39. [Bisra K et al. Inducing self-explanation: a meta-analysis. Educational Psychology Review 2018](https://doi.org/10.1007/s10648-018-9434-x)
40. [Wisniewski B, Zierer K, Hattie J. The power of feedback revisited: a meta-analysis. Frontiers in Psychology 2020](https://doi.org/10.3389/fpsyg.2019.03087)
41. [Rowland CA. The effect of testing versus restudy on retention: a meta-analytic review. Psychological Bulletin 2014](https://doi.org/10.1037/a0037559)
42. [Cepeda NJ et al. Spacing effects in learning: a temporal ridgeline of optimal retention. Psychological Science 2008](https://doi.org/10.1111/j.1467-9280.2008.02209.x)
43. [Wood D, Bruner JS, Ross G. The role of tutoring in problem solving. J Child Psychology and Psychiatry 1976](https://doi.org/10.1111/j.1469-7610.1976.tb00381.x)
44. [Sweller J. Cognitive load during problem solving: effects on learning. Cognitive Science 1988](https://doi.org/10.1207/s15516709cog1202_4)
45. [Atkinson RK, Derry SJ, Renkl A, Wortham D. Learning from examples: instructional principles from the worked examples research. Review of Educational Research 2000](https://doi.org/10.3102/00346543070002181)
46. [Kalyuga S, Ayres P, Chandler P, Sweller J. The expertise reversal effect. Educational Psychologist 2003](https://doi.org/10.1207/S15326985EP3801_4)
47. [Richland LE, Kornell N, Kao LS. The pretesting effect: do unsuccessful retrieval attempts enhance learning? J Exp Psych: Applied 2009](https://doi.org/10.1037/a0016496)
48. [Becker J et al. (METR). Measuring the impact of early-2025 AI on experienced open-source developer productivity. arXiv:2507.09089](https://arxiv.org/abs/2507.09089)
49. [Anthropic. Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)
50. [OpenAI. GPT-5 prompting guide](https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide)
51. [Schulhoff S et al. The Prompt Report: a systematic survey of prompt engineering techniques. arXiv:2406.06608](https://arxiv.org/abs/2406.06608)
52. [Anthropic Engineering. How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
53. [Tomašev N, Franklin M, Osindero S. Intelligent AI delegation. arXiv:2602.11865](https://arxiv.org/abs/2602.11865)
54. [Zamfirescu-Pereira JD et al. Why Johnny can't prompt: how non-AI experts try (and fail) to design LLM prompts. CHI 2023](https://doi.org/10.1145/3544548.3581388)
55. [Hill F, Cho K, Korhonen A, Bengio Y. Learning to understand phrases by embedding the dictionary. TACL 2016](https://doi.org/10.1162/tacl_a_00080)
56. [Zhang MJQ, Choi E. Clarify when necessary: resolving ambiguity through interaction with LMs. arXiv:2311.09469](https://arxiv.org/abs/2311.09469)
57. [Mu F et al. ClarifyGPT: empowering LLM-based code generation with intention clarification. arXiv:2310.10996](https://arxiv.org/abs/2310.10996)
58. [Anthropic Engineering. Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
59. [Jaroslawicz D et al. How many instructions can LLMs follow at once? arXiv:2507.11538](https://arxiv.org/abs/2507.11538)
60. [Grove AS. High Output Management (1983): task-relevant maturity](https://en.wikipedia.org/wiki/High_Output_Management)
61. [Lee HP et al. The impact of generative AI on critical thinking: self-reported reductions in cognitive effort and confidence effects from a survey of knowledge workers. CHI 2025](https://doi.org/10.1145/3706598.3713778)
62. [Kosmyna N et al. Your brain on ChatGPT: accumulation of cognitive debt when using an AI assistant for essay writing task. arXiv:2506.08872](https://arxiv.org/abs/2506.08872)
63. [Stanković M et al. Comment on: Your brain on ChatGPT. arXiv:2601.00856](https://arxiv.org/abs/2601.00856)
64. [Anthropic. Anthropic Education Report: how university students use Claude (2025)](https://www.anthropic.com/news/anthropic-education-report-how-university-students-use-claude)
65. [Risko EF, Gilbert SJ. Cognitive offloading. Trends in Cognitive Sciences 2016](https://doi.org/10.1016/j.tics.2016.07.002)
66. [OpenAI. Sycophancy in GPT-4o: what happened and what we're doing about it (2025)](https://openai.com/index/sycophancy-in-gpt-4o/)
67. [Padmakumar V, He H. Does writing with language models reduce content diversity? arXiv:2309.05196](https://arxiv.org/abs/2309.05196)
68. [Etkin J. The hidden cost of personal quantification. Journal of Consumer Research 2016](https://doi.org/10.1093/jcr/ucv095)
69. [Epstein DA et al. A lived informatics model of personal informatics. UbiComp 2015](https://doi.org/10.1145/2750858.2804250)
70. [Staab R et al. Beyond memorization: violating privacy via inference with large language models. arXiv:2310.07298](https://arxiv.org/abs/2310.07298)
71. [Tamkin A et al. Clio: privacy-preserving insights into real-world AI use. arXiv:2412.13678](https://arxiv.org/abs/2412.13678)
72. [Sailer M, Homner L. The gamification of learning: a meta-analysis. Educational Psychology Review 2020](https://doi.org/10.1007/s10648-019-09498-w)
73. [Deci EL, Koestner R, Ryan RM. A meta-analytic review of experiments examining the effects of extrinsic rewards on intrinsic motivation. Psychological Bulletin 1999](https://doi.org/10.1037/0033-2909.125.6.627)
74. [Li I, Dey A, Forlizzi J. A stage-based model of personal informatics systems. CHI 2010](https://doi.org/10.1145/1753326.1753409)
75. [Baumer EPS. Reflective informatics: conceptual dimensions for designing technologies of reflection. CHI 2015](https://doi.org/10.1145/2702123.2702234)
