---
name: new-project
description: Scaffold a new project directory with a standardized devcontainer, compose, Dockerfile, Makefile, pyproject.toml, and the ledger governance harness (decisions, controls, generated rule view, build/review agents). Copies template files from assets/ and substitutes {variable} placeholders with user-provided values.
user-invocable: true
command: new-project
---

# New Project Scaffold

Scaffold a new project directory from the templates in `~/.claude/skills/new-project/assets/`.

The scaffold is two layers:

- **The dev environment** — devcontainer, compose, Dockerfile, Makefile, pyproject.
- **The ledger governance harness** — decisions, executable controls, a generated rule
  view, the integrity check, its tests, and the agents and skills that drive the
  build→review→triage loop. See "What the harness is" at the bottom.

## Variables

| Placeholder | Description |
|---|---|
| `{project_name}` | Project name — used in compose, devcontainer, pyproject, docs |
| `{package_name}` | Python package name — `{project_name}` with hyphens as underscores |
| `{container_name}` | Docker container name for the dev service |
| `{GOOGLE_CLOUD_PROJECT}` | GCP project ID |
| `{today}` | Today's date, `YYYY-MM-DD` — used in DEC-0's frontmatter |

Substitute **only these exact tokens**. The Python sources contain literal `{` and `}`
in f-strings and format calls; leave them alone.

## Steps

### 1. Parse project name

The project name comes from the skill argument. Example: `/new-project my-api` →
`project_name = my-api`.

If no argument was provided, ask the user for the project name before proceeding.

### 2. Ask for variable values

Ask the user for the remaining variables. Show suggested defaults in brackets — accept
them with Enter:

- **package_name** [`{project_name}` with `-` → `_`]
- **container_name** [`{project_name}-dev`]
- **GOOGLE_CLOUD_PROJECT** [no default — required]

`{today}` is not asked for; fill it from the current date.

Collect all values before writing any files.

### 3. Resolve destination

The destination directory is `./{project_name}` relative to the current working
directory. If the directory already exists and is non-empty, warn the user and ask
whether to proceed before writing anything.

### 4. Copy and substitute

Copy every file from `~/.claude/skills/new-project/assets/` into the destination
directory, preserving the directory structure. Include dotfiles and dot-directories —
`.claude/`, `.devcontainer/`, `.github/`, `.editorconfig`, `.env`, `.gitignore` are all
easy to miss with a naive glob.

Replace each placeholder in file **contents**. Two paths also carry a placeholder in
their **name** and must be renamed:

- `{project_name}.code-workspace` → e.g. `my-api.code-workspace`
- `src/{package_name}/` → e.g. `src/my_api/`

Full manifest:

```
.claude/agents/builder.md
.claude/agents/boundary-reviewer.md
.claude/agents/control-author.md
.claude/agents/reviewer.md
.claude/skills/build-loop/SKILL.md
.claude/skills/finding-triage/SKILL.md
.claude/skills/ledger-ops/SKILL.md
.devcontainer/devcontainer.json
.github/workflows/ci.yml
controls/fitness/view_naming.py
controls/lint/.gitkeep
docs/governance-harness.md
docs/ledger-findings.md
governance/decisions/DEC-0-generated-view-is-not-agents-md.md
governance/registry.json          # generated — regenerated in step 5
governance/scripts/build_views.py
governance/scripts/check_governance.py
governance/views/RULES.md         # generated — regenerated in step 5
src/{package_name}/__init__.py
tests/__init__.py
tests/governance/__init__.py
tests/governance/conftest.py
tests/governance/ledger.py
tests/governance/test_build_views.py
tests/governance/test_check_governance.py
.editorconfig
.env
.gitignore
AGENTS.md
compose.yaml
dev.Dockerfile
Makefile
pyproject.toml
README.md
{project_name}.code-workspace
```

### 5. Install and verify the gate

The harness ships green. Prove it before handing over:

```bash
cd {project_name}
uv sync
make check     # must exit 0
```

`make check` runs the controls, proves the generated view is current, runs the nine
integrity checks, and runs the harness's own tests. **If it is not green, fix it before
reporting done** — a new project that starts on a red gate teaches its user to ignore
the gate.

### 6. Git setup

```bash
cd {project_name}
git init
git checkout -b main
git add .
git commit -m "chore: initial project scaffold"
git checkout -b dev
```

Unless the user specified different branch names in their request, use `main` as the
default branch and create a `dev` branch off it.

### 7. Fill in AGENTS.md, then confirm

`AGENTS.md` ships with `<!-- TODO -->` markers in four sections: the opening paragraph,
"Architectural shape", "Always" / "Never", and "Working context". Those are the parts no
template can supply and the parts that make the file worth having.

Offer to fill them in now from what the user has told you about the project. If they
decline, leave the markers — but say plainly that an unfilled `AGENTS.md` is the one
piece of this scaffold that does nothing until it is written.

Then report: the directory path, files written, variables substituted, `make check`
result, and git branches. Keep it concise.

## What the harness is

Worth understanding before you scaffold it, so you can explain it if asked.

Three layers, tethered both ways:

```
DECISION (the why)          CONTROL (the teeth)        VIEW (what agents read)
governance/decisions/  ──►  controls/fitness/*.py ──►  governance/views/RULES.md
DEC-N-<slug>.md             fails CI when violated     GENERATED, live rules only
      │                            ▲
      └── frontmatter: controls ───┴── pragma: "governance: enforces DEC-N"
```

`check_governance.py` runs nine integrity checks and refuses to pass unless both
directions line up. Rules change only by supersession — a new decision, the old one
marked superseded, the control and pragma retargeted, the view rebuilt, all in one diff
a human reviews.

**The new project starts with exactly one decision, DEC-0**, which says no generated
file may be named `AGENTS.md`. That is a structural invariant of the harness itself, not
a project rule. Everything after it should be *discovered* through review, at three
sightings, via the `finding-triage` skill. Do not seed rules speculatively when
scaffolding — rules imagined in advance are usually taste dressed as controls.
