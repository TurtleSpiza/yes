"""restate_binder1666.py - restate document 60203 from its own retained line_text (rule 19.2, R1666-1).

The batch arrived RED on one document of a hundred. Tennyson Group 60203 recorded no table_headers, so its
amount column was never anchored, and two consequences sit in the capture: the GST column was read as the line
amount, and the three header figures were taken off the wrong labelled rows. The document understated by
$257.40 and still declared TIE, because the mis-read line matched the mis-read subtotal exactly.

Nothing here is inferred. The corpus retained the row verbatim, and the source page C00309400_2.pdf prints the
bands that settle it:

    header row 11   '    Job        Quantity                Description                          Net Price    GST'
                     Net Price label [89,97], its value 286.00 at [93,98]  -> amount band [89,98]
                     GST       label [102,104], its value 28.60 at [107,111] -> gst band [102,111]
    priced row 13   '   30212                4   Parks Corflute Signs                    286.00        28.60'

28.60 sits at [107,111] and does not overlap the amount band at all, so a band that had been recorded and
calibrated as section 4.1 requires would have made this mis-read impossible. That is the whole of P11's case.

    totals row 26   Net   $   286.00        row 28   GST $   28.60        row 30   Total $   314.60

R1666-1: on document 60203, take the line amount and the three header figures from the bands above, type the
item table's header row TABLE_HEADER, and record the bands with the priced row they were calibrated against.
Every other document is untouched.

Usage: python3 restate_binder1666.py  (writes corpus_binder1666_v7.json beside the as-received corpus)
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'corpus_binder1666_as_received.json')
OUT = os.path.join(HERE, 'corpus_binder1666_v7.json')
REF = '60203'
BANDS = {'job': [3, 7], 'quantity': [15, 24], 'description': [39, 49], 'amount': [89, 98], 'gst': [102, 111]}
MONEY = re.compile(r'[\d,]+\.\d{2}')


def money_in(text, band):
    """Every money token on the row whose character span overlaps this band (prompt v7 4.2)."""
    out = []
    for m in MONEY.finditer(text):
        if m.start() <= band[1] and m.end() - 1 >= band[0]:
            out.append(float(m.group(0).replace(',', '')))
    return out


def main():
    corpus = json.load(open(SRC))
    doc = next(d for d in corpus['documents'] if str(d.get('doc_ref')) == REF)
    lines = {l['line_no']: l for l in doc['lines']}

    hdr, row = lines[11], lines[13]
    assert 'Net Price' in hdr['line_text'] and 'GST' in hdr['line_text'], hdr['line_text']

    amounts = money_in(row['line_text'], BANDS['amount'])
    gsts = money_in(row['line_text'], BANDS['gst'])
    assert amounts == [286.00] and gsts == [28.60], (amounts, gsts)

    net = money_in(lines[26]['line_text'], [100, 115])
    gst = money_in(lines[28]['line_text'], [100, 115])
    tot = money_in(lines[30]['line_text'], [100, 115])
    assert net == [286.00] and gst == [28.60] and tot == [314.60], (net, gst, tot)

    before = dict(subtotal=doc['printed_subtotal_ex_gst'], gst=doc['printed_gst'],
                  captured=doc['captured_ex_gst'], line=row.get('line_ex_gst'))

    hdr['line_type'] = 'TABLE_HEADER'
    doc['table_headers'] = [dict(page=80, row=11, text=hdr['line_text'], bands=BANDS,
                                 bands_calibrated_on=dict(page=80, row=13), is_item_table=True)]
    row['line_ex_gst'] = amounts[0]
    row['gst'] = gsts[0]
    row['band_hits'] = ['amount', 'gst']
    row['note'] = ('R1666-1: the amount was read from the GST band. 286.00 spans [93,98] and overlaps the '
                   'amount band [89,98]; 28.60 spans [107,111] and does not.')
    doc['printed_subtotal_ex_gst'] = net[0]
    doc['printed_gst'] = gst[0]
    doc['printed_total_incl_gst'] = tot[0]
    doc['captured_ex_gst'] = amounts[0]
    doc['header_sources'] = {'printed_subtotal_ex_gst': {'page': 80, 'row': 26},
                             'printed_gst': {'page': 80, 'row': 28},
                             'printed_total_incl_gst': {'page': 80, 'row': 30}}
    doc['header_adds_up'] = True
    doc['self_tie'] = 'TIE'
    doc['tie_tolerance'] = '1c'
    doc['notes'] = (doc.get('notes', '') + ' R1666-1: restated from the retained line_text against the bands the '
                    'source page prints; the subtotal and the GST had been read off each other\'s rows and the '
                    'line amount taken from the GST band, understating the document by $257.40.').strip()

    m = corpus['manifest']
    m['prompt_version'] = 'v7.2'
    m['captured_ex_gst_total'] = round(sum(float(d.get('captured_ex_gst') or 0) for d in corpus['documents']), 2)
    m['restatements'] = [dict(rule='R1666-1', doc_ref=REF, before=before,
                              after=dict(subtotal=doc['printed_subtotal_ex_gst'], gst=doc['printed_gst'],
                                         captured=doc['captured_ex_gst'], line=row['line_ex_gst']),
                              understated_by=257.40,
                              basis='source page C00309400_2.pdf, bands recorded and calibrated on row 13')]
    m['gate'] = 'AMBER'
    json.dump(corpus, open(OUT, 'w'), indent=1)
    print(f'restated {REF}: subtotal {before["subtotal"]} -> {doc["printed_subtotal_ex_gst"]}, '
          f'GST {before["gst"]} -> {doc["printed_gst"]}, line {before["line"]} -> {row["line_ex_gst"]}')
    print(f'corpus captured ex GST total {corpus["manifest"]["captured_ex_gst_total"]:,.2f} '
          f'(was {json.load(open(SRC))["manifest"]["captured_ex_gst_total"]:,.2f})')


if __name__ == '__main__':
    main()
