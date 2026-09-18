"""pbr_reports.py - the derived reports as one leg, and the check that they match the shipped register.

WHY THIS EXISTS. `pbr_contractor_pull.py`, `pbr_journal_pull_report.py`, `pbr_unidentified_queue.py` and
`pbr_sighted_coverage.py` each read the shipped registers and each is a separate command. Nothing made the build run them, so a version could
ship with its reports left at the previous one, and the only symptom would be a figure quoted to Finance that
the register had already moved past. Every version from v12 to v25 does in fact carry a full set, so the
practice held; what was missing was anything that would notice if it stopped.

BOTH REGISTERS, EVERY TIME. The contractor pull and the journal pull are each cut from BOTH registers, and
only the branch version appears in the filename. A PS & WP register that moves while the branch stands still
therefore leaves those reports stale under a filename that still looks right. That is not hypothetical:
regenerating the contractor pull against PS & WP v128 rather than v129 changes 16 lines of the same
Contractor_Pull_v25.md. So the check compares the md5 of BOTH registers the reports were built from, recorded
in the manifest by --build, and `assert_sources` names and checks both on every pull that is created or
requested, whoever runs it and however.

`--check` stays cheap enough for the ship leg: it reads two filenames per family and two md5s, never regenerating. With no
manifest the answer is UNVERIFIED, not a pass, because nothing then records what the reports were cut from.

Usage:
  python3 toolkit/branch/pbr_reports.py --check v25    # current at this version, from both registers unchanged?
  python3 toolkit/branch/pbr_reports.py --build        # regenerate every family from the newest shipped registers
  python3 toolkit/branch/pbr_reports.py --build --out /tmp/x   # ... to somewhere else, to diff before shipping
"""
import argparse, datetime, glob as _glob, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
REPORTS = os.path.join(ROOT, 'reports')
MANIFEST = 'pull_reports_manifest.json'

# stem -> (script, reads_both_registers). The argv shapes differ and getting them wrong is silent:
# pbr_unidentified_queue.py takes (branch register, outdir) and reads the branch register ONLY, so handing
# it the PS & WP register as a third argument would make it the OUTPUT DIRECTORY, not a second source.
FAMILIES = {
    'Contractor_Pull': ('pbr_contractor_pull.py', True),
    'Journal_Pull': ('pbr_journal_pull_report.py', True),
    'Unidentified_Contractors': ('pbr_unidentified_queue.py', False),
    'Sighted_Coverage': ('pbr_sighted_coverage.py', True),
}
BOTH_REGISTER_FAMILIES = tuple(k for k, (_, both) in FAMILIES.items() if both)


def latest(pattern, regdir=None):
    """Newest shipped register matching a glob, by version number rather than by name or mtime."""
    best, bestv = None, -1
    for p in _glob.glob(os.path.join(regdir or os.path.join(ROOT, 'registers'), pattern)):
        m = re.search(r'_v(\d+)(?:_[A-Z]+)?\.xlsx$', os.path.basename(p))
        if m and int(m.group(1)) > bestv and 'CANDIDATE' not in os.path.basename(p):
            best, bestv = p, int(m.group(1))
    return best


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sources(branch=None, pswp=None):
    """The two registers every one of these reports is cut from, with the md5 that identifies each."""
    b = branch or latest('Parks_Branch_Transaction_Register_FY2627_v*.xlsx')
    p = pswp or latest('PS_WP_Transaction_Register_3FY_v*.xlsx')
    return {'branch': {'file': os.path.basename(b), 'md5': md5(b)} if b else None,
            'pswp': {'file': os.path.basename(p), 'md5': md5(p)} if p else None}


def check(ver, reports=REPORTS, branch=None, pswp=None):
    """Why these reports are not current, as a list of reasons. Empty list means current.

    TWO REGISTERS, ONE VERSION IN THE NAME. Every one of these reports is cut from BOTH registers, and the
    branch version is the only one in the filename. So a PS & WP register that moves while the branch stands
    still leaves the reports stale under a filename that still looks right, and a check on the filename alone
    cannot see it. Confirmed rather than assumed: regenerating the contractor pull against PS & WP v128 rather
    than v129 changes 16 lines of the same Contractor_Pull_v25.md.

    Existence is therefore only the first limb. The second compares the md5 of both registers the reports were
    actually built from, recorded by --build, against the registers on disk now. With no manifest the answer is
    UNVERIFIED, which is not a pass: nothing records what the reports were cut from, so nothing can say.
    """
    v = ver if str(ver).startswith('v') else f'v{ver}'
    reasons = []
    missing = [f'{stem}_{v}.{ext}' for stem in FAMILIES for ext in ('md', 'xlsx')
               if not os.path.exists(os.path.join(reports, f'{stem}_{v}.{ext}'))]
    if missing:
        reasons.append(f'{len(missing)} file(s) missing at {v}: ' + ', '.join(missing[:4])
                       + ('...' if len(missing) > 4 else ''))
    mpath = os.path.join(reports, MANIFEST)
    if not os.path.exists(mpath):
        reasons.append(f'UNVERIFIED: no {MANIFEST}, so nothing records which registers these were cut from')
        return reasons
    try:
        man = json.load(open(mpath))
    except (ValueError, OSError) as e:
        reasons.append(f'UNVERIFIED: {MANIFEST} unreadable ({e})')
        return reasons
    now, was = sources(branch, pswp), man.get('sources') or {}
    for side in ('branch', 'pswp'):
        a, b = was.get(side), now.get(side)
        if not b:
            reasons.append(f'{side} register not found on disk')
        elif not a:
            reasons.append(f'UNVERIFIED: manifest records no {side} register')
        elif a.get('md5') != b.get('md5'):
            reasons.append(f'{side} register CHANGED since the reports were built: '
                           f'{a.get("file")} ({(a.get("md5") or "")[:8]}) -> {b["file"]} ({b["md5"][:8]})')
    return reasons


def assert_sources(bpath, ppath, tool='pull', log=print):
    """Check BOTH registers every time a contractor or journal pull is created or requested.

    These two reports partition their scope across the registers: the assessed years come from the newest
    shipped PS & WP register and FY2026/27 from the Parks Branch register. Reading a superseded copy of
    either does not fail and does not look wrong; it quietly asks Finance for documents a later version has
    already sighted. So the sources are named on every run and a superseded one is called out by name.

    It warns rather than exits. A pull taken deliberately against an older register is a legitimate thing to
    do (reproducing a figure someone is querying), and the run says plainly which registers it used either way.
    """
    newest = {'branch': latest('Parks_Branch_Transaction_Register_FY2627_v*.xlsx'),
              'pswp': latest('PS_WP_Transaction_Register_3FY_v*.xlsx')}
    given = {'branch': bpath, 'pswp': ppath}
    stale = []
    for side, want in newest.items():
        got = given[side]
        if not got or not os.path.exists(got):
            stale.append(f'{side} register not found ({got})')
        elif want and os.path.abspath(got) != os.path.abspath(want):
            stale.append(f'{side}: reading {os.path.basename(got)}, newest shipped is {os.path.basename(want)}')
    log(f'{tool}: branch={os.path.basename(bpath) if bpath else None} '
        f'pswp={os.path.basename(ppath) if ppath else None}')
    for w in stale:
        log(f'  WARNING both-register check: {w}')
    return stale


def build(out=REPORTS, branch=None, pswp=None, log=print):
    b = branch or latest('Parks_Branch_Transaction_Register_FY2627_v*.xlsx')
    p = pswp or latest('PS_WP_Transaction_Register_3FY_v*.xlsx')
    if not b or not p:
        raise SystemExit(f'cannot find a shipped register: branch={b} pswp={p}')
    os.makedirs(out, exist_ok=True)
    log(f'reports: branch={os.path.basename(b)} pswp={os.path.basename(p)} -> {out}')
    for stem, (script, both) in FAMILIES.items():
        argv = [b, p, out] if both else [b, out]
        r = subprocess.run([sys.executable, os.path.join(HERE, script)] + argv,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f'{script} failed ({r.returncode}):\n{r.stderr[-2000:]}')
        log(f'  {stem}: written')
    man = {
        '_readme': [
            "What the derived reports in this directory were last cut from. Written by pbr_reports.py --build.",
            "Both registers are recorded because every one of these reports reads BOTH, while only the branch",
            "version appears in the filename. A PS & WP register that moves while the branch stands still leaves",
            "the reports stale under a filename that still looks right, and only the md5 below catches it.",
        ],
        'built_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'families': sorted(FAMILIES),
        'sources': sources(b, p),
    }
    with open(os.path.join(out, MANIFEST), 'w') as fh:
        json.dump(man, fh, indent=1)
        fh.write('\n')
    log(f'  {MANIFEST}: branch={man["sources"]["branch"]["md5"][:8]} pswp={man["sources"]["pswp"]["md5"][:8]}')
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', metavar='VER', help='assert every report family exists at this register version')
    ap.add_argument('--build', action='store_true', help='regenerate every family from the newest shipped registers')
    ap.add_argument('--out', default=REPORTS, help='output directory (default reports/)')
    a = ap.parse_args(argv)
    if a.check:
        reasons = check(a.check, a.out)
        if reasons:
            print(f'reports NOT CURRENT for {a.check}:')
            for r in reasons:
                print(f'  - {r}')
            print('Re-run: python3 toolkit/branch/pbr_reports.py --build')
            return 1
        src = sources()
        print(f'reports current for {a.check}: all {len(FAMILIES)} families (md and xlsx), cut from '
              f'{src["branch"]["file"]} and {src["pswp"]["file"]}, both md5 unchanged')
        return 0
    if a.build:
        build(a.out)
        return 0
    ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
