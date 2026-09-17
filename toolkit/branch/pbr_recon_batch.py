"""pbr_recon_batch.py - Batch recon_1: prepare and audit TechOne Document Reconstruction exports (rule 21).

A Document Reconstruction is a second, different evidence route into a journal. Where a Document Line Table is
keyed to a document FILE and carries the external account (PK000xxx) on every leg, a Document Reconstruction is
keyed to a Document Cross Reference and carries the internal ledger account (1-20361-7C111) instead. It reaches
the Council-side counterparty legs that a Document Line Table taken inside the branch never shows, which is
exactly what the Tier A entries on the Journal_Pull sheet say is missing. The register carries the internal
account verbatim in its own grey source block (Src Account), so a reconstruction leg maps to a register line
without any crosswalk being invented here.

What it does, in order:
  1. md5 every export and screen it against the register's embedded Data_Acquisition and the PS & WP v127
     Data_Acquisition (rule 12 GATE). A second export of the same cross reference is kept only once: identical
     body rows are a duplicate copy, not evidence.
  2. Read the parameter row verbatim (Document Cross Reference, Ledger Name, Account, Transaction) and every
     leg verbatim. A leg's amount is its printed Debit less its printed Credit; nothing is inferred.
  3. Prove each document nets to exactly zero over all its legs (Decimal, ROUND_HALF_UP).
  4. Map each leg to the register 1:1 on Src Account and amount, narration-exact first then key-only. A leg
     that matches is IN BRANCH SCOPE; every other leg is a counterparty leg and is retained as such.
  4b. Screen the document file those matched lines sit on against BOTH held embeds: the branch Journal_Sources
     (batch journal_1) and the PS & WP v127 Journal_Sources, which is Tier D of the pull list. A document already
     embedded either side is a re-sighting through a different export type and is AUDITED, never re-captured
     (rule 12). The two formats project the same document differently, so the audit is on what both carry: the
     leg count and the multiset of leg amounts.
  5. For every journal reference the document reaches, prove the in-scope leg sum ties that reference's
     register net AND that every register line of that reference is matched.
  6. Report coverage against the document file the reference sits on, so a partial reach is stated and never
     read as a full one (the open item "Journal pull taken with a Document filter" is exactly this failure).

Authored content (question, answer, finding, note, open items per document) is data in notes_recon_1_v9.json,
merged here. Nothing in this file infers an amount or edits a narration: the export is the evidence.

Usage: python3 pbr_recon_batch.py [outdir]
"""
import collections, datetime as dt, glob, hashlib, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

from python_calamine import CalamineWorkbook

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('PBR_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))
PULLS = os.environ.get('PBR_RECONS', os.path.join(ROOT, 'data', 'inputs_2026-09-11', 'reconstructions'))
V127 = os.environ.get('PBR_V127', os.path.join(ROOT, 'registers', 'PS_WP_Transaction_Register_3FY_v127_CANDIDATE.xlsx'))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'batches', 'recon_1')
# One batch folder per pull, because the md5 screen rejects an export the register has already received: re-running
# over a folder that still holds a captured pull always fails rule 12. The batch id is the folder it writes to and
# the version is the register version it ships into, both overridable so the bare command still reproduces recon_1 v9.
BATCH = os.environ.get('PBR_BATCH') or os.path.basename(os.path.normpath(OUT)) or 'recon_1'
VER = os.environ.get('PBR_VER', 'v9')
PULLED = os.environ.get('PBR_PULLED', '14-Sep-2026')  # the date the exports were taken, as the export names print it
NOTES = os.path.join(OUT, f'notes_{BATCH}_{VER}.json')

# Register column positions (1-based, per Config): read once here so the driver never hardcodes a letter.
C_LINEKEY, C_SECTION, C_REF, C_NA, C_PK, C_AMOUNT, C_NARR, C_SRCACCT, C_DOCFILE = 1, 3, 8, 14, 17, 20, 22, 55, 69

# The Document Reconstruction column codes this driver reads (row 4 of the export). TechOne emits two layouts:
# the narrow one, these nine in this order, and a wide one that interleaves extra columns (OrderDetails,
# AssetDetails before ATTransactionNumber, then ATAccountNumberInternal, ATDFormatName, ATPurchaseOrderNumberV2,
# IsArchived, CreditOrDebitAmount). Every leg is read by column CODE, never by position, so the requirement is
# that all nine are present, not that they are the first nine: a wide export keyed on position reads OrderDetails
# as the transaction number and silently blanks it.
RECON_COLS = ['ATLedgerName', 'D1EditAccountNumber', 'D1ShortDescription1', 'DebitAmount1', 'CreditAmount1',
              'Narration', 'ATUnits1', 'ATJournalLine', 'ATTransactionNumber']


def latest_register():
    regs = sorted(glob.glob(os.path.join(ROOT, 'registers', 'Parks_Branch_Transaction_Register_FY2627_v*.xlsx')),
                  key=lambda p: int(re.search(r'_v(\d+)\.xlsx$', p).group(1)))
    assert regs, 'no branch register to match against'
    return regs[-1]


REG = os.environ.get('PBR_REG', latest_register())


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
    assert norm(rows[0][0]).startswith('Document Reconstruction'), path
    params_text = norm(rows[1][0])
    params = {k.strip(): v.strip() for k, v in PARAM_RX.findall(params_text.replace('Parameters:', '', 1))}
    codes = [txt(c) for c in rows[3]]
    labels = [txt(c) for c in rows[4]]
    missing = [c for c in RECON_COLS if c not in codes]
    assert not missing, (path, 'missing column code(s)', missing, codes)
    idx = {c: i for i, c in enumerate(codes)}
    layout = 'narrow' if codes[:len(RECON_COLS)] == RECON_COLS else 'wide'
    legs = []
    for r in rows[5:]:
        if not any(txt(c) for c in r):
            continue
        get = lambda c: txt(r[idx[c]]) if c in idx else ''
        dr, cr = D(get('DebitAmount1')), D(get('CreditAmount1'))
        if not get('ATLedgerName') and not get('D1EditAccountNumber') and dr == 0 and cr == 0:
            continue  # the export's trailing zero row
        legs.append(dict(ledger=get('ATLedgerName'), account=get('D1EditAccountNumber'),
                         account_desc=get('D1ShortDescription1'), debit=str(dr), credit=str(cr),
                         amount=str(dr - cr), narration=get('Narration'), qty=get('ATUnits1'),
                         journal_line=get('ATJournalLine'), transaction=get('ATTransactionNumber')))
    body_hash = hashlib.md5(json.dumps(legs, sort_keys=True).encode()).hexdigest()
    return dict(file=os.path.basename(path), md5=md5(path), params_verbatim=params_text, params=params,
                columns=codes, column_labels=labels, layout=layout, legs=legs, body_hash=body_hash)


# ----------------------------------------------------------------------------------------------- register side


def load_register():
    rows = sheet(REG, 'Register')
    hdr = [txt(c) for c in rows[3]]
    assert hdr[C_SRCACCT - 1] == 'Src Account' and hdr[C_REF - 1] == 'Reference', hdr[:2]
    out = []
    for i, r in enumerate(rows[4:], 5):
        if not txt(r[C_LINEKEY - 1]):
            continue
        out.append(dict(row=i, linekey=txt(r[C_LINEKEY - 1]), section=txt(r[C_SECTION - 1]), ref=txt(r[C_REF - 1]),
                        na=txt(r[C_NA - 1]), pk=txt(r[C_PK - 1]), amount=D(r[C_AMOUNT - 1]), narr=norm(r[C_NARR - 1]),
                        srcacct=txt(r[C_SRCACCT - 1]), docfile=txt(r[C_DOCFILE - 1])))
    return out


def narr_key(s):
    """Register and reconstruction print the same narration with different separators; compare on the words."""
    return re.sub(r'[^a-z0-9]+', ' ', str(s or '').lower()).strip()


def match_legs(doc_legs, reg_lines):
    """1:1 match on Src Account and amount, narration-exact first then key-only. Returns (matches, unmatched_reg)."""
    pool = list(enumerate(reg_lines))
    matched = {}
    for pref in (True, False):
        for i, l in enumerate(doc_legs):
            if i in matched:
                continue
            lk = narr_key(l['narration'])
            for j, (_, r) in enumerate(pool):
                if r['srcacct'] != l['account'] or r['amount'] != D(l['amount']):
                    continue
                if pref and narr_key(r['narr']) != lk:
                    continue
                matched[i] = r
                pool.pop(j)
                break
    return matched, [r for _, r in pool]


# ----------------------------------------------------------------------------------------------- rule 12 re-sighting audit


def embedded_journal_docs():
    """Documents already embedded on Journal_Sources from a Document Line Table pull (batch journal_1)."""
    p = os.path.join(ROOT, 'batches', 'journal_1', 'journal_1_v6.json')
    if not os.path.exists(p):
        return []
    return [d for d in json.load(open(p))['documents'] if d.get('capture') == 'embed verbatim']


def audit_against_journal(legs, refs, held):
    """A reconstruction that reaches the same journal reference as an already-embedded Document Line Table is a
    re-sighting through a different export type: audit it, never re-capture it (rule 12, v122 precedent). The two
    exports project the same document differently (external PK account against internal ledger account), so the
    audit is on what both carry: the leg count and the multiset of leg amounts, plus the in-scope net."""
    for h in held:
        if not refs or not set(refs) <= set(h['journal_references_covered']):
            continue
        a = collections.Counter(str(D(l['amount'])) for l in legs)
        b = collections.Counter(str(D(l['amount'])) for l in h['legs'])
        same = a == b and len(legs) == len(h['legs'])
        return dict(held_document_file=h['document_file'], held_format=h['format'], held_legs=len(h['legs']),
                    pulled_legs=len(legs), amounts_identical=a == b,
                    held_in_scope_net=h['in_scope_net'], identical=same,
                    verdict=('same document as the Document Line Table already embedded on Journal_Sources '
                             f'(document file {h["document_file"]}, {h["format"]}); audited and NOT re-captured (rule 12)'
                             if same else
                             f'DIFFERS from the embedded Document Line Table for document file {h["document_file"]}; resolve before any capture'))
    return None


def v127_journal_sources():
    """Documents embedded on the PS & WP v127 Journal_Sources sheet, keyed by TechOne document file. This is Tier D
    of the pull list: the branch never re-captures a document the PS & WP register already holds."""
    rows = sheet(V127, 'Journal_Sources')
    out = collections.defaultdict(list)
    for r in rows[4:]:
        if not txt(r[0]) or not txt(r[1]).isdigit():
            continue
        out[txt(r[1])].append(dict(ref=txt(r[0]), amount=str(D(r[7]))))
    return out


def audit_against_v127(legs, docfiles, held):
    """Cross-format audit against the PS & WP v127 embed, on the same basis as the branch one: a Document Line
    Table prints the external PK account and a reconstruction the internal ledger account, so leg-by-leg keys do
    not compare. The leg count, the multiset of leg amounts and the document file do."""
    for df in docfiles:
        if df not in held:
            continue
        rows = held[df]
        a = collections.Counter(str(D(l['amount'])) for l in legs)
        b = collections.Counter(str(D(r['amount'])) for r in rows)
        same = a == b and len(legs) == len(rows)
        return dict(document_file=df, held_legs=len(rows), pulled_legs=len(legs), amounts_identical=a == b,
                    held_references=sorted({r['ref'] for r in rows}), identical=same,
                    verdict=(f'same document as the Document Line Table already embedded on PS & WP v127 '
                             f'Journal_Sources (document file {df}, Tier D); audited and NOT re-captured (rule 12)'
                             if same else
                             f'DIFFERS from the PS & WP v127 embed for document file {df} '
                             f'({len(legs)} legs against {len(rows)} held); resolve before any capture'))
    return None


# ----------------------------------------------------------------------------------------------- rule 12 md5 screen


def prior_md5s():
    seen = {}
    for path, sheetname, label in ((REG, 'Data_Acquisition', f'branch {os.path.basename(REG)} Data_Acquisition'),
                                   (V127, 'Data_Acquisition', 'PS & WP v127 Data_Acquisition')):
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
    L = [f'Gate: {m["gate"]}', '', f'# Reconstruction batch report: {m["batch_id"]}', '',
         f'Pulled {m["pulled"]}. {m["exports_received"]} TechOne Document Reconstruction exports received, '
         f'{len(m["duplicate_exports"])} of them duplicate copies, {m["documents"]} distinct documents.',
         f'Legs {m["legs_total"]:,}, of which {m["legs_in_scope"]} sit on branch O110-O115 and match '
         f'{m["register_lines_matched"]} register lines one for one.',
         f'Documents embedded verbatim {m["documents_embedded"]}, audited only under rule 12 {m["documents_audited_only"]}.',
         f'Every document nets to $0.00: {m["all_documents_net_zero"]}. Every in-scope leg sum ties its register net: {m["all_ties_true"]}.',
         '', '## Documents', '',
         '| Document cross reference | Ledger | Account | Journal ref | Legs | In scope | In-scope net | Nets to zero | Ties | Capture |',
         '|---|---|---|---|---:|---:|---:|---|---|---|']
    for d in out['documents']:
        L.append(f'| **{d["cross_reference"]}** | {d["ledger_name"]} | {d["account"]} | '
                 f'{", ".join(d["journal_references_covered"]) or "(none in scope)"} | {d["legs_total"]:,} | '
                 f'{d["in_scope_legs"]} | {money(d["in_scope_net"])} | {"Yes" if d["nets_to_zero"] else "NO"} | '
                 f'{"TRUE" if d["all_ties_true"] else "FALSE"} | {d["capture"]} |')
    for d in out['documents']:
        L += ['', f'## {d["cross_reference"]} ({", ".join(d["journal_references_covered"]) or "no in-scope reference"})', '']
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
        if d.get('journal_audit'):
            a = d['journal_audit']
            L.append(f'- **Rule 12 audit against the embedded Document Line Table:** {a["pulled_legs"]} legs against '
                     f'{a["held_legs"]} held, amounts identical {a["amounts_identical"]}. {a["verdict"]}.')
        if d.get('v127_audit'):
            a = d['v127_audit']
            L.append(f'- **Rule 12 audit against PS & WP v127 Journal_Sources:** {a["pulled_legs"]} legs against '
                     f'{a["held_legs"]} held on document file {a["document_file"]}, amounts identical '
                     f'{a["amounts_identical"]}. {a["verdict"]}.')
        for t in d['ties']:
            L.append(f'- **Tie {t["journal_reference"]}:** in-scope legs {money(t["in_scope_leg_sum"])} against register net '
                     f'{money(t["register_net"])} on {t["register_lines"]} lines, {t["register_lines_matched"]} matched: '
                     f'{"TRUE" if t["ties"] else "FALSE"}.')
        L.append(f'- **Counterparty legs (outside branch scope):** {d["counterparty_legs_count"]:,}, '
                 f'totalling {money(d["counterparty_net"])} across {len(d["counterparty_ledgers"])} ledger(s): '
                 f'{", ".join(f"{k} {v}" for k, v in sorted(d["counterparty_ledgers"].items()))}.')
    if out['open_items']:
        L += ['', '## Open items raised', '']
        for o in out['open_items']:
            L.append(f'- **{o["area"]}** ({o["scope"]}, {o["lines"]} lines, {money(o["amount"])}): {o["action"]}')
    if m['duplicate_exports']:
        L += ['', '## Duplicate exports (rule 12)', '']
        for x in m['duplicate_exports']:
            L.append(f'- {x["file"]} (md5 {x["md5"]}) is a second copy of cross reference {x["cross_reference"]}, '
                     f'{x["basis"]}; kept once, {x["duplicate_of"]} is the copy read.')
    return '\n'.join(L) + '\n'


# ----------------------------------------------------------------------------------------------- main


def main():
    os.makedirs(OUT, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(PULLS, 'Document_Reconstruction*.xlsx')))
    assert paths, f'no Document Reconstruction exports under {PULLS}'
    exports = [read_export(p) for p in paths]

    seen = prior_md5s()
    for e in exports:
        assert e['md5'] not in seen, f"rule 12: {e['file']} md5 {e['md5']} was already received ({seen[e['md5']]})"

    groups = collections.OrderedDict()
    for e in exports:
        groups.setdefault(e['params'].get('Document Cross Reference', ''), []).append(e)
    dupes = []
    for k, es in groups.items():
        hashes = {e['body_hash'] for e in es}
        assert len(hashes) == 1, f'two exports of cross reference {k} differ in their body rows: {[e["file"] for e in es]}'
        for e in es[1:]:
            dupes.append(dict(cross_reference=k, file=e['file'], md5=e['md5'],
                              duplicate_of=es[0]['file'], basis='identical body rows'))

    reg = load_register()
    by_ref = collections.defaultdict(list)
    by_file = collections.defaultdict(set)
    for r in reg:
        if r['ref']:
            by_ref[r['ref']].append(r)
        if r['docfile'] and r['ref']:
            by_file[r['docfile']].add(r['ref'])
    notes = json.load(open(NOTES)) if os.path.exists(NOTES) else {}
    held_docs = embedded_journal_docs()
    held_v127 = v127_journal_sources()

    docs = []
    for xref, es in groups.items():
        e = es[0]
        legs = e['legs']
        net = sum((D(l['amount']) for l in legs), Decimal('0'))
        # candidate register lines: every line whose Src Account appears on this document
        accts = {l['account'] for l in legs}
        reg_lines = [r for r in reg if r['srcacct'] in accts]
        matched, _ = match_legs(legs, reg_lines)
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
        docfiles = sorted({matched[i]['docfile'] for i in matched if matched[i]['docfile']})
        file_refs = sorted({r for f in docfiles for r in by_file[f]})
        cp = [l for i, l in enumerate(legs) if i not in matched]
        d = dict(cross_reference=xref, ledger_name=e['params'].get('Ledger Name', ''),
                 account=e['params'].get('Account', ''), transaction=e['params'].get('Transaction', ''),
                 params_verbatim=e['params_verbatim'], source_file=e['file'], source_md5=e['md5'],
                 columns=e['columns'], column_labels=e['column_labels'], layout=e['layout'],
                 legs=legs, legs_total=len(legs),
                 net=str(net), nets_to_zero=net == 0, in_scope_legs=len(matched),
                 in_scope_net=str(sum((D(legs[i]['amount']) for i in matched), Decimal('0'))),
                 counterparty_legs_count=len(cp),
                 counterparty_net=str(sum((D(l['amount']) for l in cp), Decimal('0'))),
                 counterparty_ledgers=dict(collections.Counter(l['ledger'] for l in cp)),
                 journal_references_covered=refs, document_files=docfiles,
                 journal_references_on_file=file_refs,
                 references_on_file_not_reached=[r for r in file_refs if r not in refs],
                 register_lines_matched=len(matched), ties=ties, all_ties_true=all(t['ties'] for t in ties))
        aud = audit_against_journal(legs, refs, held_docs)
        d['journal_audit'] = aud
        v127_aud = audit_against_v127(legs, docfiles, held_v127)
        d['v127_audit'] = v127_aud
        held_elsewhere = [a for a in (aud, v127_aud) if a]
        d['capture'] = ('audit only, not re-captured (rule 12)'
                        if any(a['identical'] for a in held_elsewhere) else 'embed verbatim')
        d.update(notes.get(xref, {}))
        docs.append(d)

    docs.sort(key=lambda d: -abs(Decimal(d['in_scope_net'])))
    for d in docs:
        assert d['nets_to_zero'], f'{d["cross_reference"]} does not net to zero: {d["net"]}'
        assert d['all_ties_true'], f'{d["cross_reference"]} in-scope legs do not tie their register lines: {d["ties"]}'
        for a in (d.get('journal_audit'), d.get('v127_audit')):
            if a:
                assert a['identical'], f'{d["cross_reference"]}: {a["verdict"]}'

    out = dict(manifest=dict(batch_id=BATCH, prepared_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
                             tool='pbr_recon_batch.py', pulled=PULLED,
                             source='TechOne Document Reconstruction exports (Document Cross Reference keyed)',
                             register_matched_against=os.path.basename(REG),
                             exports_received=len(exports), duplicate_exports=dupes, documents=len(docs),
                             documents_embedded=sum(1 for d in docs if d['capture'] == 'embed verbatim'),
                             documents_audited_only=sum(1 for d in docs if d['capture'] != 'embed verbatim'),
                             legs_total=sum(d['legs_total'] for d in docs),
                             legs_embedded=sum(d['legs_total'] for d in docs if d['capture'] == 'embed verbatim'),
                             legs_in_scope=sum(d['in_scope_legs'] for d in docs),
                             register_lines_matched=sum(d['register_lines_matched'] for d in docs),
                             all_documents_net_zero=all(d['nets_to_zero'] for d in docs),
                             all_ties_true=all(d['all_ties_true'] for d in docs),
                             gate='GREEN'),
               open_items=notes.get('_open_items', []), documents=docs)
    json.dump(out, open(os.path.join(OUT, f'{BATCH}_{VER}.json'), 'w'), indent=1)
    open(os.path.join(OUT, f'capture_report_{BATCH}_{VER}.md'), 'w').write(report(out))
    m = out['manifest']
    print(f"gate {m['gate']}; exports {m['exports_received']} ({len(dupes)} duplicate), documents {m['documents']}, "
          f"legs {m['legs_total']:,} ({m['legs_in_scope']} in branch scope), register lines matched {m['register_lines_matched']}, "
          f"net zero on all {m['all_documents_net_zero']}, ties all TRUE {m['all_ties_true']}")
    for d in docs:
        print(f"  {d['cross_reference']} {d['account']} {','.join(d['journal_references_covered']) or '(none)'}: "
              f"{d['legs_total']:,} legs, {d['in_scope_legs']} in scope, in-scope net {d['in_scope_net']}")


if __name__ == '__main__':
    main()
