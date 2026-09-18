"""restate_bands.py - record the amount band on Glascott 012195 (rule 19.2, R-A4-1).

corpus_attach_4_v6.json carries one P11: document 012195/C00318419.pdf has a PRICED line and an empty
table_headers, so section 4 was never anchored on it.

It is the case 4.1 already names. No item table prints on page 1 at all: the single priced row reads "Please
refer to attached sheet for details." with the amount in the totals column, and the detail is the schedule on
page 2. 4.1 says to say so in notes, set the amount band from the totals block's own money column, which is the
same band, and calibrate it against a priced row.

Read off the retained line_text, every money token in the page 1 totals block occupies the same column:

    row 34  PRICED  35,866.01  span [141,149]   <- the priced row, and the calibration
    row 36  TOTALS  35,866.01  span [141,149]
    row 37  TOTALS   3,586.60  span [142,149]
    row 39  TOTALS  39,452.61  span [141,149]

So the amount band is [141,149] and it is calibrated on row 34. Nothing is inferred and no amount moves.

Usage: python3 restate_bands.py
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'corpus_attach_4_v6.json')
REF = '012195/C00318419.pdf'
BAND = [141, 149]
MONEY = re.compile(r'[\d,]+\.\d{2}')


def main():
    corpus = json.load(open(SRC))
    doc = next(d for d in corpus['documents'] if d.get('doc_ref') == REF)
    assert not doc.get('table_headers'), 'bands already recorded'
    priced = [l for l in doc['lines'] if l.get('line_type') == 'PRICED']
    assert len(priced) == 1, len(priced)
    row = priced[0]
    hits = [m for m in MONEY.finditer(row['line_text'] or '') if m.start() <= BAND[1] and m.end() - 1 >= BAND[0]]
    assert len(hits) == 1 and hits[0].group(0).replace(',', '') == f"{doc['printed_subtotal_ex_gst']:.2f}", hits
    doc['table_headers'] = [dict(page=row.get('page'), row=row.get('line_no'), text=None,
                                 bands={'amount': BAND},
                                 bands_calibrated_on=dict(page=row.get('page'), row=row.get('line_no')),
                                 is_item_table=True)]
    row['band_hits'] = ['amount']
    doc['notes'] = ((doc.get('notes') or '') + ' R-A4-1: no item-table header prints on this document. The single '
                    'priced row refers to the schedule on page 2 and carries its amount in the totals column, so '
                    'the amount band is taken from that column, [141,149], and calibrated on the priced row '
                    'itself (4.1, the Kachel case).').strip()
    corpus['manifest'].setdefault('restatements', []).append(
        dict(rule='R-A4-1', doc_ref=REF, band=BAND, basis='the page 1 totals column, read off the retained line_text'))
    json.dump(corpus, open(SRC, 'w'), indent=1)
    print(f'{REF}: amount band {BAND} recorded, calibrated on page {row.get("page")} row {row.get("line_no")}')


if __name__ == '__main__':
    main()
