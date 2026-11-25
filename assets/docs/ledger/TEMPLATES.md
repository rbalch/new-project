# Entry templates

Not an entry: `make entries-check` and `make ledger` skip this file.

Two PRs that each log something add two different files, so nothing here is ever edited to add a
sighting. Counts come from `make ledger REFS=origin` after a fetch (the table in `build/ledger.md`), never from a line in a
finding: a finding's count is the number of `sights:` items naming it across the runs.
`make entries-check` fails on a bad file name, a duplicate id, a missing field, a wrong `kind` or `bin`, an id whose
MMDD is not the `date`, a slug that is not the slugified title, an id no finding defines, a subfolder or a non-`.md` file.
It needs `docs/ledger/README.md` plus the `findings/` and `runs/` folders.
A new finding is never only a `(new)` bullet in a run: it gets its own file. In text, write the full id.
A bare `F-MMDD` passes only while one finding has that prefix; a second finding that day turns it red.
Only F and H ids named in ledger bodies are checked. P ids, DEC ids and preference bodies are not.

For accepted limitations under `AGENTS.md`'s outside PR feedback policy, repeated
reports of the same unchanged case are decision updates, not fresh sightings toward
the rule of three. Use `updates:`, not `sights:`, in the new run. Preserve the original
scores and decision link; record any new evidence or explicit human override. The
ordinary sighting rules still apply to other findings. Acceptance does not itself
call for a task, issue, code change, or control.

## A new finding: `docs/ledger/findings/<id>.md`

The id is `F-MMDD-<slug>` (or `H-MMDD-<slug>` for a harness finding): the month and day, then the slug
of the title (lower case, `a-z0-9` and single dashes, 60 characters at most). The file is named exactly
`<id>.md`. Two branches collide only on the same day and slug, and git shows that as one add/add path.
Its first sighting is the run that logs it, so it
should arrive together with a run file that lists it in `sights:`. A finding no run sights counts 0.

```markdown
---
id: F-0115-sightings-per-round   # F-MMDD-<slug>; H-MMDD-<slug> for a harness finding
kind: finding                    # finding, or harness for an H id
title: 'Sightings per round'   # one line, quoted; the table prints it
date: '2026-01-15'               # quoted YYYY-MM-DD, the day it was first seen
bin: '2'                         # '1', '2' or '3'; null for a harness finding (never binned)
---
### F-0115-sightings-per-round — Sightings per round
- **Date:** 2026-01-15 (T-02)     <!-- when and where it was seen -->
- **Bin:** 2                      <!-- 1 linter covers it, 2 systemic and checkable, 3 taste -->
- **Claim:** <the dislike, stated so a machine could check it>
- **Action:** soft — noted, no control yet   <!-- or: DEC-N, a control authored -->
- **Notes:** <anything surprising about the harness itself>
<!-- For outside PR feedback, add these body fields; not new frontmatter fields. -->
- **Risk:** L<n> (<reason>) × I<n> (<reason>) = <product>; exception: <none or reason>
- **Evidence:** <trigger, supported-use evidence, actual consequence>
- **Decision:** <fix / accept limitation / decline / needs human>; <thread link>
- **Reopened:** <new evidence or explicit human override, if any>
```

## A new run: `docs/ledger/runs/<date>-<slug>.md`

One run file per triage run. `<date>` equals the frontmatter `date`, and `<slug>` is the slug of the
title, so the file is named `2026-01-15-t-02-12-triage.md` for the title `T-02 (#12) triage`.
Two PRs collide only on the same date and title.

```markdown
---
date: '2026-01-15'               # quoted YYYY-MM-DD, the day of the run
title: 'T-02 (#12) triage'       # one line, quoted; the file name is its slug
updates: [F-0115-sightings-per-round]   # finding ids this run adds a note to; [] if none
sights: [F-0115-sightings-per-round]   # one item per independent sighting; a finding seen in two review rounds is listed twice
---
### T-02 (#12) triage
- F-0115-sightings-per-round: <what was seen, and where>
- **Preferences:** the preference ids added, or none   <!-- optional: a preference this run distilled -->
```

Every id in `updates` and `sights` must be defined by a finding file. Never edit an existing finding or
run to add a sighting: write a new run.
