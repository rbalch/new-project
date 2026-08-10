---
name: build-loop
description: The build→review→triage loop for this repo. Dispatch a builder subagent, two reviewer subagents, bounce findings until the review approves at 4/5 or better, then triage the findings so recurring ones can graduate to CI-enforced controls. Use when implementing a milestone, spec item, or scoped work item.
---

# The build loop

You are the orchestrator. **You do not write the feature code yourself** — you brief
subagents, judge what comes back, and decide. Tiny hotfixes you fully understand are
allowed, but hand them to the reviewer in the next round rather than absorbing them
silently.

```
ORCHESTRATOR (you, in this context)
  │
  │   ┌───────────────────────────── the loop ─────────────────────────────┐
  ├──▶│ builder             writes code, ends on `make check` = 0           │
  ├──▶│ boundary-reviewer   live rules + this project's architectural seams │
  ├──▶│ reviewer            correctness, tests, maintainability             │
  └──◀│ findings → builder → re-review → APPROVE and score ≥ 4/5           │
      └─────────────────────────────────────────────────────────────────────┘
  │
  ▼  ═══ loop closed. The rest is what makes this a ledger repo. ═══
  │
  ├─ triage every finding        Bin 1 / Bin 2 / Bin 3
  ├─ log sightings               docs/ledger-findings.md
  ├─ Bin 2 at three sightings?   dispatch control-author
  ├─ make check
  └─ commit + Manual QA write-back
```

**One work item at a time.** Take the next incomplete item from the spec doc, run it
through the whole loop *including* the commit and the Manual-QA write-back, and only
then start the next. No parallel builders unless the human explicitly asks.

---

## 0. Before dispatching anything

Read:

- **The spec doc** named in the request — the milestone, phase, or design document the
  work item comes from. It is authoritative for scope.
- **`governance/views/RULES.md`** — the generated view of live rules. So you can
  recognise a rule violation in a report without re-deriving it. Never read
  `governance/decisions/` for rules; it retains superseded records on purpose.
- **`AGENTS.md`** — architecture and the contract.
- **`docs/ledger-findings.md`** — specifically the **sighting counts**. You cannot apply
  the rule of three without knowing what is already sitting at one or two.
- **`review.md` and `review.json`** at the repo root, if a prior round left them.

Extract before briefing: exact scope, explicit **non**-scope (later milestones, other
repos), acceptance criteria as runnable checks, environment facts a fresh agent cannot
know, and safety rules.

**Confirm `make check` is green before you start.** Starting on a red gate means you
will not be able to tell which failures you caused.

---

## 1. Builder dispatch

`Agent` tool, `subagent_type: builder`, **`model: sonnet`** by default. Reuse a previous
builder via `SendMessage` when its context is still warm — fix rounds are far cheaper
than fresh spawns.

The brief must contain:

- **Numbered scope items**, and explicit non-scope.
- **Environment facts**: where work happens, how deps are managed, the spec doc path,
  which files are safe to touch.
- **Safety rules**: what is real versus disposable, read-only versus mutable.
- **Secret hygiene**: never print a token; run a `grep -rE 'token|secret|key'` sweep over
  changed files and outputs as a *named verification*, not a promise.
- **A numbered verification list** with exact commands and expected exit codes.
  `make check` exit 0 is always on it.
- **Commit instructions**: small conventional commits, clean tree at the end.

Three ledger-specific additions:

- **`make views` after touching any decision.** The generated view and `registry.json`
  are derived from `governance/decisions/`. A stale one fails the *next* work item's
  gate for reasons that look unrelated to it.
- **Never re-record a `pragma: external` hash.** If a hashed config file changed, the
  builder reports it and *you* decide whether the decision still holds. A hash bumped
  without a human reading the diff turns that control into ceremony.
- **"Blocked by a rule" is a valid outcome, and you want it.** Ask for it explicitly. A
  builder reporting "DEC-3 stopped me splitting this sensibly" is producing the most
  valuable data this project collects. A builder that quietly works around a rule has
  corrupted the experiment and you will not find out for weeks.

Require a structured return: commit SHAs and messages, per-verification evidence
(**command output, not claims**), the `make check` exit code stated explicitly,
deviations with reasons, blocked-by-a-rule items, and follow-ups.

### Model escalation

Stay on Sonnet while it is working. Escalate that role to **`model: opus`** when the
same finding survives two fix rounds, the builder's "evidence" turns out false on
re-verification, or there are no forward commits after two attempts. Note the escalation
and why. Drop back to Sonnet for the next routine round.

---

## 2. Reviewer dispatch — two of them

Run both after the builder returns. They cover different ground and barely overlap.

- **`subagent_type: boundary-reviewer`, `model: sonnet`** — every live rule in
  `RULES.md` against the diff, citing `DEC-N`, plus this project's architectural seams
  as declared in `AGENTS.md`: dependency direction, secrets crossing a named boundary,
  module internals reached into, and control evasion.
- **`subagent_type: reviewer`, `model: sonnet`** — correctness, tests, contracts,
  failure directions, code shape. It owns `review.md` and `review.json`.

Both briefs must demand:

- **Verify by execution, not by reading.** Re-run the builder's key verifications
  independently, especially secret sweeps and negative paths.
- Findings with severity (`blocker` / `important` / `minor` / `nit`), `file:line`, and a
  concrete failure scenario for anything called a bug.
- Attention to: interface contracts (what one side emits and the other parses),
  **failure direction — ambiguity must fail closed, and a false success is always
  blocking**, secrets in outputs *and* artifacts, and regressions against
  previously-approved rounds.
- A verdict (`APPROVE` / `CHANGES_REQUESTED` / `NEEDS_HUMAN`) and a score out of 5.

`boundary-reviewer` reports but does not write the review record. Fold its findings in
yourself, or have `reviewer` absorb them next pass.

**A boundary finding citing a `DEC-N` is blocking, always.** Not a severity judgement —
CI will fail on it regardless of what anyone scores it.

Same escalation rule as the builder.

---

## 3. The loop

```
while verdict != APPROVE or score < 4 or any blocking/important findings remain:
    send findings → builder (SendMessage, warm context) as ONE numbered list,
        each with the required fix shape and how to re-verify
    builder fixes and returns evidence
    reviewers re-review the DELTAS (git show <fix-shas>), re-run what they can,
        update review.md / review.json marking findings resolved with SHAs
```

- Fold cheap minors and nits into fix rounds. Do not carry one-line debt into the next
  work item.
- At 4/5 with only minors left: one more polish round if the remainder is cheap. Accept
  4/5 only when the reviewer explicitly judges the leftovers acceptable by design. **5/5
  is the target.**
- Builder and reviewer disagree: **reviewer wins**, unless you can personally verify the
  reviewer is wrong — then say so in the brief, with evidence.
- **`NEEDS_HUMAN` stops the loop.** Do not iterate past it. Report and wait.

`make check` **fails fast at the first stage**, so a red gate shows only the earliest
failure, not all of them. Re-run the whole gate after each fix rather than assuming one
error was the only one.

---

## 4. Triage — the step that makes this a ledger repo

**After the verdict, before the commit. Not optional.**

Without it you have a good review loop that discards its own findings — which is exactly
the problem `docs/governance-harness.md` describes and this harness claims to solve. Fix
a finding and move on, and the next session repeats it and you review it again, forever.

Run each non-trivial finding through the three bins:

| Bin | What it means | What you do |
|---|---|---|
| **1** | An existing linter, formatter or type-checker covers it | Note it. If it recurs, tighten ruff — not the ledger. |
| **2** | A concrete, checkable, **systemic and cross-file** pattern | **Log a sighting.** This is the value. |
| **3** | Genuine subjective taste — "is this readable", "is this elegant" | Log it and say so plainly. Never manufacture a control. |

Line-level style is Bin 1. Bin 2 is what a linter cannot express and agents violate
confidently: layer A never imports layer B · no module reaches into another's internals
· dependencies flow one way · every handler passes through auth · secrets never cross a
named boundary.

Procedure per finding: restate the dislike as a checkable claim — **if you cannot state
it so a machine could check it, that is strong evidence for Bin 3** — then assign the
bin in one sentence with a reason, and log it in `docs/ledger-findings.md` with a
sighting count.

**Honest sorting matters more than control coverage.** A fat Bin 3 is a real result. If
nearly everything lands in Bin 1 or Bin 3 over the coming milestones, the harness is not
earning its keep, and saying so is the correct outcome — that is the experiment
returning a negative, not a failure.

Findings **already caught by an existing control are not new sightings** — that rule
already works. Note that it fired; that is evidence the ratchet is paying off.

---

## 5. Graduation — rare, and gated

Only when a Bin 2 finding reaches its **third** logged sighting: dispatch
`subagent_type: control-author`. It re-verifies the preconditions itself and refuses if
they do not hold. Let it refuse.

**Resist promoting early, including your own eagerness to be useful.** The pull is not
toward bad rules — it is toward *plausible* ones. That is what makes the rule of three
load-bearing rather than ceremonial.

**A control that fires on correct code is the most damaging failure available here**,
because it teaches everyone to route around the harness. Worse than the nit it was meant
to catch.

---

## 6. Completion — commit and Manual QA

1. **`make check` green.** Then ensure everything from the round is committed: builders
   commit as they go, so verify with `git status` and sweep up any hotfixes you made
   yourself. Conventional commit naming the work item. Never leave an approved work item
   uncommitted.

   If the round authored or changed a decision, the commit contains **all of it
   together** — decision, control, pragma, regenerated view and registry. That combined
   diff is the guardrail a human reviews. Splitting it defeats the point.

2. **Write "Manual QA" back to the spec doc.** Add or update a
   `## Manual QA — <work item>` section in the same document the work came from, so the
   human can verify it without reading code:
   - copy-pasteable commands with expected output and exit codes
   - what to look at with their own eyes, and what "correct" looks like
   - one or two cheap negative checks ("run it with X wrong → expect error Y")
   - any human-only gates left (credential setup, a real external flow, a host-side
     test) called out as such

   A checklist, not an essay.

---

## 7. Exit and report

Done when: verdict `APPROVE`, score ≥ 4/5, zero blocking or important findings open,
`review.md` / `review.json` carry the full round history, work committed, Manual QA
written, and the findings triaged.

Report, outcome first:

- Verdict and score, then the findings that mattered and their fixes, in plain language.
- Commit range.
- What remains: carried nits, human-only steps.
- Any model escalations and why.
- **Findings by bin, with running sighting counts.**
- **Anything that graduated to a control**, or is at two sightings and close.
- **Any rule the builder was blocked by**, and whether the rule or the code was wrong.
- **Whether `check_governance` caught anything real this round**, or only agreed with a
  green build. That question decides whether the harness is earning its keep.

---

## Hard rules

- **Never let a work item pass with a known path to exit-0-on-failure.**
- **Never edit code to evade a control**, and never accept a change that does. If a rule
  is wrong, supersede it: a new decision, the old one marked `superseded` with
  `superseded_by`, control and pragma retargeted, `make views`, all in one reviewable
  diff. Rule change is a human-gated act.
- **Never hand-edit `governance/views/**` or `governance/registry.json`.** They are
  generated. `make views` is the only way they change.
- Secrets never appear in briefs, outputs, commits, or artifacts. Every round
  re-verifies with a grep, not a promise.
- Human-gated steps are reported as gates, never simulated or skipped past.
- One work item at a time.
