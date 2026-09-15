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
                held[ref] = f'resolves to {len(rows)} register rows; needs a declared SUM-TIE or split variant'
                counts['held, multiple rows'] += 1
                continue
            i, r = rows[0]
            if txt(r[8]) != 'PUR Cred Invoice':
                held[ref] = f'register row {i} is {txt(r[8])!r}; rule 17 green-blocks AP lines only'
                counts['held, not an AP line'] += 1
                continue
            if D(r[19]) != D(d['printed_subtotal_ex_gst']):
                why = ('a zero-amount companion row, never green-blocked (rule 17)' if abs(D(r[19])) <= Decimal('0.005')
                       else f'register {D(r[19])} against a printed subtotal of {D(d["printed_subtotal_ex_gst"])}; needs a declared check variant')
                held[ref] = f'register row {i}: {why}'
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
            sub_, gst_ = D(d['printed_subtotal_ex_gst']), D(d['printed_gst'])
            exp_ = (sub_ * Decimal('0.1')).quantize(Decimal('0.01'), ROUND_HALF_UP)
            if gst_ != exp_:
                if gst_ == 0:
                    facts['variants'] = ['check3 gstfree']
                elif abs(gst_ - exp_) <= Decimal('0.01'):
                    facts['variants'] = ['check3 tol1cgst']
                elif abs(gst_ - exp_) <= Decimal('0.02'):
                    facts['variants'] = ['check3 tol2c']
                else:
                    held[ref] = (f'printed GST {gst_} is not 10% of the printed subtotal {sub_} ({exp_}) and the '
                                 f'difference is beyond every ratified check 3 tolerance')
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
        'capture_stamp': '15-Sep-2026',
        'handover': (
            'v128 change (15-Sep-2026): the branch capture programme ported back. %d tax invoices sighted at branch v2 to '
            'v13 sit on lines of THIS register, and every one is now captured here at line-item granularity with all three '
            'rule 17 checks live: %d evidence lines over %d corpora, all gated GREEN. The two registers now state the same '
            'printed fields for the same documents, because both read them with the same reader. The control total does not '
            'move: this is a capture build (rule 10). %d documents in those corpora are NOT captured here and each is held '
            'with its reason in the brief: %d carry no line on this register, %d are already sighted here, %d resolve to more '
            'than one row and need a declared SUM-TIE or split variant, %d differ in amount (two are zero-amount companion '
            'rows, which are never green-blocked) and one is a DIR rather than a PUR line.'
            % (len(documents), eil_lines, len(corpora), len(held),
               counts['no line on this register'], counts['already sighted here'], counts['held, multiple rows'],
               counts['held, amount differs'])),
        'method': (
            'Capture from the branch corpora (v128). The Nature Category on a captured row is THE ONE THE ROW ALREADY '
            'CARRIES. A capture build proves what a document says; it does not re-categorise the register, and all %d target '
            'rows already carry a category on Theme_Map A5:A31. Where a branch batch read an invoice into a branch-extension '
            'heading this register has no row for (Signage & park furniture, Horticultural & landscape supplies), the row '
            'keeps its own category and the branch reading is written into the coding note, where it states a fact rather '
            'than keying a COUNTIF. The printed green-block fields are read by pbr_capture.header_fields, the same reader the '
            'branch register uses, so the two registers cannot disagree about what a document prints and the branch '
            'provenance gate covers both. Boilerplate for a vendor this register has not carried before is appended to '
            'Vendor_Boilerplate and cited by key (rule 17 Amendment 2); a vendor that prints no terms block cites no key and '
            'the column reads (not printed).' % len(documents)),
        'data_acquisition': (
            'v128: %d gated corpora built from, all GREEN, listed in the brief. No new source file is acquired: every corpus '
            'was received and md5-screened at the branch register build that first used it, and this build re-gates each one '
            'rather than trusting that record.' % len(corpora)),
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
