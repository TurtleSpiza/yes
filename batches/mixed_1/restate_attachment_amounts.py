"""restate_attachment_amounts.py - put the printed amount on the 55 ATTACHMENT rows (rule 19.2, R-M1-2).

FOUND BY the v7.7 review of this batch's line states. Prompt section 9 has said since v7.1: an
ATTACHMENT row prints an amount, "keep the printed amount in `line_ex_gst`", and 4.4's "only if"
direction runs over PRICED and ATTACHMENT for exactly that reason. All 55 ATTACHMENT rows in this
corpus carry `line_ex_gst: null` while their printed amount sits in `line_text`, so the corpus
records the rows and throws away what they say. The PVG batch, which holds the same Glascott
schedule, writes them the compliant way.

WHAT THIS SCRIPT DOES, AND WHAT IT DELIBERATELY DOES NOT.

It writes `line_ex_gst` from the first money token on the row, and `band_hits` to name the column.
It changes NO line type, so no amount enters any tie: rule 16d keeps ATTACHMENT out of the
arithmetic gate and out of register rule 17 check 1, and `captured_ex_gst` is asserted unchanged
on every document before anything is written.

IT DOES NOT RETYPE THE 52 ROWS THAT ARE PROBABLY THIS DOCUMENT'S OWN LINE ITEMS, and that is a
deliberate hold, not an oversight. Splitting the rows by the PK printed on each:

    012191/pages55-56   25 rows PK000378 = $32,477.92   printed subtotal $32,477.92
                         1 row  PK000382 = $473.52
    012197/pages57-58   27 rows PK000378 = $25,217.15   printed subtotal $25,217.15
                         1 row  PK000379 = $1,237.66
                         1 row  PK000383 = $618.83

On both documents the PK000378 rows sum to the printed subtotal TO THE CENT, so they are that
invoice's own line items and only the other-PK rows are scoped elsewhere. Against them the corpus
carries a single PRICED row reading "Please refer to attached sheet for details." holding the whole
subtotal, which is what rule 11.1 calls a critical failure: a summary row in place of line capture.

The remedy is to retype those 52 rows PRICED and take the amount off the summary row. It is HELD
because `Mixed_1.pdf` (md5 b9ddf7fd6c56188a22181921b7b2c8ab) has never been mask-screened and is
not in the repository. The same Glascott schedule page in the other binder masks rows per invoice
copy: on `97 001 281 572.pdf` page 5, invoice 012192 masks 25 rows worth $32,477.92 and prints only
$473.52, which is the exact complement of what 012191 prints here, over the same 26 rows totalling
$32,951.44. So the masking on this binder's copy is an open question with a $57,695.07 answer, and
a masked row is never captured (M1). The mask screen renders the page; it cannot be reasoned out.

Usage: python3 restate_attachment_amounts.py
"""
import json, os, re
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'corpus_mixed_1_v6.json')
MONEY = re.compile(r'\$([\d,]+\.\d{2})')


def main():
    corpus = json.load(open(SRC))
    n = 0
    for doc in corpus['documents']:
        before = doc.get('captured_ex_gst')
        priced_before = sum(Decimal(str(l['line_ex_gst']))
                            for l in doc['lines']
                            if l['line_type'] == 'PRICED' and l.get('line_ex_gst') is not None)
        for l in doc['lines']:
            if l['line_type'] != 'ATTACHMENT':
                continue
            assert l.get('line_ex_gst') is None and l.get('stated_amt') is None, \
                ('already carries an amount', doc['doc_ref'], l['line_no'])
            m = MONEY.findall(l.get('line_text') or '')
            assert m, ('no printed amount on an ATTACHMENT row', doc['doc_ref'], l['line_no'])
            # The first money token is the Ex GST column; the second is the GST and the third the
            # inc-GST total. Annexe A names the Ex GST column as the Glascott schedule's amount band.
            l['line_ex_gst'] = float(Decimal(m[0].replace(',', '')))
            l['band_hits'] = sorted(set((l.get('band_hits') or []) + ['amount']))
            pk = re.search(r'PK\d{6}', l.get('line_text') or '')
            l['note'] = ('R-M1-2: the printed Ex GST amount, which section 9 has required on an '
                         'ATTACHMENT row since v7.1 (rule 16d). Out of the tie either way.'
                         + (f" Scoped by {pk.group(0)} printed on the row." if pk else ''))
            n += 1
        # Nothing may move: ATTACHMENT is out of the tie by rule 16d.
        priced_after = sum(Decimal(str(l['line_ex_gst']))
                           for l in doc['lines']
                           if l['line_type'] == 'PRICED' and l.get('line_ex_gst') is not None)
        assert priced_before == priced_after and doc.get('captured_ex_gst') == before, doc['doc_ref']

    assert n == 55, ('expected 55 ATTACHMENT rows, wrote', n)
    corpus['manifest'].setdefault('restatements', []).append(
        dict(rule='R-M1-2', rows=n,
             detail=('printed Ex GST written to line_ex_gst on every ATTACHMENT row (section 9, rule 16d). '
                     'No line type changed, no tie changed. The 52 PK000378 rows that sum to their '
                     'documents\' printed subtotals are HELD for retyping pending the mask screen on '
                     'Mixed_1.pdf.')))
    corpus['manifest'].setdefault('held', []).append(
        dict(rule='R-M1-3', status='HELD', needs='Mixed_1.pdf for pbr_mask_screen.py',
             detail=('52 ATTACHMENT rows (25 on 012191, 27 on 012197) carry PK000378 and sum to their '
                     'documents\' printed subtotals exactly, so they are those invoices\' own line items '
                     'and the single "Please refer to attached sheet for details." PRICED row holding the '
                     'whole subtotal is a rule 11.1 summary row in place of line capture. Retyping them '
                     'PRICED needs the masked-row verdict first: the same schedule in 97 001 281 572.pdf '
                     'masks the complementary rows on invoice 012192.')))
    json.dump(corpus, open(SRC, 'w'), indent=1)
    print(f'{n} ATTACHMENT rows given their printed amount; R-M1-3 held pending Mixed_1.pdf')


if __name__ == '__main__':
    main()
