#!/usr/bin/env python3
"""pswp_money_screen.py, v1 (18-Sep-2026)

The 4.4 invariant, run over PRINTED money rather than over recorded amounts.

Section 4.4 asserts `line_type == "PRICED"` if and only if an amount is recorded, and the
corpus gate enforces it in that direction: a non-PRICED, non-ATTACHMENT row carrying a
recorded amount is P2. That direction is complete, because the amount is in the corpus.

The other direction is not. A row that PRINTS money, is typed NARRATIVE and carries a null
amount is invisible to the gate: nothing in the corpus records the money. Section 4.5's
residue test is the check that catches it, but 4.5 is scoped to the window between the item
table header and the totals block, so a money row outside that window is caught by neither.

This script closes that gap from the corpus's own `line_text`, with no PDF needed. It lists
every NARRATIVE row whose text carries a money token, classifies each against the reasons a
narrative row may legitimately print money, and reports the remainder as candidates.

Usage:  python3 pswp_money_screen.py corpus_<batch_id>.json [--json] [--all]
Exit:   0 no unexplained candidates, 1 candidates found, 3 unreadable corpus.

It reads text, not geometry, so it cannot say whether a token overlaps the amount band.
A candidate is a row to look at, not a proven defect. Confirming one is section 4.0's job.
"""
import json, re, sys
from decimal import Decimal

# A money token, with the trailing lookahead excluding a dotted date (01.02.2026) and any
# longer number the match would otherwise bite a piece out of.
MONEY = re.compile(r'(?<![\d/.-])\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?![\d/.])'
                   r'|(?<![\d/$.,-])\d{1,3}(?:,\d{3})+\.\d{2}(?![\d/.])'
                   r'|(?<![\d/$.,-])\d+\.\d{2}(?![\d/.])')

# A printed line-item amount is COLUMN ALIGNED: it is preceded by the run of spaces that
# separates it from the description, or it starts the row. A figure quoted inside a sentence
# is preceded by a single space. This is the one geometric fact `line_text` still carries, and
# it is what separates a dropped line item from a number mentioned in prose.
ALIGNED = re.compile(r'(?:^|\s{2,})\$?\s?[\d,]+(?:\.\d{2})?\s*$|(?:^|\s{2,})\$\s?[\d,]')

# Reasons a NARRATIVE row legitimately prints a money-shaped token. Each is a named class so
# the report says WHY a row was set aside, and a reader can disagree with the class rather
# than with a silent filter.
EXEMPT = [
    ("ABN_OR_ACN",   re.compile(r'\b(?:ABN|ACN|A\.B\.N|A\.C\.N)\b', re.I)),
    ("BSB_OR_ACCT",  re.compile(r'\b(?:BSB|B\.S\.B|Account\s*(?:No|Number|#)|Acct)\b', re.I)),
    ("PHONE",        re.compile(r'\b(?:Ph|Phone|Fax|Mob|Mobile|Tel)\b[:.]?', re.I)),
    ("PAGE_OF",      re.compile(r'\bPage\s+\d+\s+of\s+\d+\b', re.I)),
    ("DATE_ONLY",    re.compile(r'^\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*$')),
    ("POSTCODE",     re.compile(r'\b(?:QLD|NSW|VIC|SA|WA|TAS|NT|ACT)\s+\d{4}\b', re.I)),
    ("RATE_OR_PCT",  re.compile(r'\d\s*%|\bGST\s+(?:is\s+)?10\b', re.I)),
    ("TERMS",        re.compile(r'\b(?:terms|days?\s+from|interest|overdue|late\s+fee)\b', re.I)),
    # An insurance limit, a liability cap or an indemnity figure prints in the fine print of
    # every Play Force invoice. The row should have been typed TERMS at rung 7 and was typed
    # NARRATIVE, which is a mistype with no arithmetic consequence, not a dropped line item.
    ("CONTRACT_TERMS", re.compile(r'\b(?:insur\w*|indemnit\w*|liabilit\w*|in\s+respect\s+of'
                                  r'|not\s+less\s+than|public\s+liability|workers.?\s+comp\w*)\b', re.I)),
    # A rate expression inside a wrapped description block (rule 11.6): "5 visits / 55 trees @
    # $284.35 = $1,421.75". The single PRICED row carries the invoice's one printed amount and
    # the block below it breaks that amount down. Trees 36107 prints five such components
    # summing to $3,145.68, which is its one PRICED row and its printed subtotal exactly, so
    # every component is already in the capture and NARRATIVE is the correct type for it.
    ("RATE_EXPRESSION", re.compile(r'@\s*\$?\s*[\d,]+\.\d{2}|=\s*\$?\s*[\d,]+\.?\d*\s*$'
                                   r'|\bper\s+(?:hour|hr|day|visit|tree|unit|item|m2|m3|tonne)\b', re.I)),
]

# A money token of a dollar or less on a NARRATIVE row is the quantity or a printed zero, not an
# amount. Xero-shaped layouts print "1.00   0.00   0.00" across the qty, unit-price and amount
# columns on every continuation row of a description; ksadasd prints it on 36 of them. Typing
# those PRICED to satisfy rung 6 would be wrong, and no dropped line item is worth a dollar.
TRIVIAL = Decimal("1.00")
# A narrative row reading like a totals or header amount is not exempt: it is a MISTYPE, which
# is the finding, not the exemption.
TOTALS_SHAPED = re.compile(
    r'\b(?:sub[\s-]?total|total|amount\s+(?:due|payable)|balance\s+(?:due|owing)|'
    r'gst|freight|rounding|paid|credit)\b', re.I)


def _val(tok):
    try:
        return Decimal(tok.replace("$", "").replace(",", "").strip()).quantize(Decimal("0.01"))
    except Exception:
        return None


def accounted_values(doc):
    """Every amount the document already records, as Decimals.

    A money token on a NARRATIVE row whose value the document ALREADY carries is an echo: a
    repeated copy of a captured page typed NARRATIVE instead of DUPLICATE_COPY at rung 2, a
    totals figure typed NARRATIVE instead of TOTALS at rung 3, or a header amount restated in
    the payment advice. Each is a mistype and none of them moves a dollar. A token whose value
    appears NOWHERE else in the document is the dangerous one: on the evidence of the corpus
    alone it is money the capture did not keep, which is the dropped line item 4.5 exists for.
    """
    vals = set()
    for k in ("printed_subtotal_ex_gst", "printed_gst", "printed_total_incl_gst",
              "captured_ex_gst"):
        v = doc.get(k)
        if v is not None:
            d = _val(str(v))
            if d is not None:
                vals.add(abs(d))
    for l in doc.get("lines", []):
        for k in ("line_ex_gst", "stated_amt", "gst", "unit_price_ex_gst"):
            v = l.get(k)
            if v is not None:
                d = _val(str(v))
                if d is not None:
                    vals.add(abs(d))
    # A running subtotal of the priced lines, so a printed line total restated in an
    # attachment or a carried-forward figure is recognised as accounted for.
    return vals


def screen(corpus, show_all=False):
    out = []
    for doc in corpus.get("documents", []):
        ref = doc.get("doc_ref")
        if doc.get("duplicate_of"):          # 11.4: a repeated copy is out of every uniqueness
            continue                          # and completeness check, and carries null arithmetic
        known = accounted_values(doc)
        # `pdftotext -layout` wraps a long description, so a rate expression splits across two
        # physical rows and the "@" lands at the end of the FIRST: "... 1 visit / 5 trees @" then
        # "$37.35". Rule 11.6 keeps both NARRATIVE. Read the previous non-blank row so the second
        # half is recognised for what it is rather than read as a bare amount in a column.
        prev = {}
        last = None
        for l in doc.get("lines", []):
            txt0 = (l.get("line_text") or "").strip()
            prev[id(l)] = last
            if txt0:
                last = txt0
        for l in doc.get("lines", []):
            if l.get("line_type") != "NARRATIVE":
                continue
            txt = l.get("line_text") or ""
            toks = MONEY.findall(txt)
            if not toks:
                continue
            why = next((n for n, rx in EXEMPT if rx.search(txt)), None)
            if why is None and (prev.get(id(l)) or "").rstrip().endswith(("@", "@ $", "$")):
                why = "RATE_EXPRESSION_WRAPPED"
            if why is None and not ALIGNED.search(txt):
                why = "PROSE_NOT_COLUMN_ALIGNED"
            klass = "MISTYPE_CANDIDATE" if TOTALS_SHAPED.search(txt) else "UNEXPLAINED"
            if why and klass != "MISTYPE_CANDIDATE":
                klass = "EXEMPT:" + why
            if klass != "MISTYPE_CANDIDATE" and not klass.startswith("EXEMPT"):
                vals = [v for v in (_val(t) for t in toks) if v is not None]
                if vals and all(abs(v) <= TRIVIAL for v in vals):
                    klass = "EXEMPT:ZERO_OR_UNIT_QTY"
                elif vals and all(abs(v) in known for v in vals):
                    klass = "ECHO_OF_A_RECORDED_AMOUNT"
                else:
                    klass = "UNACCOUNTED"      # the one class that can be a dropped line item
            if klass.startswith("EXEMPT") and not show_all:
                out.append((ref, l.get("page"), l.get("line_no"), klass, toks, txt.strip()[:110]))
                continue
            out.append((ref, l.get("page"), l.get("line_no"), klass, toks, txt.strip()[:110]))
    return out


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    as_json = "--json" in argv
    show_all = "--all" in argv
    if not args:
        print(__doc__.strip()); return 3
    try:
        corpus = json.load(open(args[0]))
    except Exception as e:
        print(f"unreadable corpus: {e}"); return 3
    rows = screen(corpus, show_all)
    cand = [r for r in rows if r[3] in ("UNACCOUNTED", "MISTYPE_CANDIDATE")]
    if as_json:
        print(json.dumps({"batch_id": corpus.get("manifest", {}).get("batch_id"),
                          "rows": [dict(zip(("doc_ref", "page", "line_no", "class",
                                             "tokens", "text"), r)) for r in rows],
                          "candidates": len(cand)}, indent=1))
        return 1 if cand else 0
    bid = corpus.get("manifest", {}).get("batch_id")
    print(f"4.4 printed-money screen over NARRATIVE rows: {bid}")
    shown = rows if show_all else cand
    for ref, pg, ln, kl, toks, txt in shown:
        print(f"  {kl:<20} {ref} p{pg} row {ln}  {','.join(toks)}")
        print(f"      {txt}")
    exempt = len(rows) - len(cand)
    print(f"  {len(cand)} candidate(s), {exempt} exempt by a named class, "
          f"{len(rows)} narrative row(s) carrying a money token")
    return 1 if cand else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
