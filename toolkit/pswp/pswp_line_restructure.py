#!/usr/bin/env python3
"""
pswp_line_restructure.py - the F9 companion, aggregate-line rebuild.

Rebuilt 9-Sep-2026. It exists for one failure: an extraction that captures a whole invoice
as ONE priced line equal to the printed subtotal, on a face that plainly itemises. The
document ties, the gate goes green, and rule 16 is broken anyway, because a summary row in
place of line capture is a critical failure whether or not the arithmetic works.

`pswp_json_repair.py` family F9 detects the shape and calls `rebuild_items()` here.

THE SAFETY RULE, AND WHY IT IS ABSOLUTE
The rebuild REPLACES the aggregate only when the rebuilt items sum EXACTLY to it, to the
cent, with no tolerance. Anything else and the original capture is returned unchanged with
a finding attached. A rebuild that nearly ties is a rebuild that has invented or dropped a
line, and shipping it would put fabricated detail behind a green check.

HOW IT REBUILDS
Only from what the corpus already holds: the retained `line_text` of the rows the extractor
typed NARRATIVE inside the table region. It reads amounts at the amount band recorded on
the TABLE_HEADER row, or, where no header was captured, at the trailing-amount position,
with the section 4.3 exclusion list applied so rates, quantities, dates, phone numbers and
six-digit references are never read as money.

It never opens the PDF, never re-runs OCR, and never derives an amount by subtraction. If
the rows are not in the corpus, the answer is that the invoice needs re-capture, not that
the script should guess.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal
from typing import Any

from pswp_build_lib import D, money, f2, fmt, ties

MONEY = re.compile(r"(?<![\w.,-])(-?\$?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|-?\$?\d+\.\d{2})(?![\w-])")
RATE = re.compile(r"\b\d{1,2}(?:\.\d+)?\s*%")
DATE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")
REFERENCE = re.compile(r"(?<!\d)\d{6,}(?!\d)")
CONTACT = re.compile(r"(?:phone|mobile|fax|tel|email|e-mail)\s*(?:no\.?)?\s*[:#]|www\.|@|\bA\.?B\.?N\b|\bA\.?C\.?N\b", re.I)
TOTALISH = re.compile(r"(?<![a-z])(sub ?total|total|gst|balance due|amount due|payments made|rem\. ?amt)(?![a-z])", re.I)
QTY_HEAD = re.compile(r"^\s*(\d+(?:\.\d+)?)\s+([A-Za-z]+)?")


def _tokens(text: str) -> list[tuple[int, Decimal]]:
    masked = RATE.sub(lambda m: " " * len(m.group(0)), text)
    masked = DATE.sub(lambda m: " " * len(m.group(0)), masked)
    out = []
    for m in MONEY.finditer(masked):
        tok = m.group(1).replace("$", "")
        if "." not in tok and "," not in tok and REFERENCE.fullmatch(tok):
            continue
        out.append((m.start(1), D(tok.replace(",", ""))))
    return out


def _band_start(v):
    """A band is a single offset under extraction prompt v6 and a [start, end] SPAN under v7 (4.1). The test
    downstream is `token start >= band - 6`, so the scalar wanted is the span's left edge. Reading a v7 corpus
    without this raises `unsupported operand type(s) for -: 'list' and 'int'` inside the F9 rebuild."""
    if isinstance(v, (list, tuple)):
        return v[0] if v else None
    return v


def _amount_band(doc: dict) -> int | None:
    for h in doc.get("table_headers") or []:
        bands = (h or {}).get("bands") or {}
        for key in ("amount", "total_price", "amount_aud", "total"):
            if key in bands:
                return _band_start(bands[key])
        if bands:
            starts = [b for b in (_band_start(v) for v in bands.values()) if isinstance(b, (int, float))]
            if starts:
                return max(starts)
    return None


def _split_cents(text: str) -> Decimal | None:
    """Dollars and cents in separate columns (the Kachel layout).

    Reused from pswp_parsers so the rebuild can read a face whose amount column is split.
    Which reading is right is settled by the tie, not by a guess about the vendor.
    """
    from pswp_parsers import split_cents

    return split_cents(text)


def candidate_rows(doc: dict, split_cols: bool = False) -> list[dict]:
    """Rows that could be printed items: inside the table, amount-bearing, not a total.

    A row whose amount equals the printed total, subtotal or GST is the payable restated,
    not an item. Remittance slips and payment advices print it two or three times, and
    counting those is how a rebuild silently doubles an invoice.
    """
    band = _amount_band(doc)
    restated = {money(D(doc.get(k))) for k in
                ("printed_total_incl_gst", "printed_subtotal_ex_gst", "printed_gst")
                if doc.get(k) is not None}
    out = []
    for l in doc.get("lines", []):
        if l.get("line_type") not in ("NARRATIVE", "PRICED"):
            continue
        text = l.get("line_text") or ""
        if not text.strip() or CONTACT.search(text) or TOTALISH.search(text):
            continue
        toks = _tokens(text)
        if split_cols:
            v = _split_cents(text)
            if v is None:
                continue
            if money(v) in restated:
                continue
            out.append({"line": l, "amount": v, "unit": None,
                        "qty": float(QTY_HEAD.match(text).group(1)) if QTY_HEAD.match(text) and QTY_HEAD.match(text).start(1) < 20 else None})
            continue
        if not toks:
            continue
        if band is not None:
            hits = [t for t in toks if t[0] >= band - 6]
            if not hits:
                continue
            amount = hits[-1][1]
            unit = toks[-2][1] if len(toks) >= 2 and toks[-2][0] < band - 6 else None
        else:
            if toks[-1][0] < max(0, len(text.rstrip()) - 30):
                continue
            amount = toks[-1][1]
            unit = toks[-2][1] if len(toks) >= 2 else None
        qty = None
        qm = QTY_HEAD.match(text)
        if qm and qm.start(1) < 20:
            qty = float(qm.group(1))
        if money(amount) in restated:
            continue
        out.append({"line": l, "amount": amount, "unit": unit, "qty": qty})
    return out


def rebuild_items(doc: dict) -> list[dict] | None:
    """Return a full replacement `lines` list, or None if the rebuild does not tie exactly.

    Called by pswp_json_repair family F9. The aggregate row is dropped and each printed
    item becomes its own PRICED record; every other row keeps its captured type, so the
    document still holds one record per printed physical row.
    """
    priced = [l for l in doc.get("lines", []) if l.get("line_type") == "PRICED"]
    if len(priced) != 1:
        return None
    aggregate = priced[0]
    target = D(doc.get("printed_subtotal_ex_gst"))
    # Two readings of the amount column: the ordinary one, and the split dollars/cents
    # layout. Whichever ties EXACTLY is the right one; if neither does, nothing is written.
    cands = None
    for split_cols in (False, True):
        c = [x for x in candidate_rows(doc, split_cols) if x["line"] is not aggregate]
        if len(c) >= 2 and ties(money(sum(x["amount"] for x in c)), target, "0.00"):
            cands = c
            break
    if cands is None:
        return None

    new_lines = []
    for l in doc["lines"]:
        if l is aggregate:
            continue  # the aggregate is replaced by the items it stood for
        hit = next((c for c in cands if c["line"] is l), None)
        if hit:
            l = dict(l)
            l["line_type"] = "PRICED"
            l["line_ex_gst"] = f2(hit["amount"])
            if hit["unit"] is not None:
                l["unit_price_ex_gst"] = f2(hit["unit"])
            if hit["qty"] is not None:
                l["qty"] = hit["qty"]
            l["band_hits"] = [k for k, v in (("quantity", hit["qty"]), ("unit_price", hit["unit"]), ("amount", hit["amount"])) if v is not None]
            l["note"] = ("F9 aggregate rebuild: this printed item was captured only inside a single "
                         "summary line; restated from its own retained page text, and the rebuilt items "
                         "sum exactly to the captured aggregate")
        new_lines.append(l)
    return new_lines


def restructure(corpus: dict, log=print) -> dict:
    """Run the rebuild across a corpus. Reports what changed and what it declined to touch."""
    changed, declined = [], []
    for doc in corpus.get("documents", []):
        priced = [l for l in doc.get("lines", []) if l.get("line_type") == "PRICED"]
        if len(priced) != 1 or doc.get("printed_subtotal_ex_gst") is None:
            continue
        if not ties(D(priced[0].get("line_ex_gst") or 0), doc["printed_subtotal_ex_gst"], "0.00"):
            continue
        rebuilt = rebuild_items(doc)
        if rebuilt:
            doc["lines"] = rebuilt
            n = len([l for l in rebuilt if l["line_type"] == "PRICED"])
            changed.append((doc["doc_ref"], n))
        else:
            declined.append(doc["doc_ref"])
            doc.setdefault("findings", []).append({
                "code": "F9",
                "detail": ("Captured as one aggregate line equal to the printed subtotal. The retained page "
                           "text does not carry item rows that sum exactly to it, so no rebuild was made. "
                           "The invoice needs line-level re-capture before it can be Confirmed."),
                "amount": f2(doc["printed_subtotal_ex_gst"]),
            })
    log("restructure: rebuilt %d, declined %d" % (len(changed), len(declined)))
    for ref, n in changed:
        log("  %s rebuilt into %d printed items" % (ref, n))
    for ref in declined:
        log("  %s declined, flagged for re-capture" % ref)
    return corpus


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Rebuild aggregate-captured invoices into their printed items.")
    ap.add_argument("corpus")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    corpus = json.load(open(a.corpus, encoding="utf-8"))
    restructure(corpus)
    if a.out:
        json.dump(corpus, open(a.out, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
