# opsward.decisions

Decision capture: numbered ADRs, the one-line decision log, and their drift.

Two tiers, per ADR 0010 and `misc/docs/research/adr_and_home_finding.md`: a
trivial or medium decision is one **Y-statement** line appended to `decisions/log.md`
(“In the context of …, facing …, we decided for …, to achieve …, accepting …,
because …”); a load-bearing, expensive-to-reverse one is a numbered **MADR** file
`decisions/NNNN-slug.md` that is never edited once accepted, only superseded.

Pure functions here; the CLI (`opsward decision new|note`) is the only writer, and
it never overwrites. `maintain` uses [`check_decisions()`](#opsward.decisions.check_decisions) to report an ADR that
cites a path which no longer exists, or that has no Status, which is how rot shows up.

### Functions

| [`adr_files`](#opsward.decisions.adr_files)(decisions_dir)                         | The numbered ADR files in *decisions_dir*, in number order (the template is not one).                                                                   |
|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`check_decisions`](#opsward.decisions.check_decisions)(sr)                              | `maintain` check: ADRs citing paths that no longer exist, or carrying no status.                                                                        |
| [`cited_paths`](#opsward.decisions.cited_paths)(content)                             | Paths an ADR cites as current, outside fenced code: bare path tokens and Markdown link targets (relative ones only; URLs and host names are not paths). |
| [`clean_title`](#opsward.decisions.clean_title)(title)                               | One line, single-spaced; empty is an error the CLI reports.                                                                                             |
| [`decision_docs`](#opsward.decisions.decision_docs)(sr)                                | The ADRs a scan found (`ScanResult.decisions`), numbered files only.                                                                                    |
| [`log_append`](#opsward.decisions.log_append)(decisions_dir, text, \*[, date])      | The log file and the full content it should hold after appending *text*.                                                                                |
| [`log_entry`](#opsward.decisions.log_entry)(text, \*[, date])                      | One Y-statement line for `decisions/log.md`.                                                                                                            |
| [`new_adr`](#opsward.decisions.new_adr)(decisions_dir, title, \*[, status, ...]) | The next numbered ADR for *title*, rendered from the `adr.md` template.                                                                                 |
| [`next_number`](#opsward.decisions.next_number)(decisions_dir)                       | One more than the highest numbered ADR, so numbers never collide (1 for an empty dir).                                                                  |
| [`slugify`](#opsward.decisions.slugify)(title)                                   | A file-name slug: lowercase, hyphens, nothing else, at most 60 characters.                                                                              |
| [`status_of`](#opsward.decisions.status_of)(content)                               | The ADR's status text, from a `## Status` heading, a `**Status:**` line or MADR front matter; `None` when there is none.                                |

### opsward.decisions.adr_files(decisions_dir)

The numbered ADR files in *decisions_dir*, in number order (the template is not one).

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]

### opsward.decisions.check_decisions(sr)

`maintain` check: ADRs citing paths that no longer exist, or carrying no status.

Rot in a decision record is a path that moved: the rationale still reads well and
points at nothing. Superseded, deprecated and rejected ADRs are history and are not
checked for paths: the superseding record is where the current paths live. This
reports; it never rewrites an accepted ADR (ADR 0010).

* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`MaintenanceSuggestion`](opsward.base.html.md#opsward.base.MaintenanceSuggestion)]

### opsward.decisions.cited_paths(content)

Paths an ADR cites as current, outside fenced code: bare path tokens and Markdown
link targets (relative ones only; URLs and host names are not paths).

A path the record cites as history is not checked: wrap it in `~~strikethrough~~`,
or say so on the line (`formerly`, `previously`, `moved`, `migrated`,
`renamed`, `replaced`, `removed`, `retired`, `deleted`), as in “we moved `pkg/old.py` to `pkg/new.py`” — there
only `pkg/new.py` must exist.

```pycon
>>> cited_paths("See `pkg/a.py`, [0002](0002-x.md), [doc](../research/r.md), https://x.io/a/b.py, docs.github.com/en/x.md\n```\nsrc/in/fence.py\n```")
['../research/r.md', '0002-x.md', 'pkg/a.py']
>>> cited_paths("We moved `pkg/old.py` to `pkg/new.py`; ~~`pkg/gone.py`~~ is history.")
['pkg/new.py']
>>> cited_paths("It was read from `pkg/live.py`.\nRenamed [old](../old.md) to [new](../new.md).")
['../new.md', 'pkg/live.py']
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### opsward.decisions.clean_title(title)

One line, single-spaced; empty is an error the CLI reports.

```pycon
>>> clean_title("  two\n lines ")
'two lines'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.decisions.decision_docs(sr)

The ADRs a scan found (`ScanResult.decisions`), numbered files only.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`DocSpec`](opsward.base.html.md#opsward.base.DocSpec)]

### opsward.decisions.log_append(decisions_dir, text, , date=None)

The log file and the full content it should hold after appending *text*.

A missing log starts from the `log.md` template. The existing log is read
strictly: an unreadable or non-UTF-8 log raises (`OSError` /
`UnicodeDecodeError`) rather than being replaced by the new line alone. The
caller writes; this does not.

* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### opsward.decisions.log_entry(text, , date=None)

One Y-statement line for `decisions/log.md`.

```pycon
>>> log_entry("In the context of goldens, facing drift, we decided for pinning.", date=_dt.date(2026, 10, 19))
'- 2026-10-19 — In the context of goldens, facing drift, we decided for pinning.'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.decisions.new_adr(decisions_dir, title, , status='Proposed', date=None, evidence='')

The next numbered ADR for *title*, rendered from the `adr.md` template.

*evidence* is the issue, discussion or PR the decision rests on (a URL or `#N`);
it lands in the Evidence section so the three surfaces stay linked.

```pycon
>>> import tempfile
>>> gf = new_adr(Path(tempfile.mkdtemp()), "Pin the CLI surface", date=_dt.date(2026, 10, 19), evidence="#8")
>>> gf.target_path.name, gf.content.splitlines()[0]
('0001-pin-the-cli-surface.md', '# 0001 — Pin the CLI surface')
```

* **Return type:**
  [`GeneratedFile`](opsward.base.html.md#opsward.base.GeneratedFile)

### opsward.decisions.next_number(decisions_dir)

One more than the highest numbered ADR, so numbers never collide (1 for an empty dir).

```pycon
>>> import tempfile
>>> next_number(Path(tempfile.mkdtemp()))
1
```

* **Return type:**
  [`int`](https://docs.python.org/3/builtins/functions.html#int)

### opsward.decisions.slugify(title)

A file-name slug: lowercase, hyphens, nothing else, at most 60 characters.

```pycon
>>> slugify("Pin the CLI surface by goldens!")
'pin-the-cli-surface-by-goldens'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### opsward.decisions.status_of(content)

The ADR’s status text, from a `## Status` heading, a `**Status:**` line or
MADR front matter; `None` when there is none.

```pycon
>>> status_of("# x\n\n## Status\n\nAccepted (2026-01-01)\n")
'Accepted (2026-01-01)'
>>> status_of("---\nstatus: accepted\n---\n# x\n"), status_of("**Status:** Superseded by 0003"), status_of("# x\nno status")
('accepted', 'Superseded by 0003', None)
```

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
