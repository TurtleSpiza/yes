"""parse_attach2.py - Batch attach_2: six single-invoice TechOne attachment PDFs (EzeScan exports), raw-text route
(pdftotext -layout, page text retained), four vendor templates: BURLY, CERTIFIED, C2C_INCL, FLAVELL_ATT.

C2C_INCL trap: on this Coast2Coast layout the printed Unit Price and "Amount AUD" columns are GST INCLUSIVE and the
description states the ex-GST base ("$59,796.25 plus GST"); the invoice foot prints "INCLUDES GST 10%" and TOTAL AUD.
Lines are therefore captured ex GST as ROUND(printed/1.1, 2) with the printed figure recorded in the note (ELEMENTAL
precedent), and the printed subtotal is the arithmetically forced TOTAL AUD less the printed GST.

Usage: PDF_DIR=cache/attach_2_src OUT=batches/attach_2/corpus_attach_2_v6.json python3 parse_attach2.py
"""
import datetime as dt, hashlib, json, os, re, subprocess, sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_mixed1 import D, iso, Doc  # noqa
from parse_attach1 import text, npages  # noqa

PDF_DIR = os.environ.get('PDF_DIR', 'cache/attach_2_src')
NP = '(not printed)'
FILES = [('C00310036.pdf', 'BURLY'), ('C00311803.pdf', 'CERTIFIED'), ('C00313458.pdf', 'C2C_INCL'),
         ('C00313632.pdf', 'FLAVELL_ATT'), ('C00315793.pdf', 'C2C_INCL'), ('C00316104.pdf', 'CERTIFIED')]
INCL = Decimal('1.1')


def parse_one(fname, v):
    pdf = os.path.join(PDF_DIR, fname)
    n = npages(pdf)
    pages = {p: text(pdf, p) for p in range(1, n + 1)}
    d = Doc(v, 1); d.pages = list(range(1, n + 1)); d.page_text = pages
    full = '\n'.join(pages[p] for p in d.pages)
    h = d.h; lno = 0
    h['pk'] = sorted(set(re.findall(r'PK\s?0\d{5}', full)))
    h['pk_printed'] = sorted(set(re.findall(r'PK\s?\d{5,6}', full)))
    h['contract'] = sorted(set(re.findall(r'PAR/?\d{3}[A-Z]?/?\d{4}|PAR\d{3}[A-Z]\d{4}', full)))
    P = [(p, pages[p]) for p in d.pages]
    hp = P[0][1]

    if v == 'BURLY':
        h.update(supplier='Burly Holdings', abn='38 674 292 196', inv=re.search(r'Tax Invoice # (\d+)', hp).group(1),
                 date=iso(re.sub(r'(\d+)(?:st|nd|rd|th) (\w{3})\w* (\d{4})', r'\1 \2 \3', re.search(r'(\d+(?:st|nd|rd|th) \w+ \d{4})', hp).group(1))),
                 due=None, ref=re.search(r'Order#\s*(\d+)', hp).group(1),
                 sub=D(re.search(r'SUBTOTAL:\s+\$([\d,]+\.\d{2})', hp).group(1)), gst=D(re.search(r'GST:\s+\$([\d,]+\.\d{2})', hp).group(1)),
                 tot=D(re.search(r'(?<!SUB)TOTAL:\s+\$([\d,]+\.\d{2})', hp).group(1)), paid=D(re.search(r'PAID:\s+\$([\d,]+\.\d{2})', hp).group(1)), bal=D(re.search(r'BALANCE DUE:\s+\$([\d,]+\.\d{2})', hp).group(1)))
        for pn, p in P:
            for ln in p.splitlines():
                lno += 1
                if not ln.strip(): continue
                mm = re.match(r'^\s*(?P<d>\S.*?\S)\s{2,}(?P<q>\d+)\s+\$(?P<u>[\d,]+\.\d{2})\s+\$(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm:
                    d.add(pn, lno, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), bands=['qty', 'unit_price', 'amount'], wo=None); continue
                if re.match(r'^\s*DESCRIPTION\s+QTY\s+UNIT PRICE\s+TOTAL PRICE', ln): d.add(pn, lno, ln, 'TABLE_HEADER'); continue
                d.add(pn, lno, ln, 'TOTALS' if re.search(r'(SUBTOTAL|GST|TOTAL|PAID|BALANCE DUE):', ln) else 'NARRATIVE')
        h['due_text'] = (re.search(r'due by (\d+\w{2} \w+ \d{4})', full) or re.search(r'(due by [^\n]+)', full)).group(0)

    elif v == 'CERTIFIED':
        h.update(supplier='Certified Mowing Pty Ltd', abn='22 161 469 325', inv=re.search(r'Invoice Number[^\n]*\n[^\n]*?(INV-\d+)', hp).group(1),
                 date=iso(re.search(r'Invoice Date[^\n]*\n[^\n]*?(\d{1,2} \w{3} \d{4})', hp).group(1)), due=iso(re.search(r'Due Date:\s+(\d{1,2} \w{3} \d{4})', hp).group(1)),
                 ref=re.search(r'PO # (\d+)', hp).group(1), sub=D(re.search(r'Subtotal\s+([\d,]+\.\d{2})', hp).group(1)),
                 gst=D(re.search(r'TOTAL GST 10%\s+([\d,]+\.\d{2})', hp).group(1)), tot=D(re.search(r'TOTAL AUD\s+([\d,]+\.\d{2})', hp).group(1)))
        pend = []
        for pn, p in P:
            for ln in p.splitlines():
                lno += 1
                if not ln.strip(): continue
                mm = re.match(r'^\s*(?P<d>\S.*?\S)\s{2,}(?P<q>\d+\.\d{2})\s+(?P<u>[\d,]+\.\d{2})\s+(?P<g>\d+%)\s+(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm and 'Amount AUD' not in ln:
                    wo = re.search(r'PK\s?\d{5,6}', mm.group('d'))
                    d.add(pn, lno, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), gst=mm.group('g'), bands=['qty', 'unit_price', 'amount'],
                          wo=wo.group(0).replace(' ', '') if wo else None,
                          note=('description continues from the preceding layout row(s): ' + ' | '.join(pend)) if pend else None)
                    pend = []; continue
                if re.search(r'^\s*(Subtotal|TOTAL GST|TOTAL AUD)', ln) or re.search(r'\s(Subtotal|TOTAL GST 10%|TOTAL AUD)\s+[\d,]+\.\d{2}\s*$', ln): d.add(pn, lno, ln, 'TOTALS'); continue
                if re.match(r'^\s*Description\s+Quantity', ln): d.add(pn, lno, ln, 'TABLE_HEADER'); continue
                d.add(pn, lno, ln, 'NARRATIVE')
                if re.match(r'^(MZ\d|Standard Growth|High Growth|NOTE:|Partial)', ln.strip()) and not re.search(r'Due Date|Payment', ln):
                    pend.append(' '.join(ln.split()))

    elif v == 'C2C_INCL':
        h.update(supplier='Coast2Coast Grounds and Gardens', abn='24 488 420 203', inv=re.search(r'Invoice Number[^\n]*\n[^\n]*?(INV-\d+)', hp).group(1),
                 date=iso(re.search(r'Invoice Date[^\n]*\n[^\n]*?(\d{1,2} \w{3} \d{4})', hp).group(1)), due=iso(re.search(r'Due Date:\s+(\d{1,2} \w{3} \d{4})', hp).group(1)),
                 ref=re.search(r'Purchase Order:\s+(\d+)', hp).group(1),
                 gst=D(re.search(r'INCLUDES GST 10%\s+([\d,]+\.\d{2})', hp).group(1)), tot=D(re.search(r'TOTAL AUD\s+([\d,]+\.\d{2})', hp).group(1)))
        h['sub'] = h['tot'] - h['gst']
        pend = []
        for pn, p in P:
            for ln in p.splitlines():
                lno += 1
                if not ln.strip(): continue
                mm = re.match(r'^\s*(?P<d>\S.*?\S)\s{2,}(?P<q>\d+\.\d{2})\s+(?P<u>[\d,]+\.\d{2})\s+(?:(?P<g>\d+%)\s+)?(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm and 'Amount AUD' not in ln:
                    printed = D(mm.group('a'))
                    ex = (printed / INCL).quantize(Decimal('0.01'), ROUND_HALF_UP) if mm.group('g') else printed
                    d.add(pn, lno, ln, 'PRICED', qty=float(mm.group('q')), unit=float((D(mm.group('u')) / INCL).quantize(Decimal('0.01'), ROUND_HALF_UP) if mm.group('g') else D(mm.group('u'))),
                          amt=float(ex), gst_rate_printed=mm.group('g'), bands=['qty', 'unit_price', 'amount'],
                          note=(f'printed Unit Price and Amount AUD columns are GST inclusive (${printed}); ex GST = ROUND(printed / 1.1, 2) = ${ex}'
                                + ('; ' + ' | '.join(pend) if pend else '')) if mm.group('g') else 'zero-amount purchase order row as printed')
                    pend = []; continue
                if re.search(r'INCLUDES GST 10%|TOTAL AUD|Amount Due', ln): d.add(pn, lno, ln, 'TOTALS'); continue
                if re.match(r'^\s*Description\s+Quantity', ln): d.add(pn, lno, ln, 'TABLE_HEADER'); continue
                d.add(pn, lno, ln, 'NARRATIVE')
                if re.match(r'^(\$[\d,]+\.\d{2} plus GST|INV-\d+ MZ\d+|= \$|Vendor No|Reference|Contract Reference)', ln.strip()):
                    pend.append(' '.join(ln.split()))
        cap = sum(D(l['line_ex_gst']) for l in d.lines if l['line_type'] == 'PRICED')
        d.findings.append(f'Printed line amounts are GST inclusive; captured ex GST {cap} against the derived printed subtotal {h["sub"]} (TOTAL AUD {h["tot"]} less printed GST {h["gst"]}).')

    elif v == 'FLAVELL_ATT':
        h.update(supplier='The Trustee for Flavell-Dau Family Trust', abn='47 220 358 629', inv=re.search(r'Invoice Number[^\n]*\n[^\n]*?(INV-\d+)', hp).group(1),
                 date=iso(re.search(r'Invoice Date[^\n]*\n[^\n]*?(\d{1,2} \w{3} \d{4})', hp).group(1)), due=iso(re.search(r'Due Date:\s+(\d{1,2} \w{3} \d{4})', hp).group(1)),
                 ref=re.search(r'PO#\s?(\d+)', hp).group(1), sub=D(re.search(r'Subtotal\s+([\d,]+\.\d{2})', hp).group(1)),
                 gst=D(re.search(r'TOTAL GST 10%\s+([\d,]+\.\d{2})', hp).group(1)), tot=D(re.search(r'TOTAL AUD\s+([\d,]+\.\d{2})', hp).group(1)))
        pend = []
        for pn, p in P:
            for ln in p.splitlines():
                lno += 1
                if not ln.strip(): continue
                mm = re.match(r'^(?P<d>\S.*?\S)\s{2,}10%\s+(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm:
                    d.add(pn, lno, ln, 'PRICED', qty=1.0, unit=float(D(mm.group('a'))), amt=float(D(mm.group('a'))), gst_rate_printed='10%', bands=['amount']); continue
                mm = re.match(r'^(?P<d>\S.*?\S)\s{2,}(?P<a>0\.00)\s*$', ln)
                if mm:
                    d.add(pn, lno, ln, 'PRICED', qty=None, unit=None, amt=0.0, bands=['amount'], note='purchase order row printed at 0.00'); continue
                if re.search(r'^\s*(Subtotal|TOTAL GST|TOTAL AUD)|\s(Subtotal|TOTAL GST 10%|TOTAL AUD)\s+[\d,]+\.\d{2}\s*$|Amount Due', ln): d.add(pn, lno, ln, 'TOTALS'); continue
                d.add(pn, lno, ln, 'NARRATIVE')
    return d


def parse():
    out = []
    for fname, v in FILES:
        d = parse_one(fname, v)
        h = d.h
        cap = sum(D(l['line_ex_gst']) for l in d.lines if l['line_type'] == 'PRICED')
        gst_calc = D(h['sub'] * Decimal('0.1'))
        if h['gst'] != gst_calc:
            d.findings.append(f'Printed GST ${h["gst"]} differs from 10% of the subtotal ${gst_calc} by {abs(h["gst"] - gst_calc)}.')
        sname = {'BURLY': 'Burly', 'CERTIFIED': 'CertMow', 'C2C_INCL': 'C2C', 'FLAVELL_ATT': 'FlavellDau'}[v]
        purpose = {'BURLY': 'landscape', 'CERTIFIED': 'mowing MZ3', 'C2C_INCL': 'mowing MZ10', 'FLAVELL_ATT': 'shelter'}[v]
        stem = f'{sname}, {purpose}, {dt.date.fromisoformat(h["date"]).strftime("%b-%Y")}, {h["tot"]:.2f}'
        assert len(stem) <= 40, stem
        pdf = os.path.join(PDF_DIR, fname)
        out.append(dict(doc_ref=f'{h["inv"]}/{fname}', doc_kind='TAX_INVOICE', source_file=fname, source_md5=hashlib.md5(open(pdf, 'rb').read()).hexdigest(), page_range=[d.pages[0], d.pages[-1]],
                        supplier=h['supplier'], supplier_abn=h['abn'], abn_source='letterhead', invoice_no=h['inv'], invoice_date=h['date'], due_date=h.get('due'),
                        printed_subtotal_ex_gst=float(h['sub']), subtotal_basis='printed' if v != 'C2C_INCL' else 'derived: printed TOTAL AUD less printed GST (line columns are GST inclusive)',
                        printed_gst=float(h['gst']), printed_total_incl_gst=float(h['tot']), captured_ex_gst=float(cap), line_amount_basis='ex_gst', tie_basis='ex_gst',
                        self_tie='TIE' if cap == h['sub'] else 'OUT', retry_log=[], table_headers=[], work_orders=h['pk'], contract_refs=h['contract'],
                        po_refs=[h['ref']] if h.get('ref') else [], pk_refs=h['pk'], printed_account_codes=h['pk_printed'], evidence_stem=stem, duplicate_of=None,
                        findings=d.findings, notes=f'{v} template, raw-text route (pdftotext -layout), page text retained; TechOne attachment {fname} (EzeScan export).',
                        lines=d.lines, page_text=d.page_text, vendor_template=v))
    return out


if __name__ == '__main__':
    docs = parse()
    files = [dict(file=f, md5=hashlib.md5(open(os.path.join(PDF_DIR, f), 'rb').read()).hexdigest(), pages=npages(os.path.join(PDF_DIR, f))) for f, _ in FILES]
    ver = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True).stderr.strip().splitlines()[0]
    corpus = dict(manifest=dict(batch_id='attach_2', source_files=files, runtime='A', extraction_tool=f'parse_attach2.py raw-text route ({ver}, -layout, 4 vendor templates)',
                                extracted_utc=dt.datetime.now(dt.timezone.utc).isoformat(), prompt_version='v5 (raw-text fallback)', ocr_pages_run=0,
                                ocr_pages_not_required=sum(f['pages'] for f in files), ocr_pages_not_available=0, ocr_pages_outstanding=0, resume_point=None), documents=docs)
    json.dump(corpus, open(os.environ.get('OUT', 'corpus_attach_2_v6.json'), 'w'), indent=1)
    for d in docs:
        pl = [l for l in d['lines'] if l['line_type'] == 'PRICED']
        print(f"{d['invoice_no']:11} {d['vendor_template']:12} {d['source_file']:16} sub {d['printed_subtotal_ex_gst']:>11,.2f} cap {d['captured_ex_gst']:>11,.2f} {d['self_tie']} gst {d['printed_gst']:>9,.2f} tot {d['printed_total_incl_gst']:>11,.2f} priced {len(pl)} pk {d['printed_account_codes']} po {d['po_refs']}")
