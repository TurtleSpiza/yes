"""parse_attach1.py - Batch attach_1: five single-invoice TechOne attachment PDFs (EzeScan exports), raw-text route
(pdftotext -layout, page text retained), five vendor templates: ETSOL, GLASCOTT_LM, PROVAC, SAVCO, HERITAGE.

Emits corpus JSON in the pswp corpus schema (one document per file). Every priced row is captured verbatim from the
layout row (rule 16a); continuation rows stay NARRATIVE (Xero trap, schema section 8). Gate: pswp_json_repair.repair_and_gate.
Usage: PDF_DIR=cache/attach_1_src OUT=batches/attach_1/corpus_attach_1_v6.json python3 parse_attach1.py
"""
import datetime as dt, hashlib, json, os, re, subprocess, sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_mixed1 import D, iso, Doc, labelled  # noqa

PDF_DIR = os.environ.get('PDF_DIR', 'cache/attach_1_src')
NP = '(not printed)'
FILES = [  # file, template. One TechOne attachment (EzeScan export) per file; the file name is the TechOne attachment id.
    ('C00312585.pdf', 'ETSOL'), ('C00319690_1.pdf', 'GLASCOTT_LM'), ('C00306835.pdf', 'PROVAC'),
    ('C00309459.pdf', 'SAVCO'), ('C00307253_2.pdf', 'HERITAGE')]


def text(pdf, page):
    return subprocess.run(['pdftotext', '-layout', '-f', str(page), '-l', str(page), pdf, '-'], capture_output=True, text=True).stdout


def npages(pdf):
    out = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    return int(re.search(r'Pages:\s+(\d+)', out).group(1))


def parse_one(fname, v):
    pdf = os.path.join(PDF_DIR, fname)
    n = npages(pdf)
    pages = {p: text(pdf, p) for p in range(1, n + 1)}
    d = Doc(v, 1); d.pages = list(range(1, n + 1)); d.page_text = pages
    full = '\n'.join(pages[p] for p in d.pages)
    h = d.h; lno = 0
    h['pk'] = sorted(set(re.findall(r'PK\s?\d{6}', full)))
    h['contract'] = sorted(set(re.findall(r'PAR/?\d{3}[A-Z]?/?\d{4}|PAR\d{3}[A-Z]\d{4}', full)))
    P = [(p, pages[p]) for p in d.pages]
    if v == 'ETSOL':
        hp = P[0][1]; lp = P[-1][1]
        m = re.search(r'^\s*Logan City Council\s+(\d{1,2}/\d{2}/\d{4})\s+(\d{4,6})\s*$', hp, re.M)
        h.update(supplier='ETSol Pty Ltd t/a Eco Technology Solutions', abn='96 644 313 002', inv=m.group(2), date=iso(m.group(1)), due=None,
                 ref=re.search(r'Purchase Order Number:\s*(\d+)', hp).group(1),
                 sub=D(re.search(r'Subtotal\s+\$([\d,]+\.\d{2})', lp).group(1)), gst=D(re.search(r'\bTax\s+\$([\d,]+\.\d{2})', lp).group(1)),
                 tot=D(re.search(r'\bTotal\s+\$([\d,]+\.\d{2})', lp).group(1)))
        rx = re.compile(r'^\s*(?P<d>MZ\d+-\d+.*?\S)\s+(?P<q>\d+)\s+(?P<u>-?[\d,]+\.\d{2})\s+GST\s+(?P<a>-?[\d,]+\.\d{2})\s*$')
        last_priced = None
        for pn, p in P:
            for ln in p.splitlines():
                lno += 1
                if not ln.strip(): continue
                mm = rx.match(ln)
                if mm:
                    d.add(pn, lno, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), gst='GST', bands=['qty', 'rate', 'amount'], wo=None,
                          note='TAX column prints GST (code, not an amount)' + ('; negative line (partial deletion)' if mm.group('a').startswith('-') else ''))
                    last_priced = lno; continue
                if re.match(r'^\s*(Subtotal|Tax|Total)\b', ln): d.add(pn, lno, ln, 'TOTALS'); continue
                if re.match(r'^\s*Description\s+Qty\s+Rate\s+TAX\s+Amount', ln): d.add(pn, lno, ln, 'TABLE_HEADER'); continue
                cont = last_priced == lno - 1 and re.match(r'^\S', ln) and not ln.startswith(('PK', 'ETSol', 'Logan', 'PO Box', 'QLD'))
                d.add(pn, lno, ln, 'NARRATIVE', note='continuation of the preceding priced row (site address or qualifier)' if cont else None)
        d.findings.append('Printed PK000400 (Parks/Roads) on the last page against invoice text "Mowing Zone 1 High Growth Parks" and MZ1 site codes; PK000400 is the Zone 6 mowing WO Task in SE2, PK000422 the Zone 1 task (see the register line).')
    elif v == 'GLASCOTT_LM':
        hp = P[0][1]
        h.update(supplier='Glascott Landscape and Civil Pty Limited (letterhead prints "Technigro ABN 97 001 281 572")', abn='97 001 281 572',
                 inv=re.search(r'Invoice No\s+(\d+)', hp).group(1), date=iso(re.search(r'Invoice\s+Date\s+:\s+(\S+)', hp).group(1)), due=iso(re.search(r'Due Date\s+:\s+(\S+)', hp).group(1)),
                 ref=re.search(r'Order Ref\s+:\s+(\d+)', hp).group(1), sub=labelled(hp, 'Invoice Amount'), gst=labelled(hp, 'Plus GST'), tot=labelled(hp, r'Total\s+Incl\.\s+GST'))
        region = False; buf = []; start = None
        for ln in hp.splitlines():
            lno += 1
            if not ln.strip(): continue
            if 'DESCRIPTION OF SUPPLY' in ln: region = True; d.add(1, lno, ln, 'TABLE_HEADER'); continue
            if re.search(r'Invoice Amount|Plus GST|Total\s+Incl', ln): region = False; d.add(1, lno, ln, 'TOTALS'); continue
            if region:
                mm = re.match(r'^\s*(?P<d>.*?\S)\s{2,}(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm:
                    txt = ' '.join(buf + [mm.group('d')])
                    d.add(1, start or lno, txt, 'PRICED', qty=1.0, unit=float(D(mm.group('a'))), amt=float(D(mm.group('a'))), bands=['amount'],
                          note=f'description spans {len(buf) + 1} layout rows; the amount prints on the last: {ln.strip()}')
                    buf = []; start = None; continue
                if start is None: start = lno
                buf.append(ln.strip()); continue
            d.add(1, lno, ln, 'NARRATIVE')
        d.findings.append('Face-only invoice (no attached schedule); one priced line. Letterhead prints Technigro ABN 97 001 281 572; payment account name Glascott Landscape and Civil Pty Limited; APLEDGER GLA009 carries the same ABN.')
    elif v in ('PROVAC', 'HERITAGE'):
        hp = P[0][1]
        name = {'PROVAC': ('Provac Australia Pty Ltd', '24 130 227 164'), 'HERITAGE': ('Heritage Tree Services Pty Ltd ATF Rowan Family Trust', '32 416 129 034')}[v]
        h.update(supplier=name[0], abn=name[1], inv=re.search(r'Invoice Number[^\n]*\n[^\n]*?(INV-\d+)', hp).group(1),
                 date=iso(re.search(r'Invoice Date[^\n]*\n[^\n]*?(\d{1,2} \w{3} \d{4})', hp).group(1)), due=iso(re.search(r'Due Date:\s+(\d{1,2} \w{3} \d{4})', hp).group(1)),
                 ref=re.search(r'Reference[\s\S]*?\n\s*(\d{6,9})\s*$', hp, re.M).group(1),
                 sub=D(re.search(r'Subtotal\s+([\d,]+\.\d{2})', hp).group(1)), gst=D(re.search(r'TOTAL GST 10%\s+([\d,]+\.\d{2})', hp).group(1)), tot=D(re.search(r'TOTAL AUD\s+([\d,]+\.\d{2})', hp).group(1)))
        rx = re.compile(r'^\s*(?:(?P<item>\d+)\s+)?(?P<d>\S.*?\S)\s{2,}(?P<q>\d+\.\d{2})\s+(?P<u>[\d,]+\.\d{2})\s+(?P<g>\d+%)\s+(?P<a>[\d,]+\.\d{2})\s*$')
        for pn, p in P:
            for ln in p.splitlines():
                lno += 1
                if not ln.strip(): continue
                if pn > 1: d.add(pn, lno, ln, 'NARRATIVE', note='payment advice page' if lno else None); continue
                mm = rx.match(ln)
                if mm and 'Amount AUD' not in ln:
                    d.add(pn, lno, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), gst=mm.group('g'), bands=['qty', 'unit_price', 'amount'],
                          note=(f'item code {mm.group("item")} prints in the Item column' if mm.group('item') else None)); continue
                if re.search(r'^\s*(Subtotal|TOTAL GST|TOTAL AUD)', ln) or re.search(r'\s(Subtotal|TOTAL GST 10%|TOTAL AUD)\s+[\d,]+\.\d{2}\s*$', ln): d.add(pn, lno, ln, 'TOTALS'); continue
                if re.match(r'^\s*(Item\s+)?Description\s+Quantity', ln): d.add(pn, lno, ln, 'TABLE_HEADER'); continue
                d.add(pn, lno, ln, 'NARRATIVE')
        if v == 'PROVAC':
            d.findings.append('Printed PK000446 under the line against a ledger charge to PK000402 (Cemeteries); PK000446 is not a WO Task key in the FY2026/27 branch SE2.')
        else:
            d.findings.append('Printed PK000477 and CR# 3866493 (RFQ, Proposal 766158633); two priced lines (works and traffic management).')
    elif v == 'SAVCO':
        hp = P[0][1]
        m = re.search(r'^\s*(SV\d+)\s+(\d{2}/\d{2}/\d{4})\s+A\$([\d,]+\.\d{2})\s+(\d{2}/\d{2}/\d{4})\s+(NET \d+)', hp, re.M)
        h.update(supplier='Savco Vegetation Services Pty Ltd', abn='78161366749 (printed ungrouped)', inv=m.group(1), date=iso(m.group(2)), due=iso(m.group(4)), ref=re.search(r'^\s*(PO\d{6})\s*$', hp, re.M).group(1),
                 sub=D(re.search(r'SUBTOTAL\s+([\d,]+\.\d{2})', hp).group(1)), gst=D(re.search(r'GST TOTAL\s+([\d,]+\.\d{2})', hp).group(1)), tot=D(re.search(r'^\s*TOTAL\s+([\d,]+\.\d{2})\s*$', hp, re.M).group(1)))
        rx = re.compile(r'^\s*(?P<d>\S.*?\S)\s{2,}(?P<q>\d+)\s+(?P<u>[\d,]+\.\d{2})\s+GST\s+(?P<a>[\d,]+\.\d{2})\s*$')
        last_priced = None
        for ln in hp.splitlines():
            lno += 1
            if not ln.strip(): continue
            mm = rx.match(ln)
            if mm:
                d.add(1, lno, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), gst='GST', bands=['qty', 'rate', 'amount'], wo='PK000477',
                      note='GST column prints GST (code, not an amount); PK000477 printed in the description block above the line'); last_priced = lno; continue
            if re.match(r'^\s*(SUBTOTAL|GST TOTAL|TOTAL|BALANCE DUE)\b', ln) or re.match(r'^\s*A\$[\d,]+\.\d{2}\s*$', ln): d.add(1, lno, ln, 'TOTALS'); continue
            if re.match(r'^\s*DESCRIPTION\s+QTY\s+RATE', ln) or re.match(r'^\s*INVOICE NO\.\s+DATE', ln): d.add(1, lno, ln, 'TABLE_HEADER'); continue
            d.add(1, lno, ln, 'NARRATIVE', note='continuation of the preceding priced row' if last_priced == lno - 1 else None)
        d.findings.append('Printed PK000477, CR#3867562, contract PAR/329/2021, quote SQL - 005177, PO717576; ABN printed ungrouped (78161366749).')
    return d


def parse():
    out = []
    for fname, v in FILES:
        d = parse_one(fname, v)
        h = d.h
        cap = sum(D(l['line_ex_gst']) for l in d.lines if l['line_type'] == 'PRICED')
        gst_calc = D(h['sub'] * Decimal('0.1'))
        if h['gst'] != gst_calc: d.findings.append(f'Printed GST ${h["gst"]} differs from 10% of the subtotal ${gst_calc} by {abs(h["gst"] - gst_calc)}.')
        sname = {'ETSOL': 'EcoTech', 'GLASCOTT_LM': 'Glascott', 'PROVAC': 'Provac', 'SAVCO': 'Savco', 'HERITAGE': 'Heritage'}[v]
        purpose = {'ETSOL': 'mowing Z1', 'GLASCOTT_LM': 'landscape', 'PROVAC': 'grave dig', 'SAVCO': 'tree works', 'HERITAGE': 'tree prune'}[v]
        stem = f'{sname}, {purpose}, {dt.date.fromisoformat(h["date"]).strftime("%b-%Y")}, {h["tot"]:.2f}'
        assert len(stem) <= 40, stem
        pdf = os.path.join(PDF_DIR, fname)
        out.append(dict(doc_ref=f'{h["inv"]}/{fname}', doc_kind='TAX_INVOICE', source_file=fname, source_md5=hashlib.md5(open(pdf, 'rb').read()).hexdigest(), page_range=[d.pages[0], d.pages[-1]],
                        supplier=h['supplier'], supplier_abn=h['abn'], abn_source='letterhead', invoice_no=h['inv'], invoice_date=h['date'], due_date=h.get('due'),
                        printed_subtotal_ex_gst=float(h['sub']), subtotal_basis='printed', printed_gst=float(h['gst']), printed_total_incl_gst=float(h['tot']), captured_ex_gst=float(cap),
                        line_amount_basis='ex_gst', tie_basis='ex_gst', self_tie='TIE' if cap == h['sub'] else 'OUT', retry_log=[], table_headers=[], work_orders=h['pk'], contract_refs=h['contract'],
                        po_refs=[h['ref']] if h.get('ref') else [], pk_refs=h['pk'], printed_account_codes=h['pk'], evidence_stem=stem, duplicate_of=None, findings=d.findings,
                        notes=f'{v} template, raw-text route (pdftotext -layout), page text retained; TechOne attachment {fname} (EzeScan export).', lines=d.lines, page_text=d.page_text, vendor_template=v))
    return out


if __name__ == '__main__':
    docs = parse()
    files = [dict(file=f, md5=hashlib.md5(open(os.path.join(PDF_DIR, f), 'rb').read()).hexdigest(), pages=npages(os.path.join(PDF_DIR, f))) for f, _ in FILES]
    ver = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True).stderr.strip().splitlines()[0]
    corpus = dict(manifest=dict(batch_id='attach_1', source_files=files, runtime='A', extraction_tool=f'parse_attach1.py raw-text route ({ver}, -layout, 5 vendor templates)',
                                extracted_utc=dt.datetime.now(dt.timezone.utc).isoformat(), prompt_version='v5 (raw-text fallback)', ocr_pages_run=0, ocr_pages_not_required=sum(f['pages'] for f in files),
                                ocr_pages_not_available=0, ocr_pages_outstanding=0, resume_point=None), documents=docs)
    json.dump(corpus, open(os.environ.get('OUT', 'corpus_attach_1_v6.json'), 'w'), indent=1)
    for d in docs:
        pl = [l for l in d['lines'] if l['line_type'] == 'PRICED']
        print(f"{d['invoice_no']:13} {d['vendor_template']:12} {d['source_file']:16} sub {d['printed_subtotal_ex_gst']:>10,.2f} cap {d['captured_ex_gst']:>10,.2f} {d['self_tie']} priced {len(pl)} lines {len(d['lines'])} gst {d['printed_gst']} pk {d['pk_refs']} po {d['po_refs']} contract {d['contract_refs']}")
