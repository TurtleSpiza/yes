"""pbr_binder_retention.py - delete a binder once it has been parsed with no issues, keep it otherwise.

WHY THIS EXISTS. A binder PDF is evidence that is sighted, parsed and screened. It is not a repository
artefact: `*.pdf` is ignored by git, so the copy on disk is the only copy, and deleting it is permanent.
That is the point, and it is also why the decision needs a rule rather than a judgement made per file.

WHAT MAKES A DELETION SAFE. Almost everything a corpus is ever checked on survives the binder, because
the capture retains the page text. One thing does not. Fill colour is not in the text layer, so a row a
supplier has masked reads back from `pdftotext` exactly like a row the page prints, and no retained text
can tell them apart. The masked-row verdict can only be learned by rendering the page. So a binder may be
deleted only once that verdict has been taken and written down against its own md5, and the other
conditions in pbr_binder_retention_v1.json say the same thing about the checks they cover: each one is a
question that needs the page, asked and answered before the page goes.

A binder that fails any condition is KEPT, with the reason printed. The default is a dry run.

Usage:
  python3 toolkit/branch/pbr_binder_retention.py            # dry run: what would be deleted, and what is kept and why
  python3 toolkit/branch/pbr_binder_retention.py --apply    # delete the binders that qualify
  python3 toolkit/branch/pbr_binder_retention.py --json     # the plan as JSON
"""
import argparse, fnmatch, glob as _glob, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
POLICY = os.environ.get('PBR_BINDER_POLICY', os.path.join(HERE, 'pbr_binder_retention_v1.json'))
VERDICT = re.compile(r'\b(GREEN|AMBER|RED)\b')


def load_policy(path=POLICY):
    with open(path) as fh:
        return json.load(fh)


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def gate(corpus_path, tool):
    """The corpus's own gate verdict, computed from the corpus rather than read off its manifest.

    The declared gate and the computed gate can differ, and where they do the computed gate stands.
    A corpus that cannot be gated at all is treated as RED: unknown is not a pass.
    """
    r = subprocess.run([sys.executable, os.path.join(ROOT, tool), corpus_path],
                       capture_output=True, text=True)
    m = VERDICT.search(r.stdout or '')
    return (m.group(1) if m else 'RED'), '[ARCHIVAL]' in (r.stdout or '')


def batch_state(batch_dir, policy):
    """Everything the rule needs to know about one batch, read once."""
    corpora = sorted(_glob.glob(os.path.join(batch_dir, 'corpus_*.json')))
    live = [c for c in corpora if '_as_received' not in c and '_as_supplied' not in c and not c.endswith('_v5.json')]
    records, by_md5 = [], {}
    for r in sorted(_glob.glob(os.path.join(batch_dir, 'mask_screen_*.json'))):
        try:
            d = json.load(open(r))
        except (ValueError, OSError):
            continue
        records.append(r)
        for b in (d.get('binders') or ([d['binder']] if d.get('binder') else [])):
            if b.get('md5'):
                by_md5[b['md5']] = {'record': os.path.relpath(r, ROOT), 'name': b.get('name')}
    return {
        'corpora': live,
        'mask_md5': by_md5,
        'has_record': bool(records),
        'holds': sorted(_glob.glob(os.path.join(batch_dir, 'hold_record_*.md'))),
    }


def _has_text(pt):
    """page_text is a {page: text} map on a captured corpus, and absent on one that retained none.

    str and list are accepted too rather than assumed away: this decides whether a binder is deleted, so
    an unexpected shape must read as 'no text retained' and keep the file, never as a pass.
    """
    if isinstance(pt, dict):
        return any(isinstance(v, str) and v.strip() for v in pt.values())
    if isinstance(pt, str):
        return bool(pt.strip())
    if isinstance(pt, list):
        return any(isinstance(v, str) and v.strip() for v in pt)
    return False


def page_text_complete(corpus_path):
    """Every document retains non-empty page text, which is the shingle check's independent haystack."""
    try:
        d = json.load(open(corpus_path))
    except (ValueError, OSError):
        return False
    docs = d.get('documents') or []
    return bool(docs) and all(_has_text(doc.get('page_text')) for doc in docs)


def plan(root=ROOT, policy=None):
    p = policy or load_policy()
    req = p.get('require', {})
    protect = p.get('protect', [])
    out = {'delete': [], 'keep': []}
    for r in p.get('roots', ['batches']):
        for batch_dir in sorted(_glob.glob(os.path.join(root, r, '*'))):
            if not os.path.isdir(batch_dir):
                continue
            pdfs = sorted(_glob.glob(os.path.join(batch_dir, '*.pdf')))
            if not pdfs:
                continue
            st = batch_state(batch_dir, p)
            gates = {c: gate(c, p['gate_tool']) for c in st['corpora']} if st['corpora'] else {}
            for pdf in pdfs:
                rel = os.path.relpath(pdf, root)
                rec = {'path': rel, 'batch': os.path.basename(batch_dir),
                       'mb': round(os.path.getsize(pdf) / 1048576, 2)}
                prot = next((x for x in protect if fnmatch.fnmatch(rel, x['glob'])), None)
                if prot:
                    out['keep'].append(dict(rec, why='protected: ' + prot['why']))
                    continue
                fails = []
                if req.get('corpus') and not st['corpora']:
                    fails.append('no corpus: the batch is unparsed evidence')
                if req.get('no_hold_record') and st['holds']:
                    fails.append('held: ' + ', '.join(os.path.basename(h) for h in st['holds']))
                if req.get('gate_not_red'):
                    red = [os.path.basename(c) for c, (v, _) in gates.items() if v == 'RED']
                    if red:
                        fails.append('gate RED: ' + ', '.join(red))
                if req.get('page_text_every_document'):
                    bare = [os.path.basename(c) for c in st['corpora'] if not page_text_complete(c)]
                    if bare:
                        fails.append('page_text missing on ' + ', '.join(bare))
                if req.get('mask_record_md5_match'):
                    h = md5(pdf)
                    rec['md5'] = h
                    if h not in st['mask_md5']:
                        fails.append('no M1 record names this file'
                                     + ('' if st['has_record'] else ' (batch has no mask record at all)'))
                    else:
                        rec['mask_record'] = st['mask_md5'][h]['record']
                (out['keep'] if fails else out['delete']).append(
                    dict(rec, **({'why': '; '.join(fails)} if fails else {})))
    out['delete_mb'] = round(sum(x['mb'] for x in out['delete']), 2)
    out['keep_mb'] = round(sum(x['mb'] for x in out['keep']), 2)
    return out


def apply(pl, root=ROOT, log=print):
    n = 0
    for rec in pl['delete']:
        path = os.path.join(root, rec['path'])
        if os.path.exists(path):
            os.remove(path)
            n += 1
            log(f'  deleted {rec["path"]} ({rec["mb"]} MB, M1 record {rec.get("mask_record")})')
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--apply', action='store_true', help='delete the binders that qualify (default is a dry run)')
    ap.add_argument('--json', action='store_true', help='print the plan as JSON')
    a = ap.parse_args(argv)
    pl = plan()
    if a.json:
        print(json.dumps(pl, indent=1))
        return 0
    for rec in pl['keep']:
        print(f'  keep    {rec["path"]:<62} {rec["mb"]:>6.2f} MB  {rec["why"]}')
    for rec in pl['delete']:
        print(f'  DELETE  {rec["path"]:<62} {rec["mb"]:>6.2f} MB  parsed, gated and M1-screened')
    print(f'\n{len(pl["delete"])} binder(s) parsed with no issues, {pl["delete_mb"]} MB; '
          f'{len(pl["keep"])} kept, {pl["keep_mb"]} MB.')
    if not pl['delete']:
        return 0
    if not a.apply:
        print('Dry run. Re-run with --apply to delete them. There is no copy behind them.')
        return 0
    n = apply(pl)
    print(f'\ndeleted {n} binder(s), {pl["delete_mb"]} MB. The M1 record is now the only account of each page.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
