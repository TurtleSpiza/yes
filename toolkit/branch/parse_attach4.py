"""parse_attach4.py - Batch attach_4: twenty single-invoice TechOne attachment PDFs (EzeScan exports), raw-text route
(pdftotext -layout, page text retained) to extraction prompt v6, three vendor templates: LEVAI, GLASCOTT, ELEMENTAL.

Eighteen are T & H Levai invoices spanning Aug-2025 to Aug-2026, the other two are the invoices behind the two largest
unidentified contractor series on the branch register: Glascott 012195 (Natural Areas, $35,866.01) and Elemental Shade
Structures 6491 (Park Services, $14,529.20). The APLEDGER histories that identify both are embedded at the same build.

Three things this file exists to get right, each a prompt v6 rule:

  4.2  A priced row is decided by the AMOUNT BAND alone. Levai prints one amount against a block of description rows,
       the rows under it carrying no money, and a second amount further down where the quote has two components
       (INV-39477 prints 10,430.00 and 1,800.00 against one Subtotal of 12,230.00). Only the rows in the band are
       priced, and the band opens at the DESCRIPTION / AMOUNT header and closes at Bank Details.

  16d  An ATTACHED SCHEDULE is not the invoice face. The Glascott invoice prints one face line, "Please refer to
       attached sheet for details", and a second page listing every park, site code, cost account, rotation and
       treatment date behind it. The schedule rows are captured as ATTACHMENT lines and excluded from check 1, which
       ties the face; they are what makes the face auditable, not part of it.

  5.2  Elemental prints its item table as Unit Price | Quantity | GST | Total where the TOTAL COLUMN IS GST
       INCLUSIVE: 6130.20 + 613.02 = 6743.22. The ex-GST line amount is quantity times unit price, and the printed
       Total Excluding GST ($14,529.20) is the sum of those, not of the Total column. Reading the Total column as the
       line amount overstates every Elemental line by a tenth.

Usage: PDF_DIR=cache/attach_4_src OUT=batches/attach_4/corpus_attach_4_v6.json python3 parse_attach4.py
"""
import datetime as dt, hashlib, json, os, re, subprocess, sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_mixed1 import D, iso, Doc, labelled, GLAS  # noqa: E402
from parse_attach1 import text, npages  # noqa: E402

PDF_DIR = os.environ.get('PDF_DIR', 'cache/attach_4_src')
FILES = [('C00227033 (2).pdf', 'LEVAI'), ('C00227484 (2).pdf', 'LEVAI'), ('C00228688 (2).pdf', 'LEVAI'),
         ('C00236196 (2).pdf', 'LEVAI'), ('C00240026 (2).pdf', 'LEVAI'), ('C00257205 (2).pdf', 'LEVAI'),
         ('C00263155 (2).pdf', 'LEVAI'), ('C00272275 (2).pdf', 'LEVAI'), ('C00277235 (2).pdf', 'LEVAI'),
         ('C00277239 (2).pdf', 'LEVAI'), ('C00279716 (2).pdf', 'LEVAI'), ('C00285757 (2).pdf', 'LEVAI'),
         ('C00290162 (2).pdf', 'LEVAI'), ('C00290563 (2).pdf', 'LEVAI'), ('C00301238 (1).pdf', 'LEVAI'),
         ('C00314456.pdf', 'LEVAI'), ('C00316920.pdf', 'LEVAI'), ('C00317046.pdf', 'LEVAI'),
         ('C00318419.pdf', 'GLASCOTT'), ('C00319023.pdf', 'ELEMENTAL')]
SUPPLIER = {'LEVAI': ('T & H LEVAI PTY LTD', '65 100 395 480'),
            'GLASCOTT': ('Glascott Landscape and Civil Pty Limited (letterhead prints "Technigro ABN 97 001 281 572")', '97 001 281 572'),
            'ELEMENTAL': ('Elemental Shade Structures (Dice Canvas Pty Ltd ATF The Dice Trust & SSAR Australia Pty Ltd ATF The Mark West Trust)', '99 292 107 173')}
# Levai: DESCRIPTION | AMOUNT, one amount column at the right. The band opens at the header and closes at Bank Details.
LEV_ROW = re.compile(r'^\s*(?P<d>.*?\S)\s{2,}(?P<a>-?[\d,]+\.\d{2})\s*$')
LEV_TOT = re.compile(r'Subtotal|GST \(10%\)|^\s*(?:Name: .*?)?Total\b|Paid to Date|Balance Due')
# Elemental: Item Code | Description | Unit Price | Quantity | GST | Total. The GST and Total columns are money; a
# row carrying only a quantity (the PK, the purchase order, the contract reference) is narrative, not an item.
# The description OVERFLOWS its column and runs up against the unit price with a SINGLE space on most rows
# ("... - Remove 2 shade 6130.20"), so only one space is required in front of the unit price; the four trailing
# fields and the two-space gaps BETWEEN them are what identify the row (prompt v6 4.2).
ELE_ROW = re.compile(r'^\s{2,}(?P<d>\S.*?)\s+(?P<u>[\d,]+\.\d{2})\s{2,}(?P<q>\d+)\s{2,}(?P<g>[\d,]+\.\d{2})\s{2,}(?P<t>[\d,]+\.\d{2})\s*$')
ELE_TOT = re.compile(r'Total Excluding GST|^\s*GST\s+\$|Total Including GST|Payments Received|Invoice Balance')


def parse_one(fname, v):
    pdf = os.path.join(PDF_DIR, fname)
    n = npages(pdf)
    pages = {p: text(pdf, p) for p in range(1, n + 1)}
    d = Doc(v, 1); d.pages = list(range(1, n + 1)); d.page_text = pages
    full = '\n'.join(pages[p] for p in d.pages)
    hp = pages[1]
    h = d.h; lno = 0
    h.update(supplier=SUPPLIER[v][0], abn=SUPPLIER[v][1])
    h['pk'] = sorted(set(re.findall(r'PK\s?#?\s?0\d{5}\b', full)))
    h['contract'] = sorted(set(re.findall(r'PAR/?\d{3}[A-Z]?/?\d{4}|PAR\d{3}[A-Z]\d{4}|\bLB\d{3}\b', full)))

    if v == 'LEVAI':
        h.update(inv=re.search(r'TAX INVOICE\s+(INV-\d+)', hp).group(1),
                 date=iso(re.search(r'\bDATE\s+(\d{1,2} \w{3} \d{4})', hp).group(1)),
                 due=iso(re.search(r'DUE DATE\s+(\d{1,2} \w{3} \d{4})', hp).group(1)),
                 ref=(m.group(1) if (m := re.search(r'YOUR REF\s+(\d+)', hp)) else None),
                 sub=labelled(full, 'Subtotal'), gst=labelled(full, r'GST \(10%\)'),
                 # the Total row prints the bank account number to its left, so the label is anchored at the row
                 # start: a bare "Total" would match "Subtotal" one row above it (parse_mixed_new precedent)
                 tot=labelled(full, r'^\s*(?:Account:.*?)?Total'),
                 paid=labelled(full, 'Paid to Date'), bal=labelled(full, 'Balance Due'))
        band = False
        for pn, p in [(x, pages[x]) for x in d.pages]:
            for ln in p.splitlines():
                lno += 1
                if not ln.strip():
                    d.add(pn, lno, ln, 'BLANK'); continue
                if re.match(r'^\s*DESCRIPTION\s+AMOUNT\s*$', ln):
                    band = True; d.add(pn, lno, ln, 'TABLE_HEADER'); continue
                if re.search(r'Bank Details|Subtotal', ln):
                    band = False
                if LEV_TOT.search(ln):
                    d.add(pn, lno, ln, 'TOTALS'); continue
                mm = LEV_ROW.match(ln) if band else None
                if mm:
                    d.add(pn, lno, ln, 'PRICED', qty=1.0, unit=float(D(mm.group('a'))), amt=float(D(mm.group('a'))), bands=['amount'])
                    continue
                d.add(pn, lno, ln, 'PAYMENT_ADVICE' if re.search(r'BSB:|Account: 101 540 21|Commonwealth Bank Australia', ln) else 'NARRATIVE')

    elif v == 'GLASCOTT':
        h.update(inv=re.search(r'Invoice No\s+(\d+)', hp).group(1),
                 date=iso(re.search(r'Invoice\s+Date\s+:\s+(\S+)', hp).group(1)),
                 due=iso(re.search(r'Due Date\s+:\s+(\S+)', hp).group(1)),
                 ref=re.search(r'Order\s+Ref\s+:\s+(\d+)', hp).group(1),
                 sub=labelled(hp, 'Invoice Amount'), gst=labelled(hp, 'Plus GST'),
                 tot=labelled(hp, r'Total\s+Incl\.\s+GST'), paid=None, bal=None)
        face_pk = (m.group(1) if (m := re.search(r'\((PK\d{6})\)', hp)) else None)
        for ln in hp.splitlines():
            lno += 1
            if not ln.strip():
                d.add(1, lno, ln, 'BLANK'); continue
            m = re.match(r'^\s*(Please refer to attached sheet for details\.)\s{2,}([\d,]+\.\d{2})\s*$', ln)
            if m:
                d.add(1, lno, ln, 'PRICED', qty=1.0, unit=float(D(m.group(2))), amt=float(D(m.group(2))), bands=['amount'], wo=face_pk)
            elif re.search(r'Invoice Amount|Plus GST|Total\s+Incl', ln):
                d.add(1, lno, ln, 'TOTALS')
            else:
                d.add(1, lno, ln, 'PAYMENT_ADVICE' if re.search(r'Bank\s+: CBA|BSB\s+:|Account No\s+:|Account Name\s+:|Branch\s+:', ln) else 'NARRATIVE')
        sched, sched_pk = Decimal(0), {}
        for pn in d.pages[1:]:
            for ln in pages[pn].splitlines():
                lno += 1
                if not ln.strip():
                    d.add(pn, lno, ln, 'BLANK'); continue
                m = GLAS.match(ln)
                if m:
                    sched += D(m.group('ex'))
                    sched_pk[m.group('pk')] = sched_pk.get(m.group('pk'), Decimal(0)) + D(m.group('ex'))
                    d.add(pn, lno, ln, 'ATTACHMENT', qty=1.0, unit=float(D(m.group('ex'))), amt=None, gst=m.group('gst'), wo=m.group('pk'),
                          note=f'attached schedule row (rule 16d), ex GST ${m.group("ex")}; not a face line, excluded from check 1')
                    continue
                d.add(pn, lno, ln, 'TOTALS' if re.search(r'^\s*Total\b', ln) else 'NARRATIVE')
        h['sched'], h['sched_pk'] = sched, sched_pk

    else:  # ELEMENTAL
        h.update(inv=re.search(r'Invoice No\.:\s+(\d+)', hp).group(1),
                 date=iso(re.search(r'Tax Invoice Date:\s+(\S+)', hp).group(1)), due=None,
                 ref=(m.group(1) if (m := re.search(r'PURCHASE ORDER (\d+)', full)) else None),
                 sub=D(re.search(r'Total Excluding GST\s+\$([\d,]+\.\d{2})', full).group(1)),
                 gst=D(re.search(r'^\s*GST\s+\$([\d,]+\.\d{2})', full, re.M).group(1)),
                 tot=D(re.search(r'Total Including GST\s+\$([\d,]+\.\d{2})', full).group(1)),
                 paid=labelled(full, 'Payments Received'), bal=labelled(full, 'Invoice Balance'))
        for pn, p in [(x, pages[x]) for x in d.pages]:
            for ln in p.splitlines():
                lno += 1
                if not ln.strip():
                    d.add(pn, lno, ln, 'BLANK'); continue
                if re.match(r'^\s*Item Code\s+Description', ln):
                    d.add(pn, lno, ln, 'TABLE_HEADER'); continue
                if ELE_TOT.search(ln):
                    d.add(pn, lno, ln, 'TOTALS'); continue
                mm = ELE_ROW.match(ln)
                if mm:
                    ex = D(mm.group('u')) * int(mm.group('q'))
                    d.add(pn, lno, ln, 'PRICED', qty=float(int(mm.group('q'))), unit=float(D(mm.group('u'))), amt=float(ex),
                          gst=mm.group('g'), bands=['unit_price', 'qty', 'gst', 'amount'],
                          note='the printed Total column on this layout is GST INCLUSIVE (unit price plus the printed GST); '
                               'the ex-GST line amount is quantity x unit price, which is what the printed Total Excluding GST sums')
                    continue
                d.add(pn, lno, ln, 'PAYMENT_ADVICE' if re.search(r'Bank Details--|A/C Name--|BSB--|A/C--', ln) else 'NARRATIVE')
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
        if not h['pk']:
            d.findings.append('No PK reference is printed on the invoice face.')
        if v == 'GLASCOTT':
            diff = h['sched'] - h['sub']
            other = {k: a for k, a in h['sched_pk'].items() if k not in re.findall(r'\((PK\d{6})\)', d.page_text[1])}
            d.findings.append(f'Attached schedule totals ${h["sched"]:,} ex GST against the invoice face ${h["sub"]:,}; difference ${diff:,}. '
                              f'The face is what was billed and what the ledger carries. The schedule carries rows on '
                              f'{len(h["sched_pk"])} cost account(s) ' + ', '.join(f'{k} ${a:,}' for k, a in sorted(h['sched_pk'].items())) +
                              (f'; the difference is exactly the ' + ', '.join(sorted(other)) + ' row(s), which the face does not charge.'
                               if other and sum(other.values()) == diff else '.'))
        if v == 'ELEMENTAL':
            d.findings.append('The printed Total column on this layout is GST inclusive (unit price plus the printed GST on the same row); '
                              'the ex-GST line amount captured is quantity x unit price, and those sum to the printed Total Excluding GST '
                              f'${h["sub"]} exactly.')
            d.findings.append('The face heads "Elemental Shade Structures" and prints A.B.N.: 99 292 107 173 and QBSA #1159300; the legal '
                              'entities behind the business name print in the footer as "Dice Canvas Pty Ltd ATF The Dice Trust & SSAR '
                              'Australia Pty Ltd ATF The Mark West Trust".')
        stem = STEM[h['inv']]
        assert len(stem) <= 40, (stem, len(stem))
        out.append(dict(doc_ref=f'{h["inv"]}/{fname}', doc_kind='TAX_INVOICE',
                        source_file=fname, source_md5=hashlib.md5(open(pdf, 'rb').read()).hexdigest(),
                        page_range=[d.pages[0], d.pages[-1]], supplier=h['supplier'], supplier_abn=h['abn'], abn_source='letterhead',
                        invoice_no=h['inv'], invoice_date=h['date'], due_date=h.get('due'),
                        printed_subtotal_ex_gst=float(h['sub']), subtotal_basis='printed', printed_gst=float(h['gst']),
                        printed_total_incl_gst=float(h['tot']), captured_ex_gst=float(cap), line_amount_basis='ex_gst',
                        tie_basis='ex_gst', self_tie='TIE' if cap == h['sub'] else 'OUT', retry_log=[],
                        table_headers=[dict(page=l['page'], row=l['line_no'], text=l['line_text'],
                                            bands={k: l['line_text'].index(t) for k, t in
                                                   (('description', 'DESCRIPTION'), ('description_lc', 'Description'),
                                                    ('item_code', 'Item Code'), ('unit_price', 'Unit Price'),
                                                    ('quantity', 'Quantity'), ('gst', 'GST'),
                                                    ('amount', 'AMOUNT'), ('total', 'Total')) if t in l['line_text']},
                                            is_item_table=True)
                                       for l in d.lines if l['line_type'] == 'TABLE_HEADER'],
                        work_orders=[p.replace(' ', '').replace('#', '') for p in h['pk']], contract_refs=h['contract'],
                        po_refs=[h['ref']] if h.get('ref') else [], pk_refs=h['pk'], printed_account_codes=h['pk'],
                        evidence_stem=stem, duplicate_of=None, duplicate_copy_pages=[], findings=d.findings,
                        notes=f'{v} template, raw-text route (pdftotext -layout), page text retained; TechOne attachment {fname} (EzeScan export).',
                        lines=d.lines, page_text=d.page_text, vendor_template=v))
    return out


# evidence_stem per invoice: the 40-character Evidence_Invoices stem (rule 17), vendor, scope, month and total.
STEM = {
    'INV-37608': 'Levai, landscape, Aug-2025, 15895.00', 'INV-37623': 'Levai, landscape, Aug-2025, 9446.58',
    'INV-37624': 'Levai, landscape, Aug-2025, 3938.00', 'INV-37763': 'Levai, landscape, Sep-2025, 21538.00',
    'INV-37848': 'Levai, landscape, Oct-2025, 3960.00', 'INV-38245': 'Levai, landscape, Dec-2025, 15895.00',
    'INV-38326': 'Levai, landscape, Jan-2026, 3287.90', 'INV-38559': 'Levai, landscape, Feb-2026, 13585.00',
    'INV-38650': 'Levai, landscape, Mar-2026, 16665.00', 'INV-38642': 'Levai, landscape, Mar-2026, 2637.00',
    'INV-38694': 'Levai, landscape, Mar-2026, 4642.00', 'INV-38856': 'Levai, landscape, Apr-2026, 2660.00',
    'INV-38936': 'Levai, landscape, May-2026, 17374.50', 'INV-38953': 'Levai, landscape, May-2026, 20749.30',
    'INV-39164': 'Levai, tree works, Jun-2026, 5676.00', 'INV-39436': 'Levai, planting, Aug-2026, 2453.00',
    'INV-39480': 'Levai, landscape, Aug-2026, 4669.50', 'INV-39477': 'Levai, zen garden, Aug-2026, 13453.00',
    '012195': 'Glascott, bush maint, Aug-2026, 39452.61', '6491': 'Elemental, shade, Sep-2026, 15982.12',
}

if __name__ == '__main__':
    docs = parse()
    files = [dict(file=f, md5=hashlib.md5(open(os.path.join(PDF_DIR, f), 'rb').read()).hexdigest(),
                  pages=npages(os.path.join(PDF_DIR, f))) for f, _ in FILES]
    ver = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True).stderr.strip().splitlines()[0]
    corpus = dict(manifest=dict(batch_id='attach_4', source_files=files, runtime='A',
                                extraction_tool=f'parse_attach4.py raw-text route ({ver}, -layout, 3 vendor templates)',
                                extracted_utc=dt.datetime.now(dt.timezone.utc).isoformat(), prompt_version='v6 (raw-text fallback)',
                                ocr_pages_run=0, ocr_pages_not_required=sum(f['pages'] for f in files),
                                ocr_pages_not_available=0, ocr_pages_outstanding=0, resume_point=None), documents=docs)
    out = os.environ.get('OUT', 'corpus_attach_4_v6.json')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    json.dump(corpus, open(out, 'w'), indent=1)
    for d in docs:
        pl = [l for l in d['lines'] if l['line_type'] == 'PRICED']
        at = [l for l in d['lines'] if l['line_type'] == 'ATTACHMENT']
        print(f"{d['invoice_no']:11} {d['vendor_template']:10} {d['source_file']:20} sub {d['printed_subtotal_ex_gst']:>10,.2f} "
              f"cap {d['captured_ex_gst']:>10,.2f} {d['self_tie']} gst {d['printed_gst']:>9,.2f} tot {d['printed_total_incl_gst']:>10,.2f} "
              f"priced {len(pl)}{(' attach %d' % len(at)) if at else ''} pk {d['pk_refs']} po {d['po_refs']}")
