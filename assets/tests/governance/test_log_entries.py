"""Tests for governance/scripts/log_entries.py, the one-file-per-entry ledger and preferences.

Each test writes a small tree of entries into ``tmp_path`` and drives the script through
``main``, the way ``make ledger``, ``make preferences`` and ``make entries-check`` do.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import log_entries as le
import pytest

# --- builders ------------------------------------------------------------------


def finding(root: Path, title: str, date: str = '2026-01-06', letter: str = 'F', bin_: str | None = '2') -> str:
    """Write one finding under `root/findings/` and return its id."""
    fid = f'{letter}-{date[5:7]}{date[8:10]}-{le.slugify(title)}'
    kind = 'finding' if letter == 'F' else 'harness'
    bin_text = 'null' if bin_ is None else f"'{bin_}'"
    (root / 'findings').mkdir(parents=True, exist_ok=True)
    (root / 'findings' / f'{fid}.md').write_text(
        f"---\nid: {fid}\nkind: {kind}\ntitle: '{title}'\ndate: '{date}'\nbin: {bin_text}\n---\n"
        f'### {fid} — {title}\n- **Claim:** something checkable\n'
    )
    return fid


def run(root: Path, title: str, sights: list[str], date: str = '2026-01-07', body: str = '') -> Path:
    """Write one triage run under `root/runs/` and return its path."""
    (root / 'runs').mkdir(parents=True, exist_ok=True)
    p = root / 'runs' / f'{date}-{le.slugify(title)}.md'
    p.write_text(
        f"---\ndate: '{date}'\ntitle: '{title}'\nupdates: []\nsights: [{', '.join(sights)}]\n---\n"
        f'### {title}\n{body or "- seen again"}\n'
    )
    return p


def ledger_root(tmp_path: Path) -> Path:
    root = tmp_path / 'docs' / 'ledger'
    for folder in ('findings', 'runs'):
        (root / folder).mkdir(parents=True)
        (root / folder / '.gitkeep').write_text('')
    (root / 'README.md').write_text('# Ledger findings\n')
    return root


def preference(root: Path, title: str, date: str = '2026-01-06', text: str = 'Why, and where it came from.') -> str:
    pid = f'P-{date[5:7]}{date[8:10]}-{le.slugify(title)}'
    root.mkdir(parents=True, exist_ok=True)
    (root / f'{pid}.md').write_text(
        f'---\nid: {pid}\ntitle: "{title}"\ndate: \'{date}\'\n---\n- **{pid}: {title}** {text}\n'
    )
    return pid


def check(src: Path, kind: str = 'ledger') -> int:
    return le.main(['check', '--kind', kind, '--src', str(src)])


# --- check: ledger -------------------------------------------------------------


def test_an_empty_ledger_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check(ledger_root(tmp_path)) == 0
    assert 'entries OK: 0 files' in capsys.readouterr().out


def test_a_finding_and_its_run_pass(tmp_path: Path) -> None:
    root = ledger_root(tmp_path)
    fid = finding(root, 'Sightings per round')
    run(root, 'T-02 (#12) triage', [fid], body=f'- {fid}: seen in review')
    assert check(root) == 0


def test_a_duplicate_full_id_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = ledger_root(tmp_path)
    fid = finding(root, 'Sightings per round')
    # a second file with the same id, as two parallel branches could add under different names
    (root / 'findings' / 'copy.md').write_text((root / 'findings' / f'{fid}.md').read_text())
    assert check(root) == 1
    assert f'{fid} defined twice' in capsys.readouterr().err


def test_a_run_naming_a_missing_finding_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = ledger_root(tmp_path)
    run(root, 'A triage', ['F-0106-nobody-wrote-this'])
    assert check(root) == 1
    assert '`sights` names F-0106-nobody-wrote-this, which no finding defines' in capsys.readouterr().err


def test_a_body_naming_a_missing_finding_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = ledger_root(tmp_path)
    run(root, 'A triage', [], body='- F-0106-only-a-bullet (new): never got its own file')
    assert check(root) == 1
    assert 'names F-0106-only-a-bullet, which no finding file defines' in capsys.readouterr().err


def test_a_short_id_passes_only_while_one_finding_has_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = ledger_root(tmp_path)
    finding(root, 'First thing')
    run(root, 'A triage', [], body='- F-0106 again')
    assert check(root) == 0
    finding(root, 'Second thing')
    assert check(root) == 1
    assert 'F-0106 is the short form of 2 findings' in capsys.readouterr().err


@pytest.mark.parametrize(
    ('edit', 'message'),
    [
        (lambda t: t.replace("date: '2026-01-06'", "date: '2026-01-09'"), "the id's MMDD (0106)"),
        (lambda t: t.replace("title: 'Sightings per round'", "title: 'Something else'"), "the title's slug"),
        (lambda t: t.replace("bin: '2'\n", ''), 'missing required field(s): bin'),
        (lambda t: t.replace('id: F-0106-sightings-per-round', 'id: F-7'), 'is not a date + slug id'),
    ],
)
def test_a_bad_finding_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str], edit, message: str) -> None:
    root = ledger_root(tmp_path)
    p = root / 'findings' / f'{finding(root, "Sightings per round")}.md'
    p.write_text(edit(p.read_text()))
    assert check(root) == 1
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    ('letter', 'edit', 'message'),
    [
        ('F', lambda t: t.replace('kind: finding', 'kind: harness'), 'kind must be finding'),
        ('H', lambda t: t.replace('kind: harness', 'kind: finding'), 'kind must be harness'),
        ('F', lambda t: t.replace("bin: '2'", "bin: '4'"), "bin must be '1', '2' or '3'"),
        ('F', lambda t: t.replace("bin: '2'", 'bin: 2'), "bin must be '1', '2' or '3'"),
        ('F', lambda t: t.replace("bin: '2'", 'bin: null'), "bin must be '1', '2' or '3'"),
        ('H', lambda t: t.replace('bin: null', "bin: '2'"), 'a harness finding is never binned'),
    ],
)
def test_a_wrong_kind_or_bin_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], letter: str, edit, message: str
) -> None:
    root = ledger_root(tmp_path)
    fid = finding(root, 'Sightings per round', letter=letter, bin_=None if letter == 'H' else '2')
    p = root / 'findings' / f'{fid}.md'
    p.write_text(edit(p.read_text()))
    assert check(root) == 1
    assert message in capsys.readouterr().err


def test_a_run_with_the_wrong_file_name_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = ledger_root(tmp_path)
    run(root, 'A triage', []).rename(root / 'runs' / 'whatever.md')
    assert check(root) == 1
    assert 'file name must be 2026-01-07-a-triage.md' in capsys.readouterr().err


def test_a_stray_file_or_folder_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = ledger_root(tmp_path)
    (root / 'findings' / 'notes.txt').write_text('x')
    (root / 'runs' / 'nested').mkdir()
    assert check(root) == 1
    err = capsys.readouterr().err
    assert 'notes.txt: not an entry' in err
    assert 'nested: a directory inside' in err


# --- check: preferences --------------------------------------------------------


def test_preferences_pass_and_an_empty_folder_passes(tmp_path: Path) -> None:
    root = tmp_path / 'prefs'
    root.mkdir()
    (root / '.gitkeep').write_text('')
    assert check(root, 'preferences') == 0
    preference(root, 'Small PRs.')
    assert check(root, 'preferences') == 0


def test_a_duplicate_preference_id_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / 'prefs'
    pid = preference(root, 'Small PRs.')
    (root / 'copy.md').write_text((root / f'{pid}.md').read_text())
    assert check(root, 'preferences') == 1
    assert f'{pid} defined twice' in capsys.readouterr().err


def test_a_preference_whose_title_is_not_its_lead_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / 'prefs'
    p = root / f'{preference(root, "Small PRs.")}.md'
    p.write_text(p.read_text().replace('**P-0106-small-prs: Small PRs.**', '**P-0106-small-prs: Big PRs.**'))
    assert check(root, 'preferences') == 1
    assert 'must equal the body lead' in capsys.readouterr().err


def test_a_numbered_preference_id_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / 'prefs'
    root.mkdir()
    (root / 'P-6-small-prs.md').write_text(
        '---\nid: P-6\ntitle: "Small PRs."\ndate: \'2026-01-06\'\n---\n- **P-6: Small PRs.** x\n'
    )
    assert check(root, 'preferences') == 1
    assert 'is not a date + slug id' in capsys.readouterr().err


# --- view ----------------------------------------------------------------------


def test_the_ledger_view_counts_sightings_and_keeps_every_entry(tmp_path: Path) -> None:
    root = ledger_root(tmp_path)
    fid = finding(root, 'Sightings per round')
    hid = finding(root, 'Gate too slow', letter='H', bin_=None)
    run(root, 'First triage', [fid], date='2026-01-07')
    run(root, 'Second triage', [fid, fid, hid], date='2026-01-08')
    out = tmp_path / 'build' / 'ledger.md'
    assert le.main(['view', '--src', str(root), '--out', str(out)]) == 0
    text = out.read_text()
    assert text.startswith('# Ledger findings\n')
    assert f'| {fid} | finding | 2 | 3 | Sightings per round |' in text
    assert f'| {hid} | harness |  | 1 | Gate too slow |' in text
    # F rows before H rows; the runs follow the findings, oldest first
    assert text.index(f'| {fid} ') < text.index(f'| {hid} ')
    assert text.index('### First triage') < text.index('### Second triage')
    assert text.index(f'### {hid}') < text.index('### First triage')


def test_the_preferences_view_lists_every_preference_in_order(tmp_path: Path) -> None:
    root = tmp_path / 'prefs'
    later = preference(root, 'Later one.', date='2026-01-09')
    earlier = preference(root, 'Earlier one.', date='2026-01-02')
    out = tmp_path / 'build' / 'preferences.md'
    assert le.main(['view', '--kind', 'preferences', '--src', str(root), '--out', str(out)]) == 0
    text = out.read_text()
    assert text.startswith('# Standing preferences\n')
    assert text.index(f'- **{earlier}: ') < text.index(f'- **{later}: ')


# --- view --refs ---------------------------------------------------------------


def git(cwd: Path, *args: str) -> str:
    env = {
        **os.environ,
        'GIT_AUTHOR_NAME': 't',
        'GIT_AUTHOR_EMAIL': 't@example.com',
        'GIT_COMMITTER_NAME': 't',
        'GIT_COMMITTER_EMAIL': 't@example.com',
        'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_CONFIG_NOSYSTEM': '1',
    }
    return subprocess.run(['git', *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


def test_refs_counts_sightings_and_flags_unsettled_preferences_on_other_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = ledger_root(tmp_path)
    prefs = tmp_path / 'docs' / 'preferences'
    fid = finding(ledger, 'Sightings per round')
    run(ledger, 'First triage', [fid], date='2026-01-07')
    settled = preference(prefs, 'Small PRs.')
    git(tmp_path, 'init', '-q', '-b', 'develop')
    git(tmp_path, 'add', '-A')
    git(tmp_path, 'commit', '-q', '-m', 'base')
    git(tmp_path, 'update-ref', 'refs/remotes/origin/develop', 'HEAD')
    # a feature branch, pushed and fetched, that logs a second sighting and proposes a preference
    git(tmp_path, 'checkout', '-q', '-b', 'feature')
    run(ledger, 'Second triage', [fid], date='2026-01-08')
    pending = preference(prefs, 'Tests first.', date='2026-01-08')
    git(tmp_path, 'add', '-A')
    git(tmp_path, 'commit', '-q', '-m', 'feature')
    git(tmp_path, 'update-ref', 'refs/remotes/origin/feature', 'HEAD')
    git(tmp_path, 'checkout', '-q', 'develop')
    assert not (prefs / f'{pending}.md').exists()
    monkeypatch.chdir(tmp_path)

    assert le.main(['view', '--out', 'build/ledger.md']) == 0
    assert f'| {fid} | finding | 2 | 1 |' in Path('build/ledger.md').read_text()
    assert le.main(['view', '--out', 'build/ledger.md', '--refs', 'origin']) == 0
    text = Path('build/ledger.md').read_text()
    assert text.startswith('This view is not a gate.')
    assert '- origin/feature ' in text
    assert f'| {fid} | finding | 2 | 2 |' in text

    assert le.main(['view', '--kind', 'preferences', '--out', 'build/preferences.md', '--refs', 'origin']) == 0
    text = Path('build/preferences.md').read_text()
    head, _, others = text.partition(le.NOT_SETTLED_HEADING)
    assert f'- **{settled}: ' in head
    assert f'- **{pending}: ' in others
    assert 'On origin/feature:' in others


def test_refs_without_fetched_refs_says_to_fetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ledger_root(tmp_path)
    git(tmp_path, 'init', '-q')
    monkeypatch.chdir(tmp_path)
    assert le.main(['view', '--refs', 'origin']) == 1
    assert 'git fetch --prune origin' in capsys.readouterr().err
