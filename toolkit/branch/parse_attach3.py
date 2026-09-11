"""parse_attach3.py - Batch attach_3: eight single-invoice TechOne attachment PDFs (EzeScan exports), raw-text route
(pdftotext -layout, page text retained), four vendor templates: MPDT, HERITAGE_CN, PLAYFORCE_ATT and PPG.

MPDT (Tree Acq Pty Ltd) is a new supplier on this register: a standard Xero layout, three tree-removal invoices, every
one of them on a register line that reads Unidentified today. Two PK typos print on the face and are captured as
printed (rule 13): PK#00047 on INV-14305 and PK#0000477 on INV-13576, both PK000477 on the ledger.

HERITAGE_CN is the Heritage Tree Services CREDIT NOTE layout, and it carries a trap worth stating plainly. The credit
advice at the foot prints "Credit Amount 0.00", which is the credit REMAINING after the note has been applied to an
invoice, not the value of the note: the note itself prints Subtotal $408.33, TOTAL GST 10% $40.83 and TOTAL AUD
$449.16, and the ledger posts -$408.33. Taking the advice figure as the total yields a $0.00 credit note that no longer
ties anything. Amounts are captured negative (rule 17 / F8 sign convention, doc_kind CREDIT_NOTE); the printed figures
stay positive in line_text, which is never edited.

PPG is an SAP layout new to this register: Item No | Material | Item Description | Quantity | Unit Price | Net Value,
with the unit price printed to FOUR decimals (191.1400) and no row labelled Subtotal. The printed subtotal is PRODUCT
TOTAL plus FREIGHT plus PAINTBACK LEVY, each of which prints separately, and neither invoice carries a PK on its face.

Usage: PDF_DIR=cache/attach_3_src OUT=batches/attach_3/corpus_attach_3_v6.json python3 parse_attach3.py
"""
import datetime as dt, hashlib, json, os, re, subprocess, sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_mixed1 import D, iso, Doc  # noqa
from parse_attach1 import text, npages  # noqa

PDF_DIR = os.environ.get('PDF_DIR', 'cache/attach_3_src')
FILES = [('C00301520_1.pdf', 'MPDT'), ('C00313294.pdf', 'MPDT'), ('C00310738.pdf', 'MPDT'),
         ('C00315202.pdf', 'HERITAGE_CN'), ('C00318738.pdf', 'HERITAGE_CN'),
         ('C00317309.pdf', 'PLAYFORCE_ATT'), ('C00312177_1.pdf', 'PPG'), ('C00306732_1.pdf', 'PPG')]
# Xero item row: Description | Quantity | Unit Price | GST | Amount AUD. The GST band prints a rate, not an amount,
# and is absent on a zero-amount row, so it is optional here and never read as money.
XERO = re.compile(r'^(?P<d>\S.*?\S)\s{2,}(?P<q>\d+\.\d{2})\s{2,}(?P<u>[\d,]+\.\d{2})\s{2,}(?:(?P<g>\d{1,2}%)\s{2,})?(?P<a>-?[\d,]+\.\d{2})\s*$')
TOTROW = re.compile(r'\s(?:Subtotal|TOTAL GST 10%|TOTAL AUD|Less Credit to Invoice\(s\)|REMAINING CREDIT)\s+[\d,]+\.\d{2}\s*$')
# Play Force attachment: Qty | Item | Description | Unit Price | Price (Ex. GST). The unit price can print without
# decimals, so the decimal places are not part of the test (prompt v6 4.2).
PFROW = re.compile(r'^\s*(?P<q>\d+\.\d{2})\s{2,}(?P<item>\S+)\s{2,}(?P<d>.*?)\s{2,}(?P<u>[\d,]+(?:\.\d+)?)\s{2,}(?P<a>-?[\d,]+\.\d{2})\s*$')
PFTOT = re.compile(r'(?:Total \(Ex\. GST\)|GST \(10%\)|Total \(Inc\. GST\))\s+\$\s?[\d,]+\.\d{2}\s*$')
# PPG (SAP): Item No | Material | Item Description | Quantity | Unit Price | Net Value, unit price to four decimals.
PPGROW = re.compile(r'^\s*(?P<item>\d+)\s+(?P<mat>\d+)\s{2,}(?P<d>\S.*?)\s{2,}(?P<q>\d+)\s{2,}(?P<u>[\d,]+\.\d{2,4})\s{2,}(?P<a>-?[\d,]+\.\d{2})\s*$')
PPGTOT = re.compile(r'(?:PRODUCT TOTAL|FREIGHT|PAINTBACK LEVY|GST|INVOICE TOTAL)\s+[\d,]+\.\d{2}\s*$')
SUPPLIER = {'MPDT': ('MPDT (Tree Acq Pty Ltd)', '92 626 678 635'),
            'HERITAGE_CN': ('Heritage Tree Services Pty Ltd ATF Rowan Family Trust', '32 416 129 034'),
            'PLAYFORCE_ATT': ('Play Force Australia Pty Ltd', '89 677 476 541'),
            'PPG': ('PPG Industries Australia Pty Ltd', '82 055 500 939')}
STEM = {'INV-13892': 'MPDT, tree removal, Jun-2026, 7425.00', 'INV-13576': 'MPDT, tree removal, May-2026, 5610.00',
        'INV-14305': 'MPDT, tree removal, Jul-2026, 8580.00', 'CN-48535': 'Heritage, credit, Aug-2026, -449.16',
        'CN-48871': 'Heritage, credit, Sep-2026, -429.00',
        'INV-8776': 'PlayForce, digger, Aug-2026, 6331.36', '5214496428': 'PPG, paint, Aug-2026, 210.25',
        '5214452043': 'PPG, paint, Jul-2026, 181.67'}


def below(page, label, value, span=4):
    """Read a header value printed on a row BENEATH its label. The Xero header stacks label over value and the
    letterhead block prints to the right of both, so a label-then-newline read finds the letterhead, not the value."""
    rows = page.splitlines()
    for i, r in enumerate(rows):
        if re.search(label, r):
            for x in rows[i + 1:i + 1 + span]:
                m = re.search(value, x)
                if m:
                    return m.group(0)
    raise AssertionError(f'{label!r} found no {value!r} within {span} rows beneath it')


def parse_one(fname, v):
    pdf = os.path.join(PDF_DIR, fname)
    n = npages(pdf)
    pages = {p: text(pdf, p) for p in range(1, n + 1)}
    d = Doc(v, 1); d.pages = list(range(1, n + 1)); d.page_text = pages
    full = '\n'.join(pages[p] for p in d.pages)
    hp = pages[1]
    h = d.h; lno = 0
    credit = v == 'HERITAGE_CN'
    sign = Decimal('-1') if credit else Decimal('1')
    xero = v in ('MPDT', 'HERITAGE_CN')
    h['pk'] = sorted(set(re.findall(r'PK\s?#?\s?0\d{5}\b', full)))
    h['pk_printed'] = sorted(set(re.findall(r'PK\s?#?\s?\d{4,7}', full)))
    h['contract'] = sorted(set(re.findall(r'PAR/?\d{3}[A-Z]?/?\d{4}|PAR\d{3}[A-Z]\d{4}', full)))
    # The Xero header prints each label and its value on different physical rows, with the letterhead block printing
    # to the right of both, so a label-then-newline read fails. Read the label row, then the row beneath it (prompt v6 5.2).
    h.update(supplier=SUPPLIER[v][0], abn=SUPPLIER[v][1])
    if xero:
        lbl = 'Credit Note Number' if credit else 'Invoice Number'
        h.update(inv=below(hp, lbl, r'(?:INV|CN)-\d+'),
                 date=iso(below(hp, r'\bDate\b' if credit else r'Invoice Date', r'\d{1,2} \w{3} \d{4}')),
                 due=(iso(m.group(1)) if (m := re.search(r'Due Date:\s+(\d{1,2} \w{3} \d{4})', full)) else None),
                 ref=(m.group(1) if (m := re.search(r'(?:Blanket Order #:|Reference\s*\n[^\n]*?)\s*(7\d{5})\b', full)) else None),
                 sub=sign * D(re.search(r'Subtotal\s+([\d,]+\.\d{2})', full).group(1)),
                 gst=sign * D(re.search(r'TOTAL GST 10%\s+([\d,]+\.\d{2})', full).group(1)),
                 tot=sign * D(re.search(r'TOTAL AUD\s+([\d,]+\.\d{2})', full).group(1)))
    elif v == 'PLAYFORCE_ATT':
        h.update(inv=re.search(r'Invoice Number\s+(INV-\d+)', hp).group(1),
                 date=iso(re.search(r'^\s*.*?\bDate\s+(\d{1,2}-\w{3}-\d{4})', hp, re.M).group(1)),
                 due=iso(re.search(r'Due Date\s+(\d{1,2}-\w{3}-\d{4})', hp).group(1)),
                 ref=(m.group(1) if (m := re.search(r'Reference\s+(\d+)', hp)) else None),
                 sub=D(re.search(r'Total \(Ex\. GST\)\s+\$\s?([\d,]+\.\d{2})', full).group(1)),
                 gst=D(re.search(r'GST \(10%\)\s+\$\s?([\d,]+\.\d{2})', full).group(1)),
                 tot=D(re.search(r'Total \(Inc\. GST\)\s+\$\s?([\d,]+\.\d{2})', full).group(1)))
    else:  # PPG: no row is labelled Subtotal; the ex-GST total is PRODUCT TOTAL + FREIGHT + PAINTBACK LEVY
        prod = D(re.search(r'PRODUCT TOTAL\s+([\d,]+\.\d{2})', full).group(1))
        frt = D(re.search(r'FREIGHT\s+([\d,]+\.\d{2})', full).group(1))
        lev = D(re.search(r'PAINTBACK LEVY\s+([\d,]+\.\d{2})', full).group(1))
        h.update(inv=below(hp, r'Invoice No\b', r'\d{10}'), date=iso(re.search(r'Date:\s+(\d{2}-\w{3}-\d{4})', hp).group(1)),
                 due=iso(re.search(r'Due Date:\s+(\d{2}-\w{3}-\d{4})', hp).group(1)),
                 ref=(m.group(1) if (m := re.search(r'Customer Reference\s*\n\s*(\d{6})', hp)) else None),
                 sub=prod + frt + lev, gst=D(re.search(r'^\s*GST\s+([\d,]+\.\d{2})\s*$', full, re.M).group(1)),
                 tot=D(re.search(r'INVOICE TOTAL\s+([\d,]+\.\d{2})', full).group(1)),
                 product_total=prod, freight=frt, levy=lev)
    for pn, p in [(x, pages[x]) for x in d.pages]:
        for ln in p.splitlines():
            lno += 1
            if not ln.strip():
                d.add(pn, lno, ln, 'BLANK'); continue
            if re.match(r'^\s*Description\s+Quantity\s+Unit Price', ln) or re.match(r'^\s*Qty\s+Item\s+Description', ln) \
                    or re.match(r'^\s*Item No\s+Material\s+Item Description', ln):
                d.add(pn, lno, ln, 'TABLE_HEADER'); continue
            if v == 'PLAYFORCE_ATT':
                if PFTOT.search(ln):
                    d.add(pn, lno, ln, 'TOTALS'); continue
                mm = PFROW.match(ln)
                if mm:
                    d.add(pn, lno, ln, 'PRICED', qty=float(D(mm.group('q'))), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))),
                          bands=['qty', 'unit_price', 'amount'], wo=None,
                          note='the printed Unit Price carries no decimals on some rows of this layout; the amount band decides (prompt v6 4.2)'
                               if '.' not in mm.group('u') else None)
                    continue
                d.add(pn, lno, ln, 'PAYMENT_ADVICE' if re.search(r'Electronic Funds Transfer|BSB:|Account:|Remittance To:', ln) else 'NARRATIVE')
                continue
            if v == 'PPG':
                if PPGTOT.search(ln):
                    d.add(pn, lno, ln, 'TOTALS'); continue
                mm = PPGROW.match(ln)
                if mm:
                    d.add(pn, lno, ln, 'PRICED', qty=float(D(mm.group('q'))), unit=float(Decimal(mm.group('u').replace(',', ''))),
                          amt=float(D(mm.group('a'))), bands=['qty', 'unit_price', 'amount'], wo=None,
                          note='the printed Unit Price carries four decimals on this layout; captured as printed')
                    continue
                d.add(pn, lno, ln, 'TERMS' if pn > 1 else ('PAYMENT_ADVICE' if re.search(r'Remit To:|Bank Deposit:|A/C:', ln) else 'NARRATIVE'))
                continue
            if TOTROW.search(ln) or re.search(r'Credit Amount\s+[\d,]+\.\d{2}', ln):
                d.add(pn, lno, ln, 'TOTALS',
                      note=('"Credit Amount" on the credit advice is the credit REMAINING after application, not the value '
                            'of this credit note (TOTAL AUD prints above)') if 'Credit Amount' in ln else None)
                continue
            mm = XERO.match(ln)
            if mm:
                amt = sign * D(mm.group('a'))
                d.add(pn, lno, ln, 'PRICED', qty=float(D(mm.group('q'))), unit=float(sign * D(mm.group('u'))), amt=float(amt),
                      gst=mm.group('g'), bands=[b for b, k in (('qty', 'q'), ('unit_price', 'u'), ('gst', 'g'), ('amount', 'a')) if mm.group(k)],
                      wo=None, note=('credit note: the face prints positive figures and the ledger posts the credit negative; '
                                     'captured negative, line_text as printed' if credit else
                                     ('zero-amount row as printed (rule 16a)' if amt == 0 else None)))
                continue
            d.add(pn, lno, ln, 'NARRATIVE')
    return d


def parse():
    out = []
    for fname, v in FILES:
        d = parse_one(fname, v)
        h = d.h
        full = '\n'.join(d.page_text[k] for k in sorted(d.page_text))
        cap = sum((D(l['line_ex_gst']) for l in d.lines if l['line_type'] == 'PRICED'), Decimal('0'))
        pdf = os.path.join(PDF_DIR, fname)
        gst_calc = D(h['sub'] * Decimal('0.1'))
        if h['gst'] != gst_calc:
            d.findings.append(f'Printed GST ${h["gst"]} differs from 10% of the printed subtotal ${gst_calc}.')
        if h['sub'] + h['gst'] != h['tot']:
            d.findings.append(f'Printed subtotal ${h["sub"]} plus printed GST ${h["gst"]} does not equal the printed total ${h["tot"]}.')
        odd = [p for p in h['pk_printed'] if not re.fullmatch(r'PK\s?#?\s?\d{6}', p)]
        if odd:
            d.findings.append(f'PK printed on the face is not of the PK000000 form: {", ".join(odd)}. Captured as printed (rule 13); '
                              f'the ledger work order is PK000477.')
        if v == 'PPG':
            d.findings.append(f'No row is labelled Subtotal on this layout: the ex-GST total is PRODUCT TOTAL ${h["product_total"]} '
                              f'plus FREIGHT ${h["freight"]} plus PAINTBACK LEVY ${h["levy"]}, captured as the printed subtotal.')
            if not h['pk_printed']:
                d.findings.append('No PK or work order is printed on the invoice face; the only reference printed is Customer Reference '
                                  f'{h.get("ref")}.')
        if v == 'PLAYFORCE_ATT':
            if 'Account: undefined' in full:
                d.findings.append('The Account field on the face prints the literal word "undefined", so the invoice carries no PK.')
            q = re.search(r'as per Quote (\d+)', full)
            if q:
                d.findings.append(f'The only description is "as per Quote {q.group(1)}" and the quote is not attached; '
                                  'the quote is needed to evidence what was supplied.')
        if v == 'HERITAGE_CN':
            d.findings.append('Credit note. The credit advice prints "Credit Amount 0.00", which is the credit remaining after this '
                              f'note was applied; the note itself is ${-h["tot"]} incl GST (${-h["sub"]} ex GST).')
        stem = STEM[h['inv']]
        assert len(stem) <= 40, stem
        out.append(dict(doc_ref=f'{h["inv"]}/{fname}', doc_kind='CREDIT_NOTE' if v == 'HERITAGE_CN' else 'TAX_INVOICE',
                        source_file=fname, source_md5=hashlib.md5(open(pdf, 'rb').read()).hexdigest(),
                        page_range=[d.pages[0], d.pages[-1]], supplier=h['supplier'], supplier_abn=h['abn'], abn_source='letterhead',
                        invoice_no=h['inv'], invoice_date=h['date'], due_date=h.get('due'),
                        printed_subtotal_ex_gst=float(h['sub']), subtotal_basis='printed', printed_gst=float(h['gst']),
                        printed_total_incl_gst=float(h['tot']), captured_ex_gst=float(cap), line_amount_basis='ex_gst',
                        tie_basis='ex_gst', self_tie='TIE' if cap == h['sub'] else 'OUT', retry_log=[],
                        table_headers=[dict(page=l['page'], row=l['line_no'], text=l['line_text'],
                                            bands={k: l['line_text'].index(t) for k, t in
                                                   (('description', 'Description'), ('quantity', 'Quantity'), ('qty', 'Qty'),
                                                    ('item', 'Item'), ('material', 'Material'), ('unit_price', 'Unit Price'),
                                                    ('gst', 'GST'), ('amount', 'Amount AUD'), ('amount_ex', 'Price (Ex. GST)'),
                                                    ('net_value', 'Net Value')) if t in l['line_text']})
                                       for l in d.lines if l['line_type'] == 'TABLE_HEADER'],
                        work_orders=[p.replace(' ', '').replace('#', '') for p in h['pk']], contract_refs=h['contract'],
                        po_refs=[h['ref']] if h.get('ref') else [],
                        pk_refs=h['pk_printed'],  # rule 13: the PK as printed; MPDT prints PK#00047 and PK#0000477
                        printed_account_codes=h['pk_printed'], evidence_stem=stem, duplicate_of=None, findings=d.findings,
                        notes=f'{v} template, raw-text route (pdftotext -layout), page text retained; TechOne attachment {fname} (EzeScan export).',
                        lines=d.lines, page_text=d.page_text, vendor_template=v))
    return out


if __name__ == '__main__':
    docs = parse()
    files = [dict(file=f, md5=hashlib.md5(open(os.path.join(PDF_DIR, f), 'rb').read()).hexdigest(),
                  pages=npages(os.path.join(PDF_DIR, f))) for f, _ in FILES]
    ver = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True).stderr.strip().splitlines()[0]
    corpus = dict(manifest=dict(batch_id='attach_3', source_files=files, runtime='A',
                                extraction_tool=f'parse_attach3.py raw-text route ({ver}, -layout, 2 vendor templates)',
                                extracted_utc=dt.datetime.now(dt.timezone.utc).isoformat(), prompt_version='v6 (raw-text fallback)',
                                ocr_pages_run=0, ocr_pages_not_required=sum(f['pages'] for f in files),
                                ocr_pages_not_available=0, ocr_pages_outstanding=0, resume_point=None), documents=docs)
    out = os.environ.get('OUT', 'corpus_attach_3_v6.json')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    json.dump(corpus, open(out, 'w'), indent=1)
    for d in docs:
        pl = [l for l in d['lines'] if l['line_type'] == 'PRICED']
        print(f"{d['invoice_no']:11} {d['vendor_template']:12} {d['source_file']:16} sub {d['printed_subtotal_ex_gst']:>10,.2f} "
              f"cap {d['captured_ex_gst']:>10,.2f} {d['self_tie']} gst {d['printed_gst']:>9,.2f} tot {d['printed_total_incl_gst']:>10,.2f} "
              f"priced {len(pl)} pk {d['printed_account_codes']} po {d['po_refs']}")
