"""restate_schedule_rows.py - type the Glascott schedule rows ATTACHMENT (rule 19.2, R-PVG-1).

This corpus was extracted under prompt v6 and reads RED on 104 P2 rows: 103 amount-bearing rows typed
NARRATIVE and one DUPLICATE_COPY carrying an amount.

The 103 are not misclassified line items and capturing them as PRICED would be wrong. Glascott prints ONE site
schedule across a set of invoices, every row carrying its own cost account, so on invoice 012192 the single
PK000382 row is the line item and the twenty-five PK000378 rows belong to other invoices in the same set. That
is provable from the corpus without the binder: all five affected documents tie their printed subtotal EXACTLY
on their PRICED rows alone, and adding the schedule rows would break every tie, $124,347.79 in all.

Under v6 the extractor had no type for such a row, so its only conformant option was to drop the amount. v7.1
added ATTACHMENT for exactly this case (section 9, register rule 16d): the row keeps its printed amount and is
excluded from the tie and from rule 17 check 1. R-PVG-1 retypes them and lifts the corpus to v7.1, which is the
version whose vocabulary it now uses.

The DUPLICATE_COPY row is separate and is a straight defect: 4.0 rung 2 requires a repeated copy to carry null
arithmetic. Its amount is nulled, and the printed figure survives verbatim in line_text either way.

Lifting the corpus to v7.1 turns on P17, and it finds a third defect the v6 scope had hidden: all 183
header_sources entries record a page and leave the row null, so not one header figure can be shown against the
row it came from. R-PVG-2 repairs what the retained text decides: for each field, the rows on the cited page
whose line_text prints that figure. Exactly one match is the row; none or several is left null and P17 is
allowed to fail it, because guessing which row a figure came from is the defect P17 exists to catch.

Usage: python3 restate_schedule_rows.py
"""
import json, os
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'corpus_playforce_vinton_glascott_20260916_v6.json')
OUT = os.path.join(HERE, 'corpus_playforce_vinton_glascott_20260916_v7.json')
D = lambda x: Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)


def amount(l):
    return l.get('line_ex_gst') if l.get('line_ex_gst') is not None else l.get('stated_amt')


def main():
    corpus = json.load(open(SRC))
    att = dup = 0
    proof = []
    for doc in corpus['documents']:
        rows = [l for l in doc['lines'] if l.get('line_type') == 'NARRATIVE' and amount(l) is not None]
        if rows:
            priced = sum((D(amount(l)) for l in doc['lines'] if l.get('line_type') == 'PRICED'), Decimal('0.00'))
            sub = D(doc.get('printed_subtotal_ex_gst'))
            # the tie on PRICED alone is the evidence that the rest is a schedule and not a dropped line item
            assert priced == sub, (doc['doc_ref'], priced, sub)
            proof.append((doc['doc_ref'], str(priced), str(sum((D(amount(l)) for l in rows), Decimal('0.00')))))
            for l in rows:
                l['line_type'] = 'ATTACHMENT'
                l['note'] = ('R-PVG-1: a Glascott site-schedule row scoped to another invoice in the set by the '
                             'cost account printed on the row. Amount kept, excluded from the tie (rule 16d).')
                att += 1
        for l in doc['lines']:
            if l.get('line_type') == 'DUPLICATE_COPY' and amount(l) is not None:
                l['line_ex_gst'] = l['stated_amt'] = l['gst'] = None
                l['note'] = 'R-PVG-1: a repeated copy carries null arithmetic (4.0 rung 2); the figure stays in line_text.'
                dup += 1
    # R-PVG-2: repoint the null row citations from the retained text
    fixed = amb = 0
    for doc in corpus['documents']:
        hs = doc.get('header_sources') or {}
        for field, loc in hs.items():
            if not isinstance(loc, dict) or loc.get('row') is not None:
                continue
            val = doc.get(field)
            if val is None:
                continue
            want = f'{abs(D(val)):.2f}'
            page = loc.get('page')
            hits = [l for l in doc['lines']
                    if (page is None or l.get('page') == page)
                    and want in str(l.get('line_text') or '').replace(',', '').replace('$', '')]
            if len(hits) == 1:
                loc['row'] = hits[0].get('line_no')
                loc['page'] = hits[0].get('page')
                fixed += 1
            else:
                amb += 1
    print(f'R-PVG-2: {fixed} header citations repointed from the retained text, {amb} left null '
          f'(no unique row prints the figure)')

    m = corpus['manifest']
    m['prompt_version'] = 'v7.1'
    m.setdefault('restatements', []).append(
        dict(rule='R-PVG-1 and R-PVG-2', attachment_rows=att, duplicate_rows_nulled=dup,
             header_citations_repointed=fixed, header_citations_left_null=amb,
             basis='every affected document ties its printed subtotal exactly on its PRICED rows alone',
             ties=proof))
    json.dump(corpus, open(OUT, 'w'), indent=1)
    print(f'{att} schedule rows typed ATTACHMENT over {len(proof)} documents, {dup} duplicate-copy amount nulled')
    for ref, priced, sched in proof:
        print(f'  {ref}: PRICED {priced} ties the printed subtotal; schedule rows {sched} sit outside it')


if __name__ == '__main__':
    main()
