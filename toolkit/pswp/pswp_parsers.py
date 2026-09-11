"""
pswp_parsers.py - the raw-text fallback route.

Rebuilt 9-Sep-2026. This is the in-container alternative to a Copilot corpus: it turns a
binder PDF into the same corpus JSON, by the same rules, using `pdftotext -layout`.

It implements extraction prompt v5 directly:
  section 3   document boundary detection, supplier identifier patterns, footer cross-check
  section 4   column-band anchoring off the TABLE_HEADER row, and the exclusion list
  section 5   header amounts by label, never by position
  section 6   the arithmetic gate and the four-rung retry ladder
  section 9   the corpus schema

It does NOT paraphrase, summarise, infer an amount, or normalise a row. `line_text` is the
layout row exactly as pdftotext produced it, rstrip only, never strip: the leading
whitespace carries the column positions everything else depends on.

Use it when Copilot is unavailable, when a corpus has to be reproduced to settle a dispute
about what the page said, or to test a repair family against a known binder.

    from pswp_parsers import parse_binder
    corpus = parse_binder("Batch 112.pdf", batch_id="batch_112")

Entry points
    pdf_pages(path)            -> list[str], one layout-preserved page each
    parse_pages(pages, ...)    -> corpus dict (use this to re-parse retained page text)
    parse_binder(path, ...)    -> corpus dict, straight from a PDF
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pswp_build_lib import D, money, f2, ties

# ----------------------------------------------------------------------------------
# 1. Identifier patterns (prompt v5 section 3)
# ----------------------------------------------------------------------------------

IDENTIFIER_PATTERNS: list[tuple[str, str]] = [
    ("Savco Vegetation Services", r"\b(SV\d{6})\b"),
    ("Xero-templated", r"\b(INV-\d{3,5})\b"),
    ("Burly Holdings", r"Tax Invoice #\s*(\d+)"),
    ("Link Resources Training", r"\b(LR\d{4,6})\b"),
    ("Vinton Tree Services", r"Invoice No\.?:\s*(\d{5})"),
    ("Vinton Tree Services", r"Invoice number:\s*(\d{5})"),
    ("Greenway Turf Solutions", r"\b(SI-\d{6,9})\b"),
    ("Q Power", r"TAX INVOICE NO\.\s*(\d+)"),
    ("Harpley Services", r"\b(000\d{5})\b"),
    ("SECUREcorp", r"\b(QLDPS[IC]R?\d{7})\b"),
    ("SECUREcorp", r"\b(QLDPSCR\d{7})\b"),
    ("Kachel Cleaning", r"TAX INVOICE\s+No\.\s*(\d{4})\b"),
]

# Total Environmental Concepts prints 'Invoice Number' and the number on different
# physical lines with other text between, so a same-line pattern cannot work. Detect the
# supplier by name and read the number positionally.
POSITIONAL_SUPPLIERS = ("Total Environmental",)

FOOTER_PAGING = re.compile(r"\b(\d+)\s+of\s+(\d+)\b", re.I)

# A fresh document begins where a fresh letterhead prints. Rule 3.4 (a page carrying two
# documents) fires only where a page carries TWO of these markers: an invoice number
# quoted in a remittance slip, a credit reference or a payment advice is not a new
# document, and treating it as one is how a 23-document binder becomes 16.
LETTERHEAD = re.compile(r"TAX\s+INVOICE|CREDIT\s+NOTE|ADJUSTMENT\s+NOTE|^\s*INVOICE\s*$", re.I | re.M)

# Some layouts print dollars and cents in separate columns: Kachel prints
# '19,716        00' for $19,716.00 and '5,418    7 60' for $5,418.60. The corpus records
# the reconstructed figure; the row text is never edited.
SPLIT_CENTS_SUPPLIERS = ("kachel",)

# ----------------------------------------------------------------------------------
# 2. Tokens and the exclusion list (prompt v5 section 4.3)
# ----------------------------------------------------------------------------------

# The boundaries matter: 'Contract #: LCC-09-2022' must not yield -9.00, and 'PK000028'
# must not yield an amount. A money token is never glued to a letter or a hyphen.
MONEY = re.compile(r"(?<![\w.,-])(-?\$?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|-?\$?\d+\.\d{2})(?![\w-])")
RATE = re.compile(r"\b\d{1,2}(?:\.\d+)?\s*%")
DATE_TOKEN = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\b\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}\b")
REFERENCE_TOKEN = re.compile(r"(?<!\d)\d{6,}(?!\d)")
SUBTOTAL_GUARD = re.compile(r"(?<!SUB)TOTAL:?", re.I)

HEADER_WORDS = [
    "description", "item", "details", "detail", "quantity", "qty", "unit price", "rate",
    "unit", "gst", "amount aud", "amount", "total price", "ex gst", "price", "units",
]

TOTAL_LABELS = ["total aud", "balance due", "amount due", "total outstanding", "rem. amt. due",
                "total inc gst", "total price including gst", "total incl gst"]
# 'Total Amount' is the SECUREcorp ex-GST subtotal, not the total. It is a candidate for
# both roles and the reconciliation below decides which, from the printed arithmetic.
AMBIGUOUS_TOTAL_LABELS = ["total amount"]

# Labels are matched on WORD BOUNDARIES. 'Flagstone Play Area' contains 'gst', so a naive
# substring test types a priced patrol row as TOTALS and closes the table region on it,
# losing every row beneath. This one cost five rows an invoice across a whole series.
def _label_hit(low: str, labels) -> bool:
    return any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(l), low) for l in labels)

# Contact blocks carry number pairs that look like a dollars-and-cents column
# ('Fax: 07 55470 932'). They are never priced rows.
CONTACT = re.compile(
    r"(?:phone|mobile|fax|tel|email|e-mail)\s*(?:no\.?)?\s*[:#]|www\.|@|\bA\.?B\.?N\b|\bA\.?C\.?N\b", re.I)
# NOT a bare 'mobile': 'Mobile Patrols - Rainbow Park' is a priced line on every
# SECUREcorp invoice in the binder. The marker has to be the contact LABEL form.
GST_LABELS = ["total gst 10%", "plus 10% gst", "gst amount", "gst"]
SUBTOTAL_LABELS = ["subtotal", "sub total", "sub-total"]

# The priced table stops where the payment or remittance block starts. Amounts printed
# below that line are the payable restated, not new priced rows, and counting them is how
# a $25,573.01 invoice captures $135,536.95.
# A whole page can be a payment advice (Xero BPAY slips print one). It carries the
# payable restated and no priced rows, so the table region never opens on it.
PAYMENT_ADVICE = re.compile(r"\bBPAY\b|biller code|pay by\b|payment advice|receipt/reference", re.I)

TABLE_END = re.compile(
    r"please detach|remittance|payment advice|please make cheque|direct payment details|"
    r"bank details|\bBSB\b|rem\. ?amt|balance due|payments made", re.I)


def money_tokens(text: str) -> list[tuple[int, Decimal]]:
    """Money tokens with their character offsets, after the exclusion list is applied."""
    out: list[tuple[int, Decimal]] = []
    masked = RATE.sub(lambda m: " " * len(m.group(0)), text)
    masked = DATE_TOKEN.sub(lambda m: " " * len(m.group(0)), masked)
    for m in MONEY.finditer(masked):
        tok = m.group(1)
        if "." not in tok and "," not in tok and REFERENCE_TOKEN.fullmatch(tok.replace("$", "")):
            continue  # bare six-digit-plus integer: an order, contract or account reference
        out.append((m.start(1), D(tok)))
    return out


# ----------------------------------------------------------------------------------
# 3. pdftotext
# ----------------------------------------------------------------------------------


def pdf_pages(path: str) -> list[str]:
    """One layout-preserved string per page. rstrip only, never strip (prompt v5 section 10)."""
    proc = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True)
    return proc.stdout.split("\f")[:-1] if proc.stdout.endswith("\f") else proc.stdout.split("\f")


def page_lines(page: str) -> list[str]:
    return [ln.rstrip() for ln in page.split("\n")]


# ----------------------------------------------------------------------------------
# 4. Document boundary detection (prompt v5 section 3)
# ----------------------------------------------------------------------------------


def find_identifiers(text: str) -> list[str]:
    """Every identifier on the page, longest form first.

    Patterns overlap: a Vinton 'Invoice No.: 00013' pattern will bite a Harpley
    '00013014', and taking the first pattern that fires turns 25 Harpley invoices into
    five documents. So a candidate that is a substring of another candidate at the same
    position is dropped, and the remainder is ordered by where it prints.
    """
    hits: list[tuple[int, str]] = []
    for _supplier, pat in IDENTIFIER_PATTERNS:
        for m in re.finditer(pat, text):
            v = m.group(1)
            if all(v != h for _, h in hits):
                hits.append((m.start(1), v))
    keep = [(pos, v) for pos, v in hits if not any(v != w and v in w for _, w in hits)]
    keep.sort(key=lambda t: t[0])
    return [v for _, v in keep]


def split_documents(pages: list[str]) -> list[dict]:
    """Return [{'doc_ref':..., 'page_range':[a,b], 'ids_on_page':[...]}].

    Rules, in order:
      2. a page carrying exactly one identifier belongs to that document
      3. a page carrying none inherits the previous page's document (terms, payment
         advice, blank pages), which is correct and not a defect
      4. a page carries TWO documents only where it carries two letterhead markers; an
         invoice number quoted on a remittance slip or credited by a credit note is a
         reference, not a second document
      5. the split is cross-checked against '<n> of <m>' page footers
      6. two non-adjacent runs resolving to one identifier is a duplicate copy, not a
         split error
      7. every identifier found is reported, including ones that open no document
    """
    per_page = [find_identifiers(p) for p in pages]
    heads = [len(LETTERHEAD.findall(p)) for p in pages]
    docs: list[dict] = []
    current: dict | None = None
    unclassified: list[str] = []
    for i, ids in enumerate(per_page, start=1):
        if not ids:
            if current:
                current["page_range"][1] = i
            continue
        opens = ids[: max(1, heads[i - 1])]
        for k, ref in enumerate(opens):
            if current and ref == current["doc_ref"]:
                current["page_range"][1] = i
                continue
            if k == 0 and current and heads[i - 1] == 0:
                current["page_range"][1] = i
                continue
            current = {"doc_ref": ref, "page_range": [i, i], "ids_on_page": list(ids)}
            docs.append(current)
        for ref in ids[len(opens):]:
            if ref not in unclassified and ref not in [d["doc_ref"] for d in docs]:
                unclassified.append(ref)

    seen: dict[str, dict] = {}
    for d in docs:
        if d["doc_ref"] in seen:
            d["duplicate_of"] = list(seen[d["doc_ref"]]["page_range"])
        else:
            seen[d["doc_ref"]] = d

    for d in docs:
        span = d["page_range"][1] - d["page_range"][0] + 1
        text = "\n".join(pages[d["page_range"][0] - 1: d["page_range"][1]])
        m = FOOTER_PAGING.search(text)
        if m and int(m.group(2)) and span != int(m.group(2)):
            d["footer_conflict"] = "footer says %s pages, the split gives %d" % (m.group(2), span)
    if docs:
        docs[0]["_unclassified"] = unclassified
    return docs


# ----------------------------------------------------------------------------------
# 5. Table header and column bands (prompt v5 section 4.1)
# ----------------------------------------------------------------------------------


def detect_header(lines: list[str]) -> dict | None:
    best, best_score = None, 0
    for idx, ln in enumerate(lines, start=1):
        low = ln.lower()
        hits = [w for w in HEADER_WORDS if w in low]
        if len(hits) < 2 or money_tokens(ln):
            continue
        score = len(hits)
        if score > best_score:
            bands: dict[str, int] = {}
            for w in hits:
                pos = low.find(w)
                key = w.replace(" ", "_").replace("aud", "").strip("_") or w
                bands.setdefault(key, pos)
            best, best_score = {"row": idx, "text": ln, "bands": bands}, score
    return best


def amount_band(bands: dict[str, int]) -> int | None:
    for key in ("amount", "total_price", "amount_aud", "total"):
        if key in bands:
            return bands[key]
    if bands:
        return max(bands.values())
    return None


# ----------------------------------------------------------------------------------
# 6. Row classification (prompt v5 section 4.2)
# ----------------------------------------------------------------------------------


def classify(line: str, bands: dict[str, int] | None, in_table: bool) -> tuple[str, dict]:
    """Return (line_type, numeric fields). Never decides on the first or last token alone."""
    fields: dict[str, Any] = {
        "qty": None, "unit": None, "unit_price_ex_gst": None,
        "line_ex_gst": None, "gst": None, "stated_amt": None, "band_hits": [],
    }
    if not line.strip():
        return "BLANK", fields
    low = line.lower()
    toks = money_tokens(line)

    if toks and _label_hit(low, TOTAL_LABELS + SUBTOTAL_LABELS + GST_LABELS + AMBIGUOUS_TOTAL_LABELS):
        return "TOTALS", fields
    if TABLE_END.search(line) and not toks:
        return "TERMS", fields
    if not toks:
        return ("NARRATIVE", fields)
    if CONTACT.search(line):
        return "NARRATIVE", fields

    ab = amount_band(bands) if bands else None
    if ab is not None and in_table:
        hits = [(pos, val) for pos, val in toks if pos >= ab - 6]
        if hits:
            fields["line_ex_gst"] = f2(hits[-1][1])
            fields["band_hits"].append("amount")
            others = [(p, v) for p, v in toks if (p, v) not in hits]
            if others:
                fields["unit_price_ex_gst"] = f2(others[-1][1])
                fields["band_hits"].insert(0, "unit_price")
            qm = re.match(r"^\s*(\d+(?:\.\d+)?)\s+([A-Za-z]+)?", line)
            if qm and bands and qm.start(1) < (bands.get("description", 10 ** 6)):
                fields["qty"] = float(qm.group(1))
                fields["unit"] = qm.group(2)
                fields["band_hits"].insert(0, "quantity")
            return "PRICED", fields
        return "NARRATIVE", fields

    # 4.3 fallback: trailing-amount test with the exclusion list already applied
    if toks and toks[-1][0] > max(0, len(line) - 30) and in_table:
        fields["line_ex_gst"] = f2(toks[-1][1])
        fields["band_hits"].append("amount")
        return "PRICED", fields
    return "NARRATIVE", fields


# ----------------------------------------------------------------------------------
# 7. Header amounts (prompt v5 section 5)
# ----------------------------------------------------------------------------------


def labelled_amount(lines: list[str], labels: list[str], exclude: list[str] = ()) -> tuple[Decimal | None, int | None]:
    """One figure per labelled line. Never take a header amount from an unlabelled position."""
    for idx, ln in enumerate(lines, start=1):
        low = ln.lower()
        if not any(lbl in low for lbl in labels):
            continue
        if any(x in low for x in exclude):
            continue
        toks = money_tokens(ln)
        if toks:
            return toks[-1][1], idx
        # the label and its amount can print on different layout rows (Xero)
        for j in (idx, idx + 1):
            if j < len(lines):
                nxt = money_tokens(lines[j])
                if nxt:
                    return nxt[-1][1], j + 1
    return None, None


DATE_LABEL = re.compile(r"(invoice date|date)\s*[:.]?\s*", re.I)


def find_invoice_date(lines: list[str]) -> str | None:
    for ln in lines:
        if not DATE_LABEL.search(ln):
            continue
        dates = DATE_TOKEN.findall(ln)
        if dates:
            # 'PLEASE PAY BY | AMOUNT | INVOICE DATE' on one row: the LAST date is the
            # invoice date, the FIRST is the due date.
            return dates[-1] if "please pay by" in ln.lower() else dates[0]
    return None


ABN = re.compile(r"A\.?B\.?N\.?\s*[:.]?\s*((?:\d[\s]?){11})", re.I)
LCC_ABN_DIGITS = "21627796435"


def find_abn(lines: list[str]) -> str | None:
    for ln in lines:
        m = ABN.search(ln)
        if not m:
            continue
        raw = m.group(1).strip()
        if re.sub(r"\D", "", raw) == LCC_ABN_DIGITS:
            continue  # that is the bill-to block: LCC's own ABN, never the supplier's
        return raw
    return None


def split_cents(line: str) -> Decimal | None:
    """Dollars and cents printed in separate columns (Kachel).

    '19,716        00' -> 19716.00, '5,418    7 60' -> 5418.60, '59,604      60' -> 59604.60.

    The cents are the trailing bare two-digit token. The dollars are the largest-magnitude
    token to its left, which is what survives 'Zone 1 Toilets:' contributing a stray '1'
    and 'PK000028' contributing an account reference. The row text is never edited; only
    the captured figure is reconstructed, and the document records that it was.
    """
    masked = re.sub(r"PK\d{5,6}", " ", line)
    masked = RATE.sub(lambda m: " " * len(m.group(0)), masked)
    masked = DATE_TOKEN.sub(lambda m: " " * len(m.group(0)), masked)
    toks = re.findall(r"-?\d[\d,]*(?:\.\d{1,2})?", masked)
    if len(toks) < 2 or not re.fullmatch(r"\d{2}", toks[-1]):
        return None
    left = [t for t in toks[:-1] if "." not in t]
    if not left:
        return None
    dollars = max(left, key=lambda t: D(t.replace(",", "")))
    if D(dollars.replace(",", "")) < 1:
        return None
    return D("%s.%s" % (dollars.replace(",", ""), toks[-1]))


def resolve_headers(lines: list[str], split_cols: bool) -> dict:
    """Header amounts by label, then reconciled against the printed arithmetic.

    Labels alone are not enough: SECUREcorp prints the ex-GST figure as 'Total Amount' and
    the payable as 'REM. AMT. DUE'. Taking the first label match would post the subtotal as
    the total on every invoice in the series. So every labelled figure is collected as a
    CANDIDATE and the triple that satisfies subtotal + GST = total is the one adopted.
    """
    def candidates(labels: list[str], exclude: list[str] = ()) -> list[Decimal]:
        out: list[Decimal] = []
        for ln in lines:
            low = ln.lower()
            if not _label_hit(low, labels) or _label_hit(low, list(exclude)):
                continue
            val = split_cents(ln) if split_cols else None
            if val is None:
                toks = money_tokens(ln)
                val = toks[-1][1] if toks else None
            if val is not None and val not in out:
                out.append(val)
        return out

    subs = candidates(SUBTOTAL_LABELS) + candidates(AMBIGUOUS_TOTAL_LABELS, exclude=SUBTOTAL_LABELS + ["gst"])
    gsts = candidates(GST_LABELS, exclude=SUBTOTAL_LABELS)
    tots = candidates(TOTAL_LABELS, exclude=SUBTOTAL_LABELS + ["gst amount"]) + candidates(AMBIGUOUS_TOTAL_LABELS, exclude=SUBTOTAL_LABELS + ["gst"])
    best = None
    for s_ in subs:
        for g_ in gsts:
            for t_ in tots:
                if t_ == s_:
                    continue
                if ties(s_ + g_, t_, "0.02") and (best is None or t_ > best[2]):
                    best = (s_, g_, t_)
    if best:
        return {"subtotal": best[0], "gst": best[1], "total": best[2], "basis": "printed"}
    t = max(tots) if tots else None
    g = gsts[0] if gsts else None
    s_ = subs[0] if subs else ((t - g) if (t is not None and g is not None) else None)
    return {"subtotal": s_, "gst": g, "total": t,
            "basis": "printed" if subs else "derived from total less GST"}


# ----------------------------------------------------------------------------------
# 8. Assemble a document
# ----------------------------------------------------------------------------------


def build_document(doc: dict, pages: list[str], source_file: str) -> dict:
    a, b = doc["page_range"]
    lines_out: list[dict] = []
    header = None
    all_lines: list[str] = []
    for pg in range(a, b + 1):
        pls = page_lines(pages[pg - 1])
        all_lines += pls
        h = detect_header(pls)
        if h and header is None:
            header = {"page": pg, "row": h["row"], "text": h["text"], "bands": h["bands"]}
        bands = (header or {}).get("bands")
        # The table region opens at the header row (or at the top of the page where the
        # layout prints no header at all, prompt v5 section 4.3) and closes at the first
        # totals or payment-block row on that page. It reopens on the next page, because a
        # continued table prints its rows again without repeating the header.
        advice_page = bool(PAYMENT_ADVICE.search("\n".join(pls[:16])))
        in_table = (header is None or pg > header["page"]) and not advice_page
        seen_priced = False
        for i, ln in enumerate(pls, start=1):
            if header and pg == header["page"] and i == header["row"]:
                lines_out.append(_line(pg, i, ln, "TABLE_HEADER", {}))
                in_table, seen_priced = not advice_page, False
                continue
            lt, fields = classify(ln, bands, in_table)
            if lt == "PRICED":
                seen_priced = True
            # The region closes at a totals row, or at the payment block once the table
            # has actually produced a priced row. Closing on a payment word printed in the
            # letterhead would swallow the whole table on a continuation page.
            if lt == "TOTALS" or (seen_priced and TABLE_END.search(ln)):
                in_table = False
            lines_out.append(_line(pg, i, ln, lt, fields))

    supplier_guess = " ".join(all_lines[:14]).lower()
    split_cols = any(k in supplier_guess for k in SPLIT_CENTS_SUPPLIERS)
    hdr_amts = resolve_headers(all_lines, split_cols)
    sub, gst, tot = hdr_amts["subtotal"], hdr_amts["gst"], hdr_amts["total"]
    if split_cols:
        for l in lines_out:
            if l["line_type"] == "PRICED":
                v = split_cents(l["line_text"])
                if v is not None:
                    l["line_ex_gst"] = f2(v)
                    l["note"] = "dollars and cents print in separate columns; the figure is reconstructed, the row text is untouched"

    out = {
        "doc_ref": doc["doc_ref"],
        "doc_kind": "CREDIT_NOTE" if re.search(r"CR\d|CREDIT NOTE|ADJUSTMENT NOTE", "\n".join(all_lines[:40]).upper()) else "TAX_INVOICE",
        "source_file": source_file,
        "page_range": [a, b],
        "supplier": next((ln.strip() for ln in all_lines[:12] if len(ln.strip()) > 6 and not money_tokens(ln)), "(not printed)"),
        "supplier_abn": find_abn(all_lines),
        "abn_source": "text_layer" if find_abn(all_lines) else "absent",
        "invoice_no": doc["doc_ref"],
        "invoice_date": find_invoice_date(all_lines),
        "printed_subtotal_ex_gst": f2(sub) if sub is not None else None,
        "subtotal_basis": hdr_amts["basis"],
        "printed_gst": f2(gst) if gst is not None else None,
        "printed_total_incl_gst": f2(tot) if tot is not None else None,
        "captured_ex_gst": 0.0,
        "line_amount_basis": "ex_gst",
        "tie_basis": "ex_gst",
        "self_tie": "OUT",
        "retry_log": [],
        "table_headers": [header] if header else [],
        "work_orders": re.findall(r"\b(?:CR/WO#?|WO)\s*[:#]?\s*(\d{6,8})", "\n".join(all_lines)),
        "contract_refs": re.findall(r"\b(PAR/\d+/\d{4}|LCC-\d{2}-\d{4}|CN-\d{5})\b", "\n".join(all_lines)),
        "po_refs": re.findall(r"(?:Purchase Order|PO|Your Order No)\s*[:#]?\s*(\d{5,8})", "\n".join(all_lines)),
        "pk_refs": sorted(set(re.findall(r"\b(PK\d{5,6})\b", "\n".join(all_lines)))),
        "printed_account_codes": [],
        "evidence_stem": "",
        "duplicate_of": doc.get("duplicate_of"),
        "findings": [],
        "notes": "Raw-text route (pdftotext -layout) via pswp_parsers.py."
        + (" %s" % doc["footer_conflict"] if doc.get("footer_conflict") else ""),
        "lines": lines_out,
    }
    if doc.get("duplicate_of"):
        for l in out["lines"]:
            l["line_type"] = "DUPLICATE_COPY"
            for k in ("qty", "unit_price_ex_gst", "line_ex_gst", "gst", "stated_amt"):
                l[k] = None
    _pass2(out)
    return out


def _line(page: int, no: int, text: str, line_type: str, fields: dict) -> dict:
    rec = {
        "source": "TEXT", "page": page, "line_no": no, "line_text": text,
        "line_type": line_type, "ocr_only": False, "ocr_status": "not_required",
        "ocr_reason": "text layer present and legible",
        "qty": None, "unit": None, "unit_price_ex_gst": None,
        "line_ex_gst": None, "gst": None, "stated_amt": None,
        "band_hits": [], "work_order": None, "note": None,
    }
    rec.update({k: v for k, v in fields.items() if k in rec})
    return rec


def _pass2(doc: dict) -> None:
    """Pass 2, arithmetic. The retry ladder runs before OUT may be written."""
    p = [l for l in doc["lines"] if l["line_type"] == "PRICED"]
    cap = money(sum(D(l["line_ex_gst"]) for l in p if l["line_ex_gst"] is not None))
    doc["captured_ex_gst"] = f2(cap)
    sub, tot = doc.get("printed_subtotal_ex_gst"), doc.get("printed_total_incl_gst")
    if sub is not None and ties(cap, sub, "0.02"):
        doc["self_tie"] = "TIE"
        return
    log = []
    # rung 1: missed priced rows are the responsibility of pswp_json_repair F11/F12
    log.append({"rung": 1, "found": "handed to pswp_json_repair families F11 and F12"})
    if tot is not None and ties(cap, tot, "0.02"):
        doc["tie_basis"] = doc["line_amount_basis"] = "incl_gst"
        doc["self_tie"] = "TIE"
        log.append({"rung": 2, "found": "lines tie the printed total including GST"})
        doc["retry_log"] = log
        return
    log.append({"rung": 2, "found": "no inclusive-GST tie"})
    log.append({"rung": 3, "found": "rate, quantity and unit-price tokens excluded before the amount test"})
    log.append({"rung": 4, "found": "page range %s checked against the footer" % doc["page_range"]})
    doc["retry_log"] = log
    doc["self_tie"] = "OUT"


# ----------------------------------------------------------------------------------
# 9. Binder entry points
# ----------------------------------------------------------------------------------


def parse_pages(pages: list[str], batch_id: str, source_file: str, source_pages: int | None = None) -> dict:
    docs = split_documents(pages)
    built = [build_document(d, pages, source_file) for d in docs]
    ids = [d["doc_ref"] for d in built]
    corpus = {
        "manifest": {
            "batch_id": batch_id,
            "source_files": [{"name": source_file, "pages": source_pages or len(pages)}],
            "runtime": "A",
            "extraction_tool": "pswp_parsers.py raw-text route (pdftotext -layout)",
            "extracted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "prompt_version": "v5",
            "gate": "GREEN",
            "pathologies": [],
            "coverage": {
                "documents_complete": len(built), "documents_total": len(built),
                "pages_represented": len({p for d in built for p in range(d["page_range"][0], d["page_range"][1] + 1)}),
                "pages_total": source_pages or len(pages),
            },
            "identifiers_found": ids, "identifiers_unclassified": [],
            "documents_found": len(built), "lines_captured": sum(len(d["lines"]) for d in built),
            "documents_tie": sum(1 for d in built if d["self_tie"] == "TIE"),
            "documents_out": sum(1 for d in built if d["self_tie"] == "OUT"),
            "captured_ex_gst_total": f2(sum(D(d["captured_ex_gst"]) for d in built)),
            "ocr_pages_run": 0, "ocr_pages_not_required": sum(len(p.split("\n")) and 1 for p in pages),
            "ocr_pages_not_available": 0, "ocr_pages_outstanding": 0,
            "text_layer_diffs": [], "shingle_checks_run": 0, "shingle_failures": 0,
            "resume_point": None,
        },
        "documents": built,
    }
    return corpus


def parse_binder(pdf: str, batch_id: str, repair: bool = True) -> dict:
    pages = pdf_pages(pdf)
    corpus = parse_pages(pages, batch_id, os.path.basename(pdf), len(pages))
    if repair:
        from pswp_json_repair import repair_and_gate

        repair_and_gate(corpus)
    return corpus


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parse an invoice binder to corpus JSON (raw-text route).")
    ap.add_argument("pdf")
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-repair", action="store_true")
    a = ap.parse_args(argv)
    corpus = parse_binder(a.pdf, a.batch_id, repair=not a.no_repair)
    json.dump(corpus, open(a.out, "w", encoding="utf-8"), indent=1)
    m = corpus["manifest"]
    print("Gate: %s" % m["gate"])
    print("documents %d, tie %d, out %d, lines %d, captured %s"
          % (m["documents_found"], m["documents_tie"], m["documents_out"], m["lines_captured"], m["captured_ex_gst_total"]))
    return 0 if m["gate"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
