"""commit_budget.py - the pre-commit guard: what may be committed, and why not.

Run by toolkit/git-hooks/pre-commit. Reads commit_budget_v1.json beside it and inspects the STAGED tree only,
so it costs nothing on a normal commit and never looks at the working tree or the network.

Three refusals, each with the file and the reason:
  deny_globs   a path that must never be committed at all (a binder PDF, a report workbook)
  max_mb       any blob over the budget that no allow_paths entry covers
  (allow)      allow_paths names the inputs that are exempt, and says why each is an input rather than an output

The test is reproducibility, not size. A file a script here can rebuild is an output and does not belong in
history; a file nothing here can rebuild is an input and has to be kept.
"""
import fnmatch, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
POLICY = os.path.join(HERE, 'commit_budget_v1.json')


def staged():
    """(path, size_bytes) for every file this commit adds or modifies. Deletions are not a size problem."""
    out = subprocess.run(['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
                         capture_output=True, text=True).stdout
    rows = []
    for p in out.splitlines():
        p = p.strip()
        if not p:
            continue
        r = subprocess.run(['git', 'cat-file', '-s', f':{p}'], capture_output=True, text=True)
        rows.append((p, int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else 0))
    return rows


def main():
    if not os.path.exists(POLICY):
        return 0
    with open(POLICY) as fh:
        pol = json.load(fh)
    allow = pol.get('allow_paths', [])
    deny = pol.get('deny_globs', [])
    cap = float(pol.get('max_mb', 5)) * 1048576

    def allowed(path):
        for a in allow:
            g = a['path']
            if fnmatch.fnmatch(path, g) or (g.endswith('/**') and path.startswith(g[:-3])):
                return a
        return None

    problems = []
    for path, size in staged():
        ok = allowed(path)
        for d in deny:
            if fnmatch.fnmatch(path, d['glob']) or fnmatch.fnmatch(os.path.basename(path), d['glob']):
                if not ok:
                    problems.append((path, size, d['why']))
                break
        else:
            if size > cap and not ok:
                problems.append((path, size, f'{size / 1048576:.1f} MB exceeds the {cap / 1048576:.0f} MB budget '
                                             f'and no allow_paths entry covers it. A file this repository can '
                                             f'rebuild is an output: leave it untracked and regenerate it.'))
    if not problems:
        return 0
    if os.environ.get('PBR_ALLOW_BIG'):
        print('commit budget: OVERRIDDEN by PBR_ALLOW_BIG for %d file(s):' % len(problems), file=sys.stderr)
        for p, s, _ in problems:
            print(f'  {p} ({s / 1048576:.1f} MB)', file=sys.stderr)
        return 0
    print('\ncommit REFUSED by the commit budget (toolkit/git-hooks/commit_budget_v1.json):\n', file=sys.stderr)
    for p, s, why in problems:
        print(f'  {p}  ({s / 1048576:.1f} MB)', file=sys.stderr)
        print(f'      {why}\n', file=sys.stderr)
    print('An xlsx is a zip git cannot delta-compress, so a file committed once costs its full size in every',
          file=sys.stderr)
    print('clone forever and no later deletion takes it back out. Unstage it, or set PBR_ALLOW_BIG=1 for this',
          file=sys.stderr)
    print('commit if it is genuinely an input nothing here can rebuild (then add it to allow_paths).\n',
          file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
