# new-project

A [Claude Code](https://claude.com/claude-code) skill that scaffolds a Python project
with a devcontainer, a `make check` gate, a planner → task files → orchestrator flow
that lands one reviewed, squashed PR per task on an epic branch, and a governance harness that turns
recurring review findings into CI-enforced rules.

Run `/new-project my-api` and you get a directory that builds, lints, type-checks,
tests, and refuses to let an agent quietly change the rules it works under.

## Install

```bash
git clone git@github.com:rbalch/new-project.git ~/.claude/skills/new-project
```

Claude Code picks it up on the next session. Verify with `/new-project` — it should
appear in the skill list.

## Use

```
/new-project my-api
```

The skill asks for the package name, the container name, and a GCP project id, then
writes `./my-api`, runs `uv sync`, verifies `make check` exits 0, and initializes git
with `main` and `develop` branches. It then fills the local Nix flake (see
[Nix](#nix)).

It finishes by offering to fill in the four `<!-- TODO -->` sections of `AGENTS.md`.
Those are the parts no template can supply — what the project is, its architectural
shape, its Always/Never lists, and the working context. An unfilled `AGENTS.md` is the
one piece of the scaffold that does nothing until it is written.

## What you get

```
my-api/
├── AGENTS.md                   the hand-written agent contract
├── Makefile                    make check is the single gate
├── pyproject.toml              ruff (B/I/RUF/UP), ty, pytest, all pinned
├── compose.yaml                dev container
├── env.example                 template for .env; every variable, placeholder values only
├── .envrc                      direnv: loads the flake, .env, .envrc.local (ignored by git)
├── .nix/flake.nix              local Nix shell (kept out of commits, see Nix)
├── dev.Dockerfile
├── .devcontainer/
├── .github/workflows/ci.yml    the same gate as make check, staged so failures are named
├── .claude/
│   ├── agents/                 task-critic · builder · reviewer · boundary-reviewer · control-author · thread-judge
│   └── skills/                 planner · orchestrate · pr-feedback · ledger-ops · finding-triage
├── tasks/                      README.md is the task file format; tasks/<slug>/ is untracked, the PR keeps the brief
├── scripts/task-status.py      make tasks — status derived from PR state, never stored
├── build/                      GENERATED, ignored: make ledger and make preferences write here
├── governance/
│   ├── decisions/              DEC-N-<slug>.md — the canon, retains superseded records
│   ├── scripts/                build_views.py, check_governance.py
│   ├── views/RULES.md          GENERATED — the only rules an agent reads
│   └── registry.json           GENERATED
├── controls/fitness/           the executable rules, each carrying its pragma
├── docs/
│   ├── specs/                  one spec per plan, written by the planner
│   ├── adr/                    design decisions with rejected alternatives, when earned
│   ├── governance-harness.md   why the harness exists, and how to tell if it works
│   ├── ledger/
│   │   ├── findings/           F-MMDD-<slug>.md, one file per finding
│   │   └── runs/               YYYY-MM-DD-<slug>.md, one file per orchestrator run
│   └── preferences/            P-MMDD-<slug>.md, how the human decides; starts empty
├── src/my_api/
└── tests/governance/           95 tests covering the harness itself
```

## The harness

Three layers, tethered in both directions so nothing drifts silently.

```
DECISION (the why)          CONTROL (the teeth)        VIEW (what agents read)
governance/decisions/  ──►  controls/fitness/*.py ──►  governance/views/RULES.md
DEC-N-<slug>.md             fails CI when violated     GENERATED, live rules only
      │                            ▲
      └── frontmatter: controls ───┴── pragma: "governance: enforces DEC-N"
```

A decision's frontmatter names its control paths. Each control carries a
`governance: enforces DEC-N` comment. `check_governance.py` runs nine integrity checks
and refuses to pass unless both directions line up:

| | Checks |
|---|---|
| **Traceability** | every live decision has a control · every control path exists · every pragma is present · every pragma names a live decision · every hashed control matches its recorded sha256 |
| **Hygiene** | the generated view is current · no superseded rule text leaked into the view · ids are unique and supersessions resolve |
| **Teeth** | the control suite actually runs and passes |

**Agents read only `governance/views/RULES.md`.** The decisions directory keeps
superseded records on purpose — history is for humans. A superseded rule in an agent's
context steers it toward the exact pattern you abandoned, and the `superseded` label
does not help, because the presence of the text does the damage.

**Rules change by supersession, never by edit.** A new decision, the old one marked
superseded, the control and pragma retargeted, the view rebuilt — all in one diff a
human reviews. Enforcement is automated; changing what is enforced is not.

## Why bother

Two reasons, and the second is the real one.

**1. Architectural invariants a linter cannot express.** Not line-level style — ruff
already does that. Systemic, cross-file rules: the API layer never imports the DB layer,
no module reaches into another's internals, dependencies flow one direction, every
handler passes through auth. These are objective, structural, and exactly what coding
agents violate confidently and often.

**2. A ratchet for review findings.** Normally, every time you review agent output and
say "no, don't do that," the correction evaporates. The next session repeats it and you
review it again, forever. This gives you one move you do not otherwise have: turn a
recurring correction into a permanent control, once, so you never review for it again.

### The rule of three

A dislike does not become a control on first sighting. It stays soft — a note, an
`AGENTS.md` nudge — until its **third** logged sighting. A third sighting proves it is
recurring *and* articulable. Anything that never recurs stays soft or dies, which is
correct: it was never worth a fitness function.

Every finding sorts into one of three bins: already lintable, articulable as a control,
or genuine taste. The `finding-triage` skill runs that sort and logs it.

### The falsifiable test

**If the middle bin stays fat and review burden measurably shrinks, the harness earns
its keep. If nearly everything collapses into "already lintable" or "genuine taste," it
is complicated linters plus a wiki, and it should be dropped.**

Do not judge it by "does CI go red." Judge it by whether the middle bin turned out to be
real. That is why `docs/ledger/` exists and why the distribution has to be
recorded honestly, including when it is unflattering.

### The ledger and preferences

Every entry is its own file with a dated id: `F-MMDD-<slug>.md` for findings,
`YYYY-MM-DD-<slug>.md` for runs, `P-MMDD-<slug>.md` for preferences. Parallel PRs add
files and never collide on a shared log or a counter.

`make ledger` and `make preferences` build readable views into `build/`. With
`REFS=origin` they also count entries on fetched branches, so a sighting logged in one
open PR counts toward the rule of three before it merges. `make entries-check` validates
the entry files; it runs inside `make check` and in CI.

`AGENTS.md` carries a "decide unless torn" rule. The agent reads `make preferences`
first, takes the choice a preference settles, and asks only when none does.

### What it is not

A code-taste oracle. Do not try to encode readability or elegance as a control. Every
attempt produces a dumb proxy that fires on fine code and misses bad code. Taste stays
where it belongs: a human looks at the diff and decides.

## The task flow

```
/planner                    you + the planner until the plan is agreed
   └─▶ docs/specs/<slug>.md · tasks/<slug>/<PREFIX>-NN-*.md · docs/adr/ if alternatives were rejected

epic-<slug>                 one epic branch per spec, cut from develop

/orchestrate tasks/<slug>   per task, in dependency order:
   builder (own worktree)   codegraph init → acceptance tests committed RED → implement GREEN
   boundary-reviewer        live rules + architectural seams
   reviewer                 checks out the red commit, confirms green at HEAD, then correctness
   orchestrator             judges every finding itself, bounces to the builder, APPROVE ≥ 4/5
   land                     squash to one commit (what + why) → PR to the epic, stacked if dependent
   triage                   every finding binned and logged, orchestrator only, rule of three
   merge                    reviewed + CI green + Copilot handled → orchestrator merges into the epic

landing PR                  epic-<slug> → develop; the human approves
develop → main              a human's PR
```

Tests come first at the **acceptance boundary only**: the task file's acceptance
criteria become tests, committed alone, watched failing. The reviewer verifies that red
before anything else. Unit tests below the boundary are the builder's call. That buys
the one thing a post-hoc test cannot prove, that the test was written against the task
and not fitted to the code, without the churn of unit-level TDD on a design nobody has
seen yet.

Every task also has a **Try it**: steps a person runs on the branch, with the output they
should see. The builder runs them red then green, the reviewer re-runs them, and the PR
opens with them. Green tests with a failing Try it is not done.

Each spec gets one epic branch. Task PRs target it, one squashed commit each. A task
that depends on an open task branches off that task's reviewed branch and its PR targets
that branch. The orchestrator merges each PR into the epic once it is reviewed, CI is
green and Copilot is handled. The epic lands on `develop` through one landing PR, always
at spec end and sooner if it grows (about 4 to 10 merged PRs is the guide). Landing PRs
are the only PRs a human approves, reviewed for blockers.

When Copilot reviews, the `pr-feedback` skill takes over. A `thread-judge` agent reads
each open thread per PR, reproduces the claim, and recommends fix, decline or
needs-human. Agreed fixes go through a builder and both reviewers, the stack is
restacked, each thread is answered and resolved, and findings are triaged.

Outside feedback on PRs into `develop` or `main` uses a shared likelihood × impact
assessment, each scored 1–5. Below 8, accept the limitation without a code change or
follow-up task; at 8 or above, fix. Explicit requirements, required checks, live rules,
and credible security or data-loss findings retain their exceptions. Reviewers carry
these decisions through fix rounds and reopen them only for new evidence or an explicit
human override. Local review keeps its current loop and 5/5 target. The full policy
lives in the scaffold's `AGENTS.md`.

Parallelism is manual: open a second session and hand it a task with disjoint `files`.
The triage step is the point, and it is the one people skip. A loop that fixes findings
and forgets them is the problem the harness claims to solve.

## Seeded rules

Exactly one: `DEC-0`, which says no generated file may be named `AGENTS.md`. That is a
structural invariant of the harness itself — a hand-written contract and a generated
rule view sharing one name is a trap that fails quietly in both directions.

Everything after it should be discovered through review. Rules imagined in advance are
usually taste dressed as controls: brittle, firing on correct code, pure ceremony. A
control that fires on correct code is the worst failure available here, because it
teaches everyone to route around the harness.

## Requirements

Claude Code, plus one of:

- Docker and `uv`, or
- Nix and direnv, which supply `uv`, Python 3.13 and the rest.

The scaffolded project targets Python 3.13.

## Nix

Nix is a supported, first-class path. It comes in two layers.

**Scaffolded projects.** Each gets a near-empty `.nix/flake.nix` and an `.envrc`. The
scaffold adds `.nix/` and `.direnv/` to `.git/info/exclude`, and `.gitignore`'s `*.env*`
already covers `.envrc`. So the Nix layer is personal: it never lands in the project's
commits, and a teammate without Nix never sees it.

- The agent fills the flake at scaffold time with every tool the project calls outside
  uv (`docker-client`, `jq`, and so on).
- The orchestrator keeps it current as part of daily work: a check before each run.
  Builders report a new tool; they never install one. The flake stays ready to share if
  a teammate wants it.
- The shell pins `UV_PYTHON` to Nix's Python and sets `UV_PYTHON_DOWNLOADS=never`, so
  uv never fetches a second interpreter.
- An agent's shell does not run the direnv hook. Agents run commands as
  `direnv exec . make check`.
- Run `direnv allow` once. Without Nix, `.envrc` skips the flake and everything works
  as before.

**This repo.** It has a committed `.nix/flake.nix` and `.envrc` for working on the
template itself. Run `direnv allow` once.

## Layout of this repo

```
SKILL.md     the skill definition Claude Code reads
assets/      the template tree, copied verbatim with {placeholder} substitution
.nix/        flake for working on this repo (committed; scaffolds get their own copy from assets/)
.envrc       loads that flake through direnv
```

Placeholders substituted at scaffold time: `{project_name}`, `{package_name}`,
`{container_name}`, `{GOOGLE_CLOUD_PROJECT}`, `{today}`. Two paths carry a placeholder
in the name and get renamed: `{project_name}.code-workspace` and `src/{package_name}/`.
