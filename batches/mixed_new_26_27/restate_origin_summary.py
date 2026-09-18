"""restate_origin_summary.py - pair the Origin Energy summary block's detached labels and values,
and record the uncaptured Total Amount Due (rule 19.2, R-MN-1 and R-MN-2).

FOUND BY the 4.7 printed-money screen (pswp_money_screen.py), which read 10 rows UNACCOUNTED on
two Origin Energy consolidated invoices: money printed on the page, typed NARRATIVE, and recorded
nowhere in the corpus. Neither is a dropped line item and neither moves the register, but both are
information the capture threw away.

R-MN-1, THE DETACHED SUMMARY BLOCK. On the CONSOLIDATED INVOICE SUMMARY, `pdftotext -layout` puts
three charge labels and their figures on SEPARATE rows, because the label column wraps and the
figure column does not:

    r29 Network Charges                r32                         $195,004.73
    r30 Regulated Charges              r33                           $2,325.14
    r31 Environmental Charges          r34                          $31,516.40
    r39 Sub-Total                      r41                         $565,345.00
    r40 GST                            r42                          $56,534.10

The label rows were typed TOTALS with no value, which is right. The figure rows fell through the
4.0 ladder to rung 9 and were typed NARRATIVE, because rung 3 tests for a totals LABEL and these
rows carry none. So the charge breakdown is in the corpus as five unattached numbers.

THE PAIRING IS PROVED BY ARITHMETIC, not by position alone. On 1026099 the seven charge components
read in label order sum to $565,345.00, which is the printed subtotal to the cent:

    328,858.02 + 195,004.73 + 2,325.14 + 31,516.40 + 5,764.78 + 1,875.51 + 0.42 = 565,345.00

The same holds on 1026231. A pairing that did not hold would not sum, so this script asserts it and
writes nothing if it fails.

R-MN-2, THE TOTAL AMOUNT DUE. Row 148 prints `Total Amount Due` as a TOTALS label with no value and
row 150 carries $1,236,014.57, which row 14 also prints beside the current charges of $621,879.10
under the caption "(Current charges only)". The capture kept the current charges, which is the right
figure for the register and for this invoice's own tie. But the amount the Council would actually
pay is the account balance, and nothing in the corpus recorded it. On a part-paid invoice, section 5.0
makes a `Balance Due` differing from `Total` an F1; a balance carried forward is the same defect
mirrored, and the gap is $614,135.47 on 1026099 and $620,816.05 on 1026231.

NOTHING MOVES. No amount is added to any priced line, no tie changes, no printed text is altered,
and `printed_total_incl_gst` stays the current charges on both documents.

Usage: python3 restate_origin_summary.py
"""
import json, os, re
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'corpus_mixed_new_26_27_v6.json')

# A figure-only row STARTS with its money token: there is no label to its left, which is the
# whole reason it fell to ladder rung 9. It is not necessarily money ALONE on the row. Row 42
# reads "$56,534.10    0    47", the GST figure followed by the site counts from the panel to
# its right, and a whole-row match silently skipped it: the first cut of this script paired
# four rows instead of five and reported success, which is why the count is now asserted.
MONEY_HEAD = re.compile(r'^\$?\s?([\d,]+\.\d{2})\b')
LABEL_ORDER = ['Energy Charges', 'Network Charges', 'Regulated Charges', 'Environmental Charges',
               'Metering Charges', 'Retail Service Charges',
               'Additional Charges, Credits & Adjustments']


def d(x):
    return Decimal(str(x).replace('$', '').replace(',', ''))


def signed(txt, amount):
    """A trailing `Cr` makes the figure a CREDIT, so it subtracts.

    1026231 prints `Additional Charges, Credits & Adjustments   $52.91 Cr`. Read as positive it
    put the component sum $105.82 over the printed subtotal, which is exactly twice $52.91: the
    arithmetic assertion below caught it, and it is the reason that assertion is in this script
    rather than a comment saying the pairing looks right."""
    return -amount if re.search(r'\bCR\b|\bCr\b', txt) else amount


def summary_rows(doc):
    """The label rows with no figure, and the figure-only rows, on the summary page, in order."""
    pg = doc['page_range'][0]
    labels, figures = [], []
    for l in doc['lines']:
        if l['page'] != pg:
            continue
        txt = (l.get('line_text') or '')
        if l['line_type'] == 'TOTALS' and not re.search(r'[\d,]+\.\d{2}', txt):
            labels.append(l)
        elif l['line_type'] == 'NARRATIVE' and MONEY_HEAD.match(txt.strip()):
            figures.append(l)
    # The summary block begins at its first unpaired label. Row 14, in the header block above it,
    # also starts with a money token: it prints the current charges and the account balance side
    # by side, and pairing it with a summary label would be nonsense.
    if labels:
        figures = [f for f in figures if f['line_no'] > labels[0]['line_no']]
    return labels, figures


def charge_total(doc):
    """Every charge component on the summary page, whether it prints beside its label or below it."""
    pg = doc['page_range'][0]
    vals = []
    for l in doc['lines']:
        if l['page'] != pg:
            continue
        txt = (l.get('line_text') or '')
        if l['line_type'] == 'TOTALS' and any(txt.strip().startswith(k) for k in LABEL_ORDER):
            m = re.search(r'\$([\d,]+\.\d{2})', txt)
            if m:
                vals.append(signed(txt[m.end():], d(m.group(1))))
    return vals


def main():
    corpus = json.load(open(SRC))
    retyped = found = 0
    for doc in corpus['documents']:
        if 'Origin Energy' not in (doc.get('supplier') or ''):
            continue
        if doc.get('duplicate_of'):
            continue                      # 11.4: the repeated copy is out of every such check
        labels, figures = summary_rows(doc)
        assert len(figures) == 5, (doc['doc_ref'], 'expected 5 detached figures, found',
                                   [f['line_no'] for f in figures])

        # Label rows with no figure, in printed order, take the figure-only rows in printed order.
        unpaired = [l for l in labels if l['line_no'] < figures[-1]['line_no']]
        pairs = list(zip(unpaired[:len(figures)], figures))
        assert len(pairs) == len(figures), (doc['doc_ref'], len(unpaired), len(figures))

        # PROVE the pairing before writing it: the charge components must sum to the subtotal.
        comps = charge_total(doc)
        for lab, fig in pairs:
            name = (lab.get('line_text') or '').strip()
            if any(name.startswith(k) for k in LABEL_ORDER):
                ftxt = (fig.get('line_text') or '').strip()
                comps.append(signed(ftxt, d(MONEY_HEAD.match(ftxt).group(1))))
        assert sum(comps) == d(doc['printed_subtotal_ex_gst']), \
            (doc['doc_ref'], str(sum(comps)), doc['printed_subtotal_ex_gst'])

        for lab, fig in pairs:
            name = (lab.get('line_text') or '').strip()
            val = MONEY_HEAD.match((fig.get('line_text') or '').strip()).group(1)
            fig['line_type'] = 'TOTALS'
            fig['note'] = (f"R-MN-1: the figure for '{name}' (row {lab['line_no']}). "
                           f"pdftotext -layout split the label and its figure onto separate rows, "
                           f"so this row reached ladder rung 9 and was typed NARRATIVE. "
                           f"The pairing is proved by the components summing to the printed subtotal.")
            lab['note'] = f"R-MN-1: its figure ${val} prints on row {fig['line_no']}."
            retyped += 1

        # R-MN-2. The Total Amount Due, which is the account balance, not this invoice's total.
        due = None
        for l in doc['lines']:
            if l['line_type'] == 'TOTALS' and 'Total Amount Due' in (l.get('line_text') or ''):
                nxt = [x for x in doc['lines']
                       if x['page'] == l['page'] and x['line_no'] > l['line_no']
                       and re.search(r'\$([\d,]+\.\d{2})', x.get('line_text') or '')]
                if nxt:
                    due = re.search(r'\$([\d,]+\.\d{2})', nxt[0]['line_text']).group(1)
                    nxt[0]['note'] = (f"R-MN-2: the Total Amount Due (row {l['line_no']}), which is the "
                                      f"ACCOUNT BALANCE and not this invoice's total.")
                break
        if due:
            gap = d(due) - d(doc['printed_total_incl_gst'])
            doc.setdefault('findings', []).append(
                f"F1 Total Amount Due ${due} is the account balance and differs from the invoice total "
                f"${doc['printed_total_incl_gst']:,.2f} by ${gap:,.2f}, because a balance is carried "
                f"forward. printed_total_incl_gst is the CURRENT CHARGES and is the right figure for the "
                f"register; the payable amount is the balance. R-MN-2.")
            doc['amount_due_printed'] = float(d(due))
            found += 1

    corpus['manifest'].setdefault('restatements', []).append(
        dict(rule='R-MN-1/R-MN-2', rows=retyped, findings=found,
             detail=('Origin Energy summary: detached figures retyped NARRATIVE -> TOTALS and paired with '
                     'their labels, pairing proved against the printed subtotal; Total Amount Due recorded '
                     'as F1. No amount, tie or printed text changed.')))
    # Write only if something changed. A no-op run that rewrites the file still reserialises it,
    # which is a whole-file diff over a capture for no reason.
    assert retyped and found, ('nothing matched; refusing to rewrite the corpus', retyped, found)
    json.dump(corpus, open(SRC, 'w'), indent=1)
    print(f'{retyped} figure rows paired and retyped; {found} F1 finding(s) recorded')


if __name__ == '__main__':
    main()
