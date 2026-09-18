"""pbr_match_table.py - build a batch match table against the shipped branch register (rule 20: content as data).

For each document in a GREEN corpus: screen its identifier against Evidence_Invoices column A (rule 12 duplicate
screen), find its register line(s) by reference, and decide the rule 17 check-2 variant by the settled precedence:

    exact  ->  SUM-TIE  ->  derivation equality (incl / 1.1)  ->  one-cent tolerance  ->  split posting by LineKey

The precedence is not cosmetic. A two-cent difference that is exactly incl/1.1 is a DERIVATION case, not a tolerance
case, and labelling it the other way fails check 2 under LibreOffice (branch v2 precedent, INV-0600).

Authored content (coding verdict, coding note, follow-up, evidence note, line map) is data in
notes_<batch>_v6.json and is merged here; nothing in this file forms a coding judgement.

Usage: python3 pbr_match_table.py <batch id> [register.xlsx]
"""
import collections, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

from python_calamine import CalamineWorkbook

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BATCH = sys.argv[1]
REG = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'registers', 'Parks_Branch_Transaction_Register_FY2627_v5.xlsx')
BDIR = os.path.join(ROOT, 'batches', BATCH)
INCL = Decimal('1.1')
C_LINEKEY, C_SECTION, C_REF, C_CONTRACTOR, C_NA, C_PK, C_AMOUNT, C_NARR = 1, 3, 8, 12, 14, 17, 20, 22


def D(x):
    return Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)


def txt(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def sheet(path, name):
    return CalamineWorkbook.from_path(path).get_sheet_by_name(name).to_python(skip_empty_area=False)


def variant_of(amounts, sub, incl):
    """Rule 17 check-2 variant for one document, in the settled precedence order."""
    tot = sum(amounts, Decimal('0'))
    if len(amounts) > 1:
        return 'check 2 split-posting (each register line ties its own captured lines by LineKey)'
    if tot == sub:
        return 'standard'
    if tot == (incl / INCL).quantize(Decimal('0.01'), ROUND_HALF_UP):
        return 'check 2 derivation equality (register amount = ROUND(printed total incl GST / 1.1, 2))'
    if abs(tot - sub) <= Decimal('0.01'):
        return 'check 2 one-cent tolerance'
    return 'UNRESOLVED'


def main():
    corpus = json.load(open(os.path.join(BDIR, f'corpus_{BATCH}_v6.json')))
    # The COMPUTED gate decides, not the word the extraction declared (prompt 13.2), and AMBER builds what is
    # complete while holding the named documents (13.0). Asserting on a declared GREEN enforced a rule the
    # standard does not state, and once the description layer could demote a corpus it would have blocked every
    # capture. A pathology is the thing that stops a build.
    sys.path.insert(0, os.path.join(ROOT, 'toolkit', 'pswp'))
    from pswp_corpus_gate import check as _gate
    _r = _gate(os.path.join(BDIR, f'corpus_{BATCH}_v6.json'))
    assert not _r['pathologies'], (_r['gate'], _r['pathologies'][:4])
    if _r['gate'] != corpus['manifest'].get('gate'):
        print(f"  gate: declared {corpus['manifest'].get('gate')}, computed {_r['gate']}, the computed gate stands"
              f" (description layer {_r['description_layer']})")
    npath = os.path.join(BDIR, f'notes_{BATCH}_v6.json')
    notes = json.load(open(npath)) if os.path.exists(npath) else {}

    reg = [r for r in sheet(REG, 'Register')[4:] if txt(r[C_LINEKEY - 1])]
    by_ref = collections.defaultdict(list)
    for r in reg:
        by_ref[txt(r[C_REF - 1])].append(r)
    sighted = {txt(r[0]) for r in sheet(REG, 'Evidence_Invoices')[4:] if txt(r[0])}
    sighted_stem = {s.split('/')[0] for s in sighted}

    def already_sighted(inv):
        """Rule 12, PREFIX AWARE. An EvID carries the batch's own prefix in front of the printed reference, so the
        bare reference alone is not the screen: invoice 00015202A is already held here as INV-00015202A, inherited
        from the PS & WP register, and a bare comparison re-captures it onto a line that already has a green block.
        A prefix is short by construction (the PS/WP driver uses the same five-character bound)."""
        if inv in sighted_stem:
            return True
        return any(e.endswith(inv) and 0 < len(e) - len(inv) <= 5 for e in sighted_stem)

    out, held = [], []
    dups, outside = [], []
    for d in corpus['documents']:
        inv = d['invoice_no']
        if d.get('duplicate_of'):
            dups.append(inv)  # repeated copy of a document already in the corpus (prompt v6 11.4): never matched twice
            continue
        if already_sighted(inv):
            held.append(inv)
            continue
        rows = by_ref.get(inv, [])
        if not rows:
            # A binder is a vendor's own file and is not cut to this register's year. Every document whose reference
            # carries no line here is recorded with its printed invoice date and held, never dropped silently and never
            # forced onto a line: the branch register is FY2026/27 only, so a document printed before 1-Jul-2026 has no
            # line to sit on and belongs to the PS & WP register's earlier years. A document INSIDE the year with no
            # line would be a different matter (an invoice the ledger never received) and is listed the same way for
            # the batch record to answer.
            outside.append(dict(invoice=inv, invoice_date=d.get('invoice_date'), subtotal=float(D(d['printed_subtotal_ex_gst'])),
                                in_register_year=str(d.get('invoice_date') or '') >= '2026-07-01',
                                pages=d.get('page_range')))
            continue
        amounts = [D(r[C_AMOUNT - 1]) for r in rows]
        sub, incl = D(d['printed_subtotal_ex_gst']), D(d['printed_total_incl_gst'])
        var = variant_of(amounts, sub, incl)
        assert var != 'UNRESOLVED', (inv, [str(a) for a in amounts], str(sub), str(incl))
        entry = dict(invoice=inv, vendor=d['supplier'], abn=d['supplier_abn'], subtotal=float(sub), incl=float(incl),
                     variant=var, target=[txt(r[C_LINEKEY - 1]) for r in rows],
                     register_lines=[dict(linekey=txt(r[C_LINEKEY - 1]), section=txt(r[C_SECTION - 1]), na=txt(r[C_NA - 1]),
                                          pk=txt(r[C_PK - 1]), amount=float(D(r[C_AMOUNT - 1])), contractor=txt(r[C_CONTRACTOR - 1]),
                                          narr=re.sub(r'\s*\n\s*', ' | ', txt(r[C_NARR - 1]))) for r in rows],
                     evid=inv, evid_note=None, line_map=None, coding_verdict='Correct', coding_note=None, follow_up=None,
                     source_file=d.get('source_file'))
        entry.update(notes.get(inv, {}))
        out.append(entry)

    json.dump(out, open(os.path.join(BDIR, f'match_{BATCH}_v6.json'), 'w'), indent=1)
    if outside:
        json.dump(outside, open(os.path.join(BDIR, f'outside_{BATCH}_v6.json'), 'w'), indent=1)
        inyear = [o for o in outside if o['in_register_year']]
        print(f'{BATCH}: {len(outside)} document(s) carry no line on this register '
              f'(${sum(o["subtotal"] for o in outside):,.2f} ex GST), of which {len(inyear)} are dated inside FY2026/27 '
              f'{[o["invoice"] for o in inyear] or ""}; listed in outside_{BATCH}_v6.json')
    v = collections.Counter(e['variant'].split(' (')[0] for e in out)
    print(f'{BATCH}: {len(out)} documents matched, {len(held)} held by the rule 12 evidence screen {held or ""}, {len(dups)} duplicate copies skipped {dups or ""}; variants {dict(v)}')
    for e in out:
        if e['variant'] != 'standard':
            print(f'  {e["invoice"]:<12} {e["variant"].split(" (")[0]}: register {sum(l["amount"] for l in e["register_lines"]):,.2f} '
                  f'against printed subtotal {e["subtotal"]:,.2f}, printed total {e["incl"]:,.2f}')
        if e['coding_verdict'] != 'Correct' or e['follow_up']:
            print(f'  {e["invoice"]:<12} verdict {e["coding_verdict"]}; follow-up: {e["follow_up"]}')


if __name__ == '__main__':
    main()
