"""restate_woodmans.py - restate Woodmans 6431345 from its source page (rule 19.2, R1666-2).

The document that held Binder1666 at RED. It parsed nothing: zero PRICED lines, no table header, no bands,
subtotal recorded $0.00 and total $39.99, which is the first row's unit price. The corpus's retained line_text
is truncated at the right edge, so the Total Inc GST column is cut from every item row and the totals read
"$268.0" and "$290.8". It could not be restated from the corpus alone and was held for the binder.

Page 48 was supplied on 18-Sep-2026 and settles it. The item table prints

    SKU        Description                      Qty  UM   Price Ex GST   Disc %   GST    Total Inc GST

and the line ex-GST is the Inc column less the GST column, NOT quantity times the unit price. That distinction
is the whole of the earlier ambiguity: on the rake, 2 x 22.27 is 44.54 and Inc less GST is 44.55, and only the
second reconciles. Derived that way all three printed totals tie exactly, with no rounding left over:

    sum of line ex-GST   268.00   against the printed GST Ex Total    268.00
    sum of line GST       22.80   against the printed GST             22.80
    sum of line Inc      290.80   against the printed GST Inc Total   290.80

The document is also a MIXED SUPPLY: B601927 carries GST 0.00 on a $39.99 line, so a tenth of the subtotal is
$26.80 against a printed $22.80. That is 5.6, not a defect, and P16 exempts it from v7.5 because the line GSTs
sum to the printed GST.

Usage: python3 restate_woodmans.py
"""
import json, os, re
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'corpus_binder1666_v7_2.json')
OUT = os.path.join(HERE, 'corpus_binder1666_v7_5.json')
REF = '6431345'
D = lambda x: Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)

# SKU, qty, unit price ex GST, discount, GST, total inc GST, as page 48 prints them
FACE = [('B601927', 1, '39.99', None, '0.00', '39.99'),
        ('7511850', 1, '22.68', None, '2.27', '24.95'),
        ('2166353', 2, '22.27', None, '4.45', '49.00'),
        ('1035716', 1, '59.09', None, '5.91', '65.00'),
        ('2454916', 1, '58.50', '2.50%', '5.85', '64.35'),
        ('2438067', 1, '6.82', '5.00%', '0.68', '7.51'),
        ('B018003', 1, '36.36', None, '3.64', '40.00')]
HEADER = {'subtotal': '268.00', 'gst': '22.80', 'total': '290.80'}
BANDS = {'sku': [0, 17], 'description': [18, 61], 'qty': [62, 66], 'um': [69, 73],
         'price_ex_gst': [78, 84], 'disc': [93, 98], 'gst': [101, 107], 'amount': [116, 125]}


def main():
    corpus = json.load(open(SRC))
    doc = next(d for d in corpus['documents'] if str(d.get('doc_ref')) == REF)
    by_sku = {}
    for l in doc['lines']:
        m = re.match(r'\s*([A-Z]?\d{6,7})\s', l.get('line_text') or '')
        if m:
            by_sku[m.group(1)] = l

    ex_total = gst_total = inc_total = Decimal('0.00')
    for sku, qty, unit, disc, gst, inc in FACE:
        l = by_sku.get(sku)
        assert l is not None, f'{sku} has no retained row'
        ex = D(inc) - D(gst)
        l['line_type'] = 'PRICED'
        l['qty'] = float(qty)
        l['unit_price_ex_gst'] = float(D(unit))
        l['line_ex_gst'] = float(ex)
        l['gst'] = float(D(gst))
        l['stated_amt'] = float(D(inc))
        l['band_hits'] = ['qty', 'price_ex_gst', 'gst', 'amount']
        l['note'] = ('R1666-2: line ex-GST is the printed Total Inc GST less the printed GST, not quantity '
                     'times the unit price; only that derivation reconciles the three printed totals.'
                     + (f' Discount {disc} printed.' if disc else ''))
        ex_total += ex
        gst_total += D(gst)
        inc_total += D(inc)

    assert (ex_total, gst_total, inc_total) == (D(HEADER['subtotal']), D(HEADER['gst']), D(HEADER['total'])), \
        (ex_total, gst_total, inc_total)

    # The retained totals rows are truncated at the right edge ("$268.0", "$290.8"), so they are restated from
    # the page verbatim and typed TOTALS, and header_sources is repointed at them. Without this P17 is right to
    # fail the document: the figures were not printed on the rows it cited.
    import subprocess
    pdf = os.path.join(HERE, 'Pages_from_Binder1666_p48.pdf')
    page = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout.splitlines()
    want = {'printed_subtotal_ex_gst': 'GST Ex Total', 'printed_gst': 'GST', 'printed_total_incl_gst': 'GST Inc Total'}
    src = {}
    for field, label in want.items():
        real = next(t for t in page if label in t and ('$' in t)
                    and (label != 'GST' or ('Ex Total' not in t and 'Inc Total' not in t)))
        row = next((l for l in doc['lines'] if label in (l.get('line_text') or '')
                    and (label != 'GST' or ('Ex Total' not in l['line_text'] and 'Inc Total' not in l['line_text']))), None)
        assert row is not None, field
        row['line_text'] = real.rstrip()
        row['line_type'] = 'TOTALS'
        src[field] = dict(page=48, row=row.get('line_no'))
    doc['header_sources'] = src

    hdr = next((l for l in doc['lines'] if 'Description' in (l.get('line_text') or '') and 'Qty' in (l.get('line_text') or '')), None)
    if hdr:
        hdr['line_type'] = 'TABLE_HEADER'
    doc['table_headers'] = [dict(page=48, row=(hdr or {}).get('line_no', 26), text=(hdr or {}).get('line_text', ''),
                                 bands=BANDS, bands_calibrated_on=dict(page=48, row=by_sku['B601927'].get('line_no')),
                                 is_item_table=True)]
    doc['printed_subtotal_ex_gst'] = float(D(HEADER['subtotal']))
    doc['printed_gst'] = float(D(HEADER['gst']))
    doc['printed_total_incl_gst'] = float(D(HEADER['total']))
    doc['captured_ex_gst'] = float(ex_total)
    doc['header_adds_up'] = True
    doc['self_tie'] = 'TIE'
    doc['tie_tolerance'] = '1c'
    doc['residue_rows'] = []
    doc['gst_basis'] = 'read off the printed GST label'
    doc['subtotal_basis'] = 'printed'
    doc['mixed_supply'] = True
    doc['notes'] = ((doc.get('notes') or '') + ' R1666-2: restated from source page 48 (Pages_from_Binder1666_p48.pdf). '
                    'Seven priced rows, line ex-GST derived as Total Inc GST less GST. Mixed supply: B601927 '
                    'carries GST 0.00 on a $39.99 line, so the printed GST of $22.80 is not a tenth of the '
                    '$268.00 subtotal (5.6).').strip()

    m = corpus['manifest']
    m['prompt_version'] = 'v7.5'
    m['captured_ex_gst_total'] = round(sum(float(d.get('captured_ex_gst') or 0) for d in corpus['documents']), 2)
    m.setdefault('restatements', []).append(
        dict(rule='R1666-2', doc_ref=REF, recovered_ex_gst=float(ex_total),
             basis='source page 48 supplied 18-Sep-2026; all three printed totals tie exactly'))
    json.dump(corpus, open(OUT, 'w'), indent=1)
    print(f'{REF} restated: 7 priced lines, ex GST {ex_total}, GST {gst_total}, inc {inc_total}')
    print(f"corpus captured ex GST {m['captured_ex_gst_total']:,.2f}")


if __name__ == '__main__':
    main()
