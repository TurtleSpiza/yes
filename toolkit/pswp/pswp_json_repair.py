"""
pswp_json_repair.py - corpus repair families F1 to F13, and the gate.

Rebuilt 9-Sep-2026. This file is authoritative for the family list (schema section 10).

Standing position, and the reason this script exists: an extraction corpus is evidence of
what the page printed, so a repair may only RESTATE something already present in the
retained text (rule 19.2). No family here infers an amount, adjusts a figure to make a tie
work, or edits line_text. A repair that cannot be justified from the row's own retained
text is not a repair, it is a fabrication, and the family declines it and raises a
pathology instead.

FAMILIES
  F1  header amounts: derive a null subtotal as total less GST, take the total from a
      Balance Due / Amount Due label, never from Subtotal
  F2  number hygiene: quoted amounts, '$', thousands separators, more than two decimals (P8)
  F3  supplier ABN: LCC's own ABN 21 627 796 435 read out of the bill-to block (P4)
  F4  doc_ref hygiene: leading zeros preserved, TechOne C-image id kept out of doc_ref
  F5  page ranges: gaps, and overlaps beyond the single page section 3.4 permits (P9); tested per source file when a corpus carries several
  F6  the 4.4 invariant: PRICED iff an amount is present, asserted both ways (P2)
  F7  duplicate doc_ref with neither copy marked duplicate_of (P7)
  F8  credit notes: sign convention, doc_kind
  F9  aggregate-line capture: one PRICED line equal to the whole subtotal where the page
      text shows an itemised table. The dominant extraction failure. Rebuild is delegated
      to pswp_line_restructure.py and REPLACES only when the rebuilt sum ties exactly
  F10 GST rate read as an amount: a '10%' token landing in line_ex_gst
  F11 column-header token bleed: a TABLE_HEADER row typed TOTALS, header tokens inside a
      priced row's numeric fields
  F12 wrapped-description head: SECUREcorp-style rows where a printed line wraps over
      several physical rows, the rate and amount printing on the first row and the
      quantity on the second. Typed NARRATIVE by the extractor, so the amounts are lost
  F13 evidence stems: 40 characters, the amount is NEVER trimmed, unique across the batch
  F14 the 4.5 residue on a document the extractor did not parse at all: where a document has
      NO priced line and a non-zero printed subtotal (the P1 shape), a NARRATIVE row whose
      last money token starts inside the item table's own `amount` band is that row's amount,
      and the row is retyped PRICED. Scoped to the P1 shape on purpose: it cannot touch a
      document that already carries priced lines, so it can never move a tie that holds
  F16 a ZERO-amount row inside the item table typed NARRATIVE. Section 4.4 asserts
      PRICED iff an amount is present, and $0.00 is an amount that is present, so the
      row is P2 as it stands. Retyping it moves no value by construction, which is why
      the family is scoped to zero: it can never turn a tie into an OUT or back
  F15 repeated copy inside ONE page_range: a binder that prints the same invoice twice in a
      row, where the extractor emitted one document over both copies and counted the amounts
      twice. The second half is retyped DUPLICATE_COPY and recorded in duplicate_copy_pages,
      the treatment binder11111 already carries. Declines where either is already marked

GATE
  RED   any unresolved P1 to P9
  AMBER a declared partial run carrying a resume_point
  GREEN everything ties and every invariant holds

A corpus that fails any of its own gates is logged, held and NOT part-built from
(rule 19.2, v122 precedent corpus_mix1).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pswp_build_lib import D, money, gst_of, ties, f2, fmt

LCC_ABN_DIGITS = "21627796435"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

MONEY_TOKEN = re.compile(r"(?<![\d.,])-?\$?\d{1,3}(?:,\d{3})*\.\d{2}(?![\d])")
RATE_TOKEN = re.compile(r"\b\d{1,2}(?:\.\d+)?\s*%")
# F12: a wrapped head sits inside the detail band, carries no quantity token, and ends
# with exactly two money tokens (the rate band and the amount band).
F12_HEAD = re.compile(r"^\s{40,}\S.*?\s{2,}(-?[\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})\s*$")
F12_QTY = re.compile(r"^\s+(\d+(?:\.\d+)?)\s+(Months?|Each|Hours?|Units?|Weeks?|Visits?)\s*$", re.I)
C_IMAGE = re.compile(r"\bC\d{6,}\b")


@dataclass
class Repair:
    family: str
    doc_ref: str
    detail: str
    amount: Decimal = Decimal("0")


@dataclass
class Pathology:
    code: str
    doc_ref: str
    page: int
    detail: str

    def as_dict(self) -> dict:
        return {"code": self.code, "doc_ref": self.doc_ref, "page": self.page, "detail": self.detail}


@dataclass
class GateResult:
    gate: str
    pathologies: list[Pathology] = field(default_factory=list)
    repairs: list[Repair] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def recovered(self) -> Decimal:
        return sum((r.amount for r in self.repairs), Decimal("0"))


# ----------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------


def priced(doc: dict) -> list[dict]:
    return [l for l in doc.get("lines", []) if l.get("line_type") == "PRICED"]


def line_amount(l: dict) -> Decimal | None:
    for k in ("line_ex_gst", "stated_amt"):
        if l.get(k) is not None:
            return D(l[k])
    return None


def captured(doc: dict) -> Decimal:
    return money(sum((line_amount(l) or Decimal("0")) for l in priced(doc)))


def is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ----------------------------------------------------------------------------------
# F2 number hygiene (P8 prevention)
# ----------------------------------------------------------------------------------

NUM_DOC = ("printed_subtotal_ex_gst", "printed_gst", "printed_total_incl_gst", "captured_ex_gst")
NUM_LINE = ("qty", "unit_price_ex_gst", "line_ex_gst", "gst", "stated_amt")


def f2_number_hygiene(doc: dict, out: GateResult) -> None:
    for k in NUM_DOC:
        v = doc.get(k)
        if v is None or is_number(v):
            continue
        doc[k] = f2(v)
        out.repairs.append(Repair("F2", doc.get("doc_ref", "?"), "header %s was %r, emitted as a JSON number" % (k, v)))
    for l in doc.get("lines", []):
        for k in NUM_LINE:
            v = l.get(k)
            if v is None or is_number(v):
                continue
            if isinstance(v, str) and not re.search(r"\d", v):
                l[k] = None
                continue
            l[k] = f2(v)
            out.repairs.append(
                Repair("F2", doc.get("doc_ref", "?"), "line %s %s was %r, emitted as a JSON number" % (l.get("line_no"), k, v))
            )


# ----------------------------------------------------------------------------------
# F1 header amounts
# ----------------------------------------------------------------------------------


def f1_headers(doc: dict, out: GateResult) -> None:
    sub, gst, tot = doc.get("printed_subtotal_ex_gst"), doc.get("printed_gst"), doc.get("printed_total_incl_gst")
    ref = doc.get("doc_ref", "?")
    if sub is None and tot is not None and gst is not None:
        doc["printed_subtotal_ex_gst"] = f2(D(tot) - D(gst))
        doc["subtotal_basis"] = "derived from total less GST"
        out.repairs.append(Repair("F1", ref, "subtotal derived as total less GST"))
    if tot is None and sub is not None and gst is not None:
        doc["printed_total_incl_gst"] = f2(D(sub) + D(gst))
        out.repairs.append(Repair("F1", ref, "total derived as subtotal plus GST, restated from the printed pair"))
    if gst is None and sub is not None and tot is not None:
        doc["printed_gst"] = f2(D(tot) - D(sub))
        out.repairs.append(Repair("F1", ref, "GST derived as total less subtotal"))
    s, g, t = doc.get("printed_subtotal_ex_gst"), doc.get("printed_gst"), doc.get("printed_total_incl_gst")
    if None not in (s, g, t) and not ties(D(s) + D(g), t, "0.02"):
        out.notes.append(
            "%s: printed subtotal %s plus printed GST %s does not equal the printed total %s. Left as printed."
            % (ref, fmt(s), fmt(g), fmt(t))
        )


# ----------------------------------------------------------------------------------
# F3 supplier ABN
# ----------------------------------------------------------------------------------


def f3_abn(doc: dict, out: GateResult) -> None:
    abn = doc.get("supplier_abn") or ""
    if re.sub(r"\D", "", abn) == LCC_ABN_DIGITS:
        doc["supplier_abn"] = None
        doc["abn_source"] = "absent"
        doc.setdefault("findings", []).append(
            {"code": "F1", "detail": "The captured ABN was Logan City Council's own bill-to ABN, not the supplier's. Cleared; the supplier ABN must be read from the letterhead or footer.", "amount": 0.00}
        )
        out.repairs.append(Repair("F3", doc.get("doc_ref", "?"), "LCC bill-to ABN removed from supplier_abn"))


# ----------------------------------------------------------------------------------
# F4 doc_ref hygiene
# ----------------------------------------------------------------------------------


def f4_doc_ref(doc: dict, out: GateResult) -> None:
    ref = str(doc.get("doc_ref", ""))
    inv = str(doc.get("invoice_no", "") or "")
    if inv and inv != ref and inv.lstrip("0") == ref.lstrip("0") and len(inv) > len(ref):
        doc["doc_ref"] = inv
        out.repairs.append(Repair("F4", ref, "doc_ref restored to the printed form %s, leading zeros kept" % inv))
    if C_IMAGE.fullmatch(ref):
        doc.setdefault("notes", "")
        doc["notes"] = (doc["notes"] + " ").strip() + " TechOne document image id %s moved out of doc_ref." % ref
        out.repairs.append(Repair("F4", ref, "TechOne C-image id was sitting in doc_ref"))


# ----------------------------------------------------------------------------------
# F8 credit notes
# ----------------------------------------------------------------------------------


def f8_credit_notes(doc: dict, out: GateResult) -> None:
    ref = str(doc.get("doc_ref", ""))
    kind = doc.get("doc_kind")
    looks_credit = bool(re.search(r"CR\d|CREDIT|ADJUSTMENT", ref.upper())) or kind == "CREDIT_NOTE"
    if not looks_credit:
        return
    doc["doc_kind"] = "CREDIT_NOTE"
    if D(doc.get("printed_total_incl_gst") or 0) > 0:
        for k in NUM_DOC:
            if doc.get(k) is not None:
                doc[k] = f2(-abs(D(doc[k])))
        for l in priced(doc):
            for k in ("line_ex_gst", "stated_amt", "gst"):
                if l.get(k) is not None:
                    l[k] = f2(-abs(D(l[k])))
        out.repairs.append(Repair("F8", ref, "credit note carried positive amounts; signs restated negative"))


# ----------------------------------------------------------------------------------
# F10 GST rate read as amount
# ----------------------------------------------------------------------------------


def f10_rate_as_amount(doc: dict, out: GateResult) -> None:
    for l in priced(doc):
        amt = line_amount(l)
        if amt is None:
            continue
        txt = l.get("line_text", "")
        if amt in (Decimal("10"), Decimal("0.1")) and RATE_TOKEN.search(txt):
            toks = [t for t in MONEY_TOKEN.findall(txt)]
            if toks:
                l["line_ex_gst"] = f2(toks[-1].replace("$", "").replace(",", ""))
                out.repairs.append(
                    Repair("F10", doc.get("doc_ref", "?"), "line %s carried the GST rate as its amount; recomputed from the amount band" % l.get("line_no"), D(l["line_ex_gst"]))
                )


# ----------------------------------------------------------------------------------
# F11 column-header token bleed
# ----------------------------------------------------------------------------------

HEADER_TOKENS = ("description", "quantity", "unit price", "amount", "qty", "rate", "details", "item")


def f11_header_bleed(doc: dict, out: GateResult) -> None:
    for l in doc.get("lines", []):
        txt = (l.get("line_text") or "").lower()
        hits = sum(1 for t in HEADER_TOKENS if t in txt)
        if hits >= 3 and l.get("line_type") in ("TOTALS", "NARRATIVE", "PRICED") and not MONEY_TOKEN.search(txt):
            l["line_type"] = "TABLE_HEADER"
            for k in NUM_LINE:
                l[k] = None
            out.repairs.append(
                Repair("F11", doc.get("doc_ref", "?"), "row %s was the table header typed %s; retyped TABLE_HEADER" % (l.get("line_no"), l.get("line_type")))
            )


# ----------------------------------------------------------------------------------
# F12 wrapped-description head
# ----------------------------------------------------------------------------------


def f12_wrapped(doc: dict, out: GateResult) -> None:
    """Reclassify NARRATIVE to PRICED where the row is the head of a wrapped printed line.

    Fires only when ALL of the following hold, so it cannot invent a priced line:
      1. the row begins inside the detail band (character 40 or later) with no quantity token
      2. the row ends with exactly two money tokens, the rate band and the amount band
      3. the next non-blank row is a bare '<n> Months|Each|Hours' quantity row

    line_text is never touched. The quantity row and any description-tail row stay
    NARRATIVE (prompt v5 rule 11.6): one record per printed physical row.
    """
    lines = doc.get("lines", [])
    for i, l in enumerate(lines):
        if l.get("line_type") != "NARRATIVE":
            continue
        m = F12_HEAD.match(l.get("line_text") or "")
        if not m:
            continue
        qty, qrow = None, None
        for j in range(i + 1, min(i + 4, len(lines))):
            if lines[j].get("line_type") == "BLANK":
                continue
            q = F12_QTY.match(lines[j].get("line_text") or "")
            if q:
                qty, qrow = float(q.group(1)), lines[j].get("line_no")
            break
        if qty is None:
            continue
        rate = D(m.group(1).replace(",", ""))
        amt = D(m.group(2).replace(",", ""))
        l["line_type"] = "PRICED"
        l["qty"] = qty
        l["unit_price_ex_gst"] = f2(rate)
        l["line_ex_gst"] = f2(amt)
        l["band_hits"] = ["unit_price", "amount"]
        l["note"] = (
            "F12 wrapped printed line: the description continues on the following rows and the "
            "quantity %g prints on row %s of the same printed line. Restated from retained page text."
            % (qty, qrow)
        )
        out.repairs.append(
            Repair("F12", doc.get("doc_ref", "?"), "row %s reclassified NARRATIVE to PRICED" % l.get("line_no"), amt)
        )


# ----------------------------------------------------------------------------------
# F9 aggregate-line capture
# ----------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------
# F14 the 4.5 residue on an unparsed document (the P1 shape)
# ----------------------------------------------------------------------------------

# The header word marks where its column starts; a right-aligned figure can begin a little
# before it. Six characters is the slack the Play Force and Savco layouts need and is far
# narrower than the gap to the next band left, so it cannot pull in a unit price.
AMOUNT_BAND_SLACK = 6


def _item_table_bounds(doc: dict):
    """(page, header_row, first_totals_row) for the item table.

    `line_no` restarts on every page, so a document whose second page is a payment advice
    carries low line numbers again there. Bounding a row by min() across the whole document
    therefore excludes the item table itself. Both bounds are taken on the item table's OWN
    page, and a row is only considered when it sits on that page."""
    page = header = None
    for th in doc.get("table_headers") or []:
        if th and th.get("row"):
            page, header = th.get("page"), th["row"]
            break
    if header is None:
        return None, None, None
    totals = [l.get("line_no") or 0 for l in doc.get("lines", [])
              if l.get("line_type") == "TOTALS" and l.get("page") == page and (l.get("line_no") or 0) > header]
    return page, header, (min(totals) if totals else None)


def _in_item_table(l: dict, page, header, first_total) -> bool:
    if page is not None and l.get("page") != page:
        return False
    n = l.get("line_no") or 0
    if header and n <= header:
        return False
    if first_total and n >= first_total:
        return False
    return True


def _amount_band(doc: dict) -> int | None:
    for th in doc.get("table_headers") or []:
        b = (th or {}).get("bands") or {}
        if is_number(b.get("amount")):
            return int(b["amount"])
    return None


def f14_residue(doc: dict, out: GateResult) -> None:
    """Retype the item row on a document the extractor left with no priced line at all.

    This restates, it does not infer: the band offsets come from the document's own printed
    header row, and the amount is the token already sitting in that band on that row. Where
    the band is absent the family declines, because then there is nothing to read the column
    off and P11 is the answer, not a guess."""
    sub = doc.get("printed_subtotal_ex_gst")
    if priced(doc) or doc.get("duplicate_of") or sub is None or D(sub) == 0:
        return
    band = _amount_band(doc)
    if band is None:
        return
    page, header_row, first_total = _item_table_bounds(doc)
    for l in doc.get("lines", []):
        if l.get("line_type") != "NARRATIVE" or not _in_item_table(l, page, header_row, first_total):
            continue
        toks = list(MONEY_TOKEN.finditer(l.get("line_text") or ""))
        if len(toks) < 2 or toks[-1].start() < band - AMOUNT_BAND_SLACK:
            continue
        l["line_type"] = "PRICED"
        l["line_ex_gst"] = f2(toks[-1].group().replace("$", "").replace(",", ""))
        out.repairs.append(
            Repair("F14", doc.get("doc_ref", "?"), "row %s carried its amount in the item table's amount band and was typed NARRATIVE; retyped PRICED" % l.get("line_no"), D(l["line_ex_gst"]))
        )


# ----------------------------------------------------------------------------------
# F16 zero-amount row inside the item table
# ----------------------------------------------------------------------------------


def f16_zero_row(doc: dict, out: GateResult) -> None:
    """Retype a $0.00 row sitting inside the item table from NARRATIVE to PRICED.

    Heritage prints a `1   0.00` row above each priced crew row, carrying the site and
    scope block. It is an amount-bearing row typed NARRATIVE, so assess() raises P2 and the
    corpus is RED, on a document that ties to the cent. The amount is zero, so the 4.4
    invariant is satisfied by typing it PRICED and nothing else changes: captured() sums the
    priced rows and this one adds nothing. The family declines any non-zero amount, which is
    F14's territory and a real arithmetic question rather than a typing one."""
    band = _amount_band(doc)
    if band is None or doc.get("duplicate_of"):
        return
    page, header_row, first_total = _item_table_bounds(doc)
    for l in doc.get("lines", []):
        if l.get("line_type") != "NARRATIVE" or not _in_item_table(l, page, header_row, first_total):
            continue
        toks = list(MONEY_TOKEN.finditer(l.get("line_text") or ""))
        if not toks or toks[-1].start() < band - AMOUNT_BAND_SLACK:
            continue
        if D(toks[-1].group().replace("$", "").replace(",", "")) != 0:
            continue
        l["line_type"] = "PRICED"
        l["line_ex_gst"] = f2("0")
        out.repairs.append(
            Repair("F16", doc.get("doc_ref", "?"), "row %s is a $0.00 row inside the item table typed NARRATIVE; retyped PRICED (4.4), which moves no value" % l.get("line_no"), Decimal("0"))
        )


# ----------------------------------------------------------------------------------
# F15 repeated copy inside one page_range
# ----------------------------------------------------------------------------------


def _page_rows(doc: dict, lo: int, hi: int) -> list[str]:
    return [(l.get("line_text") or "").rstrip() for l in doc.get("lines", [])
            if lo <= (l.get("page") or 0) <= hi]


def f15_repeated_copy(doc: dict, out: GateResult) -> None:
    """A binder that prints one invoice twice, emitted as a single document over both copies.

    Declines where either copy is already marked: binder11111 carries this treatment correctly
    on 19827 and 19997, and a family that fired there would un-tie two documents that hold."""
    pr = doc.get("page_range") or []
    if len(pr) != 2 or doc.get("duplicate_of") or doc.get("duplicate_copy_pages"):
        return
    span = pr[1] - pr[0] + 1
    if span < 2 or span % 2:
        return
    n = span // 2
    if any(l.get("line_type") == "DUPLICATE_COPY" for l in doc.get("lines", [])):
        return
    first, second = _page_rows(doc, pr[0], pr[0] + n - 1), _page_rows(doc, pr[0] + n, pr[1])
    if not first or first != second:
        return
    pages = list(range(pr[0] + n, pr[1] + 1))
    for l in doc.get("lines", []):
        if (l.get("page") or 0) in pages:
            l["line_type"] = "DUPLICATE_COPY"
    doc["duplicate_copy_pages"] = pages
    out.repairs.append(
        Repair("F15", doc.get("doc_ref", "?"), "pages %s repeat pages %s verbatim; retyped DUPLICATE_COPY and recorded, so the amounts are counted once" % (pages, list(range(pr[0], pr[0] + n))))
    )


def f9_aggregate(doc: dict, out: GateResult) -> None:
    """One PRICED line carrying the whole subtotal where the page clearly itemises.

    The rebuild lives in pswp_line_restructure.py and replaces the aggregate ONLY when the
    rebuilt items sum EXACTLY to the aggregate. Without that module present the family
    flags and does not touch the corpus: an aggregate that ties is a capture weakness, not
    an arithmetic defect, and silently splitting it would be invention.
    """
    p = priced(doc)
    if len(p) != 1:
        return
    sub = doc.get("printed_subtotal_ex_gst")
    if sub is None or not ties(line_amount(p[0]) or 0, sub, "0.00"):
        return
    itemised = sum(1 for l in doc.get("lines", []) if l.get("line_type") == "NARRATIVE" and MONEY_TOKEN.search(l.get("line_text") or ""))
    if itemised < 2:
        return
    try:
        from pswp_line_restructure import rebuild_items  # optional companion
    except Exception:
        out.notes.append(
            "%s: F9 candidate, a single priced line equal to the whole subtotal alongside %d amount-bearing narrative rows. "
            "pswp_line_restructure.py is not on the path, so the corpus was left as captured and the invoice is flagged for line-level re-capture."
            % (doc.get("doc_ref", "?"), itemised)
        )
        doc.setdefault("findings", []).append(
            {"code": "F9", "detail": "Captured as one aggregate line; the face itemises. Rule 16 needs line-level capture before this invoice is Confirmed.", "amount": f2(sub)}
        )
        return
    rebuilt = rebuild_items(doc)
    if rebuilt and ties(sum(D(r["line_ex_gst"]) for r in rebuilt), sub, "0.00"):
        doc["lines"] = rebuilt
        out.repairs.append(Repair("F9", doc.get("doc_ref", "?"), "aggregate line rebuilt into %d printed items" % len(rebuilt)))


# ----------------------------------------------------------------------------------
# F13 evidence stems
# ----------------------------------------------------------------------------------


def _mon_year(s: str) -> str:
    for f in ("%d/%m/%Y", "%d/%m/%y", "%d-%b-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            dt = datetime.strptime(str(s).strip(), f)
            return "%s-%d" % (MONTHS[dt.month - 1], dt.year)
        except ValueError:
            continue
    return str(s or "").strip()


def f13_stems(corpus: dict, out: GateResult) -> None:
    """Business Name, What it was For, Date, Amount. 40 characters. Unique in the batch.

    Degrade in this order and NEVER trim the amount: full date, then Mon-YYYY, then a
    shorter purpose, then a shorter business name. A stem cut through its amount
    ('SECUREcorp, mobile patrols, 06-2025, 281') is the failure this family exists for.
    """
    seen: dict[str, str] = {}
    for doc in corpus.get("documents", []):
        if doc.get("duplicate_of"):
            continue  # a repeated copy shares its original's stem by design; it is never captured
        ref = str(doc.get("doc_ref", ""))
        stem = str(doc.get("evidence_stem") or "")
        amt = "%.2f" % D(doc.get("printed_total_incl_gst") or 0)
        ok = stem.endswith(amt) and len(stem) <= 40
        if not ok:
            parts = [p.strip() for p in stem.split(",")]
            name = (parts[0] if parts else (doc.get("supplier") or "Vendor"))[:18]
            purpose = parts[1] if len(parts) > 2 else "invoice"
            my = _mon_year(doc.get("invoice_date"))
            for cand in (
                "%s, %s, %s, %s" % (name, purpose, my, amt),
                "%s, %s, %s, %s" % (name, purpose[:8], my, amt),
                "%s, %s, %s" % (name, my, amt),
                "%s, %s" % (name[:12], amt),
            ):
                if len(cand) <= 40:
                    break
            doc["evidence_stem"] = cand
            out.repairs.append(Repair("F13", ref, "stem rebuilt: %r -> %r" % (stem, cand)))
            stem = cand
        if stem in seen:
            # Break the collision with the invoice-number suffix, then fit 40 characters by shortening the NAME.
            # Slicing the whole candidate is what produced an over-long stem here before: cand[:40] can cut through
            # the amount, and refusing that slice used to leave the untrimmed candidate in place, so the stem failed
            # the length rule instead of the amount rule. The amount and the suffix are never touched.
            tie = "%s %s" % (stem.split(",")[0], ref[-3:])
            my = _mon_year(doc.get("invoice_date"))
            cand = "%s, %s, %s" % (tie, my, amt)
            while len(cand) > 40 and len(tie) > len(ref[-3:]) + 1:
                tie = tie[:-1].rstrip()
                cand = "%s, %s, %s" % (tie, my, amt)
            if len(cand) > 40:
                cand = "%s, %s" % (tie, amt)
            doc["evidence_stem"] = cand
            out.repairs.append(Repair("F13", ref, "stem collided with %s; broken by invoice-number suffix" % seen[stem]))
            stem = doc["evidence_stem"]
        seen[stem] = ref


# ----------------------------------------------------------------------------------
# arithmetic gate and pathologies
# ----------------------------------------------------------------------------------


def retie(doc: dict, out: GateResult) -> None:
    """Recompute captured, then run the ladder rungs that are decidable from the corpus."""
    if doc.get("duplicate_of"):
        # prompt v6 11.4: a separate record for a repeated copy carries duplicate_of, every row DUPLICATE_COPY and
        # no arithmetic; it is not re-tied and not counted as OUT.
        doc["captured_ex_gst"] = f2(captured(doc))
        doc["self_tie"] = "TIE"
        return
    cap = captured(doc)
    doc["captured_ex_gst"] = f2(cap)
    sub = doc.get("printed_subtotal_ex_gst")
    tot = doc.get("printed_total_incl_gst")
    if sub is not None and ties(cap, sub, "0.02"):
        doc["self_tie"], doc["tie_basis"] = "TIE", "ex_gst"
        return
    if tot is not None and ties(cap, tot, "0.02"):
        doc["self_tie"], doc["tie_basis"] = "TIE", "incl_gst"
        doc["line_amount_basis"] = "incl_gst"
        out.repairs.append(Repair("R2", doc.get("doc_ref", "?"), "rung 2: lines are GST-inclusive; tie basis set to incl_gst"))
        return
    doc["self_tie"] = "OUT"


def assess(corpus: dict) -> list[Pathology]:
    pats: list[Pathology] = []
    seen_refs: dict[str, dict] = {}
    for doc in corpus.get("documents", []):
        ref = str(doc.get("doc_ref", "?"))
        p = priced(doc)
        sub = doc.get("printed_subtotal_ex_gst")
        pr = doc.get("page_range") or [0, 0]
        if sub is not None and D(sub) != 0 and not p and not doc.get("duplicate_of"):
            pats.append(Pathology("P1", ref, pr[0], "printed subtotal %s with zero priced lines" % fmt(sub)))
        for l in p:
            if line_amount(l) is None:
                pats.append(Pathology("P2", ref, l.get("page", 0), "PRICED line %s carries no amount" % l.get("line_no")))
        for l in doc.get("lines", []):
            if l.get("line_type") == "NARRATIVE" and F12_HEAD.match(l.get("line_text") or ""):
                pats.append(Pathology("P2", ref, l.get("page", 0), "amount-bearing row %s typed NARRATIVE" % l.get("line_no")))
        if doc.get("supplier_abn") and re.sub(r"\D", "", str(doc["supplier_abn"])) == LCC_ABN_DIGITS:
            pats.append(Pathology("P4", ref, pr[0], "supplier_abn is the LCC bill-to ABN"))
        if doc.get("printed_total_incl_gst") is None:
            pats.append(Pathology("P5", ref, pr[0], "no printed total captured"))
        pages = {l.get("page") for l in doc.get("lines", [])}
        resume = (corpus.get("manifest", {}).get("resume_point") or {})
        resume_page = resume.get("page", 10 ** 9) if isinstance(resume, dict) else 10 ** 9
        for pg in range(pr[0], pr[1] + 1):
            if pg not in pages and pg < resume_page:
                pats.append(Pathology("P3", ref, pg, "page inside a completed document carries no line records"))
        for k in NUM_DOC:
            if doc.get(k) is not None and not is_number(doc[k]):
                pats.append(Pathology("P8", ref, pr[0], "%s emitted as %r" % (k, doc[k])))
        if ref in seen_refs and not (doc.get("duplicate_of") or seen_refs[ref].get("duplicate_of")):
            pats.append(Pathology("P7", ref, pr[0], "second document with this doc_ref and neither marked duplicate_of"))
        seen_refs[ref] = doc
    m = corpus.get("manifest", {})
    if m.get("runtime") == "A" and int(m.get("ocr_pages_outstanding") or 0) > 0:
        pats.append(Pathology("P6", "-", 0, "%s OCR pages outstanding" % m.get("ocr_pages_outstanding")))
    # P9 page coverage across the binder. A corpus may carry several source files (one attachment PDF per document,
    # branch batch attach_1): coverage and overlap are then tested per source file, never across files.
    sfs = [sf for sf in (m.get("source_files") or []) if isinstance(sf, dict)]
    pages_of = {str(sf.get("file")): int(sf.get("pages") or 0) for sf in sfs}
    groups: dict[str, list] = {}
    for d in corpus.get("documents", []):
        key = str(d.get("source_file")) if len(sfs) > 1 else "-"
        groups.setdefault(key, []).append(tuple(d.get("page_range") or [0, 0]))
    for key, spans in groups.items():
        spans = sorted(spans)
        total = pages_of.get(key, 0) if key != "-" else max([0] + list(pages_of.values()))
        covered: set[int] = set()
        for a, b in spans:
            covered |= set(range(a, b + 1))
        if total:
            missing = sorted(set(range(1, total + 1)) - covered)
            if missing:
                pats.append(Pathology("P9", key, missing[0], "pages not covered by any page_range: %s" % missing))
        for i in range(1, len(spans)):
            prev, cur = spans[i - 1], spans[i]
            if cur[0] < prev[1]:  # more than the single shared page 3.4 allows
                pats.append(Pathology("P9", key, cur[0], "page ranges %s and %s overlap by more than one page" % (prev, cur)))
    return pats


# ----------------------------------------------------------------------------------
# entry point
# ----------------------------------------------------------------------------------


def repair_and_gate(corpus: dict, families: str = "all") -> GateResult:
    """Repair in place, then gate. Returns the gate result; corpus is mutated."""
    out = GateResult(gate="GREEN")
    run = (lambda f: True) if families == "all" else (lambda f: f in families.split(","))
    for doc in corpus.get("documents", []):
        if run("F2"):
            f2_number_hygiene(doc, out)
        if run("F11"):
            f11_header_bleed(doc, out)
        if run("F12"):
            f12_wrapped(doc, out)
        if run("F10"):
            f10_rate_as_amount(doc, out)
        if run("F15"):
            f15_repeated_copy(doc, out)
        if run("F1"):
            f1_headers(doc, out)
        if run("F3"):
            f3_abn(doc, out)
        if run("F4"):
            f4_doc_ref(doc, out)
        if run("F8"):
            f8_credit_notes(doc, out)
        if run("F9"):
            f9_aggregate(doc, out)
        if run("F14"):
            f14_residue(doc, out)
        if run("F16"):
            f16_zero_row(doc, out)
        retie(doc, out)
    if run("F13"):
        f13_stems(corpus, out)

    out.pathologies = assess(corpus)
    m = corpus.setdefault("manifest", {})
    docs = corpus.get("documents", [])
    m["documents_tie"] = sum(1 for d in docs if d.get("self_tie") == "TIE")
    m["documents_out"] = sum(1 for d in docs if d.get("self_tie") == "OUT")
    m["documents_found"] = len(docs)
    m["lines_captured"] = sum(len(d.get("lines", [])) for d in docs)
    m["captured_ex_gst_total"] = f2(sum((D(d.get("captured_ex_gst") or 0) for d in docs), Decimal("0")))
    m["pathologies"] = [p.as_dict() for p in out.pathologies]
    if out.pathologies:
        out.gate = "RED"
    elif m.get("resume_point"):
        out.gate = "AMBER"
    else:
        out.gate = "GREEN"
    m["gate"] = out.gate
    if out.repairs:
        m.setdefault("repair_log", []).append(
            {
                "tool": "pswp_json_repair.py",
                "utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
                "repairs": ["%s %s: %s" % (r.family, r.doc_ref, r.detail) for r in out.repairs],
            }
        )
    return out


def rule16_check(corpus: dict) -> list[str]:
    """Rule 16(b): every invoice's captured lines reconcile to its printed target."""
    bad = []
    for doc in corpus.get("documents", []):
        if doc.get("duplicate_of"):
            continue  # repeated copy, outside the arithmetic (prompt v6 11.4)
        basis = doc.get("tie_basis", "ex_gst")
        target = doc.get("printed_total_incl_gst") if basis == "incl_gst" else doc.get("printed_subtotal_ex_gst")
        if not ties(captured(doc), target, "0.02"):
            bad.append("%s: captured %s against printed %s (%s basis)" % (doc.get("doc_ref"), fmt(captured(doc)), fmt(target), basis))
    return bad


def report(corpus: dict, res: GateResult) -> str:
    m = corpus.get("manifest", {})
    out = ["Gate: %s" % res.gate, "", "# Repair and gate report, %s" % m.get("batch_id", "(no batch id)"), ""]
    out.append("- Documents: %s, at TIE %s, at OUT %s" % (m.get("documents_found"), m.get("documents_tie"), m.get("documents_out")))
    out.append("- Captured ex GST total: %s" % fmt(m.get("captured_ex_gst_total")))
    out.append("- Repairs applied: %d, value restated %s" % (len(res.repairs), fmt(res.recovered)))
    by_family: dict[str, int] = {}
    for r in res.repairs:
        by_family[r.family] = by_family.get(r.family, 0) + 1
    if by_family:
        out.append("- By family: " + ", ".join("%s %d" % kv for kv in sorted(by_family.items())))
    out.append("")
    out.append("## Pathologies")
    out.append("")
    if res.pathologies:
        for p in res.pathologies:
            out.append("- %s, %s, page %s: %s" % (p.code, p.doc_ref, p.page, p.detail))
    else:
        out.append("None.")
    bad = rule16_check(corpus)
    out += ["", "## Rule 16 reconciliation", ""]
    out += ["- " + b for b in bad] if bad else ["Every invoice reconciles to its printed target."]
    if res.notes:
        out += ["", "## Notes", ""] + ["- " + n for n in res.notes]
    if res.repairs:
        out += ["", "## Repair log", ""]
        out += ["- %s, %s: %s" % (r.family, r.doc_ref, r.detail) for r in res.repairs]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Repair and gate a PS/WP extraction corpus.")
    ap.add_argument("corpus")
    ap.add_argument("--out", help="write the repaired corpus here")
    ap.add_argument("--report", help="write the markdown report here")
    ap.add_argument("--families", default="all", help="comma list, e.g. F12,F13")
    ap.add_argument("--strict", action="store_true", help="exit 1 unless the gate is GREEN")
    a = ap.parse_args(argv)

    corpus = json.load(open(a.corpus, encoding="utf-8"))
    res = repair_and_gate(corpus, a.families)
    if a.out:
        json.dump(corpus, open(a.out, "w", encoding="utf-8"), indent=1)
    txt = report(corpus, res)
    if a.report:
        open(a.report, "w", encoding="utf-8").write(txt)
    print(txt if not a.report else txt.splitlines()[0])
    return 1 if (a.strict and res.gate != "GREEN") else 0


if __name__ == "__main__":
    sys.exit(main())
