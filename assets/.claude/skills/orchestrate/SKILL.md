---
name: orchestrate
description: >-
  Run task files through the build→review→triage loop. For each task, in dependency order: a builder in its own worktree, acceptance tests first, two reviewers, findings mediated by you until approved, then squash, push, and a PR to the spec's epic branch, which you merge there once CI and Copilot are handled. The epic lands on develop by a landing PR from the epic branch itself, always at spec end (or once only human-run work is left) and sooner if it grows (on average 4 to 10 merged PRs as a guide; suggest one to the human when well past that, never force it). Triage findings into the ledger after each task. Use with a task directory or a single task file written by the planner skill.
---

# Orchestrate

You are the orchestrator. **You do not write feature code.** You brief subagents, judge
what comes back, and decide. Builder and reviewers never talk to each other; every
finding passes through you, and you form your own view before forwarding it.

```
ORCHESTRATOR (you, on develop, never inside a worktree)
  │
  │  for each task, in dependency order:
  │
  │   ┌──────────────────────────── one task ─────────────────────────────────┐
  ├──▶│ task-critic (root)   task file vs the tree it names → CLEAN or human    │
  ├──▶│ builder (worktree)   codegraph init → acceptance tests RED → impl GREEN │
  ├──▶│ boundary-reviewer    live rules + seams, in its OWN detached checkout   │
  ├──▶│ reviewer             red-then-green proof, correctness, tests, shape    │
  └──◀│ findings → you judge → builder → re-review → APPROVE, score ≥ 4/5       │
      │ squash to one commit → push → PR to the epic (or to the predecessor)   │
      └────────────────────────────────────────────────────────────────────────┘
  │
  ▼  after each task
  ├─ triage every finding        Bin 1 / Bin 2 / Bin 3, orchestrator-only
  ├─ log sightings               one new file per finding and per run under docs/ledger/, in a chore worktree + PR (step 4.4)
  ├─ Bin 2 at three sightings?   dispatch control-author
  ├─ status is derived: open PR = in_review, merged = done (`make tasks`)
  ├─ reviewed, CI green, Copilot handled → you merge it into the epic (section 8)
  └─ when the human says, spec end, or only human-run work left   landing PR, epic-<slug> → develop, the human's (section 9)
```

## Talking to the human

The human reads none of the reports. They read you. Every time you stop for a decision,
you translate; the critic, builder and reviewer reports stay as they are, for you.

- **One line of what is wrong, in behaviour, no code names.** "A test that should catch a
  no-op rerun passes by accident", not the symbol chain that proves it. The proof stays
  in the report. Cite **one** file or path per item in backticks so they can go look;
  never more.
- **Each option says what changes for the human**, in plain words, before any id or file
  name. A fork that leads with task ids and jargon gets bounced back. Ids go last, one
  path at most.
- **When the human asks for more context**, answer what is missing with one concrete
  example (a scenario, a sample output) before asking again. If they decline the picker to
  clarify, do not re-ask it: ask what needs clarifying, answer in plain prose, and only then
  put the fork back.
- **Recommend, always, with one clause of why.** They usually take it. The shape is:
  problem → your pick → why → confirm.
- **Show choices only at a real fork.** Two answers you would each defend, or none you
  would, and no settled preference settles it (`build/preferences.md`, outside its
  *On other branches, not settled* part). If one does, take it, cite it, and list it
  under *Choices made*. At a real fork, one bullet per option with its one-line cost,
  say what makes it close, and still say which you prefer.
- **Distill every answer.** When the human settles a fork or reverses one of your
  choices, add or rewrite a file under `docs/preferences/` before moving on, unless the
  answer is truly about this case alone, with a date + slug id (`docs/preferences/TEMPLATES.md`). It ships in
  the triage PR.
- **A question about a task file holds that file.** While it is open, do not edit the
  file; patch the answer in once it comes.
- **Nits are yours.** Fix them, or say no to them, and list the outcome one line each.
  Only forks and blockers get a question.
- **Ask with the question tool** (`AskUserQuestion`), one question per fork,
  recommended option first. Not a wall of "your call on 1–6".
- **Hard cap 15 lines** for the whole stop. If it needs more, the task file needs
  splitting, not the message lengthening.

Before this rule, a critic stop looked like six numbered paragraphs of `module.func`
citations with the actual choice buried mid-sentence. After: "2 blockers, 4 nits. (1)
Task describes as new work something the code already does; reword the bullet. (2) The
no-op test can pass vacuously; the orchestrator should mark units done, alt: the stub
does. Nits fixed as listed." Then the picker.

## 0. Before dispatching anything

Read:

- **The task files** given to you. A directory means every task in it, in dependency
  order. A single file means that task only.
- **`governance/views/RULES.md`** — so you recognise a rule violation in a report
  without re-deriving it. Read it from `origin/epic-<slug>`
  (`git show origin/epic-<slug>:governance/views/RULES.md`), where controls merged into
  the epic live; before the epic exists, read it from `origin/develop`. Never read
  `governance/decisions/` for rules.
- **`AGENTS.md`** — architecture and the contract.
- **The flake**, if `.nix/flake.nix` exists in the root checkout: check that it lists every tool
  the Makefile, CI and `pyproject.toml` call for, and add what is missing before dispatching
  (`AGENTS.md`, *Dev environment*).
- **The ledger's sighting counts** (`docs/ledger/`, built by `make ledger REFS=origin` into `build/ledger.md` after a fetch).
  You cannot apply the rule of three without knowing what already sits at one or two. The
  count is the table's `count` column.

**Read the ledger and preferences across every branch.** After the retargets below, run
`git fetch --prune origin`; if the fetch fails, stop. Then run `make ledger REFS=origin` and
`make preferences REFS=origin`, and read the tables in `build/ledger.md` and `build/preferences.md`. The
header lists the working tree and every `origin` branch read, so triage not yet on `develop`
(an open `chore-*` PR, another epic) is counted, and a run file on several branches counts once. A fork's PR is not on `origin` and is not counted.
Only a preference in the working tree or on `origin/develop` settles a fork. One listed under
`## On other branches, not settled`, with the branches it is on, has not reached `develop`: read it as
context, never cite it as settling a choice, and treat its id as taken.
Re-run before each triage. Each `sights:` item in a run file is one
independent sighting (accepted limitations follow section 5), and distinct rounds on one PR stay distinct sightings (a finding seen in
two rounds is listed twice); section 5's same-batch grouping still applies. Counts include
triage of task PRs not yet merged, or later abandoned, on purpose: a sighting records what a review
saw, which stays true whatever happens to the task. Section 5 and
`pr-feedback` step 0 count from the same place; this is the one statement of the rule.

Then confirm the starting state:

- **Merge what is ready.** Every open PR into the epic that meets section 8 merges now,
  bottom-up, its completed-review condition included. While a landing PR of this epic is
  ready for review (not a draft), section 8 holds all but its fixes.
- You are on `develop`, the tree is clean, and `make check` is green. Starting on a red
  gate means you cannot tell which failures a task caused.
- **The epic branch exists, is current, and is green.** The spec names it,
  `epic-<slug>`. Only `develop` and `main` need a human approval, so this branch is yours
  to push to and merge into. **No task is dispatched until the spec has merged into
  `develop`** by its own PR, the human's approval of the plan (`planner` step 5): opening
  that PR does not approve it. Check with
  `git fetch --prune && git cat-file -e origin/develop:docs/specs/<slug>.md`. Then:
  - Spec on `develop`, no `origin/epic-<slug>`: cut the epic from `develop` and push it,
    `git push origin origin/develop:refs/heads/epic-<slug>`.
  - Spec on `develop`, an epic cut before it merged (`git cat-file -e
    origin/epic-<slug>:docs/specs/<slug>.md` fails): if the epic has nothing of its own
    (`git log origin/develop..origin/epic-<slug>` is empty), remove its local worktree and branch
    if they exist, delete it on `origin` and cut it again; if it
    has, leave it: the develop sync below brings the spec in, since `develop` is ahead of it.
  - Spec already on the epic but not on `develop` (its tasks under way): keep
    going; it is not re-PR'd.
  - Spec not on `develop` and not on the epic: dispatch nothing for this plan, and skip
    every step below that needs its epic (the epic worktree, the develop sync, `make tasks`
    on the epic, retargets onto it, the task-critic loop): the epic may not exist yet, or
    carries no spec. The section-0 steps above this bullet (inventory, merging what is
    ready, the gate, the ledger reads, other epics' checks) still run. Find the spec's PR
    by the file it adds, whatever its head is called: an open PR whose files include
    `docs/specs/<slug>.md` (`gh pr list --state open --limit 200 --json number,baseRefName,files --jq '.[] | select(any(.files[]; .path == "docs/specs/<slug>.md")) | {number, baseRefName}'`).
    Then, one of three cases:
    - **A PR is found and targets `epic-<slug>`** (opened against the epic by mistake):
      retarget it with `gh pr edit <n> --base develop`.
    - **No PR, but the spec file exists** on some branch: open one against `develop` now
      (step 4.4, the spec-PR exception).
    - **No spec file at all:** if the plan is one held task file alone (no further split)
      whose file already fixes its scope (a Scope, Non-scope and Acceptance, and no
      open-question text), draft the spec from that file and open that PR, with no planner
      session: a planning talk over a decided one-file scope changes nothing. The spec says
      it was drafted that way, its *Decisions* quote the task file, and its PR carries
      *Choices made* and the suggestion to share it with the team (`planner` step 5); the
      human's merge approves the plan as usual. Otherwise stop and send the human to
      `planner`.

    The plan resumes on a later invocation, once that PR has merged.

  Once the epic exists and the spec is on it or on `develop` (any case above but the last), **every run, make the epic worktree exist and be current**,
  whether or not `develop` moved; sections 8 and 9 gate in it. `<wt>` =
  `.claude/worktrees/epic-<slug>`: if it does not exist,
  `git worktree add -B epic-<slug> <wt> origin/epic-<slug> && direnv exec <wt> uv sync --directory <wt>`;
  if it does, `git -C <wt> fetch && git -C <wt> merge --ff-only origin/epic-<slug>`. While
  a landing PR of this epic is ready for review (not a draft), skip the develop sync below: the epic is frozen
  (section 9), and the sync runs on the first run after the landing merges. If
  `develop` has moved since (`git rev-list --count origin/epic-<slug>..origin/develop` is
  not 0, say because another epic landed), **merge `develop` into the epic, never
  rebase**: the branch is shared and holds merge commits. In that worktree,
  `git -C <wt> merge --no-ff origin/develop`, `direnv exec <wt> make -C <wt> check`, and
  `git -C <wt> push origin HEAD:epic-<slug>`. A conflict in `docs/ledger/` (two files at one path
  that both sides added) or in `docs/preferences/` is yours: resolve it by taking
  both sides' entries and recounting sightings (above), run `make entries-check`, and give it the
  step 4.4 reviewer pass. A conflict in
  code goes to a builder dispatched into that worktree by path, as `pr-feedback` step 4
  does. Either way it is reviewed before the push. If `make check` is red after the
  merge, push nothing to the epic: push the merge as branch `sync-develop-<slug>`
  (`git -C <wt> push origin HEAD:sync-develop-<slug>`), then
  `git -C <wt> reset --hard origin/epic-<slug>` so the worktree matches the epic again;
  open it as a PR into `epic-<slug>`, fix it there with a builder and both reviewers, and
  merge it under section 8. Last, the epic's tip is green (section 8's local gate); a red one stops every dispatch until it is fixed, except the recovery
  task that fixes it (section 8).
  **A premerge sync.** Work held only behind other PRs' approvals (PRs not yet on `develop`) builds on a
  premerge of them, not on a wait: a `premerge` branch merges those PRs onto `develop` with merge commits,
  and the epic takes it in like a develop sync, so the held tasks build on what will land under them; once
  the PRs land, `develop` holds the same content. It follows the same rules:
  merge, never rebase; conflicts in `AGENTS.md` and the ledger get the step 4.4 pass; skipped while a landing PR is
  open. It always goes as a `sync-premerge-<slug>` PR into the epic, never pushed straight to it.
- Run `make tasks PLAN=tasks/<slug>`. Status is **derived from PR state**, never
  stored in the task file: a merged `<id>:` PR is `done`, an open one is `in_review`,
  every dependency done or in review is `ready`, anything else is `blocked`. A merged PR
  means merged into the epic; `from develop` in its output means from the epic branch.
  Build only
  `ready` tasks, and skip any whose body opens with `> **Blocked:`; report it as held
  (`tasks/README.md`, *A hold is not a status*). **A ready task whose dependency is still `in_review` stacks:** its
  branch starts from that dependency's branch, which `make tasks` names
  (`stacks on T-02 (<branch>)`). The human comes back to a chain of PRs, each one
  testable on top of the last.
- No `ready` task already has a branch or worktree from another session. If one does,
  skip it and say so.
- **Retarget after merges.** For every open PR whose base PR has merged into the epic
  (section 8): `gh pr edit <n> --base epic-<slug>` if section 8
  did not already retarget it. Do not rebase it: the merge commit left its parent's
  commit in the epic unchanged, so its diff is already right, and a rebase would stale
  the SHAs its `Fixed in <sha>` replies cite. Rebase onto `origin/epic-<slug>` only when
  GitHub reports a conflict, then `make check` and force-push with lease. A stacked PR is
  rebased whenever its parent's branch is rewritten: in its own worktree (git refuses to
  rebase a branch checked out elsewhere), bottom-up, `git rebase --onto <new> <old>`, then
  its gate and Try it, then force-push with lease. Never let a dependent carry a stale
  copy of its base. The combined
  state is checked by the epic's own CI after each merge (section 8). A child is never
  retargeted to `develop`. If a child shows closed because its base was deleted first,
  restore the parent branch from its merged SHA and retarget.

Then, **for each task, before its builder exists**, dispatch `subagent_type: task-critic`,
in the root checkout — no worktree, it is read-only. Brief: the task file
path, the epic branch it checks against (`origin/epic-<slug>`, where this plan's merged
tasks are; `develop` lacks them until the epic lands, section 9), and that its report is findings
or `CLEAN`. It checks that every symbol the task names exists, that no acceptance bullet contradicts the task's own scope, and that every
bullet can be written as a test that goes red here. Task-file defects caught after code
exists cost a fix round each; this is the minute of reading that catches them first.
The planner already ran the critic at plan time, so expect `CLEAN` (not for a spec drafted from its task file, section 0, which had no plan-time critic). A finding now
usually means the tree moved since planning: a dependency merged or its branch exists,
and the planner's `DEFERRED` guesses about it can finally be checked. Name those items
in the brief.

- `CLEAN` → dispatch the builder.
- Findings → **stop and take them to the human**, in the shape under *Talking to the
  human*. A task file changes only by their decision; apply it to the file (it is untracked, nothing to commit) and dispatch.
  Patch every finding they settle into the file, blockers and nits alike: the merged PR carries
  the brief verbatim as its only permanent record, so it should say what was built. You
  do not fix the task file yourself; your own reading is the least-reviewed input in the loop.

## 1. Builder dispatch

`Agent` tool, `subagent_type: builder`, **`isolation: "worktree"`**; its own `model:` pin
(Sonnet) decides. The worktree is created for you under `.claude/worktrees/` and branches from
your current HEAD, `develop`, so the brief always names the base and the builder's first
command is `git reset --hard <base>`, before `codegraph init`. The base is
`origin/epic-<slug>`, fetched just before (a fix to a landing PR included); for a
stacked task, the branch it stacks on. Reuse the same builder via
`SendMessage` for fix rounds; its context is warm and the worktree is already set up.

The brief is the task file's **absolute path in the root checkout** (`tasks/` is
untracked, so it is not in any worktree; every agent reads it from the root), plus:

- **Worktree setup**: `git reset --hard <base>` first. Then
  `codegraph init` if codegraph is installed, so the graph reflects the tree being edited, then `uv sync`. Report the worktree path in the return; you need it for the
  reviewers.
- **Acceptance tests first.** Turn every runnable acceptance criterion in the task into
  a test, lint and type-check them, commit those tests alone as
  `test(<id>): acceptance for <title>`, run the
  suite, and record the failing output. Run the Try it steps and record that they fail
  too. Then implement until both are green. This commit is the red proof and the
  reviewer will check out that SHA.
- **Environment facts**: everything happens in the worktree; `uv run` for every command;
  the task's `files` list is the expected footprint and anything beyond it is reported.
- **A refused command is reported, never routed around**: the exact command goes in the return as a step not
  run, and is never wrapped in a script, renamed or re-quoted to get past the refusal. A plant or
  test run through a script is fine; that never covers a command the sandbox refused.
- **Secret hygiene**: never print a token; run a `grep -rE 'token|secret|key'` sweep over
  changed files as a named verification, not a promise.
- **Verification list**: the task's acceptance commands with expected results,
  `make check` exit 0, and every Try it step producing what the task says.
- **Commit instructions**: small conventional commits, clean tree at the end. The
  history will be squashed by you, so commit freely.

Three ledger-specific additions:

- **`make views` after touching any decision.**
- **Never re-record a `pragma: external` hash.** The builder reports it; you decide.
- **"Blocked by a rule" is a valid outcome, and you want it.** A builder reporting
  "DEC-N stopped me" is producing the most valuable data this project collects.

Require a structured return: worktree path, branch name, the acceptance-test commit SHA
and its failing output, subsequent commit SHAs, per-verification evidence (**output, not
claims**), the `make check` exit code, the Try it transcripts (failing before, passing after, real
output verbatim), deviations from the task with reasons,
blocked-by-a-rule items, files touched outside the task's `files` list, and any new tool it
needed (you add it to the root checkout's flake, `AGENTS.md` *Dev environment*).

If the return does not arrive (the builder says it is waiting on its own background
work, or ends without the list), do not wait for it: read the worktree itself
(`git -C <wt> log` and `status`, the test run) and judge the items the return would have
listed: the acceptance-test commit, the `make check` exit code and the Try it output.

### Model escalation

Workers (every Sonnet pin: the builder, `task-critic`, `thread-judge`, `boundary-reviewer`) run on their pinned Sonnet
while they are working. Escalate a worker with `model: opus` on the dispatch when the same
finding survives two fix rounds, the builder's evidence turns out false on
re-verification, or there are no forward commits after two attempts (these three are the
builder's triggers). A read-only worker (`task-critic`, `thread-judge`, `boundary-reviewer`)
escalates when its report is wrong on the same item twice in a row. Note the escalation
and why. Drop back to the pin for the next routine round. `reviewer` and `control-author` (the Opus pins)
run on their frontmatter model every round, never overridden. Otherwise
dispatch every agent without a `model:` override, so its pin and the dispatch never disagree.

## 2. Reviewer dispatch — two of them, in two separate checkouts

Both run after the builder returns. Neither subagent inherits the builder's directory,
so every brief opens with an absolute path and the instruction to `cd` there before
anything else. A reviewer that runs `make check` in the root checkout has reviewed the
wrong tree.

**The boundary reviewer gets its own checkout. This is not optional.** Before
dispatching, create one at the reviewed SHA and point its brief there:

```bash
git worktree add --detach <scratchpad>/<id-lowercase>-boundary <reviewed-sha>
```

The code reviewer keeps the builder's worktree. Tell each that the other has its own
tree and is not to be touched. On a fix round, move the detached checkout forward with
`git checkout --detach <new-sha>` before re-dispatching, and remove it once the PR is
open.

The reason is that reviewers verify by execution, which means planting a deliberate
defect and reverting it. Sharing one tree, each sees the other's plant and reports it as
a real finding — or worse, correctly guesses it is the other reviewer's mess and
dismisses it, which is a reviewer teaching itself to wave anomalies through. Two trees
cost one command and some disk, and buy genuinely independent findings: each reviewer's
experiments stay out of the other's tree.

- **`subagent_type: boundary-reviewer`**, in its own detached checkout —
  every live rule in `RULES.md` against the diff, citing `DEC-N`, plus the seams declared
  in `AGENTS.md`.
- **`subagent_type: reviewer`**, in the builder's worktree — the
  red-then-green proof, correctness, tests, contracts, failure directions, code shape. It
  owns `review.md` / `review.json` there; both are gitignored.

Both briefs carry: that reviewer's own path, the task file's absolute root path, the
acceptance-test commit SHA, and the range to review (`<base>..HEAD`, where `<base>` is
`origin/epic-<slug>` or the stacked dependency's branch). The code
reviewer's brief also carries the builder's Try it transcript. Try it is a required
check for the reviewer, run from a clean state, like the red proof.

Both briefs name `review_stage: local-build` for ordinary task work and pass prior
accepted limitations. Fixes made for outside feedback on a PR into `develop` or `main`
use `review_stage: pr-feedback` even when the fix lands through a task PR. Carry this
stage through every fix and re-review. All reviewers return the risk assessment from
`AGENTS.md` **Outside PR feedback: worth fixing now?**

Both briefs must demand: verify by execution, not by reading; findings with severity,
`file:line`, and a concrete failure scenario for anything called a bug; attention to
interface contracts, failure direction (false success is blocking in `local-build`;
`pr-feedback` uses the shared policy), secrets in outputs, and regressions against earlier rounds; a verdict and a
score out of 5.

**A boundary finding citing a `DEC-N` is blocking, always.** CI will fail on it regardless
of what anyone scores it.

## 3. The loop — you in the middle

The loop below is the `local-build` default. In `pr-feedback`, apply the shared
`AGENTS.md` policy first: only findings requiring action enter the fix list or count
as blocking/important for the loop. Accepted limitations do not lower readiness
below 4. The cheap-nit and 5/5 instructions below apply only to `local-build`.
Pass the stage and prior decisions to the builder and both reviewers every round.

```
while verdict != APPROVE or score < 4 or blocking/important findings remain
      or any Try it step fails:
    read both reports; for each finding decide: agree / disagree with evidence / needs human
    send the findings you agree with → builder (SendMessage), ONE numbered list,
        each with the required fix shape and how to re-verify
    builder fixes and returns evidence, including a fresh Try it transcript
    reviewers re-review the DELTAS (git show <fix-shas>) in the worktree, re-run what
        they can, mark findings resolved with SHAs
```

- **Form your own view before forwarding.** You are not a relay. If a reviewer finding
  is wrong, say so in the brief with evidence and do not send it. If the builder's
  evidence does not support its claim, send it back before the reviewers see it again.
- Builder and reviewer disagree: **reviewer wins**, unless you can personally verify the
  reviewer is wrong.
- Fold cheap minors and nits into fix rounds. Do not carry one-line debt into the PR.
- Accept 4/5 only when the reviewer explicitly judges the leftovers acceptable by design.
  **5/5 is the target.**
- **`NEEDS_HUMAN` stops the loop.** Report in the *Talking to the human* shape and wait.
  Do not iterate past it.
- **An acceptance test the builder wants to change** is a planning question, not a fix
  round. If the criterion was wrong, stop and report; the human decides whether the task
  file changes.
- **A review idea deferred out of the task's scope gets a drafted task**, when the human
  agrees, since a note alone is easy to lose. Draft it in the plan's directory in
  `tasks/README.md` format, run `make tasks`, and open its body with a hold line
  (`tasks/README.md`, *A hold is not a status*) naming what it waits for. The spec's *Open
  questions* points at the draft, since task files are untracked. The task-critic runs
  when the hold lifts.

`make check` fails fast at the first stage. Re-run the whole gate after each fix.

## 4. Land it — squash, push, PR

On approval, in the worktree, by you or by the builder under your instruction:

1. `make check` green, tree clean.
2. **Squash to one commit.** `git reset --soft $(git merge-base <base> HEAD)` then one
   commit, where `<base>` is `origin/epic-<slug>` or, for a stacked task, the branch it stacks on (a dependency's or a control PR's). Squashing against the epic on a stacked branch folds the dependency's commit
   into this one. If the dependency merged into the epic while this task was building,
   `git fetch` first and re-check: its base is now `origin/epic-<slug>`. **Take the commits by SHA from the worktree's
   HEAD, never from a branch name** (`git -C <wt> rev-parse HEAD`): a builder's worktree can end
   on a detached HEAD, so its branch lags it. Save the reviewed tree
   first (`T=$(git rev-parse 'HEAD^{tree}')`) and, after the squash commit, check that `git rev-parse 'HEAD^{tree}'`
   equals `$T` before pushing. If HEAD is detached,
   create the task branch at the reviewed SHA before squashing (`git switch -c <id-lowercase>-<short-slug>`; it keeps
   any commits beyond the old branch tip), so step 3 has a branch to push; the lagging `worktree-agent-<hash>`
   branch is left for worktree cleanup. Subject `<type>(<id>): <title>`. The body is **bullets, not prose, hard cap
   15 lines**, in exactly this shape:

   ```
   Changed:
   - one bullet per file or behaviour, what it does now
   Why: one line
   Watch out:
   - up to 3 bullets, only for things a reader would not guess; omit the section if none
   ```

   The review rounds, the fix history, and the story of how a bug was found do not go
   here. That belongs in the ledger (`docs/ledger/`), which already has it. If a bullet
   needs a paragraph, it is a ledger entry, not a PR bullet.
3. Rename the worktree's branch to a readable one (skip this if step 2 already created the named branch), then push
   it under the same name:
   `git branch -m <id-lowercase>-<short-slug>` (e.g. `t-02-orders-cli`), then
   `git push -u origin HEAD`. The worktree tool names branches after the agent
   (`worktree-agent-<hash>`); without the rename, `git worktree list` and `make tasks`
   show that instead of the task. The
   worktree folder keeps its tool-given name; find it by branch with `git worktree list --porcelain`.
   Open the PR with `gh pr create`. Write the body to a file with a quoted heredoc
   delimiter (`<<'EOF'`) and pass it with `--body-file`: an unquoted heredoc runs every
   backtick in the body as a command. The body is short, in this order:
   a one- or two-sentence summary of what changed and why, linking the spec; one bullet
   per change; a **Watch out** list only for things a reader would not guess; a **Choices
   made** list of every call you or the builder made without asking; then two collapsed
   blocks. No builder output, no test counts, no review history.

   ````
   <summary, with spec link>

   - <one bullet per change>

   **Watch out**
   - <only the surprises; omit if none>

   **Choices made**
   - <the choice, one clause of why, and the preference it followed if any; omit if none>

   <details><summary>Try it</summary>

   ```
   git fetch && git checkout <branch> && uv sync
   <each Try it step from the task>
   ```
   </details>

   <details><summary>Task brief <id></summary>

   (task file, verbatim, after any task-critic corrections)

   </details>
   ````

   If the task's Try it is `None — <reason>`, the Try it block says so, reason included.
   The task brief stays because `tasks/` is untracked, so **the merged PR is the only
   permanent record of the brief**.
   - **Base is `epic-<slug>`** (a fix for a landing PR that is ready for review included: it bases on the
     epic, since there is no other branch, section 9), never `develop`, unless this task stacks on an open PR: a
     `depends_on` task's, or a control PR whose code it needs (step 4.4). Then the base is
     that PR's branch, and the PR is stacked. It is retargeted to the epic when that PR
     merges (section 8).
   - Title `<id>: <what changed>`, the task's full id with its plan prefix (`T-03`,
     `CT-01`), then a few plain words, not the task's title. `make tasks` matches PRs on
     the prefix only. The task title's extras ("inspectable by hand") can go in the
     commit message, not the PR title or description.
   - **Reviewers go in the same `gh pr create` call**, never a later step, on every PR this skill, `planner` and
     `pr-feedback` open (task, chore, control, spec, sync-develop and landing PRs: wherever a step says to open one, this applies). The only exceptions are the two named below: a draft landing PR with live checks open, and the `@copilot` refusal fallback. A landing PR with live checks still open (section 9) is created as a
     **draft** with `--reviewer @copilot` only: GitHub may refuse human review requests on a draft, so note
     the human reviewers and request them right after `gh pr ready`, with the `gh pr edit` in section 9's *Live checks* bullet.
     Always `--reviewer @copilot`: Copilot's review is the one that does not start by itself (CI does). Add the
     human reviewers too (except on a draft landing PR with live checks open, above), from the standing list you already hold for this human (a personal memory), or, when you
     hold none, ask once at the first PR of the run: "Do you want to add reviewers to this run's PRs?"
     (`AskUserQuestion`), and use the answer on every PR of the run. That list, or that answer, is the authorization for
     review requests; inside a `pr-feedback` run the question is asked the same way, at the first PR it opens. This skill names no
     one, because the list changes. Afterwards check the issue timeline for each reviewer's `review_requested` event
     (`gh api --paginate repos/{owner}/{repo}/issues/<n>/timeline --jq '.[]|select(.event=="review_requested")|.requested_reviewer.login'`):
     Copilot never shows in `reviewRequests`. If this `gh` refuses `@copilot` at creation, no PR was created:
     run the same `gh pr create` with only the human reviewers, then
     `gh pr edit <n> --add-reviewer @copilot` on the PR it made, and say so.
     A draft landing PR with live checks open has no human reviewers to retry with: run the same `gh pr create --draft` with no
     reviewer, add Copilot with that same `gh pr edit`, and request the human reviewers at `gh pr ready`.
4. **Every check-in you make is its own worktree and PR, on the chore chain.** This is
   where section 5's ledger changes land, with preference files, skill edits, and any
   other file you commit. `develop` is protected, and you never commit on it. Each
   check-in carries the triage before it. This is the one statement of the rule;
   `pr-feedback` cites it.
   - **Base:** a check-in for an epic's work chains inside that epic: the newest open
     `chore-*` PR of ours based in its chain, from any run; if none is open, the epic
     branch. A check-in outside any epic: the newest open `chore-*` PR of ours not in an
     epic; if none, `develop`. Never a task PR: the chain sits on the epic (or `develop`),
     so a ledger or skill change never waits behind a task's review or breaks when a task
     is reworked. An epic's chore PRs merge into it like task PRs (section 8). A check-in
     already based in an epic's chain stays in it. A
     task never stacks on a chore; it may stack on a control PR whose code it needs, with
     that branch named as its base in the builder brief (section 1). A graduated control's
     PR is not a check-in, and it is pushed and opened at once, never held back "for review":
     the PR is where the human reviews a rule change. It bases on `develop` when the code it governs is there, and on
     the epic branch's tip (not its chore chain) when that code is only on the epic; you
     merge the latter into the epic like a task PR (section 8), and its landing PR lists its
     decision change on its own line for real human review (section 9). Its branch is
     `control-<dec-n>`, never `chore-*`, so it stays out of the chain. A plan's spec PR is not
     a check-in either: it always bases on `develop` (the human's approval of the plan,
     `planner` step 5), carries no triage, and its branch is `spec-<slug>`, never `chore-*`,
     so nothing chains on it and section 0 never reads the ledger from it. This is the one
     statement of the base.
   - **Name:** `chore-<id>-triage`, `<id>` lowercased (`t-03`); a `pr-feedback` run uses
     its PRs' task ids joined (`t-02-t-03`). The commit subject uses the same `<id>`. If that branch or worktree already exists
     under any case (a second check-in for the same id), add the next free suffix, `-2`,
     `-3`, to both.
   - **Review:** a check-in that edits a skill or a preference file gets one
     `reviewer` pass before the push. Its brief: trace every step, in both skills, that
     reads or writes what the new rule touches. Skipping the build loop for a doc edit
     does not skip this pass. A ledger-only check-in needs none.
   - **Bundle:** when check-ins outside any epic stall waiting on approval, the
     human may have them bundled into one PR to `develop`, one squashed commit with each
     original message in its body; the old PRs are closed with a pointer to it. The PR says
     that their approvals do not carry over. A part still under review goes in only if the
     human accepts that it may hold the rest. Check-ins
     inside an epic never bundle, since the orchestrator merges them there. A control PR
     (`control-<dec-n>`), a spec PR and any decision change never go into a bundle: each
     keeps its own PR and its own review.
   - Then: `git fetch --prune`, `git worktree add -b <name> .claude/worktrees/<name> origin/<base>` (the fetched tip;
     a local `<base>` may be missing or stale), edit there with
     `git -C <wt>` and absolute paths (never `EnterWorktree`; you stay on `develop`), run
     `make check`, commit one `chore(<id>): triage` (`pr-feedback`: `chore(<id>): copilot
     triage`), run the id rule's check again (section 5), push, and open `gh pr create --base <base> --head <name>` with step 3's
     reviewers (you are on `develop`, so `gh` cannot infer the head). Retarget these like task PRs (section 0),
     and rebase a stacked one as section 0 says.
   Do not touch the task file; the open PR *is* its status.
5. Remove nothing. The worktree stays until the PR merges and no child still builds or
   reviews on its branch (section 8), in case of Copilot's threads or review comments. Whenever a builder returns (first return or a fix round), look at
   `ps` for the wait loops it left behind (an `until` loop on a log file) and stop any whose job is done.

If a decision was authored or changed in this task, its whole supersession diff stays
inside the single squashed commit: decision, control, pragma, regenerated view and
registry, together.

## 5. Triage — the step that makes this a ledger repo

**After the PR is open, before the next task. Not optional. Orchestrator-only** — builders
and reviewers never touch `docs/ledger/`; reviewers propose candidate
sightings in their reports and you decide. You record triage as new files only: a new finding is
one file under `docs/ledger/findings/`, and each triage run is one file under `docs/ledger/runs/`
whose `sights:` list holds one item per independent sighting (`docs/ledger/TEMPLATES.md`). Never
edit an existing entry just to add a sighting.

Count sightings with `make ledger REFS=origin` after `git fetch --prune origin` (section 0), re-read before each
task's triage: after the first task's step 4.4 its chore PR is on `origin`, so a batch never counts a sighting
twice or misses one.

**The id rule: a new `DEC-N` is the next free one across `develop`, every epic branch and every
open PR.** F, H and P ids are not: a new finding's id is date + slug, `F-MMDD-<slug>` (`H-` for a
harness finding), a new preference's is `P-MMDD-<slug>`, each unique in the tree, and `make entries-check` enforces it. Epic branches count because a PR merged into one is no longer open and not yet
on `develop`. The next-free-one rule covers
every `DEC-N` you write, in a ledger entry or a
decision. Sightings are counted by `make ledger REFS=origin` (section 0); ids come from this rule,
which also covers the chore chain, since it is an open PR. `git fetch --prune origin` first, on every
run of this check, the one before a push included; if the fetch fails, stop. Then take the
highest in
`git grep -ohwE 'DEC-[0-9]+' origin/develop $(git branch -r --list 'origin/epic-*') -- governance/decisions`
and in the added lines of every open PR, drafts and other authors' included
(`gh pr list --state open --limit 100 --json number -q '.[].number'`, then for each
`gh pr diff <n> | grep '^+[^+]' | grep -ohwE` with the same pattern; if `gh pr diff` refuses a
large diff, `git diff origin/<base>...origin/<head>`, the base from
`gh pr view <n> --json baseRefName`), and use the next one above all of them (the grep also
matches citations; that can only raise the next id). **Run it again just before each push** (step
4.4, `pr-feedback`'s push): a parallel session can take the same id in between.
On a recheck, skip your own PR in the loop over open PRs, since its ids are what is under
test. A collision is an id your PR
*newly defines*, one not defined at its merge-base with `origin/<base>` (a `DEC-N-*.md` file), that `origin/develop`, an epic
branch or another open PR also defines. Rewriting a definition that already exists is not one, and neither is a
citation (`see DEC-N`), so neither asks the PR to renumber. The first run, while
drafting, skips nothing; your own PR's earlier ids only push the next free id higher.
On a collision: renumber the colliding definitions in your PR and every reference to
them (a `DEC-N`'s file name, `id:` and pragmas).
Do all of it in the PR's worktree `<wt>`, never the root checkout you sit in: edit by
absolute path, and run every command as `git -C <wt> …` or `direnv exec <wt> make -C <wt> …`.
Run `make -C <wt> views` if a `DEC-N` moved, then `git -C <wt> add -A`, then
`git -C <wt> commit --amend` (still one commit, section 8; fix any id in the message), then rerun
`make -C <wt> check`, then run this check again (its git commands via `git -C <wt>`) before
pushing.
This is the one statement of the rule; the steps that write or push ids,
here and in `planner`, `finding-triage`, `pr-feedback`, `ledger-ops` and the
`control-author` agent, cite it.

Accepted limitations from `pr-feedback` retain their scores, evidence, action, and
thread link in ledger body text. Repeated reports of the same unchanged accepted case
use `updates:`, not fresh `sights:` toward the rule of three. They do not create a
follow-up task or control by default. See `docs/ledger/TEMPLATES.md`.

Run each non-trivial finding from the whole task through the three bins:

| Bin | What it means | What you do |
|---|---|---|
| **1** | An existing linter, formatter or type-checker covers it | Note it. If it recurs, tighten ruff, not the ledger. |
| **2** | A concrete, checkable, **systemic and cross-file** pattern | **Log a sighting.** This is the value. |
| **3** | Genuine subjective taste | Log it and say so plainly. Never manufacture a control. |

Procedure per finding: restate it as a checkable claim (if a machine could not check it,
that is Bin 3), assign the bin in one sentence, log it as a `sights:` item in the run file.

**Same-batch repeats count once.** Three tasks from one plan hitting the same pattern is
usually one cause in the plan, not a recurring habit. Log one sighting and note the
count; use judgement, and say what you decided.

Findings already caught by an existing control are not new sightings; note that it
fired. Honest sorting matters more than control coverage: a fat Bin 3 is a real result.

**Then distill, whatever the bin.** The rule of three guards controls, not preferences.
For each finding and each fork the human settled in this task, ask what it says about
how they decide. If it reaches past this case, add or rewrite a file under
`docs/preferences/` on the first sighting, with a date + slug id (`docs/preferences/TEMPLATES.md`), and note the
preference's id in the run file (its `- **Preferences:**` line, `docs/ledger/TEMPLATES.md`).
Bin 3 taste is the richest source: no control will catch it, but a preference can steer
the next builder away from it.

## 6. Graduation — rare, and gated

Only when a Bin 2 finding reaches its **third** logged sighting, and `finding-triage` step 5 has first
looked for the one function the sites share. If there is none, or the human chose a control, dispatch
`subagent_type: control-author`. If the human chose to fix the shared function instead, file that fix under
`tasks/<plan>/fixes/` (`tasks/README.md`, *Fixes*) and do not dispatch. The dispatch brief carries the decision's `DEC-N` picked by the id rule
(section 5). The agent re-verifies the preconditions and refuses if they do
not hold. Let it refuse. A control that fires on correct code is the most damaging
failure available here.

## 7. Next task, and exit

First merge every PR that now meets section 8, then run `make tasks` again and move to
the next `ready` task that is not held (section 0). A task that depends on one now
`in_review` stacks on it, as in section 0; keep going until no unheld task is `ready`. Build
the chain in id order so each branch exists before its dependents need it. A task is
`blocked` only when a dependency is unbuilt or two in-review dependencies sit on
separate branches; merge whichever meets section 8, then re-run `make tasks`, and report
and stop only if none does.

**Copilot's review threads** go through the `pr-feedback` skill, which runs this same
fix-and-restack loop across the whole stack. A PR it leaves handled merges into the epic
(section 8).

**If the human asks for changes on a PR mid-stack**, fix it in its worktree, then
restack each dependent as section 0 says, and re-run its gate and Try it.

When the batch is finished or blocked, report, outcome first:

- Per task: PR URL, verdict and score, one line of what to try, the findings that
  mattered and their fixes, and the base branch for stacked PRs.
- What you merged into the epic, and what still waits on Copilot, CI or a parent PR
  (section 8). Any landing PR opened this run, and when the next landing is due (section 9).
- Tasks blocked on a merge, and which PR unblocks them.
- Tasks held (`> **Blocked:`), each with its condition.
- Any model escalations and why.
- Whether the root checkout's `.nix/flake.nix` changed, and what was added.
- **Choices made** without asking, one line each, so the human can reverse any.
- **Preferences added or rewritten**, by id.
- **Findings by bin, with running sighting counts.**
- **Anything that graduated to a control**, or is at two sightings and close.
- **Any rule the builder was blocked by**, and whether the rule or the code was wrong.
- **Any acceptance criterion that turned out wrong**, since that is a planning finding.
- **Whether `check_governance` caught anything real**, or only agreed with a green build.

## 8. Merge into the epic, yourself

The epic branch needs no human approval, so you merge task, chore and control PRs into
it. In an `orchestrate` run that needs no confirm: merging into our own epic
branch is not speaking for the human. A `pr-feedback` run merges the same way, with no
confirm. This is the one statement; `pr-feedback` cites it. A PR merges when all of
these hold:

- it passed the review its kind needs: a task PR, our reviewers at 4/5 or more
  (section 3); a check-in that edits a skill or a preference file, its step 4.4 reviewer
  pass; a ledger-only check-in, none; a control PR, the control-author's red/green proof.
  Every change since was re-reviewed the same way. A conflict-free rebase is not a
  change; a conflict resolution is;
- it is one commit, and CI is green on that head (`gh pr checks <n>`). A fix is re-squashed into
  the commit, never appended, even on a PR that arrived with several, and the squashed body keeps
  the substance of every original message. Two kinds of PR are the exception, never squashed and
  merged with a merge commit: a `sync-develop-<slug>` or `sync-premerge-<slug>` PR (section 0),
  which carries the synced branch's commits plus the merge, and a landing PR (section 9);
- Copilot has reviewed it and every thread is handled as `pr-feedback` says: fixed and
  resolved, declined with a reply, or, past `pr-feedback`'s three-round cap (step 1), settled with the human.
  A thread waiting on a human decision holds the merge, and so does a human review body
  that is an inventory item with no final reply (`pr-feedback` step 0; a bare approval is not one);
- Copilot's review requested after the PR's latest diff change has completed (a conflict-free
  restack is not a diff change). Human reviewers on the PR do not hold the merge by being
  requested; only an unsettled human ask does (below). The newest review by
  `copilot-pull-request-reviewer[bot]`
  is on the head, or on a commit the head differs from only by a conflict-free restack
  (`git range-diff` shows no changed patch). Read it with
  `gh api --paginate repos/{owner}/{repo}/pulls/<n>/reviews --jq '[.[]|select(.user.login=="copilot-pull-request-reviewer[bot]")]|last|.commit_id'`.
  GitHub does not list Copilot in `reviewRequests`, so a pending request is invisible
  there: if Copilot was re-requested after the last diff change and has not reviewed that
  head yet, the condition fails. This is the one statement for every path that merges
  (section 0's *Merge what is ready*, step 4.4's chore PRs, a landing fix (section 9),
  `pr-feedback`'s empty-inventory path and step 5); they cite it;
- its base is `epic-<slug>`. A stacked PR waits for its parent, then is retargeted
  (section 0);
- no landing PR of this epic is ready for review (a draft does not count, section 9), unless this PR is a fix for it or the triage
  check-in of such a fix (section 9);
- no human review body, PR comment or unresolved review thread (not ours: leave out our own login) asks for
  something before the merge that is still unsettled. Read them with
  `gh api --paginate repos/{owner}/{repo}/pulls/<n>/reviews`, `.../issues/<n>/comments` and the unresolved
  human threads of `pr-feedback` step 0's query (an inline comment is in neither of the first two; reading a thread
  does not change the rule against replying to it).
  The hold lifts when the human says to merge, or our final reply to it is posted (`pr-feedback` step 0) and the
  human has not contradicted it. Merely reading a human's review settles nothing;
- the epic's tip is green (below). The one exception is the red-epic recovery PR (below):
  reviewed like a task PR, with its own checks green against the failing tip, it merges
  while every unrelated merge stays blocked.

Bottom-up, one PR at a time:

```bash
gh pr merge <n> --merge
[ "$(gh pr view <n> --json state -q .state)" = MERGED ] || exit 1   # a failed call can still merge, or not
for c in $(gh pr list --base <branch> --state open --json number -q '.[].number'); do
  gh pr edit "$c" --base epic-<slug>
done
git push origin --delete <branch>   # GitHub does not auto-delete here; only after every child is retargeted
```

**A merge commit, never squash or rebase.** The PR is already one commit, so the merge
keeps that commit as it is, and a child stacked on it keeps a valid base: its parent's
commit is now in the epic unchanged. Retarget the children before deleting the branch: a
PR whose base branch is deleted first is closed and cannot be reopened. Not
`gh pr merge --delete-branch`, which also tries the local branch, still checked out in
its worktree. Remove that worktree and its local branch only once no child still builds
or reviews on it; a child still building squashes against `origin/epic-<slug>` (step 4.2).

**Check the epic's tip after every merge, and merge nothing else until it is green.**
Siblings each green against an older epic can still be red together. CI does not run on a
push to an epic branch (`ci.yml` pushes are `main` and `develop` only), so run the gate locally
(`git fetch --prune` first, since `gh pr merge` does not move the local `origin/epic-<slug>`):
`git -C <wt> fetch && git -C <wt> merge --ff-only origin/epic-<slug> && direnv exec <wt> make -C <wt> check`
(section 0). The next PR into the epic and its landing PR then run CI on the merged state.

**Waiting is a watcher, not a promise.** Nothing runs between turns, so never say you will check back. After opening a
PR, or merging into the epic, start a `Monitor` loop that prints a line on each change and exits only on a terminal
state (CI passed or failed, Copilot's review on the current head, the count of unresolved threads). Write the exit test
out in the loop (`while true; ...; case ... exit 0 ...; sleep 45; done`): an `until s=$(...); case ...; do` loop tests
the `case`'s own status, which is 0 when nothing matches, and ends at once with no output. Read its first line by hand,
and treat a monitor that ends silent as not a result. A monitor has a ceiling (30 minutes): re-arm it,
and check that the review it waits for was requested, or it waits for nothing. Prefer it to a blocking
`gh pr checks --watch`, which errors at once when no check has registered yet.

**Red-epic recovery.** A red epic stops merging. The fix is a task PR into `epic-<slug>`:
a new task file in the plan's directory, through sections 0 to 8 like any other, with
the epic as its base. It is the recovery PR the merge conditions above let through. Never
a commit pushed straight to the epic; a clean, green develop sync (section 0, never while
a landing PR is ready for review) is the one exception. A `sync-premerge` PR is a PR like any other, so it too waits for
a green epic.

## 9. Land the epic: a PR to `develop`

**Land while it is still reviewable.** As a guide, a landing carries on average 4 to 10
merged PRs; as long as it is not wildly outside that, it is fine. It is a guideline, not
a rule: nothing counts PRs, blocks or forces a landing on it. When the epic is well past
about ten unlanded PRs, suggest a landing to the human, who decides when. **Never land while the epic holds a premerge of PRs
not yet on `develop` (section 0)**: the landing would carry their unapproved diffs, so this wait overrides the
human-run early landing below and the size guide. Always land
when the spec is done (every task `done`, held tasks aside, unless a held task waits only on approvals expected
soon: then, once the rest is done, stop and talk it over with the human rather than land or lift
a hold alone; never land early just to unblock another plan). Land, too, when every task
left is human-run work (one the spec says the human runs outside this flow): a small
landing is easier to review and `develop` gets the fixes sooner, and the human's piece lands
in a later small landing. Either way, only once no PR based on
`epic-<slug>` (task, chore or control) is still open, so deleting the epic afterwards
closes nothing. A landing PR kept as a draft for live checks (below) is exempt from the 4 to 10 guide while it waits.

**The landing PR comes from the epic itself.** There is no second branch. Merge
`origin/develop` into the epic if it moved (section 0), run
`direnv exec <wt> make -C <wt> check` in the epic worktree (section 0), confirm the
epic's tip is green as section 8 checks it, and open
`gh pr create --base develop --head epic-<slug>` with step 3's reviewers (a landing with live checks still open is a draft with Copilot only: see the *Live checks* bullet below), titled
`epic-<slug>: <what it delivers>` (not `<id>:`, which `make tasks` would read as a task).
This is the only PR of the epic that waits on a human approval. **While it is ready for review (not a draft) the
epic is frozen**: nothing merges into it except a fix for this landing PR (section 8), so
the reviewer's diff moves only for fixes they asked for. Tasks keep building and their PRs
keep getting reviewed; they wait to merge. A landing PR with live checks still open
(the *Live checks* bullet below) is opened as a **draft** instead, so none of this applies
until it is marked ready. The body, in this order:

- **Merge with "Create a merge commit", not squash or rebase**: `develop` keeps each
  task's commit (section 8's one-commit exception);
- one or two sentences of what the spec delivers, linking the spec;
- **Review for blockers only**: something wrong, unsafe, or hard to undo; never "I would
  have built it differently", since direction and design were settled at the spec PR,
  before the build. Every piece has already passed two reviewers, CI and Copilot in its
  own PR. List these as places to look, not a complete list, and ask the reviewer to say
  what is wrong, not what they would prefer:
  correctness, migrations (data rewritten or dropped, order with other plans' migrations),
  public API and contract changes (a CLI flag, a table, an API endpoint, an output format
  others read), cross-service impact (what another repository or job now sees), and data
  and permission boundaries (what reaches a model, a log, another project). Security
  changes get the real review in the next bullet. The one exception is next;
- **Rule and security changes**, for real human review, not blockers-only, one line each
  with its PR: every change under `governance/decisions/` (`DEC-N`, new or superseded,
  its control PR), and every security-sensitive change: credential handling, IAM and
  infrastructure code, CI workflows (`.github/`), and authentication. Find them with `git diff --stat
  origin/develop...origin/epic-<slug>` and the PRs' titles; when unsure, list it;
- **Live checks**, when the work reaches a real model, database or provider:
  list what fake clients could not prove, what each check needs and who runs it, in the
  same section as the list for real review. The PR is still opened at spec end, but as a
  **draft** (`gh pr create --draft --base develop --head epic-<slug> --reviewer @copilot`; step 3's human reviewers are requested right after `gh pr ready`), and the body says the checks are recommended before it merges, not required. Recommend
  running them first; when the human asks to merge sooner, run the mark-ready steps below without objection and
  note the open checks in the recap. A draft is not up for review, so the epic is NOT frozen while it
  waits: other PRs merge as usual, and the draft's **Pieces** list is refreshed whenever
  the epic gains a PR. The human is reminded of the open checks in each run's recap. When the
  checks can actually run, or the human asks to merge sooner, mark it ready: first merge `develop` into the epic if it moved, re-run `make check` and refresh the **Pieces** list; then `gh pr ready <n>`; then request the human reviewers with `gh pr edit <n> --add-reviewer <login>` (`<n>` is the landing PR's number, since you sit on `develop`). The
  freeze starts then (only fixes for the landing merge), and only the human decides when
  it merges. A fix a failed live check needs is a fix for this landing PR, so it merges
  into the epic (section 8);
- **Pieces**: every task, chore and control PR in this landing, in merge order, one line
  each (`#n <id>: <what it did>`), so the reviewer can read the history chunk by chunk;
- every task PR's **Choices made**, collected, and any held task with its condition;
- one collapsed **Try it** block per task, from its PR.

It is **not squashed**. It merges with a merge commit, so `develop` keeps one commit per
task (section 8's one-commit exception). The human approves and merges it; you never do.
Once it has merged, the freeze is over. If the spec is done, `git push origin --delete
epic-<slug>`, remove `.claude/worktrees/epic-<slug>` and its local branch, and
`git fetch --prune`, so a landed epic stops feeding the id rule and the sighting counts.
If work goes on (an earlier landing), merge `origin/develop` back into the epic, exactly as
section 0 does, before any further merge into it.

- **Copilot on a landing PR starts no fix round.** Its threads repeat what the small PRs
  settled, so each gets an acknowledgement and is resolved, as `pr-feedback` step 1 says (its
  round cap applies from the first pass). Only a finding requiring a fix under the shared PR risk policy is fixed, the way a human's is.
- **A fix the human reviewers ask for** is a task PR into `epic-<slug>`: a new task file
  in the plan's directory, through sections 0 to 8 like any other. The landing PR updates
  when it merges. Its triage check-in (step 4.4) counts as part of the fix and merges into
  the epic before the landing does, so deleting the epic closes nothing. Their comments
  and review bodies are answered like Copilot's (`pr-feedback` step 0); we never resolve their threads.

## Hard rules

- **In `local-build`, never let a task pass with a known path to exit-0-on-failure.**
  In `pr-feedback`, use the shared risk policy and its exceptions.
- **Never edit code to evade a control**, and never accept a change that does. Rule
  change is a supersession diff a human reviews.
- **Never hand-edit `governance/views/**` or `governance/registry.json`.**
- Secrets never appear in briefs, outputs, commits, or PR bodies.
- Human-gated steps are reported as gates, never simulated or skipped past.
- Dependent tasks stack on their dependency's branch, never on a guess: a base is an
  open PR that passed review. Rebase rules: section 0.
- You stay on `develop`. You never `EnterWorktree`; subagents get isolation, you get the
  view from above.
- You merge into an epic branch, never into `develop` or `main`. Never rebase or
  force-push an epic branch; it is shared. The one exception is an empty epic cut before its
  spec merged, deleted and recut (section 0).
