"""parse_binders.py - Batches mix222 and binder11111: the two binders that were HELD at v6, now supplied, parsed on
the raw-text route (pdftotext -layout, page text retained) to extraction prompt v6.

Both were held because their supplied Copilot corpora carried no line record at all for eleven pages (P3), which is
the one pathology that cannot be restated downstream: there is nothing to restate from. Every one of those pages turns
out to be a blank separator page carrying a single form feed, so under prompt v6 section 3.9 each gets one BLANK
record and the coverage assertion holds.

  mix222        mix_222.pdf, 58 pages, 29 Harpley Services invoices, template HARPLEY.
  binder11111   Binder11111.pdf, 38 pages, 13 RST Systems invoices, template VINTON (two printed layouts).

Traps this file exists to get right, each one a prompt v6 rule:
  4.2  VINTON layout A prints DESCRIPTION | EX AMOUNT | TAX CODE with NO quantity and NO unit price column. A
       classifier that wants three numeric bands parses none of it, which is what put $11,950.00 at zero on the v5 run.
  5.2  Both templates split a label from its amount across physical rows. Harpley prints the GST amount on its own
       row between "Sub Total:" and "Total Inc GST:"; VINTON layout B prints the GST amount one row ABOVE its "GST:"
       label. Neither is read positionally from the totals block: the amount is taken and then proved by 5.4.
  5.4  The header block must add up. Every document here is tested subtotal + GST = total before it is emitted.
  3.9  Every page inside a document's range carries a record, blank pages included.
  11.4 Invoice 19827 prints six identical copies (pages 1-12) and 19997 two (pages 35-38). The first is captured, the
       rest are typed DUPLICATE_COPY with their arithmetic fields null and listed in duplicate_copy_pages.
  4.5  Before a document is emitted, the residue test runs: no NARRATIVE row between the item header and the totals
       block may carry money in the amount band.

Finding raised on every binder11111 document: the face prints no ABN anywhere, and the only supplier identification
is "RST Systems Pty Ltd" in the bank block and the remittance address admin@vintontreeservices.com.au.

Usage: PDF_DIR=cache/binders OUT=batches python3 parse_binders.py [batch id]
"""
import datetime as dt, hashlib, json, os, re, subprocess, sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_mixed1 import D, iso, Doc  # noqa
from parse_attach1 import npages  # noqa

PDF_DIR = os.environ.get('PDF_DIR', 'cache/binders')
OUTDIR = os.environ.get('OUT', 'batches')
BINDERS = {
    'mix222': dict(pdf='mix_222.pdf', template='HARPLEY', supplier='Harpley Services Pty Ltd', abn='22 162 601 694',
                   start=re.compile(r'Harpley Services Pty Ltd'), inv=re.compile(r'Invoice No\.:\s+(\d+)')),
    'binder11111': dict(pdf='Binder11111.pdf', template='VINTON', supplier='RST Systems Pty Ltd', abn=None,
                        start=re.compile(r'Invoice No\.:\s+\d{5}'), inv=re.compile(r'Invoice No\.:\s+(\d{5})')),
}
# HARPLEY: QUANTITY | DESCRIPTION | UNIT PRICE(ex-GST) | TOTAL PRICE(ex-GST)
HARP_ROW = re.compile(r'^\s*(?P<q>[\d,]+(?:\.\d+)?)\s+(?P<d>\S.*?\S)\s{2,}\$(?P<u>[\d,]+\.\d{2})\s+\$(?P<a>[\d,]+\.\d{2})\s*$')
HARP_HDR = re.compile(r'^\s*QUANTITY\s+DESCRIPTION\s+UNIT PRICE')
# VINTON B: HRS | DESCRIPTION | UNIT PRICE (ex-GST) | TOTAL PRICE (ex-GST). VINTON A: DESCRIPTION | EX AMOUNT | TAX CODE.
VIN_ROW_B = re.compile(r'^\s*(?P<q>[\d,]+(?:\.\d+)?)\s{2,}(?P<d>\S.*?\S)\s{2,}\$(?P<u>[\d,]+\.\d{2})\s{2,}\$(?P<a>[\d,]+\.\d{2})\s*$')
VIN_ROW_A = re.compile(r'^(?P<d>\S.*?\S)\s{2,}\$(?P<a>[\d,]+\.\d{2})\s{2,}(?P<tax>GST|FRE|GST FREE)\s*$')
VIN_HDR = re.compile(r'^\s*(?:HRS\s+DESCRIPTION|DESCRIPTION\s+EX AMOUNT)')
TOTAL_RX = re.compile(r'(Sub Total:|Total Inc GST:|Payments Made:|Balance Due:|Subtotal:|GST:|Total \(inc-GST\):)')
MONEY_ONLY = re.compile(r'^\s*\$([\d,]+\.\d{2})\s*$')
MONEY = re.compile(r'\$?\d[\d,]*\.\d{2}')
PAGE_OF = re.compile(r'Page (\d+) of (\d+)')
BAND_LABELS = (('quantity', 'QUANTITY'), ('hrs', 'HRS'), ('description', 'DESCRIPTION'),
               ('unit_price', 'UNIT PRICE'), ('amount', 'TOTAL PRICE'), ('ex_amount', 'EX AMOUNT'), ('tax_code', 'TAX CODE'))


def text(pdf, page):
    return subprocess.run(['pdftotext', '-layout', '-f', str(page), '-l', str(page), pdf, '-'],
                          capture_output=True, text=True).stdout


def bands_of(row):
    return {k: row.index(lab) for k, lab in BAND_LABELS if lab in row}


def split_pages(cfg, pages):
    """Prompt v6 section 3: a page carrying the start marker and an identifier opens a document; every other page
    inherits the previous one, blank pages included. A later run on the same identifier is a duplicate copy (11.4)."""
    docs, cur = [], None
    for pno, p in enumerate(pages, 1):
        m = cfg['inv'].search(p)
        if m and cfg['start'].search(p):
            prior = next((d for d in docs if d.h['inv'] == m.group(1)), None)
            if prior is not None:
                # Prompt v6 3.5: the printed footer decides. "Page 2 of 2" on an identifier already open is a
                # CONTINUATION page of that invoice (00015299); anything else is a second printed copy (11.4).
                f = PAGE_OF.search(p)
                cont = bool(f) and int(f.group(1)) > 1
                prior.pages.append(pno)
                if not cont:
                    prior.copies.append(pno)
                cur = prior
                continue
            cur = Doc(cfg['template'], pno)
            cur.h['inv'] = m.group(1)
            cur.copies = []
            docs.append(cur)
        else:
            assert cur is not None, f'page {pno} precedes any document'
            cur.pages.append(pno)
    return docs


def header_fields(batch, full, hp):
    if batch == 'mix222':
        # A two-page Harpley invoice prints its totals block on BOTH pages, blank on page 1 and complete on page 2
        # (00015299, "Page 1 of 2"). Take the LAST occurrence of each label that actually carries an amount, and the
        # last bare-money row for the GST, which this template prints with no label at all (prompt v6 5.2).
        gst = re.findall(r'^\s*\$([\d,]+\.\d{2})\s*$', full, re.M)
        return dict(inv=re.search(r'Invoice No\.:\s+(\d+)', hp).group(1),
                    date=iso(re.search(r'Date:\s+(\d{2}/\d{2}/\d{4})', hp).group(1)),
                    due=iso(re.search(r'Due Date:\s+(\d{2}/\d{2}/\d{4})', hp).group(1)),
                    ref=(m.group(1) if (m := re.search(r'Purchase Order:\s+(\d+)', hp)) else None),
                    contract=(m.group(1) if (m := re.search(r'Contract #:\s*(\S+)', hp)) else None),
                    sub=D(re.findall(r'Sub Total:\s+\$([\d,]+\.\d{2})', full)[-1]),
                    gst=D(gst[-1]) if gst else None,
                    tot=D(re.findall(r'Total Inc GST:\s+\$?([\d,]+\.\d{2})', full)[-1]))
    # VINTON: layout B prints the GST amount one row ABOVE its label, layout A on the label row (prompt v6 5.2)
    g = re.search(r'GST:\s+\$([\d,]+\.\d{2})', full)
    if not g:
        rows = full.splitlines()
        i = next(i for i, r in enumerate(rows) if re.match(r'^\s*GST:\s*$', r) or ' GST:' in r)
        g = next(MONEY_ONLY.match(r) or re.search(r'\$([\d,]+\.\d{2})\s*$', r) for r in rows[i - 3:i][::-1] if MONEY.search(r))
    return dict(inv=re.search(r'Invoice No\.:\s+(\d{5})', hp).group(1),
                date=iso(re.search(r'Date:\s+(\d{1,2}/\d{2}/\d{4})', hp).group(1)),
                due=(iso(m.group(1).replace('/26', '/2026')) if (m := re.search(r'Due date: (\d{2}/\d{2}/\d{2})', full)) else None),
                ref=(m.group(1) if (m := re.search(r'PO:\s+(\d+)', hp)) else None),
                contract=(m.group(1) if (m := re.search(r'Contract\s*(?:No:)?\s*\n?\s*(PAR/\S+)', hp)) else None),
                sub=D(re.search(r'Subtotal:\s+\$([\d,]+\.\d{2})', full).group(1)),
                gst=D(g.group(1)),
                tot=D(re.search(r'Total \(inc-GST\):\s+\$([\d,]+\.\d{2})', full).group(1)))


def classify(batch, d, pages):
    """One record per printed layout row, in page order. Duplicate copies are typed and never priced (11.4)."""
    lno = 0
    hdr_seen = {}
    for pno in d.pages:
        p = pages[pno - 1]
        dup = pno in d.copies or (d.copies and pno > d.copies[0])
        rows = p.splitlines() or ['']
        for ln in rows:
            lno += 1
            if not ln.strip():
                d.add(pno, lno, ln, 'BLANK'); continue
            if dup:
                d.add(pno, lno, ln, 'DUPLICATE_COPY', note='second printed copy of this invoice; outside the arithmetic (rule 11.4)')
                continue
            if (HARP_HDR if batch == 'mix222' else VIN_HDR).match(ln):
                hdr_seen[pno] = (lno, ln, bands_of(ln))
                d.add(pno, lno, ln, 'TABLE_HEADER'); continue
            if 'How to pay' in ln or 'Scan the QR code' in ln or 'Pay online' in ln or 'Invoice number:' in ln:
                d.add(pno, lno, ln, 'PAYMENT_ADVICE'); continue
            m = HARP_ROW.match(ln) if batch == 'mix222' else (VIN_ROW_B.match(ln) or VIN_ROW_A.match(ln))
            if m and hdr_seen:
                g = m.groupdict()
                d.add(pno, lno, ln, 'PRICED', qty=float(D(g['q'])) if g.get('q') else None,
                      unit=float(D(g['u'])) if g.get('u') else None, amt=float(D(g['a'])),
                      gst=g.get('tax'), bands=[b for b in ('qty', 'unit_price', 'amount') if g.get({'qty': 'q', 'unit_price': 'u', 'amount': 'a'}[b])],
                      wo=None, note=('layout A: this template prints no quantity and no unit price column, only a '
                                     'description, an ex-GST amount and a tax code (prompt v6 4.2)') if g.get('tax') else None)
                continue
            if TOTAL_RX.search(ln) or MONEY_ONLY.match(ln):
                d.add(pno, lno, ln, 'TOTALS'); continue
            d.add(pno, lno, ln, 'NARRATIVE')
    return hdr_seen


def residue(d, hdr_seen):
    """Prompt v6 4.5: no NARRATIVE row between the item header and the totals block may carry money in the amount band."""
    if not hdr_seen:
        return []
    first = min(v[0] for v in hdr_seen.values())
    tot = min([l['line_no'] for l in d.lines if l['line_type'] == 'TOTALS' and l['line_no'] > first] or [10 ** 9])
    band = min(v[2].get('amount', v[2].get('ex_amount', 10 ** 9)) for v in hdr_seen.values())
    out = []
    for l in d.lines:
        if l['line_type'] != 'NARRATIVE' or not (first < l['line_no'] < tot):
            continue
        for m in MONEY.finditer(l['line_text']):
            if m.start() >= band - 6:
                out.append((l['line_no'], m.group(0)))
    return out


def parse(batch):
    cfg = BINDERS[batch]
    pdf = os.path.join(PDF_DIR, cfg['pdf'])
    n = npages(pdf)
    pages = [text(pdf, i) for i in range(1, n + 1)]
    docs = split_pages(cfg, pages)
    out = []
    for d in docs:
        d.pages = sorted(set(d.pages))
        full = '\n'.join(pages[p - 1] for p in d.pages if p not in d.copies and not (d.copies and p > d.copies[0]))
        hp = pages[d.pages[0] - 1]
        h = cfg | header_fields(batch, full, hp)
        hdr_seen = classify(batch, d, pages)
        res = residue(d, hdr_seen)
        assert not res, f'{h["inv"]}: residue test (prompt v6 4.5) found {res}'
        assert hdr_seen, f'{h["inv"]}: no item table header recorded (P11)'
        cap = sum((D(l['line_ex_gst']) for l in d.lines if l['line_type'] == 'PRICED'), Decimal('0'))
        assert cap == h['sub'], f'{h["inv"]}: captured {cap} against printed subtotal {h["sub"]}'
        assert h['sub'] + h['gst'] == h['tot'], f'{h["inv"]}: header does not add up (P10): {h["sub"]} + {h["gst"]} != {h["tot"]}'
        pk_printed = sorted(set(re.findall(r'PK\s?#?:?\s?\d{3,6}', full)))
        pk = sorted({'PK' + re.sub(r'\D', '', x).zfill(6) for x in pk_printed})
        findings = []
        if batch == 'binder11111':
            findings.append('No ABN is printed anywhere on this invoice. The only supplier identification on the face is '
                            '"RST Systems Pty Ltd" in the bank block and the remittance address admin@vintontreeservices.com.au; '
                            'the register carries the creditor as Vinton Tree Services, VIN003, ABN 84 008 552 538. A tax invoice '
                            'for a supply over $1,000 must show the supplier identity and ABN.')
        if d.copies:
            findings.append(f'The binder prints {len(d.copies) + 1} identical copies of this invoice '
                            f'(pages {d.pages[0]}-{d.pages[-1]}); the first is captured and the rest are typed DUPLICATE_COPY '
                            f'and excluded from the arithmetic (rule 11.4).')
        blanks = [p for p in d.pages if not pages[p - 1].strip('\x0c \n\t')]
        if blanks:
            findings.append(f'Blank separator page(s) {blanks}: one BLANK record each, so the document covers every page of '
                            f'its range (prompt v6 3.9). These are the pages the supplied corpus left with no record at all (P3).')
        stem_name = 'Harpley' if batch == 'mix222' else 'Vinton'
        purpose = 'plumbing' if batch == 'mix222' else 'tree works'
        stem = f'{stem_name}, {purpose}, {dt.date.fromisoformat(h["date"]).strftime("%b-%Y")}, {h["tot"]:.2f}'
        assert len(stem) <= 40, stem
        out.append(dict(doc_ref=h['inv'], doc_kind='TAX_INVOICE', source_file=cfg['pdf'],
                        source_md5=hashlib.md5(open(pdf, 'rb').read()).hexdigest(),
                        page_range=[d.pages[0], d.pages[-1]], supplier=cfg['supplier'], supplier_abn=cfg['abn'],
                        abn_source='letterhead' if cfg['abn'] else 'absent', invoice_no=h['inv'], invoice_date=h['date'],
                        due_date=h.get('due'), printed_subtotal_ex_gst=float(h['sub']), subtotal_basis='printed',
                        printed_gst=float(h['gst']), printed_total_incl_gst=float(h['tot']),
                        header_adds_up=True, captured_ex_gst=float(cap), line_amount_basis='ex_gst', tie_basis='ex_gst',
                        self_tie='TIE', retry_log=[dict(rung=1, found='residue test: no amount-band row typed NARRATIVE', rows=[])],
                        table_headers=[dict(page=p, row=v[0], text=v[1], bands=v[2], is_item_table=True) for p, v in sorted(hdr_seen.items())],
                        work_orders=pk, contract_refs=[h['contract']] if h.get('contract') else [],
                        po_refs=[h['ref']] if h.get('ref') else [], pk_refs=pk, printed_account_codes=pk_printed,
                        evidence_stem=stem, duplicate_of=None, duplicate_copy_pages=sorted(d.copies), findings=findings,
                        notes=f'{cfg["template"]} template, raw-text route (pdftotext -layout), page text retained; '
                              f'{cfg["pdf"]} pages {d.pages[0]}-{d.pages[-1]}.',
                        lines=d.lines, page_text={str(p): pages[p - 1] for p in d.pages}, vendor_template=cfg['template']))
    return out, n


def main():
    for batch in ([sys.argv[1]] if len(sys.argv) > 1 else list(BINDERS)):
        cfg = BINDERS[batch]
        docs, n = parse(batch)
        pdf = os.path.join(PDF_DIR, cfg['pdf'])
        ver = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True).stderr.strip().splitlines()[0]
        corpus = dict(manifest=dict(batch_id=batch, source_files=[dict(file=cfg['pdf'], pages=n,
                                                                      md5=hashlib.md5(open(pdf, 'rb').read()).hexdigest())],
                                    runtime='A', extraction_tool=f'parse_binders.py raw-text route ({ver}, -layout, template {cfg["template"]})',
                                    extracted_utc=dt.datetime.now(dt.timezone.utc).isoformat(), prompt_version='v6',
                                    ocr_pages_run=0, ocr_pages_not_required=n, ocr_pages_not_available=0,
                                    ocr_pages_outstanding=0, resume_point=None), documents=docs)
        out = os.path.join(OUTDIR, batch, f'corpus_{batch}_v6.json')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(corpus, open(out, 'w'), indent=1)
        cov = sorted({p for d in docs for p in range(d['page_range'][0], d['page_range'][1] + 1)})
        assert cov == list(range(1, n + 1)), f'{batch}: page coverage {len(cov)} of {n}'
        print(f'{batch}: {len(docs)} documents, {n} pages all covered, '
              f'{sum(len(d["lines"]) for d in docs)} line records, '
              f'captured ex GST {sum(D(d["captured_ex_gst"]) for d in docs):,.2f}, all TIE')
        for d in docs:
            if d['duplicate_copy_pages'] or len(d['findings']) > 1:
                print(f'  {d["invoice_no"]:<10} pages {d["page_range"]} ' +
                      ('; '.join(f[:70] for f in d['findings'][1:]) if len(d['findings']) > 1 else ''))


if __name__ == '__main__':
    main()
