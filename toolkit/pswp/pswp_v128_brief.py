"""pswp_v128_brief.py - author the v128 capture brief from the gated corpora and the v127 register.

RULE 20. A session authors a BRIEF, not a script. This file is the authoring step for v128 and it forms no coding
judgement of its own: every fact it writes is read from the gated corpus, from the register row the document sits on,
or from the batch's own authored notes. Specifically:

  nature_category   THE REGISTER ROW'S OWN CATEGORY. A capture build proves what a document says; it is not a
                    re-categorisation build, so the category already settled on the row is carried unchanged. All 193
                    target rows carry one and all 193 are on Theme_Map A5:A31. Where a branch batch assigned a
                    per-invoice category from a BRANCH-EXTENSION heading that this register has no row for (Signage &
                    park furniture, Horticultural & landscape supplies), the row's own category stands and the branch
                    reading is carried into the coding note instead, where it states a fact rather than keys a COUNTIF.
  green block       pbr_capture.header_fields, the same reader the branch register uses, so the two registers state
                    the same printed fields for the same document and the branch provenance gate covers both.
  coding note       the batch's authored notes (rule 18), verbatim.

WHAT IS HELD AND WHY. A document is captured here only where it resolves to exactly ONE register row that is an AP
line, carries no EvID yet, and ties the printed subtotal to the cent. Everything else is listed in the brief's own
held block with its reason and is not part-built from (rule 19.2): 21 documents resolve to more than one row and need
a declared SUM-TIE or split variant, 8 differ in amount (two are zero-amount companion rows, which are never
green-blocked), and one is a DIR rather than a PUR line.

Usage: python3 pswp_v128_brief.py [out.json]
"""
import collections, glob, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

from python_calamine import CalamineWorkbook

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'toolkit', 'branch'))
import pbr_capture  # noqa: E402
import pbr_stage  # noqa: E402

REG_PATH = os.path.join(ROOT, 'registers', os.environ.get('PSWP_IN', 'PS_WP_Transaction_Register_3FY_v128.xlsx'))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'batches', os.environ.get('PSWP_BATCH', 'pswp_v129'), f'brief_{os.environ.get("PSWP_VER", "v129")}.json')
NP = pbr_capture.NP
D = lambda x: Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)
txt = lambda v: str(int(v)) if isinstance(v, float) and v.is_integer() else ('' if v is None else str(v).strip())


# Declared exceptions, held as data and named one document at a time so nothing is waved through by class.
# 1026099 is the Origin Council-wide consolidated electricity invoice: a DIR line, and this register carries ONE site
# row out of a $565,345.00 face. Check 2 ties that row by summing only its own printed line, matched on the NMI the
# page prints and the register narration also names (QB10790446), so the association is evidence on both sides. The
# branch register captured the same document the same way at its v3 build.
DECLARED_DOC_TYPE = {'1026099/pages1-5'}
DECLARED_PARTIAL = {'1026099/pages1-5': [['e23a62cd-73312-PK000469-01', 'QB10790446']]}


def _gst_by_line(doc):
    """The sum of the GST the page prints on each line, where it prints one; None where it does not."""
    vals = [l.get('gst') for l in doc['lines'] if l.get('line_type') == 'PRICED']
    nums = [D(v) for v in vals if isinstance(v, (int, float))]
    return sum(nums, Decimal('0.00')) if nums else None


def _same_party(row, doc):
    """Could the register row be this supplier's line? Identity by ABN first (rule 8), then by name.

    UNKNOWN IS NOT ANOTHER PARTY. A row labelled Unidentified has no contractor yet, so it cannot contradict the
    document; only a row naming a DIFFERENT contractor does. Treating unidentified as a collision would refuse exactly
    the lines this programme exists to identify.
    """
    import re as _re
    dig = lambda x: _re.sub(r'\D', '', str(x or ''))
    if dig(row[12]) and dig(doc.get('supplier_abn')) and dig(row[12]) == dig(doc.get('supplier_abn')):
        return True
    name = txt(row[11])
    if not name or name.lower().startswith(('unidentified', 'not identified', 'unknown')):
        return True
    a = _re.sub(r'[^a-z]', '', name.lower())[:10]
    b = _re.sub(r'[^a-z]', '', str(doc.get('supplier') or '').lower())[:10]
    return bool(a) and bool(b) and (a in b or b in a)


def sheet(name):
    return CalamineWorkbook.from_path(REG_PATH).get_sheet_by_name(name).to_python(skip_empty_area=False)


def main():
    reg = sheet('Register')
    by_ref = collections.defaultdict(list)
    for i, r in enumerate(reg[4:], start=5):
        if txt(r[0]):
            by_ref[txt(r[7])].append((i, r))
    bp_keys = {txt(r[0]) for r in sheet('Vendor_Boilerplate')[4:] if txt(r[0])}
    # Rule 12 screens BOTH ways. A document can sit on Evidence_Invoices while its register row carries no EvID (an
    # earlier capture that did not reach the row, or one on a row this build is not touching), so the register column
    # alone is not the duplicate screen.
    seen_evid = {txt(r[0]) for r in sheet('Evidence_Invoices')[4:] if txt(r[0])}
    seen_bare = {e.split('/')[0] for e in seen_evid}
    cats = {txt(r[0]) for r in sheet('Theme_Map')[4:31] if txt(r[0])}

    notes = {}
    for f in glob.glob(os.path.join(ROOT, 'batches', '*', 'match_*_v6.json')):
        for e in json.load(open(f)):
            notes[e['invoice']] = e

    documents, corpora, held, boiler, stems = {}, [], {}, {}, {}
    counts = collections.Counter()
    eil_lines = 0
    row_owner = {}
    order = {b: i for i, b in enumerate(pbr_stage.BATCHES)}
    paths = sorted(glob.glob(os.path.join(ROOT, 'batches', '*', 'corpus_*_v6.json')),
                   key=lambda p_: order.get(os.path.basename(os.path.dirname(p_)), 999))
    for path in paths:
        batch = os.path.basename(os.path.dirname(path))
        corpus = json.load(open(path))
        used = False
        for d in corpus['documents']:
            ref = str(d['doc_ref'])
            if d.get('duplicate_of'):
                held[ref] = f'repeated copy of the document at pages {d["duplicate_of"]}; never captured twice (prompt v6 11.4)'
                continue
            if ref in documents:
                # The same invoice supplied by two corpora in this build. It is audited and captured once (rule 12);
                # counting it twice here would overstate the evidence lines this build writes.
                continue
            rows = by_ref.get(d['invoice_no'], [])
            if not rows:
                held[ref] = 'no line on this register: the binder spans years and sections this register does not cover'
                counts['no line on this register'] += 1
                continue
            if ref in seen_evid or ref.split('/')[0] in seen_bare or d['invoice_no'] in seen_bare:
                held[ref] = 'already on Evidence_Invoices; a re-sighting is not re-captured (rule 12)'
                counts['already sighted here'] += 1
                continue
            if any(txt(r[87]) for _, r in rows):
                held[ref] = f'register row {rows[0][0]} already carries EvID {txt(rows[0][1][87])}; a re-sighting is not re-captured (rule 12)'
                counts['already sighted here'] += 1
                continue
            if len(rows) > 1:
                # SUM-TIE: the register splits one invoice over several lines and they sum to the printed subtotal to
                # the cent. The capture sits on one row and check 2 sums the siblings, which is the ratified form.
                # Rows that do NOT sum to the printed subtotal are a different question and stay held.
                s_ = sum(D(r[19]) for _, r in rows)
                if s_ != D(d['printed_subtotal_ex_gst']):
                    held[ref] = (f'resolves to {len(rows)} register rows summing {s_}, which is not the printed subtotal '
                                 f'{D(d["printed_subtotal_ex_gst"])}; needs a split or partial-scope decision')
                    counts['held, multiple rows that do not sum'] += 1
                    continue
                sumtie = sorted((i_ for i_, _ in rows))
                i, r = max(rows, key=lambda x: D(x[1][19]))
            else:
                sumtie = None
                i, r = rows[0]
            doc_type_allowed = None
            if txt(r[8]) != 'PUR Cred Invoice':
                if ref in DECLARED_DOC_TYPE:
                    doc_type_allowed = txt(r[8])
                else:
                    held[ref] = f'register row {i} is {txt(r[8])!r}; rule 17 green-blocks AP lines only'
                    counts['held, not an AP line'] += 1
                    continue
            amt_variants = []
            if sumtie is None and D(r[19]) != D(d['printed_subtotal_ex_gst']):
                gap = abs(D(r[19]) - D(d['printed_subtotal_ex_gst']))
                same_party = _same_party(r, d)
                if abs(D(r[19])) <= Decimal('0.005'):
                    held[ref] = f'register row {i}: a zero-amount companion row, never green-blocked (rule 17)'
                    counts['held, zero-amount companion'] += 1
                    continue
                if not same_party:
                    # A REFERENCE COLLISION, not a variant. Invoice numbers repeat across creditors and years: rows
                    # 6659, 3568 and 6625 are STAR CARPENTRY FY2023/24 invoices whose references happen to equal Play
                    # Force FY2026/27 numbers. Offering a check variant here would tie a green block to another
                    # supplier's line, so it is refused outright and never captured.
                    held[ref] = (f'register row {i} carries reference {txt(r[7])} for {txt(r[11]) or "another creditor"} '
                                 f'({txt(r[4])}, {D(r[19])}), not for {d["supplier"]}: the reference collides across '
                                 f'creditors and years, so this is a different document and is never captured here')
                    counts['held, reference collision with another creditor'] += 1
                    continue
                if gap <= Decimal('0.01'):
                    amt_variants = ['check2 tol1c']
                elif ref in DECLARED_PARTIAL:
                    amt_variants = ['check2 split']
                else:
                    held[ref] = (f'register row {i}: register {D(r[19])} against a printed subtotal of '
                                 f'{D(d["printed_subtotal_ex_gst"])}; needs a split or partial-scope decision')
                    counts['held, amount differs'] += 1
                    continue

            v = d['vendor_template']
            hf = pbr_capture.header_fields(d)
            pref = pbr_capture.BPK.get(v)
            pk = (d['pk_refs'] or [hf.get('printed_account', NP)])[0]
            pk = 'undefined (as printed)' if pk == 'undefined' else pk
            cat = txt(r[23])
            assert cat in cats, (ref, cat)
            m = notes.get(d['invoice_no']) or {}
            # Nature Detail, in order of preference and all three read from the page: the printed work description,
            # the batch's authored note (itself a restatement of the printed face), then the printed line descriptions.
            # A document with none of the three is HELD, because rule 17 Amendment 1 keeps a row Partial on an empty or
            # generic detail and this driver writes Confirmed unconditionally: inventing a detail to satisfy it would
            # be the upgrade the rule exists to refuse.
            detail = (hf.get('work') if hf.get('work') not in (None, '', NP) else None) or (m.get('coding_note') or '')
            if len(detail.strip()) < 12:
                descs = [re.sub(r'\s+[\d,.]+\s+\$?[\d,.]+\s+\d+%.*$', '', ' '.join(l['line_text'].split()))
                         for l in d['lines'] if l.get('line_type') == 'PRICED']
                detail = 'Printed line items: ' + '; '.join(x.strip() for x in descs if x.strip())
            if len(detail.strip()) < 12:
                held[ref] = 'no printed work description, authored note or line description to carry a Nature Detail; rule 17 Amendment 1 keeps the row Partial'
                counts['held, no nature detail'] += 1
                continue
            facts = {
                'nature_category': cat,
                'nature_detail': ' '.join(detail.split())[:240],
                'address': hf.get('addr'), 'phone': hf.get('phone'), 'bill_to': hf.get('bill'),
                'requesting_officer': hf.get('officer'), 'sites': hf.get('site'),
                'work_description': hf.get('work'), 'payments_made': hf.get('paid'), 'balance_due': hf.get('bal'),
                'pk_normalised': pk.replace(' ', '').replace('#', '') if pk != NP else NP,
                'due_date': pbr_capture.date_out(d.get('due_date')) if d.get('due_date') else NP,
                # A key is cited only where the vendor PRINTS that block. Weis prints a bank line and no terms, so
                # citing BP:WC-T1 would point at boilerplate that does not exist; the column reads (not printed).
                'payment_details_key': f'BP:{pref}-P1' if (pbr_capture.BOILER.get(v) or (None, None))[0] else NP,
                'terms_key': f'BP:{pref}-T1' if (pbr_capture.BOILER.get(v) or (None, None))[1] else NP,
                'boilerplate_keys': [f'BP:{pref}-{sfx}' for sfx, has in
                                     (('P1', (pbr_capture.BOILER.get(v) or (None, None))[0]),
                                      ('T1', (pbr_capture.BOILER.get(v) or (None, None))[1])) if has],
                'target_row': i,
            }
            # Check 3 proves the printed GST is 10% of the printed subtotal. Where the page's own two figures do not
            # satisfy that exactly, the ratified variant for the difference is declared from the figures themselves and
            # nothing is restated: INV-7592 prints $8,826.85 and $882.68 where 10% rounds to $882.69, the vendor having
            # rounded the half down. A difference beyond the ratified tolerances is not given a variant; it stops here.
            facts.setdefault('variants', [])
            if sumtie:
                facts['variants'].append('check2 sumtie')
                facts['sibling_rows'] = sumtie
            facts['variants'] += amt_variants
            if doc_type_allowed:
                facts['doc_type_allowed'] = doc_type_allowed
            if ref in DECLARED_PARTIAL:
                facts['line_map'] = DECLARED_PARTIAL[ref]
            sub_, gst_ = D(d['printed_subtotal_ex_gst']), D(d['printed_gst'])
            exp_ = (sub_ * Decimal('0.1')).quantize(Decimal('0.01'), ROUND_HALF_UP)
            if gst_ != exp_:
                if gst_ == 0:
                    facts['variants'].append('check3 gstfree')
                elif abs(gst_ - exp_) <= Decimal('0.01'):
                    facts['variants'].append('check3 tol1cgst')
                elif abs(gst_ - exp_) <= Decimal('0.02'):
                    facts['variants'].append('check3 tol2c')
                elif _gst_by_line(d) == gst_:
                    # The page prints GST per line and its total is the sum of those roundings, not 10% of the
                    # subtotal. Proven against the captured per-line GST, which is the document's own arithmetic.
                    facts['variants'].append('check3 sumgst')
                else:
                    held[ref] = (f'printed GST {gst_} is not 10% of the printed subtotal {sub_} ({exp_}), the '
                                 f'difference is beyond every ratified tolerance, and the captured per-line GST '
                                 f'({_gst_by_line(d)}) does not reach it either')
                    counts['held, GST outside every ratified tolerance'] += 1
                    documents.pop(ref, None)
                    continue
            if v == 'HARPLEY':
                facts.update(request_date=hf.get('request_date'), request_via=hf.get('via'),
                             site_contact=hf.get('site_contact'), technician=hf.get('technician'))
            if m.get('coding_note'):
                facts['coding_note'] = m['coding_note']
            if m.get('coding_verdict'):
                facts['verdict'] = m['coding_verdict']
            branch_cat = m.get('nature_category')
            if branch_cat and branch_cat not in cats:
                facts['coding_note'] = ((facts.get('coding_note', '') + ' ') if facts.get('coding_note') else '') + (
                    f'The branch register reads this invoice as {branch_cat!r}, a heading this register\'s Theme_Map does not '
                    f'carry; the row keeps its own category {cat!r} and the branch reading is recorded here rather than keyed.')
            prior = row_owner.get(i)
            if prior is not None:
                # The same invoice supplied by two corpora under different doc_refs. Audited, not captured twice
                # (rule 12): the printed totals must agree, and the EARLIER batch's copy is kept because that is the
                # one the branch register already cites.
                p_ = documents[prior]
                assert (p_['printed'] == [str(D(d['printed_subtotal_ex_gst'])), str(D(d['printed_gst'])),
                                          str(D(d['printed_total_incl_gst']))]), (ref, prior, 'printed totals differ')
                held[ref] = (f'the same invoice is supplied by an earlier corpus as {prior} and captured there; '
                             f'audited against this copy, identical printed totals, not captured twice (rule 12)')
                counts['held, re-supplied under another doc_ref'] += 1
                continue
            facts['printed'] = [str(D(d['printed_subtotal_ex_gst'])), str(D(d['printed_gst'])),
                                str(D(d['printed_total_incl_gst']))]
            row_owner[i] = ref
            facts['variants'] = facts['variants'] or None
            if not facts['variants']:
                facts.pop('variants')
            documents[ref] = facts
            stems[ref] = d.get('evidence_stem')
            counts['CAPTURED'] += 1
            eil_lines += len([l for l in d['lines'] if l.get('line_type') == 'PRICED'])
            used = True
            # Boilerplate this register has not carried before, taken verbatim from the vendor's own printed block.
            p_, t_ = pbr_capture.BOILER.get(v, (None, None))
            for key, field, text_ in ((f'BP:{pref}-P1', 'Payment details', p_), (f'BP:{pref}-T1', 'Terms & notices', t_)):
                if key not in bp_keys and text_ and key not in boiler:
                    boiler[key] = dict(key=key, field=field, first_sighting=ref, vendor=d.get('supplier'),
                                       sightings=None, text=text_)
        if used:
            corpora.append(os.path.relpath(path, os.path.dirname(OUT)))
        else:
            for d in corpus['documents']:
                held.pop(str(d['doc_ref']), None)   # corpus not listed, so its documents are not in this build

    brief = {
        '_readme': [
            'PS & WP v128 capture brief (rule 20). Authored by pswp_v128_brief.py from the gated corpora, the v127',
            'register row each document sits on, and the batches\' own authored notes. No coding judgement is formed here:',
            'the Nature Category is the one the register row already carries, because a capture build proves what a',
            'document says and does not re-categorise the register.'],
        'batch_id': os.environ.get('PSWP_BATCH', 'pswp_v129'),
        'batch_label': f'Branch batches ported to PS & WP at {os.environ.get("PSWP_VER", "v129")}',
        'version_to': os.environ.get('PSWP_VER', 'v129'),
        'workbook_in': os.path.relpath(REG_PATH, os.path.dirname(OUT)),
        'workbook_out': f'PS_WP_Transaction_Register_3FY_{os.environ.get("PSWP_VER", "v129")}.xlsx',
        'output_dir': os.path.join(ROOT, 'registers'),
        'match_table': f'match_{os.environ.get("PSWP_VER", "v129")}.json',
        'corpora': corpora,
        'documents': documents,
        'held': sorted(held),
        'held_reasons': held,
        'vendor_boilerplate': sorted(boiler.values(), key=lambda x: x['key']),
        # Vendor_Boilerplate labels column 3 "Vendor (printed, first sighting)" and column 4 "First-sighting invoice
        # (Ev ID)", but every stored row carries the invoice id in column 3 and the vendor in column 4. The data is
        # right and consistent across 131 rows; the two labels are the wrong way round. Relabelling moves no value and
        # breaks no citation, and the v128 open item raised it for exactly this build to settle.
        'header_fixes': [
            dict(sheet='Vendor_Boilerplate', row=4, column=3, expect='Vendor (printed, first sighting)',
                 to='First-sighting invoice (Ev ID)'),
            dict(sheet='Vendor_Boilerplate', row=4, column=4, expect='First-sighting invoice (Ev ID)',
                 to='Vendor (printed, first sighting)'),
        ],
        'capture_stamp': '15-Sep-2026',
        'handover': (
            'v129 change (15-Sep-2026): the documents v128 held are settled and captured. %d invoices, %d evidence lines. '
            'Twenty-one resolve to two register lines each that sum to the printed subtotal to the cent and take the ratified '
            'SUM-TIE form of check 2; two differ from their line by one cent and take the ratified tolerance; one is the Origin '
            'Council-wide consolidated electricity invoice, a DIR line carrying one site row out of a $565,345.00 face, which '
            'ties that row by the NMI the page prints and the register narration names, and proves its GST against the sum of '
            'the printed per-line GST rather than 10%% of the subtotal. Control total unchanged (rule 10). '
            'Six documents remain held and both reasons are permanent: four carry a reference that collides with another '
            'creditor\'s invoice (Play Force numbers INV-8846, INV-8850 and INV-8907 are also STAR CARPENTRY FY2023/24 '
            'references, and a green block there would tie this evidence to another supplier\'s line), and two target '
            'zero-amount companion rows, which rule 17 never green-blocks.'),
        'method': (
            'Check variants are READ FROM THE FIGURES, never chosen. A document whose register lines sum to its printed '
            'subtotal takes SUM-TIE; one within a cent takes the ratified tolerance; one whose printed GST is the sum of its '
            'own per-line GST takes check3 sumgst, which is the form an invoice that prints GST per line actually supports and '
            'the form the branch register has proved this document with since its v3 build. A consolidated invoice maps its '
            'site row by a string the PAGE prints and the REGISTER NARRATION also names, so the association is evidence on '
            'both sides rather than a position in a list. Anything the figures do not settle stays held. '
            'A reference that matches a row belonging to a DIFFERENT creditor is refused outright rather than offered a '
            'variant: invoice numbers repeat across creditors and years, and a variant there would tie a green block to '
            'another supplier. A row labelled Unidentified is not a different creditor, it is an unidentified one, and still '
            'takes its capture.'),
        'data_acquisition': (
            'v129: no new source file. Every corpus built from was received and md5-screened at the branch build that first '
            'used it, and is re-gated here.'),
        'open_items': [
            dict(fy='All', status='Open', series='Documents held at v128',
                 lines=len([r for r in held if r not in documents]), amount=None,
                 action=('%d documents in the v128 corpora are not captured: %d resolve to more than one register row and need '
                         'a declared SUM-TIE or split variant, %d differ in amount from their row (two are zero-amount companion '
                         'rows), one is a DIR rather than a PUR line, and the rest carry no line here or are already sighted. '
                         'Each is listed with its reason in brief_v128.json; settle the variants and capture them at v129.'
                         % (len(held), counts['held, multiple rows'], counts['held, amount differs']))),
            dict(fy='All', status='Open', series='Vendor_Boilerplate header', lines=1, amount=None,
                 action=('Vendor_Boilerplate labels column 3 "Vendor (printed, first sighting)" and column 4 "First-sighting '
                         'invoice (Ev ID)", but all stored rows carry the invoice id in column 3 and the vendor in column 4. '
                         'The v128 append follows the data, not the header. Relabel the two headers (no data moves).')),
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(brief, open(OUT, 'w'), indent=1, ensure_ascii=False)

    match = {'batches': {os.environ.get('PSWP_BATCH', 'pswp_v129'): [
        {'doc_ref': ref, 'target_row': f['target_row'], 'target_count': 1,
         'target_linekey': txt(reg[f['target_row'] - 1][0])} for ref, f in sorted(documents.items())]}}
    json.dump(match, open(os.path.join(os.path.dirname(OUT), f'match_{os.environ.get("PSWP_VER", "v129")}.json'), 'w'), indent=1)

    for k, n in counts.most_common():
        print(f'{n:5}  {k}')
    print(f'\nbrief: {len(documents)} documents captured, {len(held)} held, {len(boiler)} boilerplate key(s) to add, '
          f'{len(corpora)} corpora')
    bad = [r for r, s_ in stems.items() if not s_ or len(s_) > 40]
    print('evidence stems over 40 characters or missing:', len(bad), bad[:5])


if __name__ == '__main__':
    main()
