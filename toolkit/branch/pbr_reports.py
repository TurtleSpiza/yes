"""pbr_reports.py - the three pull reports as one leg, and the check that they match the shipped register.

WHY THIS EXISTS. `pbr_contractor_pull.py`, `pbr_journal_pull_report.py` and `pbr_unidentified_queue.py` each
read the shipped registers and each is a separate command. Nothing made the build run them, so a version could
ship with its reports left at the previous one, and the only symptom would be a figure quoted to Finance that
the register had already moved past. Every version from v12 to v25 does in fact carry a full set, so the
practice held; what was missing was anything that would notice if it stopped.

The check is deliberately the cheap half. Regenerating all three takes longer than the build itself, so the
ship leg asserts only that a report of the shipped version EXISTS for each of the three, which is what catches
the lapse this guards against: reports left behind at an older version. Proving the contents are current is
`--build`, which regenerates them, and a diff.

Usage:
  python3 toolkit/branch/pbr_reports.py --check v25    # do all three reports exist at this version?
  python3 toolkit/branch/pbr_reports.py --build        # regenerate all three from the newest shipped registers
  python3 toolkit/branch/pbr_reports.py --build --out /tmp/x   # ... to somewhere else, to diff before shipping
"""
import argparse, glob as _glob, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
REPORTS = os.path.join(ROOT, 'reports')

# stem -> the script that writes it. All three take (branch register, pswp register, outdir).
FAMILIES = {
    'Contractor_Pull': 'pbr_contractor_pull.py',
    'Journal_Pull': 'pbr_journal_pull_report.py',
    'Unidentified_Contractors': 'pbr_unidentified_queue.py',
}


def latest(pattern, regdir=None):
    """Newest shipped register matching a glob, by version number rather than by name or mtime."""
    best, bestv = None, -1
    for p in _glob.glob(os.path.join(regdir or os.path.join(ROOT, 'registers'), pattern)):
        m = re.search(r'_v(\d+)(?:_[A-Z]+)?\.xlsx$', os.path.basename(p))
        if m and int(m.group(1)) > bestv and 'CANDIDATE' not in os.path.basename(p):
            best, bestv = p, int(m.group(1))
    return best


def check(ver, reports=REPORTS):
    """Which of the three families is missing a report at this version. Empty list means all present."""
    v = ver if str(ver).startswith('v') else f'v{ver}'
    missing = []
    for stem in FAMILIES:
        for ext in ('md', 'xlsx'):
            if not os.path.exists(os.path.join(reports, f'{stem}_{v}.{ext}')):
                missing.append(f'{stem}_{v}.{ext}')
    return missing


def build(out=REPORTS, branch=None, pswp=None, log=print):
    b = branch or latest('Parks_Branch_Transaction_Register_FY2627_v*.xlsx')
    p = pswp or latest('PS_WP_Transaction_Register_3FY_v*.xlsx')
    if not b or not p:
        raise SystemExit(f'cannot find a shipped register: branch={b} pswp={p}')
    os.makedirs(out, exist_ok=True)
    log(f'reports: branch={os.path.basename(b)} pswp={os.path.basename(p)} -> {out}')
    for stem, script in FAMILIES.items():
        r = subprocess.run([sys.executable, os.path.join(HERE, script), b, p, out],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f'{script} failed ({r.returncode}):\n{r.stderr[-2000:]}')
        log(f'  {stem}: written')
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', metavar='VER', help='assert all three reports exist at this register version')
    ap.add_argument('--build', action='store_true', help='regenerate all three from the newest shipped registers')
    ap.add_argument('--out', default=REPORTS, help='output directory (default reports/)')
    a = ap.parse_args(argv)
    if a.check:
        missing = check(a.check, a.out)
        if missing:
            print(f'reports STALE for {a.check}: {len(missing)} file(s) missing -> ' + ', '.join(missing))
            print('Re-run: python3 toolkit/branch/pbr_reports.py --build')
            return 1
        print(f'reports present for {a.check}: all three families, md and xlsx')
        return 0
    if a.build:
        build(a.out)
        return 0
    ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
