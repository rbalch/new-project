# {project_name} — agent contract

<!-- TODO: one paragraph. What this project is, and the one sentence that explains
     why it is built the way it is. An agent reading only this file should know what
     it is working on. -->

This repo runs a ledger governance harness: architectural rules live as decisions,
each decision is backed by an executable control, and CI fails on drift. Read
`docs/governance-harness.md` once for why.

## Read this first

**Binding rules live in `governance/views/RULES.md`.** It is generated. Read it before
writing code. Every rule in it is enforced by CI; violating one fails the build.

**Never read `governance/decisions/` for rules.** It retains superseded records on
purpose. A superseded rule in your context steers you toward the exact pattern this
project abandoned. History is for humans; the view is for you.

> The generated view is `RULES.md`, not `AGENTS.md`, so it can never be confused with
> this file. This file is the contract — how to behave. That file is the rules — what
> is true. See DEC-0.

**This file is hand-written, and it never restates an enforced rule.** The narrow hazard
is copying a `DEC-N` rule here, where the copy drifts from its control and quietly
becomes a lie. The `Always` / `Never` lists below are the *shape* of the design, for
orientation. The enforced wording lives in the view, and the view wins on any
disagreement.

## The contract

- **Never edit code to evade a control.** If a rule blocks you and you think it is
  wrong, supersede it: author `DEC-N+1`, set the old decision to `status: superseded`
  with `superseded_by: DEC-N+1`, update the control and its pragma, run `make views`,
  commit it together. A human reviews that diff. Changing a rule is a visible act, never
  a silent code tweak.
- **New rules ship with controls.** A governing rule arrives with an executable control
  and its `governance: enforces DEC-N` pragma in the same change, or is explicitly
  marked `enforcement: warn` with a justification.
- **One behavior, one decision.** State a rule in exactly one decision and reference its
  ID elsewhere. Never restate a rule in two places.
- **Do not author rules speculatively.** When asked to add a rule, apply the triage in
  the `finding-triage` skill first. Most dislikes are already lintable or are pure
  taste; only the articulable, recurring middle earns a control. A refusal to write a
  brittle rule is worth more than coverage.

## How work gets done here

Two skills, in order. **`planner`** turns a conversation into a spec and task files.
**`orchestrate`** turns task files into reviewed, squashed PRs against the spec's epic
branch, merges them there, lands the epic on `develop`, and feeds every
finding into the ledger instead of letting it evaporate.

```
/planner                       you + the planner, until the plan is agreed
   └─▶ docs/specs/<slug>.md, tasks/<slug>/<PREFIX>-NN-*.md, docs/adr/ (only if alternatives were rejected)

/orchestrate tasks/<slug>      ORCHESTRATOR (you, on develop, never in a worktree)
  │   ┌───────────────────────────── one task ─────────────────────────────┐
  ├──▶│ builder (worktree)   codegraph init → acceptance tests RED → GREEN │
  ├──▶│ boundary-reviewer    live rules + this project's architectural seams│
  ├──▶│ reviewer             red-then-green proof, correctness, tests, shape│
  └──◀│ findings → you judge → builder → re-review → APPROVE, score ≥ 4/5  │
      │ squash to one commit → push → PR to the epic, or stacked on its dep │
      └───────────────────────────────────────────────────────────────────┘
  ▼  ═══ per task, after the PR is open. This is what makes it a ledger repo. ═══
  ├─ triage every finding → Bin 1 (lintable) / Bin 2 (systemic) / Bin 3 (taste)
  ├─ log sightings as new files under docs/ledger/ — orchestrator only, as its own PR on the chore chain
  ├─ a Bin 2 finding on its third sighting → control-author
  ├─ next task: dependencies merged, or stacked on their open PR's branch
  ├─ reviewed, CI green, Copilot handled → you merge the PR into the epic branch
  └─ at spec end, or sooner if it grows (~4–10 merged PRs, a guide) → a landing PR, epic → develop, the human approves
```

**Tests at the acceptance boundary come first.** The task file's acceptance criteria
become tests, committed alone, watched failing, before any implementation. The reviewer
checks out that commit and confirms the red. Unit tests below the boundary are the
builder's call. A criterion that turns out wrong is a planning finding for the human,
never a test to quietly rewrite.

**Every task has a Try it.** Steps a person runs on the branch, with the output they
should see. The builder runs them red then green, the reviewer re-runs them, the PR
opens with them and the builder's real output. Green tests with a failing Try it is not
done.

**Branches.** Each spec gets one epic branch, `epic-<slug>`, cut from `develop`. Work
lands on it by PR, one PR per task, one squashed commit per PR whose body says what
changed and why, and the orchestrator merges each one there once it is reviewed. A task
that depends on an open task stacks: it branches off that task's reviewed branch and
its PR targets it. Nothing builds on an unbuilt or unreviewed branch. The epic lands
on `develop` by a landing PR from the epic branch itself, at spec end or sooner if it grows
(`orchestrate` section 9 has the guide and the draft-landing exemption). Landing
PRs are the only PRs of the epic a human approves, reviewed for blockers only, rule and
security changes aside; push back on direction at the spec, before the build.
`develop` to `main` is a human's PR. The flow is in the `orchestrate` skill.

**The triage step is the point, and it is the one people skip.** A loop that fixes
findings and forgets them is exactly the problem the harness exists to solve: the
correction evaporates, the next session repeats it, and you review it again forever.
Skipping triage means running the experiment while discarding the data.

### The pieces

| | What it is for |
|---|---|
| `planner` (skill) | Plan with the human. Writes the spec, the task files, an ADR if earned. |
| `orchestrate` (skill) | Runs task files through build → review → PR → merge into the epic → triage → landing PR. Start here for any task. |
| `builder` (agent) | One task, in a worktree. Acceptance tests first. Never evades a control. |
| `boundary-reviewer` (agent) | Live rules and this project's architectural seams. Reports; never edits. |
| `reviewer` (agent) | Red-then-green proof, correctness, tests, maintainability. Owns `review.md` / `review.json`. |
| `pr-feedback` (skill) | Copilot threads on open PRs: judge, fix, restack the stack, reply, resolve, merge into the epic, triage. |
| `thread-judge` (agent) | One PR's Copilot threads: reproduce each, recommend fix or decline. Edits nothing. |
| `finding-triage` (skill) | Sort one dislike into a bin. Apply the rule of three. |
| `control-author` (agent) | Turn a thrice-sighted Bin 2 finding into a decision plus control. |
| `ledger-ops` (skill) | Harness mechanics: author, supersede, add a control, debug a red gate. |
| `tasks/README.md` | The task file format. |

### When not to use the loop

A one-line fix, a doc edit, or a question. The loop costs several subagent round-trips;
spending them on a typo is theatre. Run `make check` and commit. **But still triage
anything you disliked along the way** — sightings accumulate regardless of how the
change was made.

### Things that will bite you

- **`make check` fails fast.** A red gate reports only the *earliest* failing stage, not
  every failure. Re-run the whole gate after a fix rather than assuming one error was
  the only one.
- **Touched a decision? Run `make views`.** The view and `registry.json` are generated
  from `governance/decisions/`. A stale one fails the *next* task's gate for reasons
  that look unrelated to it.
- **Reviewers start in the root checkout, not the worktree.** Every reviewer brief
  opens with the worktree path. A gate run in the wrong tree reviews the wrong code.
- **Blocked by a rule is a valid, wanted outcome.** Say so and stop. Do not raise a
  threshold, delete a pragma, or reach for `# noqa`. Reporting it is the most useful
  thing you can do; working around it quietly corrupts the experiment and nobody finds
  out for weeks.

## Architectural shape

<!-- TODO: the diagram or the two paragraphs that explain how this system is put
     together, and which seams the controls exist to guard. An agent that does not
     understand the shape will violate it confidently. Replace the example below. -->

```
<layer A>  ──▶  <layer B>  ──▶  <layer C>
```

## Always

<!-- TODO: the shape of the design, for orientation. Never a restatement of a DEC-N
     rule — point at the view instead. Delete these examples. -->

- Keep the dependency direction one way.
- Put secrets behind the named abstraction, never in a repo file, a log line, or a
  response payload.

## Never

<!-- TODO: negative space is first-class. What must this project never do? -->

- Never hand-edit a generated file (`governance/views/**`, `governance/registry.json`).
- Never edit a control to make a failing change pass.

## Working context (keep this current)

<!-- TODO: this is the section that earns this file's existence — the background an
     agent cannot derive from the code. Why this project exists, what was tried and
     rejected, prior art being followed, the stack, known risks, what is out of scope,
     who the audience is, and what is being worked on right now. Convert relative dates
     to absolute. Delete a line the moment it stops being true; a stale working-context
     section is worse than an empty one. -->

**Origin.** Started {today} as {project_name}. <!-- TODO: what it grew from (a POC, an
     earlier system), and what may carry over from it. -->

**What is in flight** is not kept in this file: run `make tasks` for each plan's state, and read
`docs/specs/` for what each plan decided.

## Working rules

- **Decide unless torn.** Check the preferences first (`make preferences`, then read `build/preferences.md`); if one settles a choice,
  take it and cite it. Ask the human only when two options are close and no preference
  decides, or when the choice spends money, reaches people outside the team, or cannot be undone. Ask
  as multiple choice: one question per fork, two to four options, each with a one-line
  tradeoff, the recommended one first and labelled "(Recommended)", and say what makes it
  close. In Claude Code that is the `AskUserQuestion` tool; batch every open fork in one
  call.
- **Report every choice made alone.** The recap and the PR body each carry a *Choices
  made* list, one line per choice, citing the preference it followed if any. A preference
  that keeps producing choices the human reverses is wrong; rewrite it.
- **Distill as you go.** After the human settles a fork, overrides a choice, or rejects
  output, add or rewrite a preference file under `docs/preferences/` in the same change, whenever
  the answer reaches past the case at hand. Use the list to propose, not only to answer:
  when planning, suggest what it implies that the human has not asked for.

## Standing preferences

How the human tends to decide, distilled from their answers. Not enforced and not governance.
They start empty: a new project has none, and they grow as the human settles forks.
They live in `docs/preferences/`, one file per preference, never in this file. Before deciding a
fork, run `make preferences` and read `build/preferences.md`. With `REFS=origin`, a preference under
*On other branches, not settled* is context only: it never settles a fork. A new one is a new file with a date +
slug id (`P-MMDD-<slug>.md`); the format is in `docs/preferences/TEMPLATES.md`.

## Dev environment

**Nix is optional, and local to this machine.** `.nix/flake.nix` pins the toolchain (Python 3.13,
uv, git, gh). It and `.envrc` are kept out of git (`.git/info/exclude` and `.gitignore`'s `*.env*`),
so a teammate without them installs the same tools themselves. With nix and direnv installed,
`direnv allow` once and `.envrc` loads that shell on `cd`. Without nix, `.envrc` skips it.
Change tools in `.nix/flake.nix`, never by downloading a second Python: the shell sets `UV_PYTHON` and `UV_PYTHON_DOWNLOADS=never` so uv uses Nix's interpreter.
An agent's shell does not run the direnv hook, so `uv: No such file or directory` means
you are outside it: run commands as `direnv exec . make check`. Without direnv on the machine, drop
the `direnv exec <dir>` prefix wherever a skill shows it.

**The flake ships nearly empty on purpose, and is kept current though uncommitted.** It is ready
for a teammate who wants it only if it lists what the project uses. Since `.nix/` is excluded from
git, it exists only in the root checkout, never in a worktree. Whenever it exists: the first time an
agent works in the repo, add every tool the Makefile, CI and `pyproject.toml` call for, and any
tool the project starts using goes into the root checkout's `.nix/flake.nix` the same day. Never
install a tool any other way. This is the one statement of the rule; the skills and agents point
here.

**Where settings and secrets go.** Each file is gitignored unless marked committed:

| File | For | Committed |
|---|---|---|
| `.envrc` | Loads the flake, then `.env`, then `.envrc.local`. No values. | no (local) |
| `env.example` | Template for `.env`: every variable, placeholder values only. | yes |
| `.env` | Project settings that every dev and `compose.yaml` need (`GOOGLE_CLOUD_PROJECT`, shared service credentials). Copy from `env.example`. | no |
| `.envrc.local` | Only you: personal tokens (`GH_TOKEN`), per-machine overrides. | no |

Adding a project variable means adding it to `env.example` too, with a placeholder, in
the same change. Never put a real value in a committed file, and never print one in a log
or a response. `.gitignore` ignores `*.env*` (`env.example` has no leading dot, so it needs no
exception); keep it that way. `.direnv/` is nix-direnv's per-machine cache; excluded, never
committed.

## Commands

```bash
make check       # the single gate: controls → views --check → governance → entries-check → tests
make views       # regenerate governance/views/RULES.md + registry.json
make governance  # integrity + drift check (the linchpin)
make controls    # every controls/fitness/*.py, plus ruff and ty
make test        # pytest
make entries-check  # ledger and preference files: names, ids, fields
make tasks       # each plan's task status, derived from PR state (PLAN=tasks/<slug> for one)
make ledger      # sighting counts → build/ledger.md (REFS=origin reads every branch)
make preferences # standing preferences → build/preferences.md (REFS=origin reads every branch)
```

`make check` is the only gate. Run it before you say a change is done.

---

Rules come from `governance/views/RULES.md`. Change a rule by supersession, never by
edit.
