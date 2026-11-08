# Prompts behind the `session-consumers-*` research reports

Stored so the reports can be re-run as deltas when the knowledge rots (see the design's refresh mechanism). Each prompt was given to a research subagent on 2026-11-08 with web access; re-run it with "today is <date>" and "your report is the DELTA since <date of the last report>". The reports' "What already exists (in-house)" sections list the earlier reports each one builds on.

| Report | Prompt | Model used |
|---|---|---|
| `../session-consumers-learning-from-sessions.md` | `session-consumers-learning-from-sessions.prompt.md` | Opus |
| `../session-consumers-improvement-loops.md` | `session-consumers-improvement-loops.prompt.md` | Opus |
| `../session-consumers-operator-mentoring.md` | `session-consumers-operator-mentoring.prompt.md` | Opus |
