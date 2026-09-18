"""restate_savco_dates.py - recover the 13 Savco invoice dates the extraction missed (rule 19.2, R1666-3).

Thirteen Savco documents record invoice_date "(not printed)". The date IS printed. Savco's header block reads

    INVOICE NO.            DATE                 TOTAL DUE              DUE DATE            TERMS
    SV007809               29/06/2026           A$2,275.61             13/07/2026          NET 14

so the date sits in the second column of the row beneath the labels. This is the Savco header trap section 4.1
already names from mix22, where a header-shaped row twenty rows above the item table was read as the item
table's own; here the same two-row block defeated the header-amount read in 5.0 instead.

R1666-3 takes the invoice date and the due date from that row in the retained page text, matching the row by the
document's own invoice number so it cannot pick up a neighbour's. Every date is asserted to parse and to fall
inside the binder's own date range before it is written.

Usage: python3 restate_savco_dates.py
"""
import datetime as dt, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, 'corpus_binder1666_v6.json')
PAGES = os.path.join(HERE, 'pages_binder1666.json')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'toolkit', 'branch'))
from parse_mixed1 import iso  # noqa: E402

ROW = re.compile(r'^\s*(\S+)\s+(\d{1,2}/\d{1,2}/\d{2,4})\s+A?\$?[\d,]+\.\d{2}\s+(\d{1,2}/\d{1,2}/\d{2,4})')
LO, HI = dt.date(2025, 7, 1), dt.date(2027, 6, 30)


def main():
    corpus = json.load(open(CORPUS))
    pages = json.load(open(PAGES))
    fixed, missed = 0, []
    for doc in corpus['documents']:
        if doc.get('invoice_date') != '(not printed)':
            continue
        ref = str(doc.get('doc_ref'))
        pr = doc.get('page_range') or []
        text = '\n'.join(pages.get(str(p), '') for p in range(pr[0], pr[1] + 1)) if len(pr) == 2 else ''
        hit = None
        for line in text.splitlines():
            m = ROW.match(line)
            if m and m.group(1) == ref:      # matched on this document's own invoice number
                hit = m
                break
        if not hit:
            missed.append(ref)
            continue
        inv, due = iso(hit.group(2)), iso(hit.group(3))
        for v in (inv, due):
            d_ = dt.date.fromisoformat(v)
            assert LO <= d_ <= HI, (ref, v)
        doc['invoice_date'] = inv
        doc['due_date'] = due
        doc['notes'] = ((doc.get('notes') or '') + f' R1666-3: invoice date {inv} and due date {due} recovered '
                        'from the printed header row, which the extraction recorded as "(not printed)".').strip()
        doc.setdefault('findings', []).append(
            f'[F1] The extraction recorded no invoice date; the face prints {hit.group(2)} in the DATE column of '
            f'its header block. Restated under R1666-3. Amount $0.00.')
        fixed += 1
    corpus['manifest'].setdefault('restatements', []).append(
        dict(rule='R1666-3', documents=fixed, basis='the printed Savco header row, matched on the invoice number'))
    json.dump(corpus, open(CORPUS, 'w'), indent=1)
    print(f'{fixed} Savco invoice dates recovered from the page' + (f', {len(missed)} not found: {missed}' if missed else ''))


if __name__ == '__main__':
    main()
