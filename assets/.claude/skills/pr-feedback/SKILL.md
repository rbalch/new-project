---
name: pr-feedback
description: Work through Copilot's review threads on every open PR in our stack. Judge each thread fix or decline, post the table to the human as a report (asking only about needs-human forks), fix the agreed ones with a builder and two reviewers, re-squash, restack every PR above, then give each fixed thread its commit and resolve it, re-request Copilot, merge what is done into its epic branch, and triage into the ledger. Use when Copilot has reviewed, or the human says "handle the PR feedback".
---

# PR feedback

You are the orchestrator, as in `orchestrate`, and the same rules hold: you stay on
`develop` in the root checkout, you write no feature code, and every finding passes
through your judgement. The difference is where the findings come from. Here they are
Copilot's review threads on PRs that are already open, often several PRs deep in a stack.

```
ORCHESTRATOR (you, on develop, never inside a worktree)
  │
  ├─ 0. inventory     open PRs → stacks → worktrees → unresolved Copilot threads
  ├─ 1. judge         thread-judge per PR (sonnet, parallel) → you decide each thread
  ├─ 2. report        one table, posted to the human (step 2); a question only for needs-human forks.
  ├─ 3. fix           per PR: builder (fresh worktree) → test RED → GREEN → 2 reviewers
  ├─ 4. land          bottom-up: cherry-pick → re-squash → gate → push → restack above
  ├─ 5. answer        fixed threads get their commit and are resolved; re-request @copilot;
  │                   merge every PR now handled into its epic (orchestrate section 8)
  └─ 6. triage        ledger sightings, preferences, one chore PR per chore chain
```

Copilot is requested when a PR opens (`--reviewer @copilot` at `gh pr create`, `orchestrate`
step 4.3) and only re-reviews when asked. So a run ends by asking again. The next run picks up whatever
that review raises. This is a single pass. Re-run it when Copilot's new review lands,
usually within five minutes.

## 0. Inventory

```bash
gh api user -q .login                      # us
gh pr list --author @me --state open \
  --json number,title,headRefName,baseRefName,headRefOid
git worktree list --porcelain
```

- **Build the stacks.** A PR whose base is another open PR's head branch stacks on it,
  except a landing PR's (below), which is never a stack parent. Order each stack bottom-up
  from its root: an epic branch (`epic-<slug>`) for task, chore and landing-fix PRs of an
  epic, `develop` for a check-in or control PR outside one. Ignore PRs
  that are not ours or not based on `develop`, an epic branch, or one of our branches
  (e.g. a `main`-based CI PR).
- **A landing PR** (`epic-<slug>` into `develop`, `orchestrate` section 9) is its own case:
  its Copilot threads are acknowledged, not fixed (step 1), and it is never restacked or
  re-squashed.
- **Map each PR to its worktree**: find it by branch with `git worktree list --porcelain`. A PR whose
  branch has no worktree gets one: `git worktree add .claude/worktrees/<branch> <branch>`, then
  `uv sync` in it.
- **Find branches above the stack with no PR yet** (`git branch --contains <top-PR-tip>`
  and `worktree-agent-*` branches whose merge-base is a PR tip). These are another session's
  in-flight builds. **Never touch them.** Report that their base will move.
- **Fetch threads and review bodies** per PR:

  ```bash
  gh api graphql -F n=<number> -f query='query($n:Int!){repository(owner:"<owner>",name:"<repo>"){
    pullRequest(number:$n){reviewThreads(first:100){pageInfo{hasNextPage endCursor}
      nodes{id isResolved isOutdated path line
      comments(first:20){nodes{databaseId author{login} body createdAt}}}}
      reviews(last:50){pageInfo{hasPreviousPage startCursor} nodes{id url author{login} state body submittedAt}}
      comments(last:50){pageInfo{hasPreviousPage startCursor} nodes{author{login} body createdAt}}}}}'
  ```

  A connection that returns a full page (100 threads, 50 reviews or 50 comments) is
  paginated before anything is classified, in the direction it was fetched: `reviewThreads(first:…)`
  forwards (`pageInfo{hasNextPage endCursor}`, `after:`), and `reviews(last:…)` and `comments(last:…)`
  backwards (`pageInfo{hasPreviousPage startCursor}`, `before:`), since their first page already ends at
  the newest entry. An inventory that could not be fetched whole is not ready, and nothing merges on it.

  Keep the unresolved threads whose **first** comment is by
  `copilot-pull-request-reviewer` or by a human reviewer. That list, plus the review-body items below, is the run's inventory. An unresolved thread whose last comment is ours was
  answered in an earlier run and never resolved: do not judge it again. If that reply
  is a final one (`Fixed in …` or `Not changed: …`) and the thread is Copilot's, just
  resolve it (with step 2's resolves, or step 5's). A human's thread is never resolved:
  leave it open and list it in the report. If it is a step-2 status (`Accepted. …` or `Waiting on a
  decision …`), treat the thread as in flight: it keeps its state until its fix lands or
  the human decides. Unresolved threads opened by a human are judged and answered like
  Copilot's, in the step-2 report, and never resolved by us. A human reviewer's comments
  never pause the flow: the run does not stop to ask whether to answer them, and the
  landing PR's approval is where the human signs off. This is the one statement of the
  rule for human reviewers; the steps below and `orchestrate` cite it.
- **A human review body or PR comment is an inventory item too.** A review can carry feedback in
  its body alone (a regression fix and a change of direction asked for in no thread), and a PR comment (`issues/<n>/comments`) can carry it with no review at all. An item is a review
  or PR comment whose author is neither us nor a bot (`copilot-pull-request-reviewer` or any `[bot]` login; leave
  out our own login from `gh api user -q .login`, since we post as the human), whose trimmed body is non-empty,
  and which has no later
  PR comment from us that links its `url` with a final reply (`Fixed in …`, `Not changed: …`,
  `Acknowledged…`); an `Accepted.` or `Waiting on…` comment keeps it in flight. A bare
  approval ("LGTM") is listed in the report, not judged. Everywhere below, a review-body or PR-comment
  item is handled exactly like a human's thread, with two differences: every reply to it
  is a PR comment (`gh pr comment`) that starts `@<author>` and links the item's
  `url`, and there is nothing to resolve. A thread-judge gets it as `review <id>` or `comment <id>`, with its
  author, state and body verbatim and no file or line.
- **Read the review summaries.** For each PR, take the newest review body by
  `copilot-pull-request-reviewer[bot]` and its `commit_id`
  (`gh api --paginate repos/{owner}/{repo}/pulls/<n>/reviews`). Copilot's summary says whether it lists open issues
  ("Approval recommended, no open issues" or not); a summary on an older commit than the head, or than the head's restack-equivalent
  (`orchestrate` section 8), says nothing about the head, so the bullet below reads it only against those. A human's
  review body or PR comment is an inventory item (above): one that asks for something before the merge holds that
  PR's merge until our final reply settles it (`orchestrate` section 8), on the empty-inventory path too. It is a
  needs-human fork only when it is a decision no preference settles (step 2).
- **Find what was handled with no trace on GitHub.** The human judges a PR by what the
  page shows, so these count as work:
  - a *resolved* Copilot thread with no reply from us gets one line saying what fixed it
    and where (a commit, a ledger entry), or why it was dropped;
  - a PR whose **latest Copilot summary** still lists open issues while none of its
    Copilot threads are open gets a PR comment saying each was resolved, with links to
    the real thread URLs (look them up; never guess an id), and Copilot re-requested,
    because the summary only changes on a new review.
- Confirm the root is clean on `develop` and its `make check` is green. Read
  `governance/views/RULES.md`, the preferences (`make preferences`, `build/preferences.md`), and the sighting counts
  in the ledger (the `count` column). After `git fetch --prune origin`, read the last two
  with `make preferences REFS=origin` and `make ledger REFS=origin`, as `orchestrate` section 0 says (a preference
  under *On other branches, not settled* settles nothing).

Nothing in the inventory and nothing to resolve: merge every PR that meets `orchestrate`
section 8 (step 5's last paragraph), its completed-review condition included; these merges need no confirm, as in an
`orchestrate` run (`orchestrate` section 8). Say so in one line, plus
any human threads left open, and stop.

## 1. Judge each thread

**One `thread-judge` per PR with open threads, all dispatched in one message so they run
in parallel.** `subagent_type: thread-judge`, no worktree isolation
(it is read-only and works in the PR's named worktree). Brief: PR number and task id, the
worktree's absolute path, the task file's absolute root path, the top-of-stack worktree,
a scratch dir of its own under the session scratchpad, and each thread's id, file, line
author and comment text verbatim (a human's thread flagged as one). It returns a per-thread recommendation with the reproduction
command and output.

You make the call, not the judge, and not Copilot. Read each return against the
criteria below. Where its evidence does not support its recommendation, or it guessed
instead of running something, send it back via `SendMessage`. If it says the defect
lives in an earlier PR, the fix moves to that PR's builder. The criteria:

- **A claim that reproduces is a fix**, unless a reason below applies. A claim that does
  not reproduce is a decline, with the command that shows why.
- **Fix** when it reproduces, or when it is a security property that is cheap to test:
  test it, do not only state it.
- **Decline** for one of these reasons, named in the reply:
  - it does not reproduce (show what you ran);
  - it belongs to a later task in the plan (cite that task's id);
  - the fix costs more than the case is worth: a narrow, local-only path (a default
    credential that only a local dev setup uses, say). Decline it and document the limit in a comment
    next to the code, which is itself a small fix;
  - it contradicts a standing preference or a live rule (cite the preference's id or the `DEC-N`).
- **Needs human** when it would change a task's acceptance criteria, cross into another
  task's scope, or turn on a fork no preference settles.
- **On a landing PR, the default is acknowledge.** Its threads repeat what the small PRs
  settled, so no fix round starts there (the round cap below, from the first pass). The reply is
  `Acknowledged: settled in #n (<one line>).`, or `Acknowledged as a follow-up: <one line>.`,
  and the thread is resolved with step 2's declines. Only a real blocker (a bug, a security
  hole, something actually wrong) is a fix, and it lands as a task PR into the epic
  (`orchestrate` section 9), never as a commit on the landing PR.
- **Copilot re-raising a thread we already declined** on an earlier review keeps the
  decline. The reply points at the earlier one, unless Copilot added new evidence.
- **Count the rounds.** A PR that has had three Copilot fix rounds gets no fourth:
  every thread its next review raises is **needs human**, with your recommendation, and
  the run stops there for that PR. Three rounds in, either Copilot has drifted or our
  approach is wrong, so the stop is a diagnosis with the human, who decides between
  fixing, a follow-up or merging as is. This is the one statement of the cap. Count from the PR's history (each re-request after a
  fix round is one), and say the count in the step-2 table.
- **Outdated threads still get judged.** The line moved, but the defect may not have.

Group the fixes per PR. One builder per PR takes all of that PR's fixes.

## 2. The step-2 table (a report, not a stop)

Nothing is pushed, posted or resolved before this table is posted. Shape it as *Talking to the human* in
`orchestrate` says, hard cap 15 lines:

```
PR #<b> (T-03)
  fix      a null error message crashes the CLI instead of a clean error   `<file>`
  decline  a large input breaks the index: <reason, e.g. belongs to T-0N>    `<file>`
PR #<a> (T-02)
  fix      the cleanup test passes when the child process crashes          `<test file>`
Restack: #<b> above #<a>. Not touched: worktree-agent-<hash> (T-04, no PR yet) will sit on a stale base.
Merge into epic-<slug> once CI is green: #<a>, then #<b> (orchestrate section 8).
Human threads: acted on, in the rows above (step 0), never resolved by us.
Triage: a new chore PR on <base>, or folded into #<n> (step 4.2).
```

Post the table to the human as a report, then go on: Copilot-thread fixes and
declines need no confirm. A stop here would cost a round-trip
and decide nothing. Judging, the thread replies, the test-first fix and both
reviewers all still happen. This is the one statement of the rule. Needs-human threads, if any, get one `AskUserQuestion`, one
question per fork, recommended option first. Start the fixes and declines for every other
thread first, then ask; only the needs-human threads wait for the answer.
Apply what they change, and distill it into a file under `docs/preferences/` if it reaches past
this thread. A human reviewer's threads are acted on like Copilot's (step 0).

**Right after the table, make every thread show its state**, before any builder runs:

- **Declines** get their one and only reply now and, if Copilot's, are resolved. They need no code.
  `Not changed: <the reason, one or two sentences, with the evidence or task id>.` A
  decline that documents its limit in a code comment is a fix, not a decline here: it
  gets the fixed-thread flow below, as `Fixed in <sha>: documented <the limit> next to
  <thing>; behaviour not changed because <reason>.`
- **Fixes** get a status reply now: `Accepted. <the fix, one sentence>. <where it is:
  building / built and reviewed>; it lands when <the PR, or the stack #a–#b> is pushed,
  and this thread then gets the commit and is resolved.` Not resolved yet.
- **Needs-human** threads get `Waiting on a decision from the PR author: <the fork, one
  line>.` and stay open.
- **A human's thread** gets the same replies, but is never resolved: a decline stays open
  after its reply, and its `Accepted` status ends `this thread then gets the commit.`
  Closing it is that reviewer's call.
- The "handled with no trace" items from step 0 get their notes.

A thread with no reply reads as ignored, however far along the fix is.

## 3. Fix: builder, then both reviewers, per PR

PRs in different stacks or different levels run in parallel. Each builder has its own
worktree and the landing in step 4 serialises them.

**Builder:** `subagent_type: builder`, `isolation: "worktree"`. The
original builder is gone, and the named worktree must not be edited by a subagent,
so this is a fresh one. Its brief:

- First command: `git reset --hard <pr-branch>`, then `codegraph init` if installed,
  then `uv sync`. Report the worktree path and branch.
- The numbered list of agreed threads: Copilot's claim in its own words, your
  reproduction command and its output, the required fix shape, and how to re-verify.
- **A failing test first, per thread**, the same discipline as acceptance tests: commit
  the tests alone as `test(<id>): reproduce Copilot findings`, run them, record the red.
  Then fix to green. A thread that cannot be tested (a doc comment) says so instead.
- `make check` exit 0, and the PR's Try it (from its body) still producing what it says.
- Scope is the threads. Anything else it notices is reported, not fixed.
- The same secret hygiene and structured return as `orchestrate` section 1.

**Reviewers:** exactly as `orchestrate` sections 2 and 3. The code reviewer works in the
builder's worktree, the boundary reviewer in its own detached checkout. The range is
`<pr-branch>..HEAD`, plus the red-test SHA. Loop until APPROVE at a score of at least
4 out of 5. A reviewer finding outside the threads' footprint is a new finding for you
to judge, not an automatic fix.

## 4. Land, bottom-up

Work one stack at a time, from the lowest changed PR upward. Before touching anything,
record each PR branch's current tip: `old[<branch>]=$(git rev-parse <branch>)`.

For each PR, from the bottom of the stack up:

1. **If its base branch moved:** restack it in its own worktree first (git refuses to
   rebase a branch checked out elsewhere). For a PR based on the epic, `git fetch`, then
   `git -C <wt> rebase origin/epic-<slug>` only if it conflicts (`orchestrate` section 0);
   for a stacked PR, `git -C <wt> rebase --onto <base-branch> ${old[<base-branch>]}` (`orchestrate` section 0).
   A `sync-develop-<slug>` or `sync-premerge-<slug>` PR keeps its history (the one-commit exception, `orchestrate` section 8),
   so it is never rebased and never squashed: if its base moved,
   `git -C <wt> merge origin/<base>`; then builder fixes go on as new commits with
   `git -C <wt> cherry-pick ${old[<branch>]}..<builder-branch>`. Skip step 2, then step 3.
2. **If it has fixes, or it is the chore PR that takes this run's triage** (a sync PR
   aside, step 1): in its named worktree, take the builder's commits, re-squash,
   and keep the original message:

   ```bash
   git -C <wt> cherry-pick ${old[<branch>]}..<builder-branch>
   git -C <wt> fetch
   git -C <wt> reset --soft $(git -C <wt> merge-base origin/<base> HEAD)
   git -C <wt> commit -C ${old[<branch>]} --edit   # add a Changed bullet per fix
   ```

   Cherry-pick, not fast-forward, because a restack below may already have moved this
   branch. Before each cherry-pick, print `git log --oneline <range>` and check it lists
   exactly the builder's commits. The squash body keeps the *Changed / Why / Watch out* shape from
   `orchestrate` section 4. The fix history stays out of it.
   **A chore PR takes its own triage here**, with or without builder fixes. This applies
   when the run's only PR with threads or fixes is an open `chore-*` PR at the top of the
   chore chain of the epic whose PRs the triage is about: draft step 6's ledger and preference edits now, after step 3, and put them
   in this squash (no cherry-pick when there are no fixes). `git fetch` first and take the
   merge-base against `origin/<base>`, so a stale local base cannot fold other commits in. The gate, the CI wait and the
   step-5 replies then cover the final head, and nothing re-squashes it after a reply has
   cited its SHA. If the folded edits touch a skill or a preference file, run
   `orchestrate` step 4.4's reviewer pass on them before this skill's 4.3 gate. Any other run ships its triage as a new
   chore PR (step 6).
3. `make check` and the PR's Try it in that worktree. A renamed worktree needs
   `uv sync --reinstall` first. A red gate here stops the stack. Report it. Do not
   push anything above it.
4. If the PR wrote any id, run the id rule's check (the `orchestrate` skill's section 5,
   collision repair included), whatever the folded edits touch. Then `git -C <wt> push --force-with-lease`. Never a bare
   `--force`. Then move up one PR.
   Every PR above a changed one goes through steps 1, 3 and 4, fixes or not.

After the top of the stack is pushed, wait for CI on every pushed PR
(`gh pr checks <n> --watch`, or a watcher as `orchestrate` section 8 says) before step 5. A green local gate
is not a green CI. A red check stops the replies for that PR and goes to
its builder. Green means every check on the head has finished and passed, none pending.
Cite a SHA in a reply only after the final squash and that green CI.

A rebase conflict goes to a builder dispatched into that worktree by path, not by
isolation, with the two sides named. You do not resolve it yourself. Remove the builder
worktrees and detached reviewer checkouts once the stack has landed.

## 5. Answer every thread

Only after the whole stack has landed, because a restack changes the SHAs a reply cites.
Take each PR's final head from `gh pr view <n> --json headRefOid`.

Fixed threads only. Declines and needs-human threads were answered in step 2.

- **Fixed:** the final reply, `Fixed in <sha>: <what changed, in behaviour>. <test file>
  covers <the input Copilot named>.` It follows the step-2 `Accepted…` status on the
  thread; it does not replace it.
- Plain and short, no thanks or apologies.

```bash
gh api graphql -f id=<thread-id> -f body=<reply> -f query='mutation($id:ID!,$body:String!){
  addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$id,body:$body}){comment{url}}}'
gh api graphql -f id=<thread-id> -f query='mutation($id:ID!){
  resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}'
```

Resolve each fixed Copilot thread (declines were resolved in step 2). Needs-human threads the
human did not settle keep their step-2 waiting reply and stay open, and so does every
human thread, fixed or not. Then, for every PR
whose own diff changed (not one only restacked, and never a landing PR):
`gh pr edit <n> --add-reviewer @copilot`.

Then merge into its epic every PR that is now handled, bottom-up, as `orchestrate`
section 8 says: every Copilot thread resolved or acknowledged, none waiting on a human,
no unsettled human ask (section 8), and CI green, and no Copilot review requested since its latest diff change still
pending (`orchestrate` section 8's completed-review condition). These merges need no confirm, as in an `orchestrate` run (`orchestrate`
section 8). A PR whose diff just changed waits for Copilot's re-review and the next run,
unless the PR has had its three fix rounds (step 1): then that review's threads go to the
human as needs-human, never into a fourth round.

## 6. Triage and report

Triage every thread as `orchestrate` section 5 does, declines included. Log the
sightings as one new run file per run under `docs/ledger/runs/` (its `sights:` list; never edit an
existing entry to add one). A new finding is a new file under `docs/ledger/findings/` with a date + slug id
(`docs/ledger/TEMPLATES.md`); preference ids are date + slug (`docs/preferences/TEMPLATES.md`). The useful
question is: **why did neither reviewer catch it?** A Copilot finding
that keeps landing in the same blind spot (deployment surface, Make recipes, error
paths) is a gap in the reviewer briefs. Log it as a harness finding when it repeats.
Distill every decline reason and every answer from step 2 into a file under `docs/preferences/`
when it reaches past the thread. Ship it as a new check-in on the chore chain of the epic
whose PRs the triage is about, exactly as the `orchestrate` skill's step 4.4 says (base,
name, review, commit subject); a run spanning several ships one check-in per chain. A run that folded its triage into a chore PR in
step 4.2 has already shipped it and opens no second PR.

Report, outcome first:

- Per PR: threads fixed (with the reply link), threads declined (one-line reason), the
  new head SHA, whether Copilot was re-requested, and whether it merged into its epic.
- Restacked PRs, and any stack stopped by a red gate or a conflict.
- **Branches not touched** whose base moved (in-flight builds). Their orchestrator must
  `git rebase --onto <new-tip> <old-tip>` before squashing; give both SHAs.
- Human threads that are still open, one line each, with a link.
- **Choices made** alone, **preferences added**, **findings by bin** with sighting counts.

## Hard rules

- Nothing reaches GitHub (push, reply, resolve, review request) before the step-2 table is posted to the human
  (step 2). A needs-human thread gets only its `Waiting on a decision…` reply until the human answers; no fix, push
  or resolve touches it.
- Never resolve a thread without a reply on it, and never resolve a fixed thread before
  the fix is pushed and CI is green. A status reply comes first, right after the step-2 table,
  and a decline gets exactly one reply.
- **The run is done only when the PR pages are**: every Copilot thread on every open PR
  of ours has a reply from us and is resolved, or is explicitly waiting on the human; no
  PR's latest summary lists an issue that is not open; Copilot is re-requested wherever
  the diff changed (landing PRs aside). Every human thread also has a reply from us (step 0),
  and stays open. If a run stops short of that, say which PRs are not there and why.
- Never post a link, SHA or id you did not just read from GitHub or git.
- Never resolve a thread a human opened; reply to it like any other (step 0).
- Never rebase, push, or edit a branch that has no open PR, or one another session holds.
  The one exception is the chore branch this run creates in step 6, which gets its PR at once.
  The epic branch is the other exception: you merge PRs into it (step 5) and merge
  `develop` into it (`orchestrate` section 0), never rebase or force-push it.
- `--force-with-lease` only, and only after that worktree's `make check` is green.
- A fix that would change an acceptance criterion is a needs-human stop, never a fix.
- Every rule in `orchestrate`'s *Hard rules* applies here too.
