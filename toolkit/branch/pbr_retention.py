"""pbr_retention.py - which shipped registers the repository keeps, and which are superseded.

A register is a build OUTPUT. Each one is 8 MB (branch) or 24 MB (PS & WP) of zip-compressed xlsx,
and git cannot delta-compress a zip, so every committed version adds its full size to the clone
permanently. The practice up to v8 was to drop the prior version in the same commit that shipped the
new one; it lapsed after v11 and v12 to v17 accumulated. This file makes the practice a mechanic the
driver runs, so it cannot lapse again.

The rule: keep the newest shipped register of each family and its immediate predecessor(s), the count set by
keep_newest in pbr_retention_v1.json, prune the rest,
EXCEPT where a version is still an input:

  pinned      the policy names it. PS_WP v127_CANDIDATE is the branch build's inheritance source,
              read by pbr_stage on every run and md5-stamped into the shipped workbook.
  referenced  a toolkit script or rule file names the file literally. The scan is the guard:
              retention never removes a file the toolkit still asks for by name, so a hard-coded
              default cannot be silently orphaned. A held file is reported with its citation.

Nothing here touches git history. Pruning stops the tree carrying superseded versions and caps
future growth; it does not reclaim what is already in the pack.

  python3 toolkit/branch/pbr_retention.py              # dry run, the default: report and change nothing
  python3 toolkit/branch/pbr_retention.py --apply      # delete the superseded files from the tree
  python3 toolkit/branch/pbr_retention.py --apply --git # stage the deletions with git rm as well
"""
import argparse, glob as _glob, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
POLICY = os.environ.get('PBR_RETENTION_POLICY', os.path.join(HERE, 'pbr_retention_v1.json'))


def load_policy(path=POLICY):
    with open(path) as fh:
        return json.load(fh)


def sort_key(name, version_re):
    """Version order, with the tie-break pbr_contractor_pull.latest_pswp already uses: on the same
    number a plain shipped file outranks a _CANDIDATE or _HANDOVER of that version."""
    m = re.search(version_re, name)
    if not m:
        return None
    return (int(m.group(1)), m.group(2) is None)


def scan_references(policy, root=ROOT):
    """Every register basename named literally by a toolkit script or rule file, with its citation."""
    cfg = policy.get('reference_scan') or {}
    cited = {}
    for sub in cfg.get('roots', ['toolkit']):
        for dirpath, _dirs, files in os.walk(os.path.join(root, sub)):
            if '__pycache__' in dirpath:
                continue
            for fn in files:
                if not fn.endswith(tuple(cfg.get('suffixes', ['.py', '.json']))):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, encoding='utf-8') as fh:
                        lines = fh.readlines()
                except (OSError, UnicodeDecodeError):
                    continue
                for n, line in enumerate(lines, 1):
                    for hit in re.findall(r'[A-Za-z0-9_]+_v\d+(?:_[A-Z]+)?\.xlsx', line):
                        cited.setdefault(hit, []).append(f'{os.path.relpath(p, root)}:{n}')
    return cited


def plan(regdir, policy=None, root=ROOT, below=None):
    """Classify every register in regdir as kept, held or superseded.

    below: optional {family_id: version} ceiling. The ship leg passes the version it just shipped so
    the run can only ever prune STRICTLY older files in that one family, never a newer one and never
    the other register's family.
    """
    policy = policy or load_policy()
    pinned = {p['file']: p['why'] for p in policy.get('pinned', [])}
    cited = scan_references(policy, root)
    keep_n = int(policy.get('keep_newest', 1))
    out = {'dir': regdir, 'keep_newest': keep_n, 'keep': [], 'held': [], 'prune': []}
    for fam in policy['families']:
        found = []
        for p in _glob.glob(os.path.join(regdir, fam['glob'])):
            k = sort_key(os.path.basename(p), fam['version_re'])
            if k is not None:
                found.append((k, p))
        found.sort(key=lambda t: t[0], reverse=True)
        for rank, (k, p) in enumerate(found):
            base = os.path.basename(p)
            rec = {'family': fam['id'], 'file': base, 'version': k[0],
                   'mb': round(os.path.getsize(p) / 1048576, 1), 'path': p}
            if rank < keep_n:
                rec['why'] = (f'newest shipped {fam["label"]} register' if rank == 0 else
                              f'predecessor {rank} of {keep_n - 1}, kept so the newest can be diffed '
                              f'against the register it was built from')
                out['keep'].append(rec)
            elif base in pinned:
                rec['why'] = 'pinned: ' + pinned[base]
                out['held'].append(rec)
            elif base in cited:
                rec['why'] = 'named literally by ' + ', '.join(sorted(set(cited[base])))
                out['held'].append(rec)
            elif below is not None and k[0] >= below.get(fam['id'], -1):
                rec['why'] = f'not below the {below.get(fam["id"])} ceiling this run was given'
                out['held'].append(rec)
            else:
                rec['why'] = f'superseded by {fam["label"]} v{found[0][0][0]}'
                out['prune'].append(rec)
    out['mb_pruned'] = round(sum(r['mb'] for r in out['prune']), 1)
    return out


def apply(pl, use_git=False, log=print):
    """Delete the superseded files. Returns the basenames removed."""
    done = []
    for rec in pl['prune']:
        if use_git:
            r = subprocess.run(['git', 'rm', '--quiet', '--', os.path.relpath(rec['path'], ROOT)],
                               cwd=ROOT, capture_output=True, text=True)
            if r.returncode:
                log(f'retention: git rm failed for {rec["file"]} ({r.stderr.strip()}); removing from the tree instead')
                os.remove(rec['path'])
        else:
            os.remove(rec['path'])
        done.append(rec['file'])
        log(f'retention: pruned {rec["file"]} ({rec["mb"]} MB), {rec["why"]}')
    return done


def prune_after_ship(outdir, family, version, log=print):
    """The ship leg's call. Runs only after a clean verify and a completed ship, and only ever prunes
    registers of the family just shipped that sit strictly below the version just shipped. Set
    PBR_RETAIN=all to keep every version instead."""
    if os.environ.get('PBR_RETAIN') == 'all':
        log('retention: PBR_RETAIN=all, keeping every shipped version')
        return []
    pl = plan(outdir, below={family: int(version)})
    for rec in pl['held']:
        log(f'retention: held {rec["file"]} ({rec["mb"]} MB), {rec["why"]}')
    return apply(pl, use_git=False, log=log)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dir', default=os.path.join(ROOT, 'registers'), help='register directory (default registers/)')
    ap.add_argument('--apply', action='store_true', help='delete the superseded files (default is a dry run)')
    ap.add_argument('--git', action='store_true', help='stage the deletions with git rm')
    a = ap.parse_args(argv)
    pl = plan(a.dir)
    for rec in pl['keep']:
        print(f'  keep    {rec["file"]:<55} {rec["mb"]:>6.1f} MB  {rec["why"]}')
    for rec in pl['held']:
        print(f'  held    {rec["file"]:<55} {rec["mb"]:>6.1f} MB  {rec["why"]}')
    for rec in pl['prune']:
        print(f'  prune   {rec["file"]:<55} {rec["mb"]:>6.1f} MB  {rec["why"]}')
    if not pl['prune']:
        print(f'\nNothing superseded. The tree already carries at most {pl["keep_newest"]} register(s) per family.')
        return 0
    print(f'\n{len(pl["prune"])} superseded file(s), {pl["mb_pruned"]} MB in the working tree.')
    if not a.apply:
        print('Dry run. Re-run with --apply (add --git to stage the deletions) to remove them.')
        return 0
    apply(pl, use_git=a.git)
    print(f'\nPruned {pl["mb_pruned"]} MB from the tree. This does not shrink .git: the objects stay '
          'reachable from the commits that shipped them.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
