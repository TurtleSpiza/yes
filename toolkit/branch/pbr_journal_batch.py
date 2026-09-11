"""pbr_journal_batch.py - Batch journal_1: prepare and audit TechOne Document Line Table pulls (rule 21, pipeline "per journal batch").

One export covers one document FILE (rule 21), but TechOne lets the export be taken with a Document filter, in which case it
covers one document WITHIN that file. This driver reads whatever was pulled, screens it, and states exactly what it covers.

What it does, in order:
  1. md5 every export and screen it against the register's embedded Data_Acquisition and the PS & WP v127 Data_Acquisition
     (rule 12 GATE). A second export of the same document is kept only once: identical body rows are a duplicate, not evidence.
  2. Read the parameter row verbatim (Document File, Document, Format, Processing Group) and every leg verbatim.
  3. Map each leg to the register: a leg is IN BRANCH SCOPE when it matches a register line on the same document file by
     PK Charged, natural account and amount, with the register narration carrying the leg's own narration. Matching is 1:1.
  4. Prove each document nets to exactly zero over all its legs (Decimal), and that for every journal reference the document
     covers, the in-scope legs sum to that reference's register net AND every register line of that reference is matched.
  5. Screen against PS & WP v127 Journal_Sources: a document already embedded there is AUDITED leg by leg and, if identical,
     NOT re-captured (rule 12, v122 precedent).
  6. Report file coverage: which of the document file's journal references this pull reaches, and which it does not.

Authored content (verdict, note, follow-up, open items per document) is data in notes_journal_1_v6.json, merged here.
Nothing in this file infers an amount or edits a narration: the export is the evidence.

Usage: python3 pbr_journal_batch.py [outdir]
"""
import collections, datetime as dt, glob, hashlib, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

from python_calamine import CalamineWorkbook

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('PBR_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))
PULLS = os.environ.get('PBR_PULLS', os.path.join(ROOT, 'data', 'inputs_2026-09-11', 'journal_pulls'))
REG = os.environ.get('PBR_REG', os.path.join(ROOT, 'registers', 'Parks_Branch_Transaction_Register_FY2627_v5.xlsx'))
V127 = os.environ.get('PBR_V127', os.path.join(ROOT, 'registers', 'PS_WP_Transaction_Register_3FY_v127_CANDIDATE.xlsx'))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'batches', 'journal_1')
NOTES = os.path.join(OUT, 'notes_journal_1_v6.json')
BATCH = 'journal_1'

# Register column positions (1-based, per Config): read once here so the driver never hardcodes a letter.
C_LINEKEY, C_SECTION, C_REF, C_NA, C_PK, C_AMOUNT, C_NARR, C_ATT, C_DOCFILE = 1, 3, 8, 14, 17, 20, 22, 62, 69


def D(x):
    return Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def txt(v):
    """Calamine returns numeric-looking cells as floats; keep the printed form (rule 19.8)."""
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def norm(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def sheet(path, name=None):
    wb = CalamineWorkbook.from_path(path)
    return wb.get_sheet_by_name(name or wb.sheet_names[0]).to_python(skip_empty_area=False)


# ----------------------------------------------------------------------------------------------- read an export


PARAM_RX = re.compile(r'(\w[\w {}]*?)\s*=\s*([^,]*?)\s*(?:,|$)')


def read_export(path):
    rows = sheet(path, 'Sheet1')
    assert norm(rows[0][0]).startswith('Document Line Table'), path
    params_text = norm(rows[1][0])
    params = {k.strip(): v.strip() for k, v in PARAM_RX.findall(params_text.replace('Parameters:', '', 1))}
    codes = [txt(c) for c in rows[3]]
    labels = [txt(c) for c in rows[4]]
    idx = {c: i for i, c in enumerate(codes)}
    legs = []
    for r in rows[5:]:
        if not any(txt(c) for c in r):
            continue
        get = lambda c: txt(r[idx[c]]) if c in idx else ''
        amt_raw = get('EnteredAmount')
        if not get('LedgerCode') and not get('AccountNumberExternal') and D(amt_raw) == 0:
            continue  # the export's trailing zero row
        legs.append(dict(ledger=get('LedgerCode'), account=get('AccountNumberExternal'), account_desc=get('AccountNumberDescription'),
                         fund=get('FundAccountNumberExternal'), rgroup=get('ResourceGroupCode'), rcode=get('ResourceCode'),
                         qty=get('Units1'), amount=str(D(amt_raw)), narr1=get('DocumentLineNarration1'),
                         narr2=get('DocumentLineNarration2'), narr3=get('DocumentLineNarration3')))
    body_hash = hashlib.md5(json.dumps(legs, sort_keys=True).encode()).hexdigest()
    return dict(file=os.path.basename(path), md5=md5(path), params_verbatim=params_text, params=params, columns=codes,
                column_labels=labels, legs=legs, body_hash=body_hash)


# ----------------------------------------------------------------------------------------------- register side


def load_register():
    rows = sheet(REG, 'Register')
    out = []
    for i, r in enumerate(rows[4:], 5):
        if not txt(r[C_LINEKEY - 1]):
            continue
        out.append(dict(row=i, linekey=txt(r[C_LINEKEY - 1]), section=txt(r[C_SECTION - 1]), ref=txt(r[C_REF - 1]),
                        na=txt(r[C_NA - 1]), pk=txt(r[C_PK - 1]), amount=D(r[C_AMOUNT - 1]), narr=norm(r[C_NARR - 1]),
                        att=txt(r[C_ATT - 1]), docfile=txt(r[C_DOCFILE - 1])))
    return out


def leg_narr(l):
    return '-'.join(x for x in (norm(l['narr1']), norm(l['narr2']), norm(l['narr3'])) if x)


def match_legs(doc_legs, reg_lines):
    """1:1 match, narration-exact first, then key-only. Returns (matches, unmatched_reg)."""
    pool = list(enumerate(reg_lines))
    matched = {}
    for pref in (True, False):
        for i, l in enumerate(doc_legs):
            if i in matched or l['ledger'] != 'PK':
                continue
            for j, (_, r) in enumerate(pool):
                if r['pk'] != l['account'] or r['na'] != l['rcode'] or r['amount'] != D(l['amount']):
                    continue
                if pref and not r['narr'].startswith(norm(l['narr1']) or '\x00'):
                    continue
                matched[i] = r
                pool.pop(j)
                break
    return matched, [r for _, r in pool]


# ----------------------------------------------------------------------------------------------- v127 audit


def v127_journal_sources():
    rows = sheet(V127, 'Journal_Sources')
    out = collections.defaultdict(list)
    for r in rows[4:]:
        if not txt(r[0]) or not txt(r[1]).isdigit():
            continue
        out[txt(r[1])].append(dict(ref=txt(r[0]), ledger=txt(r[2]), account=txt(r[3]), fund=txt(r[4]), rgroup=txt(r[5]),
                                   rcode=txt(r[6]), amount=str(D(r[7])), narr1=norm(r[8]), narr2=norm(r[9]), narr3=norm(r[10]),
                                   in_pswp=txt(r[11])))
    return out


def audit_against_v127(legs, held):
    """Leg by leg (rule 12). Identical means same multiset of (ledger, account, rcode, amount, narrations)."""
    key = lambda l: (l['ledger'], l['account'], l['rcode'], str(D(l['amount'])), norm(l['narr1']), norm(l['narr2']), norm(l['narr3']))
    a, b = collections.Counter(key(l) for l in legs), collections.Counter(key(l) for l in held)
    only_new = sorted(a - b)
    only_held = sorted(b - a)
    return dict(held_legs=len(held), pulled_legs=len(legs), legs_in_both=sum((a & b).values()),
                legs_only_in_pull=[list(k) for k in only_new], legs_only_in_v127=[list(k) for k in only_held],
                identical=not only_new and not only_held,
                verdict=('identical to the PS & WP v127 embed; audited leg by leg and NOT re-captured (rule 12)'
                         if not only_new and not only_held else 'DIFFERS from the PS & WP v127 embed; resolve before any capture'))


# ----------------------------------------------------------------------------------------------- rule 12 md5 screen


def prior_md5s():
    seen = {}
    for path, sheetname, label in ((REG, 'Data_Acquisition', 'branch v5 Data_Acquisition'), (V127, 'Data_Acquisition', 'PS & WP v127 Data_Acquisition')):
        for r in sheet(path, sheetname):
            for m in re.findall(r'md5 ([0-9a-f]{32})', txt(r[0])):
                seen.setdefault(m, label)
    return seen


# ----------------------------------------------------------------------------------------------- report


def money(x):
    x = D(x)
    return f'-${-x:,.2f}' if x < 0 else f'${x:,.2f}'


def report(out):
    m = out['manifest']
    L = [f'Gate: {m["gate"]}', '', f'# Journal batch report: {m["batch_id"]}', '',
         f'Pulled 11-Sep-2026. {m["exports_received"]} TechOne Document Line Table exports received, '
         f'{len(m["duplicate_exports"])} of them duplicate copies, {m["documents"]} distinct documents.',
         f'Legs {m["legs_total"]}, of which {m["legs_in_scope"]} sit on branch O110-O115 and match {m["register_lines_matched"]} register lines one for one.',
         f'Every document nets to $0.00: {m["all_documents_net_zero"]}. Every in-scope leg sum ties its register net: {m["all_ties_true"]}.',
         f'Documents embedded verbatim {m["documents_embedded"]}, audited only under rule 12 {m["documents_audited_only"]}. '
         f'Document files fully covered {m["files_fully_covered"]} of {m["documents"]}.', '', '## Documents', '',
         '| Document file | Doc | Format | Journal ref | Legs | In scope | In-scope net | Nets to zero | Ties | Capture |',
         '|---|---|---|---|---:|---:|---:|---|---|---|']
    for d in out['documents']:
        L.append(f'| **{d["document_file"]}** | {d["document"]} | {d["format"]} | {", ".join(d["journal_references_covered"])} | '
                 f'{d["legs_total"]} | {d["in_scope_legs"]} | {money(d["in_scope_net"])} | {"Yes" if d["nets_to_zero"] else "NO"} | '
                 f'{"TRUE" if d["all_ties_true"] else "FALSE"} | {d["capture"]} |')
    for d in out['documents']:
        L += ['', f'## {d["document_file"]} ({", ".join(d["journal_references_covered"])})', '']
        if d.get('question_the_register_could_not_answer'):
            L.append(f'- **What the register could not answer:** {d["question_the_register_could_not_answer"]}')
        if d.get('answer'):
            L.append(f'- **What the document says:** {d["answer"]}')
        if d.get('finding'):
            L.append(f'- **Finding:** {d["finding"]}')
        if d.get('coverage_note'):
            L.append(f'- **Coverage:** {d["coverage_note"]}')
        if d.get('note'):
            L.append(f'- **Note:** {d["note"]}')
        if d.get('v127_audit'):
            a = d['v127_audit']
            L.append(f'- **Rule 12 audit against PS & WP v127 Journal_Sources:** {a["legs_in_both"]} legs in both, '
                     f'{len(a["legs_only_in_pull"])} only in the pull, {len(a["legs_only_in_v127"])} only in v127. {a["verdict"]}.')
        L.append(f'- **Counterparty legs (outside branch scope):** {len(d["counterparty_legs"])}, '
                 f'totalling {money(sum((D(c["amount"]) for c in d["counterparty_legs"]), Decimal("0")))}.')
    if out['open_items']:
        L += ['', '## Open items raised', '']
        for o in out['open_items']:
            L.append(f'- **{o["id"]} {o["area"]}** ({o["scope"]}, {o["lines"]} lines, {money(o["amount"])}): {o["action"]}')
    if m['duplicate_exports']:
        L += ['', '## Duplicate exports (rule 12)', '']
        for x in m['duplicate_exports']:
            L.append(f'- {x["file"]} (md5 {x["md5"]}) is a second copy of document file {x["document_file"]} document {x["document"]}, '
                     f'{x["basis"]}; kept once, {x["duplicate_of"]} is the copy read.')
    return '\n'.join(L) + '\n'


# ----------------------------------------------------------------------------------------------- main


def main():
    os.makedirs(OUT, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(PULLS, 'Document_Line_Table*.xlsx')))
    assert paths, f'no Document Line Table exports under {PULLS}'
    exports = [read_export(p) for p in paths]

    seen = prior_md5s()
    for e in exports:
        assert e['md5'] not in seen, f"rule 12: {e['file']} md5 {e['md5']} was already received ({seen[e['md5']]})"

    # one document = one (document file, document) pair; a second export with identical body rows is a duplicate copy
    groups = collections.OrderedDict()
    for e in exports:
        k = (e['params'].get('Document File', ''), e['params'].get('Document', ''))
        groups.setdefault(k, []).append(e)
    dupes = []
    for k, es in groups.items():
        hashes = {e['body_hash'] for e in es}
        assert len(hashes) == 1, f'two exports of document {k} differ in their body rows: {[e["file"] for e in es]}'
        for e in es[1:]:
            dupes.append(dict(document_file=k[0], document=k[1], file=e['file'], md5=e['md5'],
                              duplicate_of=es[0]['file'], basis='identical body rows'))

    reg = load_register()
    by_file = collections.defaultdict(list)
    by_ref = collections.defaultdict(list)
    for r in reg:
        if r['docfile']:
            by_file[r['docfile']].append(r)
        if r['ref']:
            by_ref[r['ref']].append(r)
    held = v127_journal_sources()
    notes = json.load(open(NOTES)) if os.path.exists(NOTES) else {}

    docs = []
    for (df, dno), es in groups.items():
        e = es[0]
        legs = e['legs']
        net = sum((D(l['amount']) for l in legs), Decimal('0'))
        reg_lines = by_file.get(df, [])
        matched, unmatched = match_legs(legs, reg_lines)
        for i, l in enumerate(legs):
            l['in_branch_scope'] = 'Yes' if i in matched else 'No'
            l['register_linekey'] = matched[i]['linekey'] if i in matched else ''
            l['register_reference'] = matched[i]['ref'] if i in matched else ''
        refs = sorted({matched[i]['ref'] for i in matched})
        ties = []
        for ref in refs:
            legsum = sum((D(legs[i]['amount']) for i in matched if matched[i]['ref'] == ref), Decimal('0'))
            regsum = sum((r['amount'] for r in by_ref[ref]), Decimal('0'))
            covered = sum(1 for i in matched if matched[i]['ref'] == ref)
            ties.append(dict(journal_reference=ref, register_lines=len(by_ref[ref]), register_lines_matched=covered,
                             in_scope_leg_sum=str(legsum), register_net=str(regsum),
                             ties=legsum == regsum and covered == len(by_ref[ref])))
        file_refs = sorted({r['ref'] for r in reg_lines})
        audit = audit_against_v127(legs, held[df]) if df in held else None
        d = dict(document_file=df, document=dno, format=e['params'].get('Format', ''),
                 processing_group=e['params'].get('Processing Group', ''), params_verbatim=e['params_verbatim'],
                 source_file=e['file'], source_md5=e['md5'], columns=e['columns'], column_labels=e['column_labels'],
                 legs=legs, legs_total=len(legs), net=str(net), nets_to_zero=net == 0,
                 in_scope_legs=len(matched), in_scope_net=str(sum((D(legs[i]['amount']) for i in matched), Decimal('0'))),
                 counterparty_legs=[dict(ledger=l['ledger'], account=l['account'], account_desc=l['account_desc'],
                                         amount=l['amount'], narration=leg_narr(l)) for i, l in enumerate(legs) if i not in matched],
                 journal_references_covered=refs, journal_references_on_file=file_refs,
                 register_lines_on_file=len(reg_lines), register_lines_matched=len(matched),
                 file_fully_covered=sorted(refs) == file_refs and len(matched) == len(reg_lines),
                 ties=ties, all_ties_true=all(t['ties'] for t in ties),
                 v127_audit=audit, capture='audit only, not re-captured (rule 12)' if audit and audit['identical'] else 'embed verbatim')
        d.update(notes.get(df, {}))
        docs.append(d)

    docs.sort(key=lambda d: -abs(Decimal(d['in_scope_net'])))
    for d in docs:
        assert d['nets_to_zero'], f'{d["document_file"]} does not net to zero: {d["net"]}'
        assert d['all_ties_true'], f'{d["document_file"]} in-scope legs do not tie their register lines: {d["ties"]}'
        if d['v127_audit']:
            assert d['v127_audit']['identical'], f'{d["document_file"]}: {d["v127_audit"]["verdict"]}'

    out = dict(manifest=dict(batch_id=BATCH, prepared_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                             tool='pbr_journal_batch.py', source='TechOne Document Line Table exports (GENJNL and LC_INTJN formats)',
                             exports_received=len(exports), duplicate_exports=dupes, documents=len(docs),
                             documents_embedded=sum(1 for d in docs if d['capture'] == 'embed verbatim'),
                             documents_audited_only=sum(1 for d in docs if d['capture'] != 'embed verbatim'),
                             legs_total=sum(d['legs_total'] for d in docs),
                             legs_in_scope=sum(d['in_scope_legs'] for d in docs),
                             register_lines_matched=sum(d['register_lines_matched'] for d in docs),
                             all_documents_net_zero=all(d['nets_to_zero'] for d in docs),
                             all_ties_true=all(d['all_ties_true'] for d in docs),
                             files_fully_covered=sum(1 for d in docs if d['file_fully_covered']),
                             gate='GREEN'),
               open_items=notes.get('_open_items', []), documents=docs)
    json.dump(out, open(os.path.join(OUT, f'{BATCH}_v6.json'), 'w'), indent=1)
    open(os.path.join(OUT, f'capture_report_{BATCH}_v6.md'), 'w').write(report(out))
    m = out['manifest']
    print(f"gate {m['gate']}; exports {m['exports_received']} ({len(dupes)} duplicate), documents {m['documents']}, "
          f"legs {m['legs_total']} ({m['legs_in_scope']} in branch scope), register lines matched {m['register_lines_matched']}, "
          f"net zero on all {m['all_documents_net_zero']}, ties all TRUE {m['all_ties_true']}, "
          f"files fully covered {m['files_fully_covered']} of {m['documents']}")
    for d in docs:
        print(f"  {d['document_file']} doc {d['document']} {','.join(d['journal_references_covered'])}: {d['legs_total']} legs, "
              f"{d['in_scope_legs']} in scope, in-scope net {d['in_scope_net']}, {d['capture']}")


if __name__ == '__main__':
    main()
