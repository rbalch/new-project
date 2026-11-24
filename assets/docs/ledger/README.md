# Ledger findings

The experiment log. Every dislike of agent output gets sorted into a bin and recorded
here, whether or not it becomes a control. An unlogged finding is a lost data point.

- **Bin 1** — already covered by a linter or type-checker. The harness adds nothing.
- **Bin 2** — a concrete, checkable, systemic pattern. **This is the value.**
- **Bin 3** — genuine subjective taste. No control will ever catch it.

Rule of three: a Bin 2 finding stays in the soft layer (a note, a nudge, a one-off
correction) until its **third** sighting. Only then does it earn a decision and a
CI-enforced control.

**The falsifiable test:** if Bin 2 stays fat and review burden measurably shrinks, the
harness earns its keep. If nearly everything lands in Bin 1 or Bin 3, this is
complicated linters plus a wiki and we should say so and drop it. Do not judge it by
"does CI go red."

See the `finding-triage` skill for the procedure and the entry template.

**IDs.** An id is dated: `F-MMDD-<slug>` (`H-MMDD-<slug>` for a harness finding), the month and
day it was first seen and then its title's slug (`TEMPLATES.md`). So `F-0115-...` is not number 115, two findings
from the same day share the `F-0115` prefix, and the full id, slug included, is the one that must be unique. Dated ids
mean two parallel PRs never pick the same next number. `make entries-check` fails on a duplicate full id.

Findings about the **harness itself** — something it got wrong, friction that felt like
ceremony, a control that fired on correct code — are worth logging here too. Mark them
as harness findings and leave them unbinned; the bins sort dislikes of *agent output*,
and forcing a harness observation into one loses what makes it interesting.

---

## Entries

One file per entry: findings under `findings/`, triage runs under `runs/`. The formats are in
`TEMPLATES.md`. `make ledger` builds the sighting counts into `build/ledger.md`.
