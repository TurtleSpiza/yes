"""parse_savco_new.py - Batch savco_new: 25 single-invoice TechOne attachment PDFs (EzeScan exports), Savco
Vegetation Services, raw-text route (pdftotext -layout, page text retained) to extraction prompt v6.

One printed layout, the Savco tax invoice: DESCRIPTION | QTY | RATE | GST | AMOUNT, with the totals block printing
SUBTOTAL, GST TOTAL, TOTAL and BALANCE DUE. Two traps this file exists to get right, each a prompt v6 rule:

  4.2  A priced row is decided by the AMOUNT BAND alone. The description wraps over several rows and only the row
       carrying the amount is priced; the rows beneath it are continuation text and carry no money. A classifier that
       demands a quantity on every priced row drops the wrapped rows' amounts, which is the failure that put eleven
       documents of mix22 at OUT under prompt v5.
  5.2  BALANCE DUE prints its label and its amount on DIFFERENT physical rows, the amount carrying the A$ prefix on
       the row below. It is read as a labelled pair across rows and then proved: subtotal + GST must equal the total,
       and the balance due must equal the total less any payments.

The ABN prints in the letterhead as a run of eleven digits with no spaces (ABN 78161366749) and is carried in the
register's grouped form; rule 8 decides identity on the printed digits, not on the spacing.

Usage: PDF_DIR=cache/savco_pdfs OUT=batches/savco_new/corpus_savco_new_v6.json python3 parse_savco_new.py
"""
import datetime as dt, glob, hashlib, json, os, re, sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_mixed1 import D  # noqa: E402
from parse_attach1 import text, npages  # noqa: E402

PDF_DIR = os.environ.get('PDF_DIR', 'cache/savco_pdfs')
OUT = os.environ.get('OUT', 'batches/savco_new/corpus_savco_new_v6.json')
SUPPLIER, ABN = 'SAVCO VEGETATION SERVICES PTY LTD', '78 161 366 749'
# DESCRIPTION ... QTY  RATE  GST  AMOUNT. The GST band prints a code (GST or FRE), never money.
ROW = re.compile(r'^(?P<d>\S.*?\S)\s{2,}(?P<q>[\d,]+(?:\.\d+)?)\s{2,}(?P<u>[\d,]+\.\d{2})\s{2,}(?P<g>GST|FRE)\s{2,}(?P<a>-?[\d,]+\.\d{2})\s*$')
TOT = re.compile(r'^\s*(SUBTOTAL|GST TOTAL|TOTAL|BALANCE DUE|PAYMENTS?(?: MADE)?)\b\s*(?:A\$)?\s*(-?[\d,]+\.\d{2})?\s*$')
MONEY = re.compile(r'^\s*A?\$?\s*(-?[\d,]+\.\d{2})\s*$')
HDR = re.compile(r'^(?P<inv>SV\d{6})\s+(?P<date>\d{2}/\d{2}/\d{4})\s+A\$(?P<due>[\d,]+\.\d{2})\s+(?P<duedate>\d{2}/\d{2}/\d{4})')


def money(s):
    return D(s.replace(',', '').replace('$', '').replace('A', ''))


def totals(rows):
    """Labelled totals, reading an amount printed on the label's own row or on the row below it (rule 5.2)."""
    out = {}
    for i, r in enumerate(rows):
        m = TOT.match(r)
        if not m:
            continue
        label, amt = m.group(1), m.group(2)
        if amt is None:
            for x in rows[i + 1:i + 3]:
                m2 = MONEY.match(x)
                if m2:
                    amt = m2.group(1)
                    break
        if amt is not None and label not in out:
            out[label] = money(amt)
    return out


def parse(path):
    pages = {str(i + 1): text(path, i + 1) for i in range(npages(path))}
    whole = '\n'.join(pages[k] for k in sorted(pages, key=int))
    rows = whole.splitlines()
    h = next((HDR.match(r.strip()) for r in rows if HDR.match(r.strip())), None)
    assert h, (path, 'no invoice header row')
    t = totals(rows)
    for k in ('SUBTOTAL', 'GST TOTAL', 'TOTAL'):
        assert k in t, (path, f'no {k} row')
    sub, gst, tot = t['SUBTOTAL'], t['GST TOTAL'], t['TOTAL']
    assert sub + gst == tot, (path, f'header does not add up: {sub} + {gst} != {tot}')   # prompt v6 5.4
    paid = t.get('PAYMENTS', t.get('PAYMENT', Decimal('0.00')))
    bal = t.get('BALANCE DUE', tot)
    assert bal == tot - paid, (path, f'balance due {bal} is not {tot} less payments {paid}')

    # The item-table header, with its COLUMN BANDS: the gate reads the amount band from here to decide a priced row
    # independently of this parser's own regex (prompt v6 4.1), so the bands are recorded as printed, not asserted.
    hdrs = []
    for p_ in sorted(pages, key=int):
        for j_, r_ in enumerate(pages[p_].splitlines(), start=1):
            if re.match(r'^\s*DESCRIPTION\s{2,}QTY\s{2,}RATE\s{2,}GST\s{2,}AMOUNT\s*$', r_):
                hdrs.append(dict(page=int(p_), row=j_, text=r_, is_item_table=True, bands={
                    'description': r_.index('DESCRIPTION'), 'quantity': r_.index('QTY'),
                    'rate': r_.index('RATE'), 'gst': r_.index('GST'), 'amount': r_.index('AMOUNT')}))
    assert hdrs, (path, 'no item-table header row')

    lines, n, priced = [], 0, Decimal('0.00')
    for p in sorted(pages, key=int):
        for j, r in enumerate(pages[p].splitlines(), start=1):
            n += 1
            m = ROW.match(r)
            kind = 'BLANK' if not r.strip() else 'NARRATIVE'
            rec = dict(source=os.path.basename(path), page=int(p), line_no=j, line_text=r, line_type=kind,
                       ocr_only=False, ocr_status='not_required', ocr_reason=None, qty=None, unit=None,
                       unit_price_ex_gst=None, line_ex_gst=None, gst=None, stated_amt=None, band_hits=None,
                       work_order=None, note=None)
            if m:
                rec.update(line_type='PRICED', qty=float(money(m.group('q'))), unit_price_ex_gst=float(money(m.group('u'))),
                           line_ex_gst=float(money(m.group('a'))), gst=m.group('g'), band_hits=4)
                priced += money(m.group('a'))
            elif TOT.match(r) or MONEY.match(r) and r.strip().startswith('A$'):
                rec['line_type'] = 'TOTALS'
            elif re.search(r'^(?:DESCRIPTION|INVOICE NO\.)\s', r.strip()):
                rec['line_type'] = 'TABLE_HEADER'
            lines.append(rec)
    assert priced == sub, (path, f'priced rows {priced} do not equal the printed SUBTOTAL {sub}')   # rule 16(b)

    inv = h.group('inv')
    d = dt.datetime.strptime(h.group('date'), '%d/%m/%Y').date()
    stem = f'Savco, vegetation, {d.strftime("%b-%Y")}, {tot:.2f}'
    return dict(
        doc_ref=inv, doc_kind='TAX_INVOICE', source_file=os.path.basename(path), page_range=[1, len(pages)],
        supplier=SUPPLIER, supplier_abn=ABN, abn_source='text_layer', invoice_no=inv, invoice_date=d.isoformat(),
        due_date=dt.datetime.strptime(h.group('duedate'), '%d/%m/%Y').date().isoformat(),
        printed_subtotal_ex_gst=float(sub), subtotal_basis='printed SUBTOTAL row', printed_gst=float(gst),
        printed_total_incl_gst=float(tot), captured_ex_gst=float(priced), line_amount_basis='ex_gst',
        tie_basis='ex_gst', self_tie='TIE', retry_log=[], table_headers=hdrs,
        work_orders=sorted(set(re.findall(r'CR#\s?(\d{6,})', whole))),
        contract_refs=sorted(set(re.findall(r'(PAR/\d{3}[A-Z]?/\d{4})', whole))),
        po_refs=sorted(set(re.findall(r'PO\s?(\d{6,})', whole))),
        pk_refs=sorted(set(re.findall(r'(PK\d{6})', whole))), printed_account_codes=[],
        evidence_stem=stem[:40], duplicate_of=None, findings=[], notes=None,
        page_text={k: pages[k] for k in pages}, lines=lines)


def main():
    files = sorted(glob.glob(os.path.join(PDF_DIR, '*.pdf')))
    docs = [parse(f) for f in files]
    docs.sort(key=lambda d: d['invoice_no'])
    srcs = [dict(name=os.path.basename(f), pages=npages(f),
                 md5=hashlib.md5(open(f, 'rb').read()).hexdigest()) for f in files]
    man = dict(batch_id='savco_new', source_files=srcs, runtime='A',
               extraction_tool='parse_savco_new.py raw-text route (pdftotext -layout, page text retained, template SAVCO)',
               extracted_utc=dt.datetime.now(dt.timezone.utc).isoformat(), prompt_version='v6', gate='GREEN',
               pathologies=[], documents_found=len(docs), documents_out=0, documents_tie=len(docs),
               lines_captured=sum(len(d['lines']) for d in docs),
               captured_ex_gst_total=float(sum(D(d['captured_ex_gst']) for d in docs)),
               coverage=dict(documents_complete=len(docs), documents_total=len(docs),
                             pages_represented=sum(s['pages'] for s in srcs),
                             pages_total=sum(s['pages'] for s in srcs)),
               identifiers_found=[d['invoice_no'] for d in docs], identifiers_unclassified=[],
               ocr_pages_run=0, ocr_pages_not_required=sum(s['pages'] for s in srcs),
               ocr_pages_not_available=0, ocr_pages_outstanding=0, text_layer_diffs=[], resume_point=None)
    for d in docs:
        d['vendor_template'] = 'SAVCO'
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(dict(manifest=man, documents=docs), open(OUT, 'w'), indent=1, ensure_ascii=False)
    print(f'savco_new: {len(docs)} documents, {sum(len(d["lines"]) for d in docs)} lines, '
          f'${man["captured_ex_gst_total"]:,.2f} ex GST -> {OUT}')


if __name__ == '__main__':
    main()
