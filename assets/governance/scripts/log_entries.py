#!/usr/bin/env python3
"""Validate the one-file-per-entry ledger and preferences, and build their combined views.

    log_entries.py view  [--kind ledger|preferences] [--src <dir>] [--out <file>] [--refs <remote>]
    log_entries.py check [--kind ledger|preferences] [--src <dir>]

The ledger lives in ``docs/ledger/``: one file per finding under ``findings/`` and one per
triage run under ``runs/``. Preferences live in ``docs/preferences/``, one file per item.
Two parallel PRs that each log something add two different files, so they never collide.
``docs/ledger/TEMPLATES.md`` and ``docs/preferences/TEMPLATES.md`` hold the formats.

``view`` writes ``build/ledger.md`` (a count table, then every entry) or
``build/preferences.md``. With ``--refs origin`` it also reads the entries on every fetched
``refs/remotes/origin/*`` through git plumbing (no checkout, no fetch), one copy per path,
so a count includes sightings logged on branches not yet merged. ``check`` is the gate:
file names, required fields, no duplicate full id, and every id an entry names has its file.

Every failure is a message on stderr and exit 1, never a traceback.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')
FRONTMATTER_RE = re.compile(r'\A---\n(?P<fm>.*?)\n---\n(?P<body>.*)\Z', re.DOTALL)
SLUG_MAX = 60
TEMPLATES_NAME = 'TEMPLATES.md'
README_NAME = 'README.md'

# --- ledger ids: F-MMDD-<slug> for a finding, H-MMDD-<slug> for a harness finding ---
FINDINGS = 'findings'
RUNS = 'runs'
DATED_ID_RE = re.compile(r'^([FH])-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)$')
NEW_ID_HINT = 'findings use F-MMDD-<slug> (H-MMDD-<slug> for the harness); see docs/ledger/TEMPLATES.md'
FINDING_REQUIRED = ('id', 'kind', 'title', 'date', 'bin')
FINDING_KIND = {'F': 'finding', 'H': 'harness'}
FINDING_BINS = ('1', '2', '3')
RUN_REQUIRED = ('date', 'title', 'updates', 'sights')
# A full dated id named in an entry's text (`F-0115-example-finding`): it must be a finding's exact id.
BODY_DATED_ID_RE = re.compile(r'(?<![\w-])[FH]-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*(?![\w-])')
# A bare id named in an entry's text (`F-0115`): a dated id's short form, valid only while one finding has it.
BODY_ID_RE = re.compile(r'(?<![\w-])[FH]-\d+(?![\w-])')
NEW_ENTRIES_LINE = 'New entries: see docs/ledger/TEMPLATES.md.'

# --- preference ids: P-MMDD-<slug> ---
PREF_DATED_RE = re.compile(r'^P-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)$')
PREF_ITEM_RE = re.compile(r'^\s*[-*] \*\*P-[0-9]+(?:-[a-z0-9]+)*:')
PREF_NEW_ID_HINT = 'preferences use P-MMDD-<slug>; see docs/preferences/TEMPLATES.md'
PREF_REQUIRED = ('id', 'title', 'date')
PREF_SKIPPED = (README_NAME, TEMPLATES_NAME)
PREFS_DEFAULT_TITLE = '# Standing preferences\n'
NEW_PREFS_LINE = 'New preferences: see docs/preferences/TEMPLATES.md (each one is its own file with a date + slug id).'
NOT_SETTLED_HEADING = '## On other branches, not settled'
NOT_SETTLED_NOTE = (
    'These copies are only on the branches named, not in the working tree or on {develop}. '
    'None of them settles a fork: read them as context, and do not reuse their ids.'
)

DEFAULTS = {
    'ledger': ('docs/ledger', 'build/ledger.md'),
    'preferences': ('docs/preferences', 'build/preferences.md'),
}


class ToolError(Exception):
    """A message for the person running the tool; printed on stderr, exit 1."""


@dataclass
class Entry:
    rel: str  # path inside the kind's folder: `findings/<id>.md`, `runs/<name>.md` or `<id>.md`
    path: Path  # where it was read from; for a ref, `<remote>/<branch>:<repo path>`
    fm: dict[str, Any]
    body: str


# --- reading -------------------------------------------------------------------


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except OSError as e:
        raise ToolError(f'cannot read {path}: {e.strerror or e}') from e
    except UnicodeDecodeError as e:
        raise ToolError(f'{path}: not UTF-8') from e


def slugify(title: str) -> str:
    """Lower case, `a-z0-9` and single dashes, cut at a dash to SLUG_MAX characters."""
    s = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    if len(s) > SLUG_MAX:
        cut = s[:SLUG_MAX]
        if s[SLUG_MAX] != '-' and '-' in cut:
            cut = cut.rsplit('-', 1)[0]
        s = cut.strip('-')
    return s


def parse_entry_text(label: str, text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """Frontmatter, body and the problem with one entry's text; `label` names it in the problem."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, '', f'{label}: no frontmatter'
    try:
        fm = yaml.safe_load(m.group('fm')) or {}
    except yaml.YAMLError as e:
        return None, '', f'{label}: frontmatter does not parse: {" ".join(str(e).split())}'
    if not isinstance(fm, dict):
        return None, '', f'{label}: frontmatter is not a mapping'
    return fm, m.group('body'), None


def parse_entry(p: Path) -> tuple[dict[str, Any] | None, str, str | None]:
    """Frontmatter and body of one file, or the problem with it."""
    try:
        text = p.read_text(encoding='utf-8')
    except OSError as e:
        return None, '', f'{p}: cannot read: {e.strerror or e}'
    except UnicodeDecodeError:
        return None, '', f'{p}: not UTF-8'
    return parse_entry_text(str(p), text)


def load_entry(p: Path, rel: str) -> Entry:
    fm, body, bad = parse_entry(p)
    if fm is None:
        raise ToolError(str(bad))
    return Entry(rel, p, fm, body)


def entry_files(folder: Path, skipped: tuple[str, ...] = ()) -> list[Path]:
    """The `.md` entries in one flat folder; a dotfile such as `.gitkeep` is not an entry."""
    if not folder.is_dir():
        return []
    return [p for p in sorted(folder.glob('*.md')) if p.name not in skipped and '\n' not in p.name]


def load_entries(root: Path) -> list[Entry]:
    return [load_entry(p, f'{folder}/{p.name}') for folder in (FINDINGS, RUNS) for p in entry_files(root / folder)]


def load_pref_entries(root: Path) -> list[Entry]:
    if not root.is_dir():
        raise ToolError(f'{root}: not a directory of preferences')
    return [load_entry(p, p.name) for p in entry_files(root, PREF_SKIPPED)]


def id_list_of(e: Entry, key: str) -> list[str]:
    v = e.fm.get(key) or []
    return [str(x) for x in v] if isinstance(v, list) else []


def check_list_fields(e: Entry) -> None:
    """A run's `updates` and `sights` are lists of strings, else a problem naming the file."""
    if not e.rel.startswith(f'{RUNS}/'):
        return
    for key in ('updates', 'sights'):
        v = e.fm.get(key)
        if key in e.fm and not isinstance(v, list):
            raise ToolError(f'{e.path}: `{key}` must be a list')
        if isinstance(v, list) and not all(isinstance(x, str) for x in v):
            raise ToolError(f'{e.path}: `{key}` items must be strings')


def id_key(fid: str, date: str = '') -> tuple[int, str, str]:
    """F before H, then by date, then by slug."""
    if m := DATED_ID_RE.match(fid):
        return (0 if m.group(1) == 'F' else 1, date, m.group(3))
    return (9, date, fid)


def pref_key(pid: str, date: str = '') -> tuple[int, str, str]:
    if m := PREF_DATED_RE.match(pid):
        return (0, date, m.group(2))
    return (9, date, pid)


def pref_lead(body: str, start: int) -> str:
    """The bold lead after `start`, line breaks and their indentation collapsed to one space; '' if unclosed."""
    end = body.find('**', start)
    return re.sub(r'\s+', ' ', body[start:end]).strip() if end >= 0 else ''


# --- counts across branches ------------------------------------------------------
# `view --refs origin` reads the entries on every fetched refs/remotes/origin/* with git plumbing.


def git_run(*args: str, stdin: bytes | None = None) -> bytes:
    try:
        p = subprocess.run(['git', *args], input=stdin, capture_output=True, check=False)
    except OSError as e:
        raise ToolError(f'cannot run git: {e.strerror or e}') from e
    if p.returncode != 0:
        raise ToolError(f'git {" ".join(args)}: {p.stderr.decode("utf-8", "replace").strip()}')
    return p.stdout


def read_blobs(specs: list[str]) -> list[str]:
    """The text of each `<ref>:<path>`, through one `git cat-file --batch`."""
    if not specs:
        return []
    out = git_run('cat-file', '--batch', stdin=''.join(f'{x}\n' for x in specs).encode())
    texts: list[str] = []
    pos = 0
    for spec in specs:
        nl = out.find(b'\n', pos)
        fields = out[pos:nl].decode('utf-8', 'replace').split() if nl >= 0 else []
        if len(fields) != 3 or fields[1] != 'blob':
            raise ToolError(f'cannot read {spec} from git')
        size = int(fields[2])
        try:
            raw = out[nl + 1 : nl + 1 + size].decode('utf-8')
        except UnicodeDecodeError as e:
            raise ToolError(f'{spec}: not UTF-8') from e
        texts.append(raw.replace('\r\n', '\n').replace('\r', '\n'))  # universal newlines, as read_text gives
        pos = nl + 1 + size + 1
    return texts


def newest_commit_date(ref: str) -> str:
    return git_run('log', '-1', '--format=%cs', ref).decode().strip() or 'no commits'


def ref_paths(ref: str, base: str, kind: str) -> list[str]:
    """The repo paths of one ref's entries for `kind`, under `base` (a repo path ending in `/`)."""
    listing = git_run('ls-tree', '-r', '-z', '--name-only', ref, '--', base).decode('utf-8', 'replace')
    found: list[str] = []
    for x in listing.split('\0'):
        rest = x[len(base) :]
        if not x.startswith(base) or not x.endswith('.md') or '\n' in x:
            continue
        parts = rest.split('/')
        is_ledger_entry = len(parts) == 2 and parts[0] in (FINDINGS, RUNS)
        is_preference = len(parts) == 1 and rest not in PREF_SKIPPED
        if is_ledger_entry if kind == 'ledger' else is_preference:
            found.append(x)
    return found


def gather_refs(
    working: list[Entry], src: str, remote: str, kind: str
) -> tuple[list[Entry], str, dict[str, list[tuple[str, Entry]]]]:
    """The working tree's entries plus every fetched ref's, one copy per path, the page header, and every copy.

    The first copy of a path wins (the working tree first, then refs in name order). The third value maps each
    path to every copy read, as (source, entry), in read order; the source is `working tree` or `<remote>/<branch>`.
    """
    prefix = f'refs/remotes/{remote}/'
    head = f'{prefix}HEAD'
    refs = sorted(r for r in git_run('for-each-ref', '--format=%(refname)', prefix).decode().split() if r != head)
    if not refs:
        raise ToolError(f'no {prefix}* refs here; run `git fetch --prune {remote}` first')
    base = Path(src).as_posix().strip('/') + '/'  # a repo path, as git lists it
    counted: dict[str, Entry] = {}
    variants: dict[str, list[tuple[str, Entry]]] = {}

    def add(label: str, e: Entry) -> None:
        check_list_fields(e)
        counted.setdefault(e.rel, e)
        variants.setdefault(e.rel, []).append((label, e))

    for e in working:
        add('working tree', e)
    lines = [f'- working tree (HEAD {newest_commit_date("HEAD")})']
    for ref in refs:
        name = ref.removeprefix('refs/remotes/')
        paths = ref_paths(ref, base, kind)
        for x, text in zip(paths, read_blobs([f'{ref}:{x}' for x in paths]), strict=True):
            fm, body, bad = parse_entry_text(f'{name}:{x}', text)
            if fm is None:
                raise ToolError(str(bad))
            add(name, Entry(x[len(base) :], Path(f'{name}:{x}'), fm, body))
        lines.append(f'- {name} {newest_commit_date(ref)}{"" if paths else " (no entries)"}')
    for rel, found in variants.items():
        first = (found[0][1].fm, found[0][1].body)
        if any((e.fm, e.body) != first for _, e in found[1:]):
            lines.append(f'differs: {rel} ({", ".join(label for label, _ in found)})')
    intro = (
        'This view is not a gate. It reads the working tree and the refs below as already fetched; nothing is fetched.'
    )
    return list(counted.values()), intro + '\n\n' + '\n'.join(lines) + '\n\n', variants


# --- view --------------------------------------------------------------------


def write_view(dest: Path, text: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding='utf-8')


def cmd_view(args: argparse.Namespace) -> int:
    src = Path(args.src)
    entries = load_entries(src)
    for e in entries:
        check_list_fields(e)
    header = ''
    if args.refs:
        entries, header, _ = gather_refs(entries, args.src, args.refs, 'ledger')
    by_id: dict[str, Entry] = {}
    for e in entries:  # a finding has one row: the first counted copy of its id
        if e.rel.startswith(f'{FINDINGS}/'):
            by_id.setdefault(str(e.fm.get('id')), e)
    findings = sorted(by_id.values(), key=lambda e: id_key(str(e.fm.get('id')), str(e.fm.get('date') or '')))
    runs = sorted(
        (e for e in entries if e.rel.startswith(f'{RUNS}/')), key=lambda e: (str(e.fm.get('date') or ''), e.rel)
    )
    sighted = Counter(fid for e in runs for fid in id_list_of(e, 'sights'))
    rows = ['| id | kind | bin | count | title |', '| --- | --- | --- | --- | --- |']
    for e in findings:
        fid = str(e.fm.get('id'))
        title = str(e.fm.get('title') or '').replace('|', '\\|')
        rows.append(f'| {fid} | {e.fm.get("kind") or ""} | {e.fm.get("bin") or ""} | {sighted[fid]} | {title} |')
    readme = src / README_NAME
    parts = [read_text(readme).rstrip('\n') + '\n'] if readme.is_file() else ['# Ledger findings\n']
    if (src / TEMPLATES_NAME).is_file():
        parts.append(NEW_ENTRIES_LINE + '\n')
    parts.append('\n'.join(rows) + '\n')
    parts += [e.body.rstrip('\n') + '\n' for e in (*findings, *runs) if e.body.strip()]
    dest = Path(args.out)
    write_view(dest, header + '\n'.join(parts))
    print(f'wrote {dest}: {len(findings)} findings, {len(runs)} runs')
    return 0


def cmd_view_prefs(args: argparse.Namespace) -> int:
    src = Path(args.src)
    entries = load_pref_entries(src)
    header = ''
    variants: dict[str, list[tuple[str, Entry]]] = {}
    if args.refs:
        entries, header, variants = gather_refs(entries, args.src, args.refs, 'preferences')
    develop = f'{args.refs}/develop'
    # settled: the working tree's copy, else <remote>/develop's. Any other copy is only on other branches: it is
    # listed apart, as not settled, and never rendered as the settled text (even when develop has the same path).
    settled: list[Entry] = []
    elsewhere: list[tuple[Entry, list[str], bool]] = []  # (copy, its sources, whether a settled copy exists)
    for e in entries:
        copies = variants.get(e.rel) or [('working tree', e)]
        pick = next((x for want in ('working tree', develop) for label, x in copies if label == want), None)
        if pick is not None:
            settled.append(pick)
        known = [(x.fm, x.body) for label, x in copies if label == develop]
        if pick is not None:
            known.append((pick.fm, pick.body))
        groups: list[tuple[Entry, list[str]]] = []
        for label, x in copies:
            if (x.fm, x.body) in known:
                continue
            group = next((g for g in groups if (g[0].fm, g[0].body) == (x.fm, x.body)), None)
            if group is None:
                groups.append((x, [label]))
            elif label not in group[1]:
                group[1].append(label)
        elsewhere += [(x, labels, pick is not None) for x, labels in groups]

    def order(e: Entry) -> tuple[int, str, str]:
        return pref_key(str(e.fm.get('id')), str(e.fm.get('date') or ''))

    settled.sort(key=order)
    elsewhere.sort(key=lambda g: order(g[0]))
    readme = src / README_NAME
    parts = [header, (read_text(readme).rstrip('\n') + '\n' if readme.is_file() else PREFS_DEFAULT_TITLE) + '\n']
    if (src / TEMPLATES_NAME).is_file():
        parts.append(NEW_PREFS_LINE + '\n\n')
    parts += [e.body.rstrip('\n') + '\n' for e in settled]
    if elsewhere:
        parts.append(f'\n{NOT_SETTLED_HEADING}\n\n{NOT_SETTLED_NOTE.format(develop=develop)}\n')
        for x, labels, differs in elsewhere:
            note = ' (a different wording of a settled preference)' if differs else ''
            parts.append(f'\nOn {", ".join(labels)}{note}:\n\n' + x.body.rstrip('\n') + '\n')
    dest = Path(args.out)
    write_view(dest, ''.join(parts))
    print(f'wrote {dest}: {len(entries)} preferences')
    return 0


# --- check -------------------------------------------------------------------


def check_dated_id(
    p: Path, fm: dict[str, Any], m: re.Match[str] | None, mmdd: int, slug: int, hint: str, problems: list[str]
) -> None:
    """The shared rules for a date + slug id: MMDD is the date's, the slug is the title's, the file is `<id>.md`."""
    xid = str(fm['id'])
    date = str(fm.get('date', ''))
    if 'date' in fm and not DATE_RE.fullmatch(date):
        problems.append(f'{p}: date {date!r} is not YYYY-MM-DD')
    elif m and 'date' in fm and m.group(mmdd) != date[5:7] + date[8:10]:
        problems.append(f"{p}: {xid}: the id's MMDD ({m.group(mmdd)}) must be the month and day of date {date}")
    if not m:
        problems.append(f'{p}: id {xid!r} is not a date + slug id: {hint}')
    elif len(m.group(slug)) > SLUG_MAX:
        problems.append(f'{p}: {xid}: the slug is {len(m.group(slug))} characters, {SLUG_MAX} at most')
    elif 'title' in fm and m.group(slug) != slugify(str(fm['title'])):
        problems.append(f"{p}: {xid}: the slug must be the title's slug, {slugify(str(fm['title']))}")
    elif p.name != f'{xid}.md':
        problems.append(f'{p}: file name must be exactly {xid}.md')


def check_finding(p: Path, fm: dict[str, Any], problems: list[str]) -> None:
    if missing := [k for k in FINDING_REQUIRED if k not in fm]:
        problems.append(f'{p}: missing required field(s): {", ".join(missing)}')
    if 'id' in fm:
        m = DATED_ID_RE.match(str(fm['id']))
        check_dated_id(p, fm, m, 2, 3, NEW_ID_HINT, problems)
        if m:
            check_finding_kind_and_bin(p, fm, m.group(1), problems)


def check_finding_kind_and_bin(p: Path, fm: dict[str, Any], letter: str, problems: list[str]) -> None:
    """An F id is `kind: finding` with a bin of '1', '2' or '3'; an H id is `kind: harness` with a null bin."""
    xid = str(fm['id'])
    if 'kind' in fm and fm['kind'] != FINDING_KIND[letter]:
        problems.append(f'{p}: {xid}: kind must be {FINDING_KIND[letter]}, not {fm["kind"]!r}')
    if 'bin' not in fm:
        return
    if letter == 'H' and fm['bin'] is not None:
        problems.append(f'{p}: {xid}: a harness finding is never binned; bin must be null, not {fm["bin"]!r}')
    elif letter == 'F' and fm['bin'] not in FINDING_BINS:
        problems.append(f"{p}: {xid}: bin must be '1', '2' or '3' (quoted), not {fm['bin']!r}")


def check_run(p: Path, fm: dict[str, Any], problems: list[str]) -> None:
    missing = [k for k in RUN_REQUIRED if k not in fm]
    if missing:
        problems.append(f'{p}: missing required field(s): {", ".join(missing)}')
    for key in ('updates', 'sights'):
        if key in fm and not isinstance(fm[key], list):
            problems.append(f'{p}: `{key}` must be a list')
        elif key in fm and not all(isinstance(x, str) for x in fm[key]):
            problems.append(f'{p}: `{key}` items must be strings')
    if not missing:
        date, slug = str(fm['date']), slugify(str(fm['title']))
        if not DATE_RE.fullmatch(date):
            problems.append(f'{p}: date {date!r} is not YYYY-MM-DD')
        elif p.name != f'{date}-{slug}.md':
            problems.append(f'{p}: file name must be {date}-{slug}.md')


def flat_folder_problems(folder: Path, what: str) -> list[str]:
    """Entry folders are flat and hold only `.md` files (and dotfiles such as `.gitkeep`)."""
    problems = [
        f'{d}: a directory inside {folder}; entry folders are flat' for d in sorted(folder.iterdir()) if d.is_dir()
    ]
    problems += [
        f'{x}: not {what} (only .md files belong in {folder})'
        for x in sorted(folder.iterdir())
        if x.is_file() and x.suffix != '.md' and not x.name.startswith('.')
    ]
    return problems


def report(src: Path, problems: list[str], count: int) -> int:
    if problems:
        print(f'{len(problems)} problem(s) in {src}:', file=sys.stderr)
        for line in problems:
            print(f'  {line}', file=sys.stderr)
        return 1
    print(f'entries OK: {count} files in {src}')
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    src = Path(args.src)
    if not src.is_dir():
        raise ToolError(f'{src}: not a directory of entries')
    problems: list[str] = []
    defined: dict[str, list[Path]] = {}
    runs: list[tuple[Path, dict[str, Any]]] = []
    bodies: list[tuple[Path, str]] = []
    count = 0
    if not (src / README_NAME).is_file():
        problems.append(f'{src / README_NAME} is missing')
    for folder in (FINDINGS, RUNS):
        if not (src / folder).is_dir():
            problems.append(f'{src / folder} is missing: the ledger needs a {folder}/ folder')
            continue
        problems += flat_folder_problems(src / folder, 'an entry')
        for p in sorted((src / folder).glob('*.md')):
            count += 1
            fm, body, bad = parse_entry(p)
            if fm is None:
                problems.append(str(bad))
                continue
            bodies.append((p, body))
            if folder == FINDINGS:
                check_finding(p, fm, problems)
                if 'id' in fm:
                    defined.setdefault(str(fm['id']), []).append(p)
            else:
                check_run(p, fm, problems)
                runs.append((p, fm))
    for fid, paths in sorted(defined.items()):
        if len(paths) > 1:
            problems.append(f'{fid} defined twice: {", ".join(str(x) for x in paths)}')
    for p, fm in runs:
        for key in ('sights', 'updates'):
            ids = fm.get(key)
            for x in dict.fromkeys(str(i) for i in ids) if isinstance(ids, list) else []:
                if x not in defined:
                    problems.append(f'{p}: `{key}` names {x}, which no finding defines')
    for p, body in bodies:
        for x in dict.fromkeys(BODY_DATED_ID_RE.findall(body)):
            if x not in defined:
                problems.append(f'{p}: names {x}, which no finding file defines; add {src}/{FINDINGS}/{x}.md')
        for x in dict.fromkeys(BODY_ID_RE.findall(body)):
            # a bare token names its file only when exactly one dated id has that prefix
            short = [d for d in defined if d.startswith(f'{x}-')]
            if len(short) == 1:
                continue
            if short:
                problems.append(
                    f'{p}: {x} is the short form of {len(short)} findings ({", ".join(sorted(short))}); write the full id'
                )
            else:
                problems.append(f'{p}: names {x}, which no finding file defines; write the full F-MMDD-<slug> id')
    return report(src, problems, count)


def check_pref(p: Path, fm: dict[str, Any], body: str, problems: list[str]) -> None:
    if missing := [k for k in PREF_REQUIRED if k not in fm]:
        problems.append(f'{p}: missing required field(s): {", ".join(missing)}')
    if 'id' not in fm:
        return
    pid = str(fm['id'])
    lead = f'- **{pid}: '
    if not body.startswith(lead):
        problems.append(f'{p}: the body must start with `{lead}`')
    elif stray := [
        ln
        for ln in body.rstrip('\n').splitlines()[1:]
        if not ln.startswith('  ') or not ln.strip() or PREF_ITEM_RE.match(ln)
    ]:
        problems.append(
            f'{p}: the body must be exactly one item: every line after the first is indented two spaces, '
            f'with no blank line and no nested `- **P-` item (found {stray[0].strip()[:40]!r})'
        )
    elif 'title' in fm and pref_lead(body, len(lead)) != str(fm['title']):
        problems.append(f'{p}: title {str(fm["title"])!r} must equal the body lead {pref_lead(body, len(lead))!r}')
    check_dated_id(p, fm, PREF_DATED_RE.match(pid), 1, 2, PREF_NEW_ID_HINT, problems)


def cmd_check_prefs(args: argparse.Namespace) -> int:
    src = Path(args.src)
    if not src.is_dir():
        raise ToolError(f'{src}: not a directory of preferences')
    problems = flat_folder_problems(src, 'a preference')
    defined: dict[str, list[Path]] = {}
    files = [p for p in sorted(src.glob('*.md')) if p.name not in PREF_SKIPPED]
    for p in files:
        fm, body, bad = parse_entry(p)
        if fm is None:
            problems.append(str(bad))
            continue
        check_pref(p, fm, body, problems)
        if 'id' in fm:
            defined.setdefault(str(fm['id']), []).append(p)
    for pid, paths in sorted(defined.items(), key=lambda kv: pref_key(kv[0])):
        if len(paths) > 1:
            problems.append(f'{pid} defined twice: {", ".join(str(x) for x in paths)}')
    return report(src, problems, len(files))


# --- command line ------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    vp = sub.add_parser('view', help='build the combined page from the entries')
    vp.add_argument('--out', default=None, help='default build/ledger.md, or build/preferences.md for preferences')
    vp.add_argument(
        '--refs',
        default=None,
        metavar='REMOTE',
        help='also read the entries on every fetched refs/remotes/REMOTE/* (not HEAD), one copy per path',
    )
    cp = sub.add_parser('check', help='validate the entries')
    for p in (vp, cp):
        p.add_argument('--kind', choices=tuple(DEFAULTS), default='ledger')
        p.add_argument('--src', default=None, help='default docs/ledger, or docs/preferences for preferences')
    args = ap.parse_args(argv)
    default_src, default_out = DEFAULTS[args.kind]
    args.src = args.src or default_src
    if args.cmd == 'view':
        args.out = args.out or default_out
    prefs = args.kind == 'preferences'
    handler = {'view': (cmd_view, cmd_view_prefs), 'check': (cmd_check, cmd_check_prefs)}[args.cmd][prefs]
    try:
        return handler(args)
    except ToolError as e:
        print(str(e), file=sys.stderr)
        return 1
    except OSError as e:
        print(f'{e.filename or "I/O error"}: {e.strerror or e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
