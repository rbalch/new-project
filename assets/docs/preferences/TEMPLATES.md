# Preference template

Not a preference: `make entries-check` and `make preferences` skip this file.

Two PRs that each add a preference add two different files, so nothing here is edited to add one.
`make preferences` builds `build/preferences.md` from every file: read that before deciding a fork.
With `REFS=origin`, a preference only on other branches is listed under *On other branches, not settled*: context, not settled.
`make entries-check` fails on a bad file name, a duplicate id, a missing field, an id not in the dated form, an id
whose MMDD is not the `date`, a slug that is not the slugified title, a subfolder or a non-`.md` file.

## A new preference: `docs/preferences/<id>.md`

The id is `P-MMDD-<slug>`: the month and day, then the slug of the title (lower case, `a-z0-9` and single
dashes, 60 characters at most). The file is named exactly `<id>.md`. The body is exactly one list
item, with its own id, and the frontmatter `title` must equal the item's bold lead. Continuation lines
are indented two spaces. To change a preference, edit its file in place.

```markdown
---
id: P-0115-example-preference     # P-MMDD-<slug>
title: "Example preference."      # one line; quote it if it contains a colon; the body's bold lead, line breaks collapsed; the slug comes from it
date: '2026-01-15'                # quoted YYYY-MM-DD, the day it was distilled; MMDD matches the id
---
- **P-0115-example-preference: Example preference.** What the human prefers, and why. Where it
  came from (the answer, the PR, the date).
```
